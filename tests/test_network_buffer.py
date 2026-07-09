"""Unit tests for network buffer, GraphQL hints, and HAR export."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from navigation.network.buffer import NetworkRingBuffer, finalize_entry_metadata
from navigation.network.cdp_parse import extract_graphql_operation
from navigation.network.har import entries_to_har
from navigation.network.models import NetworkEntry, NetworkFilter


def test_graphql_operation_name() -> None:
	body = '{"operationName":"GetUser","query":"query GetUser { id }"}'
	op = extract_graphql_operation("POST", "http://localhost/api/graphql", body, "application/json")
	assert op == "GetUser"


def test_network_report_failures_and_api_group() -> None:
	buf = NetworkRingBuffer(max_entries=50)
	for url, status in [
		("http://localhost:5173/api/dev-insights-ok", 200),
		("http://localhost:5173/api/dev-insights-missing", 404),
	]:
		entry = NetworkEntry(
			request_id=f"id-{status}",
			url=url,
			method="GET",
			status=status,
			started_at=1.0,
			duration_ms=50.0,
		)
		finalize_entry_metadata(entry)
		buf.add(entry)

	report_fail = buf.build_report(buf.all_entries(), filter=NetworkFilter(failed_only=True))
	assert report_fail.failed_count >= 1
	assert any("dev-insights-missing" in f["url"] for f in report_fail.failures)

	report_all = buf.build_report(buf.all_entries())
	assert report_all.by_api_group.get("dev-insights-ok") == 1


def test_har_export_shape() -> None:
	entry = NetworkEntry(
		request_id="r1",
		url="http://localhost/api/test",
		method="GET",
		status=200,
		started_at=1.0,
		duration_ms=12.0,
		response_body='{"ok":true}',
		mime_type="application/json",
	)
	har = entries_to_har([entry], page_url="http://localhost/")
	assert har["log"]["version"] == "1.2"
	assert len(har["log"]["entries"]) == 1
	assert har["log"]["entries"][0]["response"]["status"] == 200


if __name__ == "__main__":
	test_graphql_operation_name()
	test_network_report_failures_and_api_group()
	test_har_export_shape()
	print("network unit tests: PASS")
