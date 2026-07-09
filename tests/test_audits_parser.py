"""Unit tests for Lighthouse report parser."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from navigation.audits.models import AuditCategory
from navigation.audits.parser import parse_lighthouse_report

FIXTURE = ROOT / "artifacts" / "test-lighthouse.json"


def test_parse_accessibility_fixture() -> None:
	if not FIXTURE.is_file():
		print("skip: fixture missing (run lighthouse once to generate)")
		return
	lhr = json.loads(FIXTURE.read_text(encoding="utf-8"))
	report = parse_lighthouse_report(lhr, AuditCategory.ACCESSIBILITY)
	assert report.category == "accessibility"
	assert 0 <= report.score <= 100
	assert report.audit_counts.get("failed", 0) >= 0
	assert isinstance(report.warnings, list)


def test_parse_performance_metrics_keys() -> None:
	lhr = {
		"lighthouseVersion": "12.0.0",
		"requestedUrl": "http://localhost/",
		"categories": {
			"performance": {
				"score": 0.81,
				"auditRefs": [{"id": "largest-contentful-paint"}, {"id": "first-contentful-paint"}],
			}
		},
		"audits": {
			"largest-contentful-paint": {
				"score": 0.9,
				"scoreDisplayMode": "numeric",
				"numericValue": 2100,
				"title": "LCP",
			},
			"first-contentful-paint": {
				"score": 0.95,
				"scoreDisplayMode": "numeric",
				"numericValue": 900,
				"title": "FCP",
			},
		},
	}
	report = parse_lighthouse_report(lhr, AuditCategory.PERFORMANCE)
	assert report.score == 81.0
	assert report.metrics.get("lcp_ms") == 2100
	assert report.metrics.get("fcp_ms") == 900


if __name__ == "__main__":
	test_parse_accessibility_fixture()
	test_parse_performance_metrics_keys()
	print("audit parser unit tests: PASS")
