"""Bearer-token authentication.

The server only ever sees sha256 hashes of client tokens (from environment
variables named in the config); plaintext tokens exist solely on the agent
side. Comparison is constant-time and iterates every client with no early
exit, so timing reveals nothing about which client (if any) matched.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from typing import Mapping

from brain_mcp.config import BrainConfig
from brain_mcp.errors import AuthError, ConfigError

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Client:
    name: str
    role: str


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token(deploy: str, client: str) -> str:
    return f"{deploy}_{client}_{secrets.token_hex(16)}"


def token_prefix(token: str) -> str:
    """Identifying prefix safe for logs/audit: deploy_client_ + 4 chars max."""
    parts = token.split("_")
    if len(parts) >= 3:
        return f"{parts[0]}_{parts[1]}_{parts[2][:4]}"
    return token[:8]


class TokenRegistry:
    def __init__(self, entries: list[tuple[str, Client]]):
        self._entries = entries  # (sha256 hex hash, client)

    @classmethod
    def from_config(cls, config: BrainConfig, environ: Mapping[str, str]) -> "TokenRegistry":
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
        return cls(entries)

    def authenticate(self, authorization: str | None) -> Client:
        if not authorization:
            raise AuthError("missing Authorization header")
        scheme, _, credential = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            raise AuthError("Authorization header must be 'Bearer <token>'")
        digest = hash_token(credential.strip())
        matched: Client | None = None
        for stored_hash, client in self._entries:
            if hmac.compare_digest(stored_hash, digest):
                matched = client
        if matched is None:
            raise AuthError("invalid token")
        return matched
