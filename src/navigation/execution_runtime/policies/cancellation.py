"""Cancellation support for in-flight execution."""

from __future__ import annotations

import asyncio


class CancellationToken:
    """Deterministic cancellation flag checked before and during execution."""

    def __init__(self) -> None:
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def check(self) -> None:
        if self._cancelled:
            raise asyncio.CancelledError("execution cancelled")
