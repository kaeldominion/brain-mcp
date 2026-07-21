"""Dynamic client registry (v1.1).

Two client sources, one authenticator:

- **static clients** from brain.config.yaml — hashes in env vars, immutable at
  runtime (the bootstrap admin lives here);
- **dynamic clients** from a server-managed ``clients.yaml`` (``clients_file``
  in the config) — hashes stored in the file, hot-reloaded on change, mutated
  through this class (used by the admin API / console). No restarts, no env
  edits, no docker access.

The exactly-one-admin rule spans both sources; the built-in ``console`` role
is exempt (it governs agents, not the console).
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from brain_mcp.auth import Client, generate_token, hash_token
from brain_mcp.config import BrainConfig
from brain_mcp.errors import AuthError, ConfigError, InvalidArgument
from brain_mcp.permissions import ADMIN_ROLE, CONSOLE_ROLE

logger = logging.getLogger(__name__)

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ClientInfo:
    name: str
    role: str
    source: str  # "static" | "dynamic"
    owner: str | None = None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "client"


class ClientRegistry:
    def __init__(
        self,
        config: BrainConfig,
        static_entries: list[tuple[str, Client]],
    ):
        self._config = config
        self.clients_file = config.clients_file
        self._static = static_entries
        self._dynamic: list[tuple[str, Client]] = []
        self._file_sig: tuple[int, int] | None = None
        self._lock = threading.RLock()
        if self.clients_file is not None and self.clients_file.exists():
            # a broken file at boot refuses boot, same as any config error
            self._dynamic = self._parse_file()
            self._file_sig = self._signature()

    # ---- construction ------------------------------------------------------

    @classmethod
    def from_config(cls, config: BrainConfig, environ: Mapping[str, str]) -> "ClientRegistry":
        entries: list[tuple[str, Client]] = []
        for c in config.clients:
            h = environ.get(c.token_hash_env, "").strip().lower()
            if not h:
                raise ConfigError(f"missing token hash env var: {c.token_hash_env}")
            if not _SHA256_HEX.match(h):
                raise ConfigError(
                    f"{c.token_hash_env} must be a 64-char hex sha256 of the client token"
                )
            entries.append((h, Client(name=c.name, role=c.role)))
        return cls(config, entries)

    # ---- file handling -----------------------------------------------------

    def _signature(self) -> tuple[int, int] | None:
        try:
            st = self.clients_file.stat()
            return (st.st_mtime_ns, st.st_size)
        except (OSError, AttributeError):
            return None

    def _parse_file(self) -> list[tuple[str, Client]]:
        data = yaml.safe_load(self.clients_file.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict) or not isinstance(data.get("clients", []), list):
            raise ConfigError(f"{self.clients_file}: root must be a mapping with a clients list")
        static_names = {c.name for _, c in self._static}
        seen: set[str] = set()
        entries: list[tuple[str, Client]] = []
        for raw in data.get("clients", []):
            name = str(raw.get("name", "")).strip()
            role = str(raw.get("role", "")).strip()
            h = str(raw.get("token_hash", "")).strip().lower()
            if not name or not role or not _SHA256_HEX.match(h):
                raise ConfigError(f"{self.clients_file}: bad entry {raw!r}")
            if role not in self._config.roles and role != CONSOLE_ROLE:
                raise ConfigError(f"{self.clients_file}: client {name!r} has unknown role {role!r}")
            if name in seen or name in static_names:
                raise ConfigError(f"{self.clients_file}: duplicate client name {name!r}")
            seen.add(name)
            owner = str(raw.get("owner", "")).strip() or None
            entries.append((h, Client(name=name, role=role, owner=owner)))
        return entries

    def _maybe_reload(self) -> None:
        if self.clients_file is None:
            return
        sig = self._signature()
        if sig == self._file_sig:
            return
        with self._lock:
            if sig != self._file_sig:
                try:
                    if sig is None:
                        self._dynamic = []
                    else:
                        self._dynamic = self._parse_file()
                except (ConfigError, OSError, yaml.YAMLError) as e:
                    # keep serving the last good registry; a bad edit must not
                    # take authentication down for every agent
                    logger.warning("clients file reload failed, keeping last good state: %s", e)
                self._file_sig = sig

    def _write_file(self, entries: list[tuple[str, Client]]) -> None:
        payload = {
            "clients": [
                {
                    "name": c.name,
                    "role": c.role,
                    **({"owner": c.owner} if c.owner else {}),
                    "token_hash": h,
                }
                for h, c in entries
            ]
        }
        self.clients_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.clients_file.parent, prefix=".clients-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("# Managed by brain-mcp (admin API / console). Hashes only — never tokens.\n")
                yaml.safe_dump(payload, f, sort_keys=False)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.clients_file)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        self._dynamic = entries
        self._file_sig = self._signature()

    # ---- queries -----------------------------------------------------------

    def _all_entries(self) -> list[tuple[str, Client]]:
        return [*self._static, *self._dynamic]

    def authenticate(self, authorization: str | None) -> Client:
        self._maybe_reload()
        if not authorization:
            raise AuthError("missing Authorization header")
        scheme, _, credential = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            raise AuthError("Authorization header must be 'Bearer <token>'")
        digest = hash_token(credential.strip())
        matched: Client | None = None
        import hmac

        for stored_hash, client in self._all_entries():
            if hmac.compare_digest(stored_hash, digest):
                matched = client
        if matched is None:
            raise AuthError("invalid token")
        return matched

    def list_clients(self) -> list[ClientInfo]:
        self._maybe_reload()
        out = [ClientInfo(c.name, c.role, "static") for _, c in self._static]
        out += [ClientInfo(c.name, c.role, "dynamic", c.owner) for _, c in self._dynamic]
        return out

    def _admin_names(self) -> list[str]:
        return [c.name for _, c in self._all_entries() if c.role == ADMIN_ROLE]

    # ---- mutations (dynamic clients only) -----------------------------------

    def _require_file(self) -> None:
        if self.clients_file is None:
            raise InvalidArgument(
                "dynamic clients are not enabled: set clients_file in brain.config.yaml"
            )

    def add_client(
        self, name: str, role: str, deploy_prefix: str = "brain", owner: str | None = None
    ) -> str:
        self._require_file()
        name = name.strip()
        with self._lock:
            self._maybe_reload()
            if not name:
                raise InvalidArgument("client name is required")
            if any(c.name == name for _, c in self._all_entries()):
                raise InvalidArgument(f"client {name!r} already exists")
            if role not in self._config.roles and role != CONSOLE_ROLE:
                raise InvalidArgument(
                    f"unknown role {role!r} (defined: {', '.join(self._config.roles)})"
                )
            if role == ADMIN_ROLE and self._admin_names():
                raise InvalidArgument(
                    f"an admin client already exists ({self._admin_names()[0]!r}); "
                    "exactly one admin is allowed"
                )
            token = generate_token(_slug(deploy_prefix), _slug(name))
            owner = (owner or "").strip() or None
            entries = [*self._dynamic, (hash_token(token), Client(name=name, role=role, owner=owner))]
            self._write_file(entries)
            return token

    def _find_dynamic(self, name: str) -> tuple[str, Client]:
        for h, c in self._dynamic:
            if c.name == name:
                return h, c
        if any(c.name == name for _, c in self._static):
            raise InvalidArgument(
                f"client {name!r} is env-managed (static config) — rotate it via "
                "generate-secrets.sh and a restart, not the API"
            )
        raise InvalidArgument(f"client {name!r} not found")

    def rotate_client(self, name: str, deploy_prefix: str = "brain") -> str:
        self._require_file()
        with self._lock:
            self._maybe_reload()
            _, client = self._find_dynamic(name)
            token = generate_token(_slug(deploy_prefix), _slug(name))
            entries = [
                (hash_token(token), c) if c.name == name else (h, c)
                for h, c in self._dynamic
            ]
            self._write_file(entries)
            return token

    def remove_client(self, name: str) -> None:
        self._require_file()
        with self._lock:
            self._maybe_reload()
            _, client = self._find_dynamic(name)
            if client.role == ADMIN_ROLE and len(self._admin_names()) == 1:
                raise InvalidArgument("refusing to remove the only admin client")
            self._write_file([(h, c) for h, c in self._dynamic if c.name != name])
