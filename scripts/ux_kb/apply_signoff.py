"""Apply default Phase 1 human sign-off decisions."""
from __future__ import annotations

import json
from typing import Any

from .db import db_session, dumps, utcnow
from .paths import KB_ROOT, TOPIC_BUDGETS

PENDING_ACCEPT = [
	"UX_VIS_PAGINATIONVS_001",
	"UX_COG_OFFLOADCOGNI_001",
	"UX_PRD_FACETEDNAVIG_001",
]

OVER_BUDGET_PROMOTE = [
	"UX_INX_ARIALIVEREGI_001",
	"UX_INX_MODALUSAGE_001",
	"UX_INX_NOTIFICATION_001",
	"UX_ARC_POSTELSLAW_001",
	"UX_ARC_INLINEERRORM_001",
]

BUDGET_BUMPS = {
	"feedback_systems": 8,
	"forms": 10,
	"hierarchy_density": 7,
	"cognitive_load": 6,
	"checkout": 6,
}


def _bump_topic_budgets() -> dict[str, int]:
	import yaml

	data = yaml.safe_load(TOPIC_BUDGETS.read_text(encoding="utf-8")) or {}
	budgets = data.get("budgets") or {}
	for topic, new_budget in BUDGET_BUMPS.items():
		budgets[topic] = max(int(budgets.get(topic, 0)), new_budget)
	data["budgets"] = budgets
	data["updated"] = utcnow()[:10]
	TOPIC_BUDGETS.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
	return budgets


def apply_default_signoff() -> dict[str, Any]:
	accepted: list[str] = []
	promoted: list[str] = []
	skipped: list[dict[str, str]] = []

	budgets = _bump_topic_budgets()

	with db_session() as conn:
		for topic, budget in BUDGET_BUMPS.items():
			conn.execute(
				"""
				INSERT INTO packs (topic, budget, card_ids_json, updated_at)
				VALUES (?, ?, '[]', ?)
				ON CONFLICT(topic) DO UPDATE SET budget=excluded.budget, updated_at=excluded.updated_at
				""",
				(topic, budget, utcnow()),
			)

		for cid in PENDING_ACCEPT + OVER_BUDGET_PROMOTE:
			row = conn.execute("SELECT id, topic, status FROM cards WHERE id=?", (cid,)).fetchone()
			if not row:
				skipped.append({"id": cid, "reason": "not_found"})
				continue
			if row["status"] == "accepted":
				skipped.append({"id": cid, "reason": "already_accepted"})
				continue

			topic = row["topic"]
			pack = conn.execute(
				"SELECT budget, card_ids_json FROM packs WHERE topic=?", (topic,)
			).fetchone()
			budget = int(pack["budget"]) if pack else budgets.get(topic, 99)
			accepted_count = conn.execute(
				"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='accepted'", (topic,)
			).fetchone()["c"]

			if accepted_count >= budget and cid not in OVER_BUDGET_PROMOTE:
				skipped.append({"id": cid, "reason": "over_budget"})
				continue

			conn.execute(
				"UPDATE cards SET status='accepted', updated_at=? WHERE id=?",
				(utcnow(), cid),
			)
			if cid in PENDING_ACCEPT:
				accepted.append(cid)
			else:
				promoted.append(cid)

			if pack:
				ids = json.loads(pack["card_ids_json"] or "[]")
				if cid not in ids:
					ids.append(cid)
					conn.execute(
						"UPDATE packs SET card_ids_json=?, updated_at=? WHERE topic=?",
						(dumps(ids), utcnow(), topic),
					)

	return {
		"accepted_pending": accepted,
		"promoted_over_budget": promoted,
		"skipped": skipped,
		"budget_bumps": BUDGET_BUMPS,
	}
