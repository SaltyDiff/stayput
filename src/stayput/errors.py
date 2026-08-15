"""Typed StayPut failures. No host or Factory types."""

from __future__ import annotations


class StayPutError(ValueError):
    """Closed operational failure. ``code`` is stable; ``message`` is diagnostic."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")
