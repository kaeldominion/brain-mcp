"""Structured errors shared across the server.

Every error carries a stable machine-readable code so MCP clients can react
programmatically (retry, surface a conflict, back off) instead of parsing text.
"""

from __future__ import annotations

from typing import Any


class BrainError(Exception):
    code = "INTERNAL"

    def __init__(self, message: str, **data: Any):
        super().__init__(message)
        self.message = message
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message, **self.data}


class ConfigError(BrainError):
    code = "CONFIG"


class AuthError(BrainError):
    code = "UNAUTHORIZED"


class PermissionDenied(BrainError):
    code = "FORBIDDEN"


class InvalidPath(BrainError):
    code = "INVALID_PATH"


class NotFound(BrainError):
    code = "NOT_FOUND"


class AlreadyExists(BrainError):
    code = "ALREADY_EXISTS"


class Conflict(BrainError):
    code = "CONFLICT"


class InvalidArgument(BrainError):
    code = "INVALID_ARGUMENT"


class TooLarge(BrainError):
    code = "TOO_LARGE"


class RateLimited(BrainError):
    code = "RATE_LIMITED"
