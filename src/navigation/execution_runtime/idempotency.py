"""Idempotency store — deduplication and replay protection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, default=str)


def compute_idempotency_key(
    tool: str,
    arguments: dict[str, Any],
    *,
    scope: str | None = None,
    explicit_key: str | None = None,
) -> str:
    if explicit_key:
        return f"{tool}:{explicit_key}"
    payload = {"tool": tool, "arguments": arguments, "scope": scope or ""}
    digest = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()[:24]
    return f"{tool}:{digest}"


@dataclass
class IdempotencyEntry:
    key: str
    tool: str
    envelope: dict[str, Any]
    execution_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "tool": self.tool,
            "execution_id": self.execution_id,
        }


@dataclass
class IdempotencyStore:
    """In-memory deduplication cache — safe tools only unless allow_repeat."""

    _entries: dict[str, IdempotencyEntry] = field(default_factory=dict)

    def get(self, key: str) -> IdempotencyEntry | None:
        return self._entries.get(key)

    def put(self, key: str, entry: IdempotencyEntry) -> None:
        self._entries[key] = entry

    def clear(self) -> None:
        self._entries.clear()
