"""Vault-root jail. Every client-supplied path passes through here.

Rules (brief §6): normalize; resolve against the vault root; reject absolute
paths; reject ``..`` traversal; reject symlinks resolving outside the vault;
reject blocked (dot-prefixed) files and directories — which covers ``.git``,
``.obsidian``, ``.env`` and any hidden credential files; restrict extensions
to Markdown and selected text formats.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from brain_mcp.errors import InvalidPath

ALLOWED_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".canvas"}


class VaultJail:
    def __init__(self, vault_root: str | Path):
        self.root = Path(vault_root).resolve()

    def _clean_parts(self, rel_path: str, *, allow_root_slash: bool) -> tuple[str, ...]:
        if rel_path is None:
            raise InvalidPath("path is required")
        raw = str(rel_path)
        if allow_root_slash:
            raw = raw.lstrip("/")
        pure = PurePosixPath(raw)
        if pure.is_absolute():
            raise InvalidPath(f"absolute paths are not allowed: {rel_path!r}")
        parts = [p for p in pure.parts if p != "."]
        for part in parts:
            if part == "..":
                raise InvalidPath(f"path traversal is not allowed: {rel_path!r}")
            if part.startswith("."):
                raise InvalidPath(f"blocked path segment {part!r} in {rel_path!r}")
            if "\x00" in part:
                raise InvalidPath("null bytes are not allowed in paths")
        return tuple(parts)

    def _check_inside(self, candidate: Path, rel_path: str) -> Path:
        resolved = candidate.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise InvalidPath(f"path escapes the vault: {rel_path!r}")
        return candidate

    def resolve(self, rel_path: str) -> Path:
        """Resolve a vault-relative *file* path. Enforces allowed extensions."""
        parts = self._clean_parts(rel_path, allow_root_slash=False)
        if not parts:
            raise InvalidPath("empty path")
        suffix = PurePosixPath(parts[-1]).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise InvalidPath(
                f"extension {suffix or '(none)'!r} not allowed; "
                f"allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        return self._check_inside(self.root.joinpath(*parts), rel_path)

    def resolve_dir(self, rel_path: str) -> Path:
        """Resolve a vault-relative *directory* path. '/' or '' means the root."""
        parts = self._clean_parts(rel_path or "", allow_root_slash=True)
        return self._check_inside(self.root.joinpath(*parts) if parts else self.root, rel_path)

    def relative(self, abs_path: Path) -> str:
        return abs_path.relative_to(self.root).as_posix()
