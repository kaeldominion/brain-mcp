"""Note operations: the implementation behind every vault MCP tool.

All writes go through a per-file lock, re-read the latest content inside the
lock, validate optional/required expected hashes, and land via temp-file +
atomic rename. Nothing here ever hard-deletes; archive moves under _Archive/.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Optional

import frontmatter

from brain_mcp.auth import Client
from brain_mcp.config import BrainConfig
from brain_mcp.permissions import ADMIN_ROLE, CONSOLE_ROLE
from brain_mcp.errors import (
    AlreadyExists,
    Conflict,
    InvalidArgument,
    NotFound,
    PermissionDenied,
    TooLarge,
)
from brain_mcp.locking import LockManager
from brain_mcp.paths import VaultJail
from brain_mcp.permissions import PermissionEngine

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_NOTE_STATUSES = {"unverified", "canonical"}

AuditHook = Callable[[dict[str, Any]], None]


def content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip()
    slug = re.sub(r"\s+", " ", slug)
    return slug or "untitled"


class VaultService:
    def __init__(self, config: BrainConfig, audit_hook: Optional[AuditHook] = None):
        self.config = config
        self.jail = VaultJail(config.vault_root)
        self.perms = PermissionEngine(config.roles)
        self.locks = LockManager()
        self._audit_hook = audit_hook

    # ---- internals -------------------------------------------------------

    def _audit(
        self,
        client: Client,
        tool: str,
        path: str,
        ok: bool,
        *,
        before_hash: str | None = None,
        after_hash: str | None = None,
        error: str | None = None,
    ) -> None:
        if self._audit_hook is None:
            return
        self._audit_hook(
            {
                "ts": _utcnow(),
                "client": client.name,
                "owner": client.owner,
                "role": client.role,
                "tool": tool,
                "path": path,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "ok": ok,
                "error": error,
            }
        )

    def _guarded(self, client: Client, tool: str, action: str, rel_path: str) -> Path:
        """Permission + jail check; denied attempts are audited before raising."""
        try:
            abs_path = self.jail.resolve(rel_path)
            self.perms.require(client.name, client.role, action, rel_path)
        except Exception as e:
            if action == "write":
                self._audit(client, tool, rel_path, ok=False, error=str(e))
            raise
        return abs_path

    def _read_text(self, abs_path: Path, rel_path: str) -> str:
        if not abs_path.is_file():
            raise NotFound(f"note not found: {rel_path}", path=rel_path)
        try:
            return abs_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise InvalidArgument(f"note is not valid UTF-8: {rel_path}") from e

    def _check_size(self, text: str, rel_path: str) -> None:
        size = len(text.encode("utf-8"))
        if size > self.config.limits.max_note_bytes:
            raise TooLarge(
                f"note exceeds max size ({size} > {self.config.limits.max_note_bytes} bytes)",
                path=rel_path,
            )

    def _atomic_write(self, abs_path: Path, text: str) -> None:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=abs_path.parent, prefix=".tmp-", suffix=".swp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, abs_path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _require_admin(self, client: Client, tool: str, rel_path: str) -> None:
        if client.role not in (ADMIN_ROLE, CONSOLE_ROLE):
            err = PermissionDenied(f"{tool} is admin-only", path=rel_path, action="write")
            self._audit(client, tool, rel_path, ok=False, error=err.message)
            raise err

    @staticmethod
    def _find_section(lines: list[str], heading: str) -> tuple[int, int]:
        """Return (heading_line_index, end_index_exclusive) for a heading."""
        target = heading.strip().lstrip("#").strip()
        start = level = None
        for i, line in enumerate(lines):
            m = _HEADING.match(line)
            if not m:
                continue
            if start is None:
                if m.group(2).strip() == target:
                    start, level = i, len(m.group(1))
            elif len(m.group(1)) <= level:
                return start, i
        if start is None:
            raise NotFound(f"heading not found: {heading!r}")
        return start, len(lines)

    def _result(self, rel_path: str, text: str, abs_path: Path) -> dict[str, Any]:
        return {
            "path": rel_path,
            "hash": content_hash(text),
            "modified": dt.datetime.fromtimestamp(
                abs_path.stat().st_mtime, tz=dt.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ---- read tools ------------------------------------------------------

    def read_note(self, client: Client, path: str) -> dict[str, Any]:
        abs_path = self.jail.resolve(path)
        self.perms.require(client.name, client.role, "read", path)
        text = self._read_text(abs_path, path)
        return {**self._result(path, text, abs_path), "content": text}

    def read_note_section(self, client: Client, path: str, heading: str) -> dict[str, Any]:
        note = self.read_note(client, path)
        lines = note["content"].splitlines()
        start, end = self._find_section(lines, heading)
        section = "\n".join(lines[start + 1 : end]).strip("\n")
        return {
            "path": path,
            "heading": heading,
            "content": section,
            "hash": note["hash"],
            "modified": note["modified"],
        }

    def list_directory(self, client: Client, path: str = "/") -> list[dict[str, Any]]:
        abs_dir = self.jail.resolve_dir(path)
        if not abs_dir.is_dir():
            raise NotFound(f"directory not found: {path}", path=path)
        entries: list[dict[str, Any]] = []
        for child in sorted(abs_dir.iterdir(), key=lambda p: p.name.lower()):
            if child.name.startswith("."):
                continue
            rel = self.jail.relative(child)
            if child.is_dir():
                if not self._dir_visible(client, rel):
                    continue
                entries.append({"name": child.name, "path": rel, "type": "dir"})
            else:
                if not self.perms.allowed(client.name, client.role, "read", rel):
                    continue
                entries.append({"name": child.name, "path": rel, "type": "file"})
        return entries

    def _dir_visible(self, client: Client, rel_dir: str) -> bool:
        """A directory is listed if the client could read something inside it."""
        if self.perms.allowed(client.name, client.role, "read", f"{rel_dir}/§probe§.md"):
            return True
        role = self.config.roles.get(client.role)
        if role is None:
            return False
        prefix = f"{rel_dir}/"
        return any(
            g.replace("{client}", client.name).startswith(prefix)
            for g in (*role.read, *role.write)
        )

    def list_recent_changes(self, client: Client, days: int = 7, limit: int = 50) -> list[dict]:
        cutoff = dt.datetime.now(dt.timezone.utc).timestamp() - days * 86400
        hits: list[tuple[float, str, Path]] = []
        for dirpath, dirnames, filenames in os.walk(self.jail.root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in filenames:
                if fn.startswith("."):
                    continue
                p = Path(dirpath) / fn
                rel = self.jail.relative(p)
                mtime = p.stat().st_mtime
                if mtime < cutoff:
                    continue
                if not self.perms.allowed(client.name, client.role, "read", rel):
                    continue
                hits.append((mtime, rel, p))
        hits.sort(reverse=True)
        out = []
        for mtime, rel, p in hits[:limit]:
            title = None
            if p.suffix == ".md":
                for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = _HEADING.match(line)
                    if m:
                        title = m.group(2)
                        break
            out.append(
                {
                    "path": rel,
                    "title": title,
                    "modified": dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
            )
        return out

    # ---- write tools -----------------------------------------------------

    def create_note(self, client: Client, path: str, content: str) -> dict[str, Any]:
        abs_path = self._guarded(client, "create_note", "write", path)
        self._check_size(content, path)
        post = frontmatter.loads(content)
        post.metadata.setdefault("created", _utcnow())
        post.metadata.setdefault("author_agent", client.name)
        post.metadata.setdefault("source", "")
        if client.role == ADMIN_ROLE:
            post.metadata.setdefault("status", "unverified")
        else:
            post.metadata["status"] = "unverified"
        text = frontmatter.dumps(post) + "\n"
        self._check_size(text, path)
        with self.locks.file_lock(path):
            if abs_path.exists():
                err = AlreadyExists(f"note already exists: {path}", path=path)
                self._audit(client, "create_note", path, ok=False, error=err.message)
                raise err
            self._atomic_write(abs_path, text)
        self._audit(client, "create_note", path, ok=True, after_hash=content_hash(text))
        return self._result(path, text, abs_path)

    def append_to_note(
        self, client: Client, path: str, content: str, expected_hash: str | None = None
    ) -> dict[str, Any]:
        abs_path = self._guarded(client, "append_to_note", "write", path)
        with self.locks.file_lock(path):
            current = self._read_text(abs_path, path)
            before = content_hash(current)
            if expected_hash is not None and expected_hash != before:
                err = Conflict(
                    f"note changed since last read: {path}",
                    path=path,
                    expected_hash=expected_hash,
                    current_hash=before,
                )
                self._audit(client, "append_to_note", path, ok=False, error=err.message)
                raise err
            text = current.rstrip("\n") + "\n\n" + content.strip("\n") + "\n"
            self._check_size(text, path)
            self._atomic_write(abs_path, text)
        self._audit(
            client, "append_to_note", path, ok=True, before_hash=before, after_hash=content_hash(text)
        )
        return self._result(path, text, abs_path)

    def update_note_section(
        self, client: Client, path: str, heading: str, content: str, expected_hash: str
    ) -> dict[str, Any]:
        if not expected_hash:
            raise InvalidArgument("expected_hash is required for update_note_section")
        abs_path = self._guarded(client, "update_note_section", "write", path)
        with self.locks.file_lock(path):
            current = self._read_text(abs_path, path)
            before = content_hash(current)
            if expected_hash != before:
                err = Conflict(
                    f"note changed since last read: {path}",
                    path=path,
                    expected_hash=expected_hash,
                    current_hash=before,
                )
                self._audit(client, "update_note_section", path, ok=False, error=err.message)
                raise err
            lines = current.splitlines()
            start, end = self._find_section(lines, heading)
            new_lines = lines[: start + 1] + ["", *content.strip("\n").splitlines(), ""] + lines[end:]
            text = "\n".join(new_lines).rstrip("\n") + "\n"
            self._check_size(text, path)
            self._atomic_write(abs_path, text)
        self._audit(
            client,
            "update_note_section",
            path,
            ok=True,
            before_hash=before,
            after_hash=content_hash(text),
        )
        return self._result(path, text, abs_path)

    def add_inbox_item(
        self, client: Client, agent_name: str, title: str, content: str
    ) -> dict[str, Any]:
        base = f"90 Staff Inbox/{agent_name}/{_utcnow()[:10]} {_slugify(title)}"
        note = f"# {title}\n\n{content}\n"
        path = f"{base}.md"
        for attempt in range(2, 100):
            try:
                return self.create_note(client, path, note)
            except AlreadyExists:
                path = f"{base} ({attempt}).md"
        raise AlreadyExists(f"could not find a free inbox path for {title!r}")

    def move_note(self, client: Client, source: str, destination: str) -> dict[str, Any]:
        return self._move(client, "move_note", source, destination)

    def _move(self, client: Client, tool: str, source: str, destination: str) -> dict[str, Any]:
        src_abs = self._guarded(client, tool, "write", source)
        dst_abs = self._guarded(client, tool, "write", destination)
        with self.locks.multi_lock(source, destination):
            if not src_abs.is_file():
                err = NotFound(f"note not found: {source}", path=source)
                self._audit(client, tool, source, ok=False, error=err.message)
                raise err
            if dst_abs.exists():
                err = AlreadyExists(f"destination already exists: {destination}", path=destination)
                self._audit(client, tool, destination, ok=False, error=err.message)
                raise err
            text = self._read_text(src_abs, source)
            dst_abs.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src_abs, dst_abs)
        h = content_hash(text)
        self._audit(client, tool, f"{source} -> {destination}", ok=True, before_hash=h, after_hash=h)
        return self._result(destination, text, dst_abs)

    # ---- admin-only tools ------------------------------------------------

    def rename_note(self, client: Client, source: str, destination: str) -> dict[str, Any]:
        self._require_admin(client, "rename_note", source)
        return self._move(client, "rename_note", source, destination)

    def archive_note(self, client: Client, path: str) -> dict[str, Any]:
        self._require_admin(client, "archive_note", path)
        return self._move(client, "archive_note", path, f"_Archive/{path}")

    def restore_note(self, client: Client, path: str) -> dict[str, Any]:
        self._require_admin(client, "restore_note", path)
        return self._move(client, "restore_note", f"_Archive/{path}", path)

    def set_note_status(self, client: Client, path: str, status: str) -> dict[str, Any]:
        self._require_admin(client, "set_note_status", path)
        if status not in _NOTE_STATUSES:
            raise InvalidArgument(
                f"status must be one of {sorted(_NOTE_STATUSES)}", path=path
            )
        abs_path = self._guarded(client, "set_note_status", "write", path)
        with self.locks.file_lock(path):
            current = self._read_text(abs_path, path)
            before = content_hash(current)
            post = frontmatter.loads(current)
            post.metadata["status"] = status
            text = frontmatter.dumps(post) + "\n"
            self._atomic_write(abs_path, text)
        self._audit(
            client, "set_note_status", path, ok=True, before_hash=before, after_hash=content_hash(text)
        )
        return self._result(path, text, abs_path)
