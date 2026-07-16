"""brain.config.yaml loader and validation.

The config is the only thing that varies per install. Validation is strict:
any error refuses boot with a clear message rather than starting a server
with a permission model that doesn't mean what the operator thinks it means.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from brain_mcp.errors import ConfigError
from brain_mcp.permissions import glob_to_regex

ADMIN_ROLE = "admin"


@dataclass(frozen=True)
class ClientConfig:
    name: str
    token_hash_env: str
    role: str


@dataclass(frozen=True)
class RoleConfig:
    read: tuple[str, ...]
    write: tuple[str, ...]
    deny: tuple[str, ...]


@dataclass(frozen=True)
class Limits:
    requests_per_minute: int = 60
    max_note_bytes: int = 1_048_576


@dataclass(frozen=True)
class BrainConfig:
    vault_root: Path
    audit_dir: Path
    clients: tuple[ClientConfig, ...]
    roles: dict[str, RoleConfig] = field(default_factory=dict)
    limits: Limits = field(default_factory=Limits)


def _require(data: dict, key: str) -> object:
    if key not in data or data[key] in (None, ""):
        raise ConfigError(f"missing required config key: {key!r}")
    return data[key]


def _glob_list(role_name: str, kind: str, value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(g, str) for g in value):
        raise ConfigError(f"role {role_name!r}: {kind} must be a list of glob strings")
    for g in value:
        try:
            glob_to_regex(g.replace("{client}", "x"))
        except ValueError as e:
            raise ConfigError(f"role {role_name!r}: bad glob {g!r}: {e}") from e
    return tuple(value)


def load_config(path: str | Path) -> BrainConfig:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ConfigError(f"config is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError("config root must be a mapping")

    vault_root = Path(str(_require(data, "vault_root")))
    audit_dir = Path(str(_require(data, "audit_dir")))

    raw_roles = _require(data, "roles")
    if not isinstance(raw_roles, dict) or not raw_roles:
        raise ConfigError("roles must be a non-empty mapping")
    roles: dict[str, RoleConfig] = {}
    for name, spec in raw_roles.items():
        if not isinstance(spec, dict):
            raise ConfigError(f"role {name!r} must be a mapping with read/write/deny")
        roles[str(name)] = RoleConfig(
            read=_glob_list(name, "read", spec.get("read")),
            write=_glob_list(name, "write", spec.get("write")),
            deny=_glob_list(name, "deny", spec.get("deny")),
        )

    raw_clients = _require(data, "clients")
    if not isinstance(raw_clients, list) or not raw_clients:
        raise ConfigError("at least one client must be configured")
    clients: list[ClientConfig] = []
    seen: set[str] = set()
    for c in raw_clients:
        if not isinstance(c, dict):
            raise ConfigError("each client must be a mapping")
        name = str(_require(c, "name"))
        if name in seen:
            raise ConfigError(f"duplicate client name: {name!r}")
        seen.add(name)
        role = str(_require(c, "role"))
        if role not in roles:
            raise ConfigError(f"client {name!r} references unknown role {role!r}")
        clients.append(
            ClientConfig(name=name, token_hash_env=str(_require(c, "token_hash_env")), role=role)
        )

    admins = [c.name for c in clients if c.role == ADMIN_ROLE]
    if len(admins) != 1:
        raise ConfigError(
            f"exactly one client must hold the '{ADMIN_ROLE}' role; found "
            f"{len(admins)} ({', '.join(admins) or 'none'})"
        )

    raw_limits = data.get("limits") or {}
    if not isinstance(raw_limits, dict):
        raise ConfigError("limits must be a mapping")
    limits = Limits(
        requests_per_minute=int(raw_limits.get("requests_per_minute", 60)),
        max_note_bytes=int(raw_limits.get("max_note_bytes", 1_048_576)),
    )
    if limits.requests_per_minute <= 0 or limits.max_note_bytes <= 0:
        raise ConfigError("limits must be positive")

    return BrainConfig(
        vault_root=vault_root, audit_dir=audit_dir, clients=tuple(clients), roles=roles, limits=limits
    )
