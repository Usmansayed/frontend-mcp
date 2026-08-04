"""Principle-identity dedup: cluster pending cards → canonical cards.

Groups by underlying UX principle (not text similarity), merges duplicates,
preserves all source references, and records conflicts.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .db import db_session, dumps, loads, utcnow
from .seed import upsert_card

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))

from foropencode_pipeline import gemini_client  # noqa: E402

TOPIC_ID_PREFIX = {
	"a11y_absolute": "A11Y",
	"motor_ergonomics": "HCI",
	"cognitive_load": "COG",
	"hierarchy_density": "VIS",
	"forms": "ARC",
	"onboarding": "PRD",
	"checkout": "PRD",
	"feedback_systems": "INX",
	"design_tokens": "DS",
	"reading_flow": "VIS",
	"human_factors": "HFE",
	"settings": "SET",
	"aesthetic_usability": "COG",
	"agentic_ux": "AGT",
	"general": "GEN",
}

EVIDENCE_RANK = {"standard": 5, "law": 4, "empirical": 3, "heuristic": 2, "opinion": 1}


def _slug(text: str, max_len: int = 12) -> str:
	s = re.sub(r"[^a-zA-Z0-9]+", "", text or "RULE")
	return (s or "RULE")[:max_len].upper()


def _card_row_to_dict(row) -> dict[str, Any]:
	return {
		"id": row["id"],
		"topic": row["topic"],
		"title": row["title"],
		"rule": row["rule"],
		"detect": row["detect"],
		"when_to_apply": row["when_to_apply"],
		"when_not_to_apply": row["when_not_to_apply"],
		"tradeoff": row["tradeoff"],
		"quote": row["quote"] or "",
		"source_ids": loads(row["source_ids_json"], []),
		"evidence_class": row["evidence_class"],
		"confidence": float(row["confidence"]),
		"status": row["status"],
		"frozen": bool(row["frozen"]),
	}


def _compact_card(card: dict[str, Any]) -> dict[str, Any]:
	return {
		"id": card["id"],
		"title": card["title"],
		"rule": (card["rule"] or "")[:400],
		"when_to_apply": (card["when_to_apply"] or "")[:200],
		"when_not_to_apply": (card["when_not_to_apply"] or "")[:200],
		"source_ids": card.get("source_ids") or [],
		"evidence_class": card.get("evidence_class"),
	}


def _load_cards(
	conn,
	*,
	status: str,
	topic: str | None = None,
	id_prefix: str | None = None,
	id_not_prefix: str | None = None,
) -> list[dict[str, Any]]:
	q = """
		SELECT id, topic, title, rule, detect, when_to_apply, when_not_to_apply,
		       tradeoff, quote, source_ids_json, evidence_class, confidence, status, frozen
		FROM cards WHERE status=?
	"""
	params: list[Any] = [status]
	if topic:
		q += " AND topic=?"
		params.append(topic)
	if id_prefix:
		q += " AND id LIKE ?"
		params.append(f"{id_prefix}%")
	if id_not_prefix:
		q += " AND id NOT LIKE ?"
		params.append(f"{id_not_prefix}%")
	q += " ORDER BY topic, title"
	return [_card_row_to_dict(r) for r in conn.execute(q, params).fetchall()]


def cluster_by_principle(
	*,
	topic: str,
	pending: list[dict[str, Any]],
	accepted: list[dict[str, Any]],
	canonical: list[dict[str, Any]] | None = None,
	model: str | None = None,
) -> dict[str, Any]:
	"""Ask Gemini to cluster cards by principle identity within a topic."""
	if not pending:
		return {"clusters": [], "unassigned": []}

	existing = accepted + (canonical or [])

	prompt = f"""Cluster UX engineering rule cards by PRINCIPLE IDENTITY — not text similarity.

Topic scope: {topic}

Two cards belong to the SAME cluster if they express the same underlying UX principle, law,
heuristic, or pattern — even when worded differently.

SAME principle examples:
- "Progressive Disclosure" / "Reveal complexity gradually" / "Show advanced options on demand"
- "Minimum 44px tap target" / "Use $square-icon-medium token for touch targets"

DIFFERENT principles (do NOT merge):
- Pagination vs infinite scroll (competing patterns — note as conflict, separate clusters)
- Visual hierarchy via whitespace vs F-pattern scanning (related but distinct)
- Form validation timing vs error message placement (distinct concerns)

Existing canonical/accepted cards already in the KB (match pending cards to these when same principle):
{json.dumps([_compact_card(c) for c in existing], indent=2)}

Pending cards to cluster (every id must appear exactly once):
{json.dumps([_compact_card(c) for c in pending], indent=2)}

Return JSON:
{{
  "clusters": [
    {{
      "principle_key": "snake_case_short_id",
      "principle_label": "Established Principle Name",
      "member_ids": ["pending_card_id", "..."],
      "matches_accepted_id": "UX_..." or null,
      "conflict_notes": "null or brief note if members disagree on application",
      "confidence": 0.0-1.0
    }}
  ],
  "unassigned": []
}}

Rules:
- Every pending card id must appear in exactly one cluster's member_ids (singletons ok).
- Prefer established names (Progressive Disclosure, Fitts's Law, etc.) for principle_label.
- If a pending card matches an existing canonical/accepted card's principle, set matches_accepted_id to that card's id.
- Do not merge cards that recommend opposite UX choices into one cluster.
"""
	return gemini_client.generate_json(prompt=prompt, temperature=0.05, model=model)


def merge_cluster(
	*,
	topic: str,
	principle_key: str,
	principle_label: str,
	members: list[dict[str, Any]],
	conflict_notes: str | None,
	model: str | None = None,
) -> dict[str, Any]:
	"""Synthesize one canonical card from cluster members."""
	prompt = f"""Synthesize ONE canonical UX engineering rule card from cards expressing the same principle.

Principle: {principle_label} ({principle_key})
Topic: {topic}

Member cards:
{json.dumps(members, indent=2)}

Conflict notes from clustering: {conflict_notes or "none"}

Return JSON object with fields:
{{
  "title": "prefer established principle name",
  "rule": "best synthesized actionable rule",
  "detect": "combined detection heuristics",
  "when_to_apply": "merged",
  "when_not_to_apply": "merged",
  "tradeoff": "merged",
  "quote": "best verbatim quote from members or empty string",
  "evidence_class": "law|standard|empirical|heuristic|opinion",
  "confidence": 0.0-1.0,
  "internal_tensions": "null or brief note if members partially disagree"
}}

Use highest-authority evidence_class among members. Boost confidence when multiple authoritative sources agree.
"""
	data = gemini_client.generate_json(prompt=prompt, temperature=0.1, model=model)
	data["principle_key"] = principle_key
	data["principle_label"] = principle_label
	return data


def _next_canonical_id(conn, topic: str, principle_key: str) -> str:
	prefix = TOPIC_ID_PREFIX.get(topic, "GEN")
	slug = _slug(principle_key.replace("_", " "))
	base = f"UX_{prefix}_{slug}"
	rows = conn.execute(
		"SELECT id FROM cards WHERE id LIKE ? ORDER BY id",
		(f"{base}_%",),
	).fetchall()
	used = {r["id"] for r in rows}
	for n in range(1, 1000):
		candidate = f"{base}_{n:03d}"
		if candidate not in used:
			return candidate
	raise RuntimeError(f"exhausted ids for {base}")


def _union_sources(cards: list[dict[str, Any]]) -> list[str]:
	seen: set[str] = set()
	out: list[str] = []
	for card in cards:
		for sid in card.get("source_ids") or []:
			if sid not in seen:
				seen.add(sid)
				out.append(sid)
	return out


def _best_evidence(cards: list[dict[str, Any]]) -> str:
	best = "heuristic"
	best_rank = 0
	for card in cards:
		ec = card.get("evidence_class") or "heuristic"
		rank = EVIDENCE_RANK.get(ec, 0)
		if rank > best_rank:
			best_rank = rank
			best = ec
	return best


def _boost_confidence(cards: list[dict[str, Any]], merged_confidence: float) -> float:
	source_count = len(_union_sources(cards))
	base = max(float(c.get("confidence") or 0.7) for c in cards)
	boost = min(0.15, 0.03 * max(0, source_count - 1))
	return min(1.0, max(base, merged_confidence) + boost)


def _build_embedding_text(card: dict[str, Any]) -> str:
	return "\n".join(
		[
			f"Title: {card.get('title')}",
			f"Topic: {card.get('topic')}",
			f"Principle: {card.get('principle_label') or ''}",
			f"Rule: {card.get('rule')}",
			f"Detect: {card.get('detect')}",
			f"When: {card.get('when_to_apply')}",
			f"When not: {card.get('when_not_to_apply')}",
			f"Tradeoff: {card.get('tradeoff')}",
			f"Quote: {card.get('quote') or ''}",
		]
	)


def _apply_cluster(
	conn,
	*,
	topic: str,
	cluster: dict[str, Any],
	pending_by_id: dict[str, dict[str, Any]],
	accepted_by_id: dict[str, dict[str, Any]],
	canonical_by_id: dict[str, dict[str, Any]] | None = None,
	model: str | None = None,
	dry_run: bool = False,
) -> dict[str, Any]:
	member_ids = cluster.get("member_ids") or []
	members = [pending_by_id[mid] for mid in member_ids if mid in pending_by_id]
	if not members:
		return {"skipped": True, "reason": "no_members", "cluster": cluster}

	principle_key = cluster.get("principle_key") or _slug(cluster.get("principle_label") or members[0]["title"]).lower()
	principle_label = cluster.get("principle_label") or members[0]["title"]
	match_id = cluster.get("matches_accepted_id")

	if len(members) == 1 and not match_id:
		# Singleton — re-ID to canonical form, keep content
		member = members[0]
		card_id = _next_canonical_id(conn, topic, principle_key)
		canonical = {
			**member,
			"id": card_id,
			"source_ids": _union_sources(members),
			"confidence": _boost_confidence(members, member["confidence"]),
			"supersedes": [member["id"]],
			"conflicts_with": [],
			"embedding_text": _build_embedding_text({**member, "principle_label": principle_label}),
			"status": "pending_review",
			"frozen": 0,
		}
		if dry_run:
			return {
				"action": "singleton_reid",
				"canonical_id": card_id,
				"merged": [member["id"]],
				"sources": canonical["source_ids"],
			}
		upsert_card(conn, canonical)
		conn.execute(
			"UPDATE cards SET status='merged', supersedes_json=?, updated_at=? WHERE id=?",
			(dumps([card_id]), utcnow(), member["id"]),
		)
		conn.execute(
			"""
			INSERT INTO principle_clusters (
			  principle_key, principle_label, topic, canonical_card_id,
			  member_ids_json, supporting_source_ids_json, conflicting_source_ids_json,
			  conflict_summary, cluster_json, created_at
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				principle_key,
				principle_label,
				topic,
				card_id,
				dumps(member_ids),
				dumps(canonical["source_ids"]),
				dumps([]),
				cluster.get("conflict_notes"),
				dumps(cluster),
				utcnow(),
			),
		)
		return {"action": "singleton_reid", "canonical_id": card_id, "merged": [member["id"]]}

	# Multi-member or match to accepted/canonical
	existing_pool = {**accepted_by_id, **(canonical_by_id or {})}
	if match_id and match_id in existing_pool:
		target = existing_pool[match_id]
		new_sources = _union_sources([target, *members])
		action = "extend_accepted" if match_id in accepted_by_id else "extend_canonical"
		if dry_run:
			return {
				"action": action,
				"canonical_id": match_id,
				"merged": member_ids,
				"sources": new_sources,
			}
		conn.execute(
			"""
			UPDATE cards SET source_ids_json=?, confidence=?, updated_at=?
			WHERE id=?
			""",
			(
				dumps(new_sources),
				min(1.0, max(float(target["confidence"]), _boost_confidence(members, 0.8))),
				utcnow(),
				match_id,
			),
		)
		for mid in member_ids:
			conn.execute(
				"UPDATE cards SET status='merged', supersedes_json=?, updated_at=? WHERE id=?",
				(dumps([match_id]), utcnow(), mid),
			)
		conn.execute(
			"""
			INSERT INTO principle_clusters (
			  principle_key, principle_label, topic, canonical_card_id,
			  member_ids_json, supporting_source_ids_json, conflicting_source_ids_json,
			  conflict_summary, cluster_json, created_at
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				principle_key,
				principle_label,
				topic,
				match_id,
				dumps(member_ids),
				dumps(new_sources),
				dumps([]),
				cluster.get("conflict_notes"),
				dumps(cluster),
				utcnow(),
			),
		)
		return {"action": action, "canonical_id": match_id, "merged": member_ids}

	merged = merge_cluster(
		topic=topic,
		principle_key=principle_key,
		principle_label=principle_label,
		members=members,
		conflict_notes=cluster.get("conflict_notes"),
		model=model,
	)
	card_id = _next_canonical_id(conn, topic, principle_key)
	sources = _union_sources(members)
	canonical = {
		"id": card_id,
		"topic": topic,
		"title": merged.get("title") or principle_label,
		"rule": merged.get("rule") or "",
		"detect": merged.get("detect") or "",
		"when_to_apply": merged.get("when_to_apply") or "",
		"when_not_to_apply": merged.get("when_not_to_apply") or "",
		"tradeoff": merged.get("tradeoff") or "",
		"quote": merged.get("quote") or "",
		"source_ids": sources,
		"evidence_class": merged.get("evidence_class") or _best_evidence(members),
		"confidence": _boost_confidence(members, float(merged.get("confidence") or 0.8)),
		"supersedes": member_ids,
		"conflicts_with": [],
		"embedding_text": _build_embedding_text({**merged, "topic": topic, "principle_label": principle_label}),
		"status": "pending_review",
		"frozen": 0,
	}
	if dry_run:
		return {
			"action": "merge",
			"canonical_id": card_id,
			"merged": member_ids,
			"sources": sources,
			"title": canonical["title"],
		}
	upsert_card(conn, canonical)
	for mid in member_ids:
		conn.execute(
			"UPDATE cards SET status='merged', supersedes_json=?, updated_at=? WHERE id=?",
			(dumps([card_id]), utcnow(), mid),
		)
	if cluster.get("conflict_notes") or merged.get("internal_tensions"):
		conn.execute(
			"""
			INSERT INTO conflicts (card_a, card_b, summary, decision_hint, created_at)
			VALUES (?, ?, ?, ?, ?)
			""",
			(
				card_id,
				card_id,
				cluster.get("conflict_notes") or merged.get("internal_tensions") or "",
				"review_tension",
				utcnow(),
			),
		)
	conn.execute(
		"""
		INSERT INTO principle_clusters (
		  principle_key, principle_label, topic, canonical_card_id,
		  member_ids_json, supporting_source_ids_json, conflicting_source_ids_json,
		  conflict_summary, cluster_json, created_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		""",
		(
			principle_key,
			principle_label,
			topic,
			card_id,
			dumps(member_ids),
			dumps(sources),
			dumps([]),
			cluster.get("conflict_notes") or merged.get("internal_tensions"),
			dumps({**cluster, "merged": merged}),
			utcnow(),
		),
	)
	return {
		"action": "merge",
		"canonical_id": card_id,
		"merged": member_ids,
		"sources": sources,
		"title": canonical["title"],
	}


def run_dedup_batch(
	*,
	topic: str | None = None,
	model: str | None = None,
	dry_run: bool = False,
	incremental: bool = False,
) -> dict[str, Any]:
	"""Cluster pending_review cards by principle identity and write canonical cards.

	When incremental=True, only process raw UX_TMP_* cards (post-extract, pre-dedup).
	Existing canonical pending_review cards are used as merge targets.
	"""
	if model:
		import os

		os.environ["FOROPENCODE_GEMINI_MODEL"] = model

	ok: list[dict[str, Any]] = []
	fail: list[dict[str, str]] = []
	clusters_written = 0
	cards_merged = 0
	canonical_created = 0

	with db_session() as conn:
		if incremental:
			topics = (
				[topic]
				if topic
				else [
					r["topic"]
					for r in conn.execute(
						"""
						SELECT DISTINCT topic FROM cards
						WHERE status='pending_review' AND id LIKE 'UX_TMP_%'
						ORDER BY topic
						"""
					).fetchall()
				]
			)
		else:
			topics = (
				[topic]
				if topic
				else [
					r["topic"]
					for r in conn.execute(
						"SELECT DISTINCT topic FROM cards WHERE status='pending_review' ORDER BY topic"
					).fetchall()
				]
			)

	for tp in topics:
		try:
			with db_session() as conn:
				if incremental:
					pending = _load_cards(
						conn, status="pending_review", topic=tp, id_prefix="UX_TMP_"
					)
					canonical = _load_cards(
						conn, status="pending_review", topic=tp, id_not_prefix="UX_TMP_"
					)
				else:
					pending = _load_cards(conn, status="pending_review", topic=tp)
					canonical = []
				accepted = _load_cards(conn, status="accepted", topic=tp)
			if not pending:
				continue

			cluster_result = cluster_by_principle(
				topic=tp,
				pending=pending,
				accepted=accepted,
				canonical=canonical,
				model=model,
			)
			clusters = cluster_result.get("clusters") or []
			pending_by_id = {c["id"]: c for c in pending}
			accepted_by_id = {c["id"]: c for c in accepted}
			canonical_by_id = {c["id"]: c for c in canonical}

			# Validate coverage
			assigned: set[str] = set()
			for cl in clusters:
				for mid in cl.get("member_ids") or []:
					assigned.add(mid)
			missing = set(pending_by_id) - assigned
			if missing:
				for mid in sorted(missing):
					clusters.append(
						{
							"principle_key": _slug(pending_by_id[mid]["title"]).lower(),
							"principle_label": pending_by_id[mid]["title"],
							"member_ids": [mid],
							"matches_accepted_id": None,
							"conflict_notes": None,
							"confidence": 0.7,
						}
					)

			with db_session() as conn:
				for cl in clusters:
					result = _apply_cluster(
						conn,
						topic=tp,
						cluster=cl,
						pending_by_id=pending_by_id,
						accepted_by_id=accepted_by_id,
						canonical_by_id=canonical_by_id,
						model=model,
						dry_run=dry_run,
					)
					if result.get("skipped"):
						continue
					clusters_written += 1
					cards_merged += len(result.get("merged") or [])
					if result.get("action") in ("merge", "singleton_reid"):
						canonical_created += 1
					ok.append({"topic": tp, **result})

		except Exception as exc:  # noqa: BLE001
			fail.append({"topic": tp, "error": str(exc)})

	with db_session() as conn:
		pending_left = conn.execute(
			"SELECT COUNT(*) AS c FROM cards WHERE status='pending_review'"
		).fetchone()["c"]
		raw_pending = conn.execute(
			"SELECT COUNT(*) AS c FROM cards WHERE status='pending_review' AND id LIKE 'UX_TMP_%'"
		).fetchone()["c"]
		merged_count = conn.execute(
			"SELECT COUNT(*) AS c FROM cards WHERE status='merged'"
		).fetchone()["c"]
		cluster_count = conn.execute("SELECT COUNT(*) AS c FROM principle_clusters").fetchone()["c"]

	return {
		"ok": ok,
		"failed": fail,
		"topics_processed": len(topics),
		"clusters_written": clusters_written,
		"cards_merged": cards_merged,
		"canonical_created": canonical_created,
		"pending_review_remaining": pending_left,
		"raw_pending_remaining": raw_pending,
		"merged_total": merged_count,
		"principle_clusters_total": cluster_count,
		"dry_run": dry_run,
		"incremental": incremental,
	}


def dedup_review(limit: int = 20) -> dict[str, Any]:
	"""Supervisor view of principle clusters + canonical cards."""
	with db_session() as conn:
		clusters = [
			dict(r)
			for r in conn.execute(
				"""
				SELECT id, principle_key, principle_label, topic, canonical_card_id,
				       member_ids_json, supporting_source_ids_json, conflict_summary, created_at
				FROM principle_clusters
				ORDER BY id DESC
				LIMIT ?
				""",
				(limit,),
			).fetchall()
		]
		for cl in clusters:
			cl["member_ids"] = loads(cl.pop("member_ids_json"), [])
			cl["supporting_source_ids"] = loads(cl.pop("supporting_source_ids_json"), [])
		multi = [c for c in clusters if len(c["member_ids"]) > 1]
		by_topic = conn.execute(
			"""
			SELECT topic, COUNT(*) AS clusters,
			       SUM(json_array_length(member_ids_json)) AS raw_members
			FROM principle_clusters GROUP BY topic ORDER BY topic
			"""
		).fetchall()
		status = {
			r["status"]: r["c"]
			for r in conn.execute("SELECT status, COUNT(*) AS c FROM cards GROUP BY status").fetchall()
		}
	return {
		"card_status": status,
		"clusters_by_topic": [dict(r) for r in by_topic],
		"multi_member_clusters": len(multi),
		"sample_merges": [
			{
				"principle": c["principle_label"],
				"topic": c["topic"],
				"canonical": c["canonical_card_id"],
				"merged_count": len(c["member_ids"]),
				"sources": len(c["supporting_source_ids"]),
				"conflict": c.get("conflict_summary"),
			}
			for c in multi[:10]
		],
		"recent_clusters": clusters[:limit],
	}
