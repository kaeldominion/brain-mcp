"""Vault search behind a stable interface.

v1 uses ripgrep when available (the Docker image ships it) with a pure-Python
scan as fallback, so results are identical either way: ripgrep only selects
candidate files, and excerpt/title/heading extraction happens in Python. The
interface is designed so the backend can later be swapped for SQLite FTS5
without changing the MCP tool schema.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from brain_mcp.auth import Client
from brain_mcp.config import BrainConfig
from brain_mcp.paths import VaultJail
from brain_mcp.permissions import PermissionEngine

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_SEARCHABLE = {".md", ".txt"}
_EXCERPT_LEN = 200
_MAX_HEADINGS = 8


class SearchEngine:
    def __init__(self, config: BrainConfig, use_ripgrep: bool | None = None):
        self.jail = VaultJail(config.vault_root)
        if use_ripgrep is None:
            use_ripgrep = shutil.which("rg") is not None
        self.use_ripgrep = use_ripgrep

    def search(
        self,
        perms: PermissionEngine,
        client: Client,
        query: str,
        folder: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        base = self.jail.resolve_dir(folder or "/")
        if not base.is_dir():
            return []
        if self.use_ripgrep:
            candidates = self._rg_candidates(query, base)
        else:
            candidates = self._python_candidates(query, base)

        hits: list[tuple[float, dict[str, Any]]] = []
        for path in candidates:
            rel = self.jail.relative(path)
            if any(part.startswith(".") for part in Path(rel).parts):
                continue
            if not perms.allowed(client.name, client.role, "read", rel):
                continue
            result = self._describe(path, rel, query)
            if result is not None:
                hits.append((path.stat().st_mtime, result))
        hits.sort(key=lambda t: t[0], reverse=True)
        return [r for _, r in hits[: max(1, limit)]]

    def _rg_candidates(self, query: str, base: Path) -> list[Path]:
        proc = subprocess.run(
            ["rg", "--files-with-matches", "--ignore-case", "--fixed-strings",
             "--no-messages", "--", query, str(base)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return [Path(line) for line in proc.stdout.splitlines() if line]

    def _python_candidates(self, query: str, base: Path) -> list[Path]:
        needle = query.lower()
        out: list[Path] = []
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in _SEARCHABLE:
                continue
            try:
                if needle in path.read_text(encoding="utf-8", errors="replace").lower():
                    out.append(path)
            except OSError:
                continue
        return out

    def _describe(self, path: Path, rel: str, query: str) -> dict[str, Any] | None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        needle = query.lower()
        title = None
        headings: list[str] = []
        excerpt = None
        for line in text.splitlines():
            m = _HEADING.match(line)
            if m:
                if title is None:
                    title = m.group(2)
                if len(headings) < _MAX_HEADINGS:
                    headings.append(m.group(2))
            if excerpt is None and needle in line.lower():
                idx = line.lower().index(needle)
                start = max(0, idx - _EXCERPT_LEN // 2)
                excerpt = line[start : start + _EXCERPT_LEN].strip()
        if excerpt is None:
            # match spanned lines or lives only in frontmatter; use the head of the note
            excerpt = text[:_EXCERPT_LEN].strip()
        return {
            "path": rel,
            "title": title,
            "excerpt": excerpt,
            "headings": headings,
            "modified": dt.datetime.fromtimestamp(
                path.stat().st_mtime, tz=dt.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
