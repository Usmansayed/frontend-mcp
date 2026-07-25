"""Supervised acceptance wave with Gemini quality gate (ADC).

Scores pending canonical principles; accepts high-signal cards within topic budgets.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .db import db_session, dumps, loads, utcnow

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))

from foropencode_pipeline import gemini_client  # noqa: E402

# Supervisor topic order (maps to KB topic keys)
ACCEPT_WAVES: list[dict[str, Any]] = [
	{"wave": "accessibility", "topics": ["a11y_absolute", "motor_ergonomics"]},
	{"wave": "forms", "topics": ["forms"]},
	{"wave": "navigation", "topics": ["hierarchy_density", "reading_flow"]},
	{"wave": "information_architecture", "topics": ["settings", "general"]},
	{"wave": "psychology", "topics": ["cognitive_load", "aesthetic_usability", "human_factors"]},
	{"wave": "dashboard", "topics": ["feedback_systems", "hierarchy_density"]},
	{"wave": "onboarding", "topics": ["onboarding", "checkout"]},
	{"wave": "design_systems", "topics": ["design_tokens", "agentic_ux"]},
]

CRITERIA = [
	"timeless",
	"actionable",
	"high_signal",
	"not_duplicate",
	"ai_useful",
]


def _load_pending(topic: str) -> list[dict[str, Any]]:
	with db_session() as conn:
		rows = conn.execute(
			"""
			SELECT id, topic, title, rule, detect, when_to_apply, when_not_to_apply,
			       tradeoff, evidence_class, confidence, source_ids_json, frozen
			FROM cards WHERE status='pending_review' AND topic=?
			ORDER BY confidence DESC, title
			""",
			(topic,),
		).fetchall()
	out = []
	for r in rows:
		d = dict(r)
		d["source_ids"] = loads(d.pop("source_ids_json"), [])
		out.append(d)
	return out


def _compact_for_score(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
	return [
		{
			"id": c["id"],
			"topic": c["topic"],
			"title": c["title"],
			"rule": (c["rule"] or "")[:350],
			"detect": (c.get("detect") or "")[:200],
			"evidence_class": c["evidence_class"],
			"confidence": c["confidence"],
			"source_count": len(c.get("source_ids") or []),
		}
		for c in cards
	]


def score_batch(
	cards: list[dict[str, Any]],
	*,
	accepted_peers: list[dict[str, Any]] | None = None,
	model: str | None = None,
) -> dict[str, Any]:
	"""Gemini quality gate on a batch of pending principles."""
	prompt = f"""You are the UX Knowledge supervisor. Score each canonical principle for inclusion in an AI engineering handbook.

For EACH card, score 0.0-1.0 on:
- timeless: still valid in 5+ years
- actionable: agent can detect/apply in code or UI review
- high_signal: non-obvious, worth storing (not generic "make it usable")
- not_duplicate: not redundant vs accepted peers listed below
- ai_useful: an AI designing UI would actually use this while building

Also verdict: accept | reject | defer
- accept: all scores >= 0.65 and not_duplicate >= 0.7
- reject: low signal, vague, duplicate, or not engineering-actionable
- defer: borderline — needs human review

Already accepted principles in this topic area (avoid duplicates):
{json.dumps(_compact_for_score(accepted_peers or []), indent=2)}

Cards to score:
{json.dumps(_compact_for_score(cards), indent=2)}

Return JSON:
{{
  "decisions": [
    {{
      "id": "UX_...",
      "verdict": "accept|reject|defer",
      "timeless": 0.0-1.0,
      "actionable": 0.0-1.0,
      "high_signal": 0.0-1.0,
      "not_duplicate": 0.0-1.0,
      "ai_useful": 0.0-1.0,
      "reason": "one sentence"
    }}
  ]
}}
"""
	return gemini_client.generate_json(prompt=prompt, temperature=0.05, model=model)


def _load_accepted(topic: str) -> list[dict[str, Any]]:
	with db_session() as conn:
		rows = conn.execute(
			"""
			SELECT id, topic, title, rule, detect, evidence_class, confidence, source_ids_json
			FROM cards WHERE status='accepted' AND topic=?
			""",
			(topic,),
		).fetchall()
	out = []
	for r in rows:
		d = dict(r)
		d["source_ids"] = loads(d.pop("source_ids_json"), [])
		out.append(d)
	return out


def apply_decisions(decisions: list[dict[str, Any]]) -> dict[str, list[str]]:
	accepted: list[str] = []
	rejected: list[str] = []
	deferred: list[str] = []
	now = utcnow()
	with db_session() as conn:
		for d in decisions:
			cid = d["id"]
			verdict = d.get("verdict")
			meta = {k: d.get(k) for k in CRITERIA + ["reason"]}
			if verdict == "accept":
				row = conn.execute(
					"SELECT id, topic, frozen FROM cards WHERE id=? AND status='pending_review'",
					(cid,),
				).fetchone()
				if not row or row["frozen"]:
					deferred.append(cid)
					continue
				# budget enforced in accept_pending per card
				accepted.append(cid)
			elif verdict == "reject":
				conn.execute(
					"UPDATE cards SET status='rejected', updated_at=? WHERE id=? AND status='pending_review'",
					(now, cid),
				)
				rejected.append(cid)
			else:
				deferred.append(cid)
			# store review metadata in supersedes_json slot temporarily — use conflicts_with for review log
			# Actually store in embedding_text append — skip, keep in report only
	return {"accepted": accepted, "rejected": rejected, "deferred": deferred}


def run_accept_wave(
	*,
	wave: str | None = None,
	topic: str | None = None,
	batch_size: int = 12,
	model: str | None = None,
	auto_accept: bool = True,
) -> dict[str, Any]:
	"""Run Gemini-scored acceptance for one wave, topic, or all waves."""
	if model:
		import os

		os.environ["FOROPENCODE_GEMINI_MODEL"] = model

	waves = ACCEPT_WAVES
	if topic and not wave:
		waves = [{"wave": topic, "topics": [topic]}]
	elif wave:
		waves = [w for w in ACCEPT_WAVES if w["wave"] == wave]
		if not waves:
			waves = [{"wave": wave, "topics": [wave]}]

	all_decisions: list[dict[str, Any]] = []
	fail: list[dict[str, str]] = []
	accepted_ids: list[str] = []
	rejected_ids: list[str] = []
	deferred_ids: list[str] = []

	for w in waves:
		for tp in w["topics"]:
			pending = _load_pending(tp)
			if not pending:
				continue
			peers = _load_accepted(tp)
			for i in range(0, len(pending), batch_size):
				batch = pending[i : i + batch_size]
				try:
					result = score_batch(batch, accepted_peers=peers, model=model)
					decisions = result.get("decisions") or []
					all_decisions.extend(decisions)
					buckets = apply_decisions(decisions)
					rejected_ids.extend(buckets["rejected"])
					deferred_ids.extend(buckets["deferred"])
				except Exception as exc:  # noqa: BLE001
					fail.append({"topic": tp, "error": str(exc)[:300]})

	# Re-run targeted accept by id for scored accepts
	if auto_accept:
		for d in all_decisions:
			if d.get("verdict") != "accept":
				continue
			cid = d["id"]
			with db_session() as conn:
				row = conn.execute(
					"SELECT topic, frozen, status FROM cards WHERE id=?", (cid,)
				).fetchone()
				if not row or row["status"] != "pending_review" or row["frozen"]:
					continue
				tp = row["topic"]
				pack = conn.execute(
					"SELECT budget, card_ids_json FROM packs WHERE topic=?", (tp,)
				).fetchone()
				if pack:
					accepted_count = conn.execute(
						"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='accepted'",
						(tp,),
					).fetchone()["c"]
					if accepted_count >= int(pack["budget"]):
						conn.execute(
							"UPDATE cards SET status='rejected_over_budget', updated_at=? WHERE id=?",
							(utcnow(), cid),
						)
						continue
				conn.execute(
					"UPDATE cards SET status='accepted', updated_at=? WHERE id=?",
					(utcnow(), cid),
				)
				if pack:
					ids = json.loads(pack["card_ids_json"] or "[]")
					if cid not in ids:
						ids.append(cid)
						conn.execute(
							"UPDATE packs SET card_ids_json=?, updated_at=? WHERE topic=?",
							(dumps(ids), utcnow(), tp),
						)
				accepted_ids.append(cid)

	with db_session() as conn:
		status_counts = {
			r["status"]: r["c"]
			for r in conn.execute("SELECT status, COUNT(*) AS c FROM cards GROUP BY status").fetchall()
		}

	return {
		"waves_run": [w["wave"] for w in waves],
		"decisions": all_decisions,
		"accepted": accepted_ids,
		"rejected": rejected_ids,
		"deferred": deferred_ids,
		"failed": fail,
		"card_status": status_counts,
	}
