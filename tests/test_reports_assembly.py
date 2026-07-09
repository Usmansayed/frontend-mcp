"""Unit tests for reports assembly (no browser)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
	sys.path.insert(0, str(SRC))

from navigation.reports.diagnosis import _assemble_report, _build_summary, _verification_from_observation
from navigation.reports.hints import build_suggested_fixes
from navigation.reports.markdown import report_to_markdown


def test_build_summary_includes_counts() -> None:
	text = _build_summary(
		url="http://localhost:5173/forms",
		blocking_count=2,
		warning_count=3,
		console={"by_level": {"error": 1}},
		network={"failed_count": 1},
		audits={"accessibility": {"score": 85}},
		mode="full",
	)
	assert "full diagnosis" in text
	assert "2 blocking" in text
	assert "accessibility score 85" in text


def test_verification_from_observation() -> None:
	v = _verification_from_observation({"url": "http://x", "dom_text": "hello"})
	assert v["ok"] is True
	assert v["dom_nonempty"] is True


def test_assemble_report_merges_console_blocking() -> None:
	obs = {
		"url": "http://localhost:5173/",
		"dom_text": "content",
		"dev_insights": {"summary": {"blocking_issues": [], "advisory_issues": []}},
		"console": {
			"total": 2,
			"session_total": 2,
			"by_level": {"error": 1},
			"blocking": ["Uncaught Error: boom"],
		},
		"network": {"total": 0, "failed_count": 0, "blocking": []},
		"visual_insights": {"blocking": [], "advisory": []},
	}
	report = _assemble_report(
		obs_dict=obs,
		scan_id="scan_test",
		mode="debug",
		audits={},
		degraded=[],
	)
	assert "Uncaught Error: boom" in report.blocking
	assert report.console is not None
	assert report.scan_id == "scan_test"


def test_suggested_fixes_console_and_network() -> None:
	hints = build_suggested_fixes(
		blocking=["x"],
		warnings=[],
		console={"by_level": {"error": 2}, "blocking": ["err"]},
		network={"failed_count": 1},
		visual=None,
		audits={"accessibility": {"score": 70}},
	)
	assert any("perception_console_get" in h for h in hints)
	assert any("network failures" in h.lower() for h in hints)
	assert any("Accessibility" in h for h in hints)


def test_report_to_markdown_sections() -> None:
	md = report_to_markdown(
		{
			"mode": "debug",
			"url": "http://localhost/",
			"scan_id": "scan_abc",
			"summary": "debug diagnosis",
			"blocking": ["issue"],
			"warnings": [],
			"suggested_fixes": ["fix it"],
		}
	)
	assert "# Perception Diagnosis Report" in md
	assert "## Blocking Issues" in md
	assert "issue" in md


def main() -> int:
	test_build_summary_includes_counts()
	test_verification_from_observation()
	test_assemble_report_merges_console_blocking()
	test_suggested_fixes_console_and_network()
	test_report_to_markdown_sections()
	print("reports assembly: PASS")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
