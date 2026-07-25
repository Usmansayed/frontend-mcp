"""Seed import: ForOpenCode normalized cards → SQLite accepted cards."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import dumps, init_db, utcnow, db_session
from .paths import NORMALIZED_SEED

# Map claim id prefix / known ids → topic budgets keys
TOPIC_BY_ID_PREFIX = {
	"UX_A11Y_": "a11y_absolute",
	"UX_HCI_": "motor_ergonomics",
	"UX_COG_": "cognitive_load",
	"UX_VIS_": "hierarchy_density",
	"UX_ARC_FORM": "forms",
	"UX_ARC_": "forms",
	"UX_PRD_": "onboarding",
	"UX_INX_": "feedback_systems",
	"UX_DS_TOKEN": "design_tokens",
	"UX_DS_DENS": "hierarchy_density",
	"UX_HFE_": "human_factors",
}

TOPIC_OVERRIDES = {
	"UX_VIS_READ_014": "reading_flow",
	"UX_VIS_GEST_006": "hierarchy_density",
	"UX_COG_FOGG_013": "onboarding",
	"UX_PRD_GUEST_001": "checkout",
	"UX_ARC_FORM_010": "forms",
}


def infer_topic(card_id: str) -> str:
	if card_id in TOPIC_OVERRIDES:
		return TOPIC_OVERRIDES[card_id]
	for prefix, topic in TOPIC_BY_ID_PREFIX.items():
		if card_id.startswith(prefix):
			return topic
	return "general"


def claim_to_kb_card(raw: dict[str, Any]) -> dict[str, Any]:
	card_id = raw["id"]
	topic = infer_topic(card_id)
	rule = raw.get("definition") or raw.get("engineering_meaning") or ""
	detect = raw.get("how_to_detect_violations") or ""
	when_to = raw.get("when_to_apply") or ""
	when_not = raw.get("when_not_to_apply") or ""
	tradeoff = raw.get("tradeoffs") or raw.get("tradeoff") or ""
	title = raw.get("name") or card_id
	source_ids = raw.get("supporting_source_ids") or []
	evidence = raw.get("evidence_class") or "heuristic"
	confidence = float(raw.get("confidence") or 0.8)
	conflicts = raw.get("conflict_claim_ids") or []
	embedding_text = "\n".join(
		[
			f"Title: {title}",
			f"Topic: {topic}",
			f"Rule: {rule}",
			f"Detect: {detect}",
			f"When: {when_to}",
			f"When not: {when_not}",
			f"Tradeoff: {tradeoff}",
		]
	)
	frozen = 1 if topic == "a11y_absolute" or card_id.startswith("UX_A11Y_") else 0
	return {
		"id": card_id,
		"topic": topic,
		"title": title,
		"rule": rule,
		"detect": detect,
		"when_to_apply": when_to,
		"when_not_to_apply": when_not,
		"tradeoff": tradeoff,
		"quote": "",
		"source_ids": source_ids,
		"evidence_class": evidence,
		"confidence": confidence,
		"supersedes": [],
		"conflicts_with": conflicts,
		"embedding_text": embedding_text,
		"status": "accepted",
		"frozen": frozen,
	}


def upsert_card(conn, card: dict[str, Any]) -> None:
	now = utcnow()
	conn.execute(
		"""
		INSERT INTO cards (
		  id, topic, title, rule, detect, when_to_apply, when_not_to_apply, tradeoff,
		  quote, source_ids_json, evidence_class, confidence, supersedes_json,
		  conflicts_with_json, embedding_text, status, frozen, created_at, updated_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
		  topic=excluded.topic,
		  title=excluded.title,
		  rule=excluded.rule,
		  detect=excluded.detect,
		  when_to_apply=excluded.when_to_apply,
		  when_not_to_apply=excluded.when_not_to_apply,
		  tradeoff=excluded.tradeoff,
		  source_ids_json=excluded.source_ids_json,
		  evidence_class=excluded.evidence_class,
		  confidence=excluded.confidence,
		  conflicts_with_json=excluded.conflicts_with_json,
		  embedding_text=excluded.embedding_text,
		  status=excluded.status,
		  frozen=excluded.frozen,
		  updated_at=excluded.updated_at
		""",
		(
			card["id"],
			card["topic"],
			card["title"],
			card["rule"],
			card["detect"],
			card["when_to_apply"],
			card["when_not_to_apply"],
			card["tradeoff"],
			card.get("quote") or "",
			dumps(card.get("source_ids") or []),
			card["evidence_class"],
			card["confidence"],
			dumps(card.get("supersedes") or []),
			dumps(card.get("conflicts_with") or []),
			card.get("embedding_text") or "",
			card.get("status") or "accepted",
			int(card.get("frozen") or 0),
			now,
			now,
		),
	)


def seed_import(seed_dir: Path | None = None) -> dict[str, int]:
	init_db()
	root = seed_dir or NORMALIZED_SEED
	paths = sorted(root.glob("UX_*.json"))
	imported = 0
	with db_session() as conn:
		for path in paths:
			raw = json.loads(path.read_text(encoding="utf-8"))
			if "id" not in raw:
				continue
			card = claim_to_kb_card(raw)
			upsert_card(conn, card)
			imported += 1
	return {"imported": imported, "files": len(paths)}
