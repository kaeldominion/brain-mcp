"""FastMCP application: tool registration, auth middleware, redacted logging.

Authorization is enforced here in the server — before any tool executes —
never solely in Traefik or in agent prompts. ``health_check`` is the only
unauthenticated tool and returns nothing sensitive.
"""

from __future__ import annotations

import contextvars
import functools
import json
import logging
import os
import re
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

from brain_mcp import __version__
from brain_mcp.api import register_api
from brain_mcp.audit import Auditor
from brain_mcp.auth import Client
from brain_mcp.config import BrainConfig, load_config
from brain_mcp.errors import BrainError
from brain_mcp.notes import VaultService
from brain_mcp.ratelimit import RateLimiter
from brain_mcp.registry import ClientRegistry
from brain_mcp.search import SearchEngine

DEFAULT_CONFIG_PATH = "/config/brain.config.yaml"

_current_client: contextvars.ContextVar[Client | None] = contextvars.ContextVar(
    "brain_mcp_client", default=None
)

# Matches Authorization header values and prefixed token shapes (deploy_client_hex).
_TOKEN_RX = re.compile(r"(?i)\bbearer\s+\S+|\b\w+_\w+_[0-9a-f]{16,}\b")


class RedactionFilter(logging.Filter):
    """Scrubs bearer tokens and token-shaped strings from every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if _TOKEN_RX.search(message):
            record.msg = _TOKEN_RX.sub("[REDACTED]", message)
            record.args = ()
        return True


def _install_redaction() -> None:
    logging.getLogger().addFilter(RedactionFilter())
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastmcp", "mcp"):
        logging.getLogger(name).addFilter(RedactionFilter())


def _tool_error(e: BrainError) -> ToolError:
    return ToolError(json.dumps(e.to_dict(), ensure_ascii=False))


class AuthMiddleware(Middleware):
    def __init__(self, registry: ClientRegistry, limiter: RateLimiter):
        self.registry = registry
        self.limiter = limiter

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.message.name != "health_check":
            try:
                headers = get_http_headers()
                client = self.registry.authenticate(headers.get("authorization"))
                self.limiter.check(client.name)
            except BrainError as e:
                raise _tool_error(e) from e
            _current_client.set(client)
        return await call_next(context)


def _client() -> Client:
    client = _current_client.get()
    if client is None:  # unreachable when middleware is installed
        raise ToolError(json.dumps({"error": "UNAUTHORIZED", "message": "not authenticated"}))
    return client


def build_server(config_path: str | Path | None = None) -> FastMCP:
    config: BrainConfig = load_config(
        config_path or os.environ.get("BRAIN_CONFIG", DEFAULT_CONFIG_PATH)
    )
    registry = ClientRegistry.from_config(config, os.environ)
    auditor = Auditor(config.audit_dir)
    service = VaultService(config, audit_hook=auditor.record)
    search_engine = SearchEngine(config)
    limiter = RateLimiter(config.limits.requests_per_minute)

    _install_redaction()

    mcp = FastMCP(
        name="Company 2nd Brain",
        instructions=(
            "Shared company knowledge vault. Read '_System/AI Agent Instructions.md' "
            "before writing. Search before answering company questions; read notes "
            "before modifying them; unverified information goes to your inbox."
        ),
    )
    mcp.add_middleware(AuthMiddleware(registry, limiter))

    def guard(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except BrainError as e:
                raise _tool_error(e) from e

        return wrapper

    register_api(mcp, config, registry, service, limiter)

    @mcp.custom_route("/health", methods=["GET"])
    async def health_route(request):
        from starlette.responses import JSONResponse

        return JSONResponse(
            {"version": __version__, "vault_mounted": config.vault_root.is_dir()}
        )

    @mcp.tool
    def health_check() -> dict:
        """Unauthenticated liveness check. Returns version, vault mount state, time."""
        import datetime as dt

        return {
            "version": __version__,
            "vault_mounted": config.vault_root.is_dir(),
            "time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    @mcp.tool
    @guard
    def search_notes(query: str, folder: str | None = None, limit: int = 20) -> dict:
        """Search the vault. Returns path, title, excerpt, headings, modified per hit."""
        return {"results": search_engine.search(service.perms, _client(), query, folder, limit)}

    @mcp.tool
    @guard
    def read_note(path: str) -> dict:
        """Read a note. Returns content plus the hash needed for section updates."""
        return service.read_note(_client(), path)

    @mcp.tool
    @guard
    def read_note_section(path: str, heading: str) -> dict:
        """Read one section of a note by its heading text."""
        return service.read_note_section(_client(), path, heading)

    @mcp.tool
    @guard
    def list_directory(path: str = "/") -> dict:
        """List a vault directory ('/' is the vault root)."""
        return {"entries": service.list_directory(_client(), path)}

    @mcp.tool
    @guard
    def list_recent_changes(days: int = 7, limit: int = 50) -> dict:
        """List recently modified notes you can read, newest first."""
        return {"changes": service.list_recent_changes(_client(), days, limit)}

    @mcp.tool
    @guard
    def create_note(path: str, content: str) -> dict:
        """Create a new note (fails if it exists). Frontmatter is injected automatically."""
        return service.create_note(_client(), path, content)

    @mcp.tool
    @guard
    def append_to_note(path: str, content: str, expected_hash: str | None = None) -> dict:
        """Append to an existing note. Optionally guard with expected_hash."""
        return service.append_to_note(_client(), path, content, expected_hash)

    @mcp.tool
    @guard
    def update_note_section(path: str, heading: str, content: str, expected_hash: str) -> dict:
        """Replace one section's body. expected_hash (from read_note) is required;
        a stale hash returns a CONFLICT error instead of overwriting."""
        return service.update_note_section(_client(), path, heading, content, expected_hash)

    @mcp.tool
    @guard
    def add_inbox_item(agent_name: str, title: str, content: str) -> dict:
        """File an unverified item into your own inbox under '90 Staff Inbox'."""
        return service.add_inbox_item(_client(), agent_name, title, content)

    @mcp.tool
    @guard
    def move_note(source: str, destination: str) -> dict:
        """Move a note within the vault (destination must not exist)."""
        return service.move_note(_client(), source, destination)

    @mcp.tool
    @guard
    def rename_note(source: str, destination: str) -> dict:
        """Admin-only: rename a note."""
        return service.rename_note(_client(), source, destination)

    @mcp.tool
    @guard
    def archive_note(path: str) -> dict:
        """Admin-only: move a note into _Archive (nothing is hard-deleted)."""
        return service.archive_note(_client(), path)

    @mcp.tool
    @guard
    def restore_note(path: str) -> dict:
        """Admin-only: restore a previously archived note to its original path."""
        return service.restore_note(_client(), path)

    @mcp.tool
    @guard
    def set_note_status(path: str, status: str) -> dict:
        """Admin-only: set a note's frontmatter status ('unverified' or 'canonical')."""
        return service.set_note_status(_client(), path, status)

    return mcp


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    server = build_server()
    server.run(
        transport="http",
        host=os.environ.get("BRAIN_HOST", "0.0.0.0"),
        port=int(os.environ.get("BRAIN_PORT", "8000")),
        path="/mcp",
    )


if __name__ == "__main__":
    main()
