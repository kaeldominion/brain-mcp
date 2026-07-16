"""Per-file locks plus a short global lock for multi-path operations.

Single-process locking is sufficient: the MCP server is the only writer to
the vault (single-writer pattern), so no cross-process coordination exists
by design. Multi-path operations (move/rename/archive) take the global lock
first, then the involved file locks in sorted order, preventing deadlock.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager


class LockManager:
    def __init__(self) -> None:
        self._registry_mutex = threading.Lock()
        self._file_locks: dict[str, threading.Lock] = {}
        self._global = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._registry_mutex:
            lock = self._file_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._file_locks[key] = lock
            return lock

    @contextmanager
    def file_lock(self, key: str):
        lock = self._lock_for(key)
        with lock:
            yield

    @contextmanager
    def multi_lock(self, *keys: str):
        locks = [self._lock_for(k) for k in sorted(set(keys))]
        with self._global:
            for lock in locks:
                lock.acquire()
            try:
                yield
            finally:
                for lock in reversed(locks):
                    lock.release()
