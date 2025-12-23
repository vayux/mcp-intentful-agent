"""Structured error types for MCP tools."""
from __future__ import annotations

from typing import Any, Literal

ToolErrorCode = Literal[
    "UNAUTHORIZED",
    "FORBIDDEN",
    "NOT_FOUND",
    "VALIDATION_FAILED",
    "CONFLICT",
    "UPSTREAM_TIMEOUT",
    "UPSTREAM_ERROR",
    "CONFIRMATION_REQUIRED",
]


class ToolError(Exception):
    """Structured error that tools can raise."""

    def __init__(
        self,
        code: ToolErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def structured_error(err: Exception) -> dict[str, Any]:
    """Convert exception to structured error response."""
    if isinstance(err, ToolError):
        return {
            "ok": False,
            "error": {
                "code": err.code,
                "message": err.message,
                "details": err.details,
            },
        }
    return {
        "ok": False,
        "error": {
            "code": "UPSTREAM_ERROR",
            "message": "Unexpected error",
            "details": {"exception": str(err)},
        },
    }

