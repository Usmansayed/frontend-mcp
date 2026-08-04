"""Profile development SEO phases — local debugging only (no browser)."""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
os.environ["SEO_GRAPH_PATH"] = str(ROOT / "artifacts" / "profile_seo_graph.json")

import sys

sys.path.insert(0, str(ROOT / "src"))

from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import handle_seo_audit_start
from navigation.seo_intelligence.models import SeoAuditMode, SeoAuditRequest
from navigation.seo_intelligence.planning.orchestrator import SeoAuditOrchestrator


def _rich_observation() -> dict:
	return {
		"url": "http://localhost:5173/forms/validation",
		"title": "Validation Form",
		"dev_insights": {
			"issues": [
				{"kind": "meta", "message": "Missing meta description", "tier": "advisory"},
				{"kind": "heading", "message": "Multiple h1 elements", "tier": "advisory"},
			],
		},
		"console": {"blocking": [], "by_level": {"warn": 2}},
		"network": {"failed_count": 0},
		"agent_summary": {"blocking": [], "advisory": ["Slow request"]},
	}


async def _timed(label: str, coro):
	t0 = time.perf_counter()
	result = await coro
	ms = (time.perf_counter() - t0) * 1000
	print(f"  {label}: {ms:.1f}ms")
	return result, ms


async def main() -> None:
	url = "http://localhost:5173/forms/validation"
	sandbox = ROOT / "sandbox"
	scans = ScanRegistry()
	record = scans.register(
		session_id="prof",
		run_id="r1",
		url=url,
		observation=_rich_observation(),
	)
	request = SeoAuditRequest(
		website_url=url,
		scan_id=record.scan_id,
		repo_root=str(sandbox),
	)
	orch = SeoAuditOrchestrator(scan_registry=scans)

	print("=== Phase profile ===")
	_, ms_probe_all = await _timed(
		"probe_connections (legacy all)",
		orch._probe_connections(SeoAuditRequest(website_url=url, scan_id=record.scan_id, mode=SeoAuditMode.PROFESSIONAL)),
	)
	_, ms_probe_dev = await _timed("probe_connections (development)", orch._probe_connections(request))

	result, ms_audit = await _timed("development_audit", orch.development_audit(request))
	print(f"  evidence={len(result.evidence)} recommendations={len(result.recommendations)}")

	seo_env, ms_handler = await _timed(
		"handle_seo_audit_start",
		handle_seo_audit_start(
			scans,
			{"website_url": url, "scan_id": record.scan_id, "repo_root": str(sandbox)},
		),
	)
	data = seo_env.get("data") or {}
	print(f"  handler ok={seo_env.get('ok')} status={data.get('status')} partial={data.get('partial')}")

	print("\n=== Summary ===")
	print(
		json.dumps(
			{
				"probe_all_ms": round(ms_probe_all, 1),
				"probe_dev_ms": round(ms_probe_dev, 1),
				"development_audit_ms": round(ms_audit, 1),
				"handler_ms": round(ms_handler, 1),
				"recommendation_count": len(result.recommendations),
			},
			indent=2,
		)
	)


if __name__ == "__main__":
	asyncio.run(main())
