"""Admin/console REST API (v1.1).

Mounted as custom routes on the same app as the MCP endpoint. Everything the
web console shows or does goes through here — it never touches the vault
filesystem. Only clients holding the ``admin`` or built-in ``console`` role
may call these routes (agents get 403); ``/api/health`` is public and returns
nothing sensitive.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import frontmatter
from starlette.requests import Request
from starlette.responses import JSONResponse

from brain_mcp import __version__
from brain_mcp.auth import Client
from brain_mcp.config import BrainConfig
from brain_mcp.errors import AuthError, BrainError, NotFound, PermissionDenied
from brain_mcp.notes import VaultService
from brain_mcp.permissions import ADMIN_ROLE, CONSOLE_ROLE
from brain_mcp.ratelimit import RateLimiter
from brain_mcp.registry import ClientRegistry

INBOX_DIR = "90 Staff Inbox"


def _error_response(e: BrainError) -> JSONResponse:
    status = {
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "ALREADY_EXISTS": 409,
        "CONFLICT": 409,
        "INVALID_PATH": 400,
        "INVALID_ARGUMENT": 400,
        "TOO_LARGE": 413,
        "RATE_LIMITED": 429,
    }.get(e.code, 500)
    return JSONResponse(e.to_dict(), status_code=status)


def register_api(
    mcp,
    config: BrainConfig,
    registry: ClientRegistry,
    service: VaultService,
    limiter: RateLimiter,
    search_engine=None,
) -> None:
    def guard(fn):
        """Authenticate + authorize (admin/console only), map errors to JSON."""

        async def handler(request: Request):
            try:
                client = registry.authenticate(request.headers.get("authorization"))
                if client.role not in (ADMIN_ROLE, CONSOLE_ROLE):
                    raise PermissionDenied("admin or console role required")
                limiter.check(client.name)
                return await fn(request, client)
            except BrainError as e:
                return _error_response(e)

        handler.__name__ = fn.__name__
        return handler

    def _iter_notes():
        for dirpath, dirnames, filenames in os.walk(config.vault_root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "_Archive"]
            for fn in filenames:
                if fn.startswith(".") or not fn.endswith(".md"):
                    continue
                p = Path(dirpath) / fn
                yield p, p.relative_to(config.vault_root).as_posix()

    @mcp.custom_route("/api/health", methods=["GET"])
    async def api_health(request: Request):
        return JSONResponse(
            {
                "version": __version__,
                "vault_mounted": config.vault_root.is_dir(),
                "time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    @mcp.custom_route("/api/stats", methods=["GET"])
    @guard
    async def api_stats(request: Request, client: Client):
        by_folder: dict[str, int] = {}
        total = unverified = inbox = 0
        for p, rel in _iter_notes():
            total += 1
            top = rel.split("/", 1)[0]
            by_folder[top] = by_folder.get(top, 0) + 1
            try:
                meta = frontmatter.loads(p.read_text(encoding="utf-8", errors="replace")).metadata
            except Exception:
                meta = {}
            if meta.get("status") == "unverified":
                unverified += 1
            if rel.startswith(f"{INBOX_DIR}/"):
                inbox += 1
        return JSONResponse(
            {
                "notes_total": total,
                "unverified": unverified,
                "inbox_items": inbox,
                "by_folder": dict(sorted(by_folder.items())),
            }
        )

    @mcp.custom_route("/api/review", methods=["GET"])
    @guard
    async def api_review(request: Request, client: Client):
        items = []
        for p, rel in _iter_notes():
            try:
                post = frontmatter.loads(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            is_inbox = rel.startswith(f"{INBOX_DIR}/")
            if post.metadata.get("status") != "unverified" and not is_inbox:
                continue
            title = None
            for line in post.content.splitlines():
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break
            items.append(
                {
                    "path": rel,
                    "title": title,
                    "kind": "inbox" if is_inbox else "unverified",
                    "author_agent": post.metadata.get("author_agent"),
                    "created": str(post.metadata.get("created", "")),
                    "modified": dt.datetime.fromtimestamp(
                        p.stat().st_mtime, tz=dt.timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )
        items.sort(key=lambda i: i["modified"], reverse=True)
        return JSONResponse({"items": items})

    @mcp.custom_route("/api/note", methods=["GET"])
    @guard
    async def api_note(request: Request, client: Client):
        path = request.query_params.get("path", "")
        return JSONResponse(service.read_note(client, path))

    @mcp.custom_route("/api/list", methods=["GET"])
    @guard
    async def api_list(request: Request, client: Client):
        path = request.query_params.get("path", "/")
        return JSONResponse({"entries": service.list_directory(client, path)})

    @mcp.custom_route("/api/search", methods=["GET"])
    @guard
    async def api_search(request: Request, client: Client):
        q = request.query_params.get("q", "").strip()
        if not q:
            return JSONResponse({"results": []})
        folder = request.query_params.get("folder") or None
        limit = min(int(request.query_params.get("limit", 20)), 100)
        return JSONResponse({"results": search_engine.search(service.perms, client, q, folder, limit)})

    @mcp.custom_route("/api/graph", methods=["GET"])
    @guard
    async def api_graph(request: Request, client: Client):
        """Nodes = notes; edges = resolved [[wikilinks]] — the mind-graph view."""
        import re as _re

        notes: list[dict] = []
        title_map: dict[str, str] = {}
        stem_map: dict[str, str] = {}
        contents: dict[str, str] = {}
        for p, rel in _iter_notes():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            post_meta: dict = {}
            try:
                post = frontmatter.loads(text)
                post_meta = post.metadata
                body = post.content
            except Exception:
                body = text
            title = None
            for line in body.splitlines():
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break
            stem = Path(rel).stem
            title = title or stem
            notes.append(
                {
                    "id": rel,
                    "title": title,
                    "folder": rel.split("/", 1)[0],
                    "status": post_meta.get("status"),
                }
            )
            contents[rel] = body
            title_map.setdefault(title.lower(), rel)
            stem_map.setdefault(stem.lower(), rel)

        edges = []
        seen = set()
        for rel, body in contents.items():
            for raw in _re.findall(r"\[\[([^\]|#]+)", body):
                key = raw.strip().lower()
                target = title_map.get(key) or stem_map.get(key)
                if target and target != rel and (rel, target) not in seen:
                    seen.add((rel, target))
                    edges.append({"source": rel, "target": target})
        degree: dict[str, int] = {}
        for e in edges:
            degree[e["source"]] = degree.get(e["source"], 0) + 1
            degree[e["target"]] = degree.get(e["target"], 0) + 1
        for n in notes:
            n["links"] = degree.get(n["id"], 0)
        return JSONResponse({"nodes": notes, "edges": edges})

    @mcp.custom_route("/api/notes/promote", methods=["POST"])
    @guard
    async def api_promote(request: Request, client: Client):
        body = await request.json()
        return JSONResponse(service.set_note_status(client, body.get("path", ""), "canonical"))

    @mcp.custom_route("/api/notes/archive", methods=["POST"])
    @guard
    async def api_archive(request: Request, client: Client):
        body = await request.json()
        return JSONResponse(service.archive_note(client, body.get("path", "")))

    @mcp.custom_route("/api/clients", methods=["GET"])
    @guard
    async def api_clients_list(request: Request, client: Client):
        return JSONResponse(
            {
                "clients": [
                    {"name": c.name, "role": c.role, "source": c.source}
                    for c in registry.list_clients()
                ]
            }
        )

    @mcp.custom_route("/api/clients", methods=["POST"])
    @guard
    async def api_clients_create(request: Request, client: Client):
        body = await request.json()
        token = registry.add_client(
            str(body.get("name", "")),
            str(body.get("role", "")),
            deploy_prefix=str(body.get("deploy_prefix", "brain")),
        )
        return JSONResponse({"name": body.get("name"), "role": body.get("role"), "token": token})

    @mcp.custom_route("/api/clients/{name}/rotate", methods=["POST"])
    @guard
    async def api_clients_rotate(request: Request, client: Client):
        name = request.path_params["name"]
        deploy_prefix = "brain"
        try:
            body = await request.json()
            deploy_prefix = str(body.get("deploy_prefix", "brain"))
        except Exception:
            pass
        return JSONResponse({"name": name, "token": registry.rotate_client(name, deploy_prefix)})

    @mcp.custom_route("/api/clients/{name}", methods=["DELETE"])
    @guard
    async def api_clients_delete(request: Request, client: Client):
        registry.remove_client(request.path_params["name"])
        return JSONResponse({"removed": request.path_params["name"]})

    @mcp.custom_route("/api/audit", methods=["GET"])
    @guard
    async def api_audit(request: Request, client: Client):
        q = request.query_params
        limit = min(int(q.get("limit", 200)), 1000)
        log = config.audit_dir / "audit.jsonl"
        events = []
        if log.exists():
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in reversed(lines):
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if q.get("client") and e.get("client") != q["client"]:
                    continue
                if q.get("tool") and e.get("tool") != q["tool"]:
                    continue
                if q.get("ok") and str(e.get("ok")).lower() != q["ok"].lower():
                    continue
                if q.get("path_prefix") and not str(e.get("path", "")).startswith(q["path_prefix"]):
                    continue
                events.append(e)
                if len(events) >= limit:
                    break
        return JSONResponse({"events": events})
