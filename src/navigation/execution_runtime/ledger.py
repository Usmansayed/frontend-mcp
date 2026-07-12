"""Execution ledger — append-only record of tool invocations."""

from __future__ import annotations

from navigation.execution_runtime.models import ExecutionRecord


class ExecutionLedger:
    """In-memory append-only execution history."""

    def __init__(self) -> None:
        self._records: list[ExecutionRecord] = []

    def append(self, record: ExecutionRecord) -> None:
        self._records.append(record)

    def records(self) -> list[ExecutionRecord]:
        return list(self._records)

    def for_tool(self, tool: str) -> list[ExecutionRecord]:
        return [r for r in self._records if r.tool == tool]

    def last(self) -> ExecutionRecord | None:
        return self._records[-1] if self._records else None

    def clear(self) -> None:
        self._records.clear()
