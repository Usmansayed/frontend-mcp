"""Unit tests for console ring buffer filtering."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from navigation.frontend_quality_intelligence.console.buffer import ConsoleRingBuffer
from navigation.frontend_quality_intelligence.console.models import ConsoleFilter, ConsoleLogEntry


def test_buffer_levels_and_contains() -> None:
	buf = ConsoleRingBuffer(max_entries=100)
	for i, (level, text) in enumerate(
		[
			("log", "hello world"),
			("info", "MCP_CONSOLE_TEST_INFO"),
			("debug", "debug detail"),
			("warn", "EDGE_LAB_CONSOLE_WARN"),
			("error", "EDGE_LAB_CONSOLE_ERROR"),
		]
	):
		buf.add(ConsoleLogEntry(level=level, text=text, timestamp=float(i)))

	report = buf.report(filter=ConsoleFilter(levels=["error", "warn"]))
	assert report.total == 2
	assert report.by_level.get("error") == 1
	assert any("EDGE_LAB_CONSOLE_ERROR" in e["text"] for e in report.entries)

	filtered = buf.report(filter=ConsoleFilter(contains="MCP_CONSOLE", limit=10))
	assert filtered.total == 1
	assert "MCP_CONSOLE_TEST_INFO" in filtered.entries[0]["text"]


def test_buffer_since_index_and_ring_drop() -> None:
	buf = ConsoleRingBuffer(max_entries=3)
	for i in range(5):
		buf.add(ConsoleLogEntry(level="log", text=f"msg-{i}", timestamp=float(i)))

	assert buf.session_total == 5
	report = buf.report(window_start_index=3)
	texts = [e["text"] for e in report.entries]
	assert texts == ["msg-3", "msg-4"]


def test_blocking_from_errors_and_exceptions() -> None:
	buf = ConsoleRingBuffer()
	buf.add(ConsoleLogEntry(level="error", text="boom", timestamp=1.0))
	buf.add(ConsoleLogEntry(level="exception", text="Uncaught TypeError", timestamp=2.0))
	report = buf.report()
	assert len(report.blocking) == 2
	assert any("boom" in b for b in report.blocking)


if __name__ == "__main__":
	test_buffer_levels_and_contains()
	test_buffer_since_index_and_ring_drop()
	test_blocking_from_errors_and_exceptions()
	print("console buffer unit tests: PASS")
