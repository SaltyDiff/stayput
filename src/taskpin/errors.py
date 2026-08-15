"""Typed TaskPin failures. No host or Factory types."""

from __future__ import annotations


class TaskPinError(ValueError):
    """Closed operational failure. ``code`` is stable; ``message`` is diagnostic."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
