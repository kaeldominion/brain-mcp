"""Append-only JSONL audit log with size-based rotation.

The audit directory lives outside the vault, so no MCP tool can ever read or
rewrite audit history. Rotation renames the active file to a numbered
generation and prunes generations beyond ``keep``.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_KEEP = 5


class Auditor:
    def __init__(self, audit_dir: str | Path, max_bytes: int = DEFAULT_MAX_BYTES, keep: int = DEFAULT_KEEP):
        self.dir = Path(audit_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "audit.jsonl"
        self.max_bytes = max_bytes
        self.keep = keep
        self._lock = threading.Lock()
        self._generation = self._latest_generation()

    def _latest_generation(self) -> int:
        gens = []
        for p in self.dir.glob("audit.*.jsonl"):
            try:
                gens.append(int(p.stem.split(".")[1]))
            except (IndexError, ValueError):
                continue
        return max(gens, default=0)

    def record(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")
        with self._lock:
            if self.path.exists() and self.path.stat().st_size + len(data) > self.max_bytes:
                self._rotate()
            with open(self.path, "ab") as f:
                f.write(data)

    def _rotate(self) -> None:
        self._generation += 1
        self.path.rename(self.dir / f"audit.{self._generation:06d}.jsonl")
        rotated = sorted(self.dir.glob("audit.*.jsonl"))
        for old in rotated[: max(0, len(rotated) - self.keep)]:
            old.unlink()
