"""End-to-end UX knowledge retrieval validation — landing + dashboard scenarios."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from navigation.mcp.design_intelligence_handlers import handle_design_knowledge_query
from navigation.ux_knowledge.influence_log import log_agent_decision


SCENARIOS = [
	{
		"name": "landing_page_conversion",
		"params": {
			"intent": "Build marketing landing page with hero CTA",
			"surface_type": "landing",
			"phase": "greenfield",
			"user_flow": "conversion",
			"problem": "reading flow",
		},
		"expected_playbook": "pb_landing",
		"agent_decisions": [
			{"recommendation": "Place primary CTA at terminal reading-flow point", "followed": True},
			{"recommendation": "Use F/Z-pattern alignment for text-heavy hero", "followed": True},
			{"recommendation": "44px minimum touch targets on mobile CTA", "followed": True},
		],
	},
	{
		"name": "saas_dashboard",
		"params": {
			"intent": "Build SaaS analytics dashboard with KPI hierarchy",
			"surface_type": "dashboard",
			"phase": "greenfield",
			"product_type": "saas",
			"problem": "information hierarchy",
		},
		"expected_playbook": "pb_dashboard",
		"agent_decisions": [
			{"recommendation": "Use layout primitives not custom CSS margins", "followed": True},
			{"recommendation": "Semantic color tokens for status indicators", "followed": True},
			{"recommendation": "Busy indicator for queries >1s", "followed": False, "reason": "Using skeleton instead for perceived performance"},
		],
	},
]


async def run_e2e() -> dict:
	repo_root = str(REPO)
	results = []
	for sc in SCENARIOS:
		envelope = await handle_design_knowledge_query(
			{
				"query_id": "ux.retrieve",
				"params": sc["params"],
				"repo_root": repo_root,
			}
		)
		knowledge = (envelope.get("data") or {}).get("knowledge") or {}
		answer = knowledge.get("answer") or {}
		retrieval = answer.get("retrieval") or {}
		pb_id = (retrieval.get("matched_playbook") or {}).get("id")
		ok = envelope.get("ok") and pb_id == sc["expected_playbook"]
		req_id = retrieval.get("request_id", "")
		for dec in sc["agent_decisions"]:
			log_agent_decision(
				repo_root=repo_root,
				request_id=req_id,
				recommendation=dec["recommendation"],
				followed=dec["followed"],
				reason=dec.get("reason", ""),
			)
		results.append(
			{
				"scenario": sc["name"],
				"pass": ok,
				"playbook_id": pb_id,
				"expected": sc["expected_playbook"],
				"decisions": len(retrieval.get("decisions") or []),
				"patterns": len(retrieval.get("patterns") or []),
				"principles": len(retrieval.get("principles") or []),
				"conflicts": len(retrieval.get("conflicts") or []),
				"evidence": len(retrieval.get("evidence") or []),
				"traversal": (retrieval.get("meta") or {}).get("traversal_path"),
				"agent_decisions_logged": len(sc["agent_decisions"]),
			}
		)
	passed = sum(1 for r in results if r["pass"])
	report = {
		"scenarios": len(SCENARIOS),
		"passed": passed,
		"coverage": round(passed / max(1, len(SCENARIOS)), 3),
		"results": results,
		"influence_log": str(REPO / "ForOpenCode" / "kb" / "logs" / "influence.jsonl"),
	}
	out = REPO / "ForOpenCode" / "kb" / "reports" / "e2e_validation.json"
	out.write_text(json.dumps(report, indent=2), encoding="utf-8")
	return report


def main() -> None:
	report = asyncio.run(run_e2e())
	print(json.dumps(report, indent=2))
	raise SystemExit(0 if report["passed"] == report["scenarios"] else 1)


if __name__ == "__main__":
	main()
