"""Smoke: UX KB retrieval + Design Sense ux_knowledge provider (MCP-facing paths)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


async def main() -> int:
	from navigation.consistency_intelligence.knowledge.queries.ux_knowledge import handle_ux_retrieve
	from navigation.design_sense_intelligence.models import ReviewRequest
	from navigation.design_sense_intelligence.providers.registry import subjective_providers
	from navigation.design_sense_intelligence.providers.ux_knowledge import UxKnowledgeProvider
	from navigation.mcp.design_intelligence_handlers import handle_design_knowledge_query

	report: dict = {"ok": True, "checks": {}}

	# 1. Provider registered
	names = [p.name for p in subjective_providers()]
	report["checks"]["provider_registered"] = {
		"ok": "ux_knowledge" in names,
		"providers": names,
	}

	# 2. Direct retrieve handler (Knowledge API)
	env = await handle_design_knowledge_query(
		{
			"query_id": "ux.retrieve",
			"params": {
				"intent": "Reduce cognitive load — Hick's law on settings choices",
				"surface_type": "settings",
				"psychology_category": "cognitive_load",
				"phase": "feature",
			},
			"repo_root": str(ROOT),
		}
	)
	knowledge = (env.get("data") or {}).get("knowledge") or {}
	answer = knowledge.get("answer") or {}
	retrieval = answer.get("retrieval") or env.get("data") or {}
	# envelope shapes vary — normalize
	if "matched_playbook" not in retrieval and isinstance(answer, dict):
		retrieval = answer.get("retrieval") or answer
	pb = (retrieval.get("matched_playbook") or {}) if isinstance(retrieval, dict) else {}
	principles = retrieval.get("principles") if isinstance(retrieval, dict) else []
	report["checks"]["ux_retrieve_mcp"] = {
		"ok": bool(env.get("ok")) and bool(pb.get("id") or principles),
		"playbook": pb.get("id"),
		"principles": len(principles or []),
		"transport_ok": env.get("ok"),
	}

	# 3. Design Sense provider — dashboard
	ux = UxKnowledgeProvider()
	dash = await ux.contribute(
		ReviewRequest(
			user_task="Build SaaS analytics dashboard with sidebar hierarchy",
			repo_root=str(ROOT),
		)
	)
	report["checks"]["design_sense_dashboard"] = {
		"ok": "ux_knowledge_structured" in dash.degraded,
		"notes": [n for n in dash.notes if n.startswith("ux_kb:")][:6],
		"findings": len(dash.findings),
		"playbook_note": next((n for n in dash.notes if n.startswith("ux_kb:playbook:")), None),
	}

	# 4. Design Sense provider — psychology
	psych = await ux.contribute(
		ReviewRequest(
			user_task="Reduce cognitive load and Hick choice overload in feature menus",
			repo_root=str(ROOT),
		)
	)
	pb_note = next((n for n in psych.notes if n.startswith("ux_kb:playbook:")), "")
	report["checks"]["design_sense_psychology"] = {
		"ok": "ux_knowledge_structured" in psych.degraded
		and ("pb_psychology" in pb_note or "pack_psychology" in " ".join(psych.notes)),
		"structured": "ux_knowledge_structured" in psych.degraded,
		"findings": len(psych.findings),
		"notes": [n for n in psych.notes if n.startswith("ux_kb:")][:6],
		"playbook_note": pb_note or None,
	}

	# 5. Forms surface
	forms = await ux.contribute(
		ReviewRequest(user_task="Sign in form password visibility", repo_root=str(ROOT))
	)
	report["checks"]["design_sense_forms"] = {
		"ok": "ux_knowledge_structured" in forms.degraded,
		"findings": len(forms.findings),
		"playbook_note": next((n for n in forms.notes if n.startswith("ux_kb:playbook:")), None),
	}

	report["ok"] = all(c.get("ok") for c in report["checks"].values())
	out = ROOT / "ForOpenCode" / "kb" / "reports" / "mcp_ux_kb_smoke.json"
	out.parent.mkdir(parents=True, exist_ok=True)
	out.write_text(json.dumps(report, indent=2), encoding="utf-8")
	print(json.dumps(report, indent=2))
	print(f"\nMCP UX KB smoke: {'PASS' if report['ok'] else 'FAIL'} -> {out}")
	return 0 if report["ok"] else 1


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
