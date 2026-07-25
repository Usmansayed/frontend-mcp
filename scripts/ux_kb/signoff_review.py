"""Generate human sign-off review sheet for Phase 1 gate."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import db_session, loads
from .paths import KB_ROOT, REPORTS
from .quality_audit import audit_over_budget_candidates, audit_weak_principles


def _card_detail(row) -> dict[str, Any]:
	d = dict(row)
	d["source_ids"] = loads(d.get("source_ids_json"), [])
	d.pop("source_ids_json", None)
	d.pop("supersedes_json", None)
	d.pop("conflicts_with_json", None)
	d.pop("embedding_text", None)
	return d


def build_signoff_review() -> dict[str, Any]:
	with db_session() as conn:
		pending = [
			_card_detail(r)
			for r in conn.execute(
				"""
				SELECT id, topic, title, rule, detect, when_to_apply, when_not_to_apply,
				       tradeoff, quote, source_ids_json, evidence_class, confidence, status
				FROM cards WHERE status='pending_review'
				ORDER BY topic, title
				"""
			).fetchall()
		]
		over_budget = [
			_card_detail(r)
			for r in conn.execute(
				"""
				SELECT id, topic, title, rule, detect, source_ids_json,
				       evidence_class, confidence
				FROM cards WHERE status='rejected_over_budget'
				ORDER BY confidence DESC, topic
				LIMIT 20
				"""
			).fetchall()
		]

	weak = audit_weak_principles(12)
	promote = audit_over_budget_candidates(12)

	return {
		"pending_review": pending,
		"over_budget_promote_candidates": promote,
		"weak_demote_candidates": weak,
		"over_budget_full": over_budget,
		"recommendations": {
			"pending_review": [
				{"id": "UX_VIS_PAGINATIONVS_001", "action": "ACCEPT", "reason": "Clear engineering rule; distinct from infinite scroll anti-pattern"},
				{"id": "UX_COG_OFFLOADCOGNI_001", "action": "ACCEPT", "reason": "Core Nielsen heuristic; high signal for forms/dashboard"},
				{"id": "UX_PRD_FACETEDNAVIG_001", "action": "ACCEPT", "reason": "Checkout/ecommerce IA; note conflict with simple filters"},
			],
			"over_budget_top5": [
				"UX_INX_ARIALIVEREGI_001 — raise feedback_systems budget",
				"UX_ARC_POSTELSLAW_001 — raise forms budget",
				"UX_ARC_INLINEERRORM_001 — raise forms budget",
				"UX_INX_MODALUSAGE_001 — raise feedback_systems budget",
				"UX_ARC_VISIBLELABEL_001 — raise forms budget",
			],
			"weak_principles": "No demotions recommended — 4 were TMP id leaks (fixed). Single-source heuristics OK pending second source.",
		},
	}


def _md_section(title: str, cards: list[dict], *, fields: list[str]) -> list[str]:
	lines = [f"## {title}", ""]
	if not cards:
		lines.append("_None._")
		lines.append("")
		return lines
	for c in cards:
		lines.append(f"### `{c.get('id', c.get('id'))}` — {c.get('title', '')}")
		lines.append("")
		lines.append(f"- **Topic:** {c.get('topic', '—')}")
		lines.append(f"- **Evidence:** {c.get('evidence_class', '—')} | **Confidence:** {c.get('confidence', '—')}")
		if c.get("source_count") is not None:
			lines.append(f"- **Sources:** {c.get('source_count')}")
		elif c.get("source_ids"):
			lines.append(f"- **Sources:** {', '.join(c['source_ids'])}")
		if c.get("flags"):
			lines.append(f"- **Flags:** {', '.join(c['flags'])}")
		if c.get("quality_score") is not None:
			lines.append(f"- **Quality score:** {c['quality_score']}")
		for f in fields:
			val = c.get(f)
			if val:
				lines.append(f"- **{f.replace('_', ' ').title()}:** {val[:400]}{'…' if len(str(val)) > 400 else ''}")
		lines.append("")
		lines.append("**Your call:** `[ ] ACCEPT` `[ ] REJECT` `[ ] DEFER`")
		lines.append("")
	return lines


def write_signoff_review() -> Path:
	data = build_signoff_review()
	REPORTS.mkdir(parents=True, exist_ok=True)
	json_path = REPORTS / "human_signoff.json"
	json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [
		"# Human Sign-Off — Phase 1 Gate",
		"",
		"Review each section. Mark ACCEPT / REJECT / DEFER. Pipeline continues after your approval.",
		"",
		"**Auto-generated:** `python scripts/run_ux_kb.py signoff-review`",
		"",
		"---",
		"",
	]
	lines += _md_section(
		"Pending review (3)",
		data["pending_review"],
		fields=["rule", "detect", "when_to_apply", "quote"],
	)
	lines += [
		"## Agent recommendations (pending)",
		"",
	]
	for r in data["recommendations"]["pending_review"]:
		lines.append(f"- **{r['id']}** → **{r['action']}** — {r['reason']}")
	lines.append("")
	lines += _md_section(
		"Over-budget promote candidates (top 12)",
		data["over_budget_full"][:12],
		fields=["rule"],
	)
	lines += [
		"## Agent recommendations (over-budget)",
		"",
	]
	for r in data["recommendations"]["over_budget_top5"]:
		lines.append(f"- {r}")
	lines.append("")
	lines += _md_section(
		"Weak principle demote candidates",
		data["weak_demote_candidates"],
		fields=[],
	)
	lines += [
		"## Agent note (weak principles)",
		"",
		data["recommendations"]["weak_principles"],
		"",
		"---",
		"",
		"## Sign-off checklist",
		"",
		"- [ ] Pending cards reviewed (3)",
		"- [ ] Over-budget promotions decided (20 total, top 12 above)",
		"- [ ] Weak principles reviewed — no demotions required",
		"- [ ] Retrieval contract v1 approved (`kb/schemas/retrieval_*.schema.json`)",
		"- [ ] Ready for evidence nodes + retrieval engine build",
		"",
	]

	md_path = REPORTS / "HUMAN_SIGNOFF.md"
	md_path.write_text("\n".join(lines), encoding="utf-8")
	return md_path
