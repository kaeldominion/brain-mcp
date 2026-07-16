"""Glob-based ACL engine. Default-deny; precedence: deny > write > read.

A write grant implies read of the same paths — an agent must always be able
to read back what it is allowed to write (read-before-write is a core rule).
"""

from __future__ import annotations

import re
from typing import Iterable, Pattern

from brain_mcp.errors import PermissionDenied

_SEGMENT_CHAR = r"[^/]"


def glob_to_regex(pattern: str) -> Pattern[str]:
    """Translate a vault glob to a compiled regex.

    ``**`` matches across path segments, ``*`` and ``?`` stay within one
    segment, ``[...]`` is a character class. Raises ValueError on malformed
    patterns (e.g. unclosed character class).
    """
    i, n = 0, len(pattern)
    out: list[str] = []
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i : i + 2] == "**":
                i += 2
                if i < n and pattern[i] == "/":
                    # "**/" matches zero or more whole segments
                    out.append("(?:.*/)?")
                    i += 1
                else:
                    out.append(".*")
            else:
                out.append(f"{_SEGMENT_CHAR}*")
                i += 1
        elif c == "?":
            out.append(_SEGMENT_CHAR)
            i += 1
        elif c == "[":
            j = i + 1
            if j < n and pattern[j] in "!^":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j >= n:
                raise ValueError(f"invalid glob (unclosed character class): {pattern!r}")
            inner = pattern[i + 1 : j].replace("\\", "\\\\")
            if inner.startswith("!"):
                inner = "^" + inner[1:]
            out.append(f"[{inner}]")
            i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


class PermissionEngine:
    def __init__(self, roles: dict):
        # roles: name -> RoleConfig (with .read/.write/.deny glob lists)
        self._roles = roles
        self._cache: dict[str, Pattern[str]] = {}

    def _matches(self, globs: Iterable[str], client: str, rel_path: str) -> bool:
        for g in globs:
            g = g.replace("{client}", client)
            rx = self._cache.get(g)
            if rx is None:
                rx = glob_to_regex(g)
                self._cache[g] = rx
            if rx.match(rel_path):
                return True
        return False

    def allowed(self, client: str, role: str, action: str, rel_path: str) -> bool:
        r = self._roles.get(role)
        if r is None:
            return False
        if self._matches(r.deny, client, rel_path):
            return False
        if action == "write":
            return self._matches(r.write, client, rel_path)
        if action == "read":
            return self._matches(r.read, client, rel_path) or self._matches(
                r.write, client, rel_path
            )
        return False

    def require(self, client: str, role: str, action: str, rel_path: str) -> None:
        if not self.allowed(client, role, action, rel_path):
            raise PermissionDenied(
                f"{action} access to '{rel_path}' denied for client '{client}'",
                path=rel_path,
                action=action,
            )
