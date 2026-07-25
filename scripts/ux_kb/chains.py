"""LangChain-style extract/normalize chains using Gemini ADC.

Uses LangChain RunnableLambda + optional langchain packages when installed.
Gemini calls reuse foropencode_pipeline.gemini_client (ADC/Vertex).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .db import db_session, dumps, utcnow
from .paths import CARD_SCHEMA, RAW
from .scrape_worker import claim_jobs, finish_job
from .seed import upsert_card

# Import Gemini client from sibling package
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))

from foropencode_pipeline import gemini_client  # noqa: E402

try:
	from langchain_core.runnables import RunnableLambda

	HAS_LANGCHAIN = True
except ImportError:  # pragma: no cover
	HAS_LANGCHAIN = False
	RunnableLambda = None  # type: ignore


MAX_SNAPSHOT = 50_000


def _read_snapshot(source_id: str, snapshot_path: str | None) -> str:
	path = Path(snapshot_path) if snapshot_path else RAW / source_id / "snapshot.md"
	text = path.read_text(encoding="utf-8", errors="replace")
	if len(text) > MAX_SNAPSHOT:
		return text[:MAX_SNAPSHOT] + "\n\n[TRUNCATED]"
	return text


def extract_payload(inputs: dict[str, Any]) -> dict[str, Any]:
	"""LLM extract → candidate JSON."""
	schema = CARD_SCHEMA.read_text(encoding="utf-8")
	prompt = f"""Extract up to {inputs.get('max_cards', 1)} high-signal UX engineering rule(s) from the snapshot.

Respect curator notes:
GET: {inputs.get('get_notes') or ''}
SKIP: {inputs.get('skip_notes') or ''}
TOPIC: {inputs.get('topic')}

Return JSON object:
{{
  "candidates": [
    {{
      "title": "...",
      "rule": "...",
      "detect": "...",
      "when_to_apply": "...",
      "when_not_to_apply": "...",
      "tradeoff": "...",
      "quote": "verbatim short quote from snapshot",
      "evidence_class": "law|standard|empirical|heuristic|opinion",
      "confidence": 0.0-1.0
    }}
  ]
}}

Target card shape schema (for field meanings):
{schema}

SNAPSHOT:
---
{inputs['snapshot']}
---
"""
	data = gemini_client.generate_json(prompt=prompt, temperature=0.1)
	if "candidates" not in data and isinstance(data.get("claims"), list):
		data = {"candidates": data["claims"]}
	data.setdefault("candidates", [])
	return data


def re_slug(text: str) -> str:
	s = re.sub(r"[^a-zA-Z0-9]+", "", text)
	return (s or "RULE")[:16]


def normalize_payload(inputs: dict[str, Any]) -> dict[str, Any]:
	"""Turn one candidate into a KB card draft."""
	cand = inputs["candidate"]
	topic = inputs["topic"]
	source_id = inputs["source_id"]
	slug = re_slug(cand.get("title") or "rule")
	card_id = inputs.get("card_id") or f"UX_TMP_{slug[:12].upper()}_001"
	embedding_text = "\n".join(
		[
			f"Title: {cand.get('title')}",
			f"Topic: {topic}",
			f"Rule: {cand.get('rule')}",
			f"Detect: {cand.get('detect')}",
			f"When: {cand.get('when_to_apply')}",
			f"When not: {cand.get('when_not_to_apply')}",
			f"Tradeoff: {cand.get('tradeoff')}",
			f"Quote: {cand.get('quote') or ''}",
		]
	)
	return {
		"id": card_id,
		"topic": topic,
		"title": cand.get("title") or card_id,
		"rule": cand.get("rule") or "",
		"detect": cand.get("detect") or "",
		"when_to_apply": cand.get("when_to_apply") or "",
		"when_not_to_apply": cand.get("when_not_to_apply") or "",
		"tradeoff": cand.get("tradeoff") or "",
		"quote": cand.get("quote") or "",
		"source_ids": [source_id],
		"evidence_class": cand.get("evidence_class") or "heuristic",
		"confidence": float(cand.get("confidence") or 0.7),
		"supersedes": [],
		"conflicts_with": [],
		"embedding_text": embedding_text,
		"status": "pending_review",
		"frozen": 0,
	}


def build_extract_chain():
	if HAS_LANGCHAIN:
		return RunnableLambda(extract_payload)
	return extract_payload


def build_normalize_chain():
	if HAS_LANGCHAIN:
		return RunnableLambda(normalize_payload)
	return normalize_payload


def run_extract_batch(
	limit: int = 5,
	model: str | None = None,
	*,
	source_ids: set[str] | None = None,
) -> dict[str, Any]:
	if model:
		import os

		os.environ["FOROPENCODE_GEMINI_MODEL"] = model
	chain = build_extract_chain()
	ok: list[str] = []
	fail: list[dict[str, str]] = []
	with db_session() as conn:
		jobs = claim_jobs(conn, "extract", limit, source_ids=source_ids)
		conn.commit()
	for job in jobs:
		sid = job["source_id"]
		try:
			with db_session() as conn:
				src = conn.execute(
					"SELECT snapshot_path, get_notes, skip_notes, topic, max_cards FROM sources WHERE id=?",
					(sid,),
				).fetchone()
			snapshot = _read_snapshot(sid, src["snapshot_path"] if src else None)
			payload_in = {
				"snapshot": snapshot,
				"get_notes": job.get("get_notes") or (src["get_notes"] if src else ""),
				"skip_notes": job.get("skip_notes") or (src["skip_notes"] if src else ""),
				"topic": job.get("topic") or (src["topic"] if src else "general"),
				"max_cards": job.get("max_cards") or (src["max_cards"] if src else 1),
			}
			if HAS_LANGCHAIN:
				data = chain.invoke(payload_in)
			else:
				data = chain(payload_in)
			with db_session() as conn:
				conn.execute(
					"""
					INSERT INTO candidates (source_id, payload_json, created_at)
					VALUES (?, ?, ?)
					""",
					(sid, dumps(data), utcnow()),
				)
				conn.execute(
					"""
					INSERT INTO jobs (source_id, job_type, status, created_at)
					VALUES (?, 'normalize', 'pending', ?)
					""",
					(sid, utcnow()),
				)
				finish_job(conn, job["job_id"], ok=True)
			ok.append(sid)
		except Exception as exc:  # noqa: BLE001
			with db_session() as conn:
				finish_job(conn, job["job_id"], ok=False, error=str(exc)[:500])
			fail.append({"source_id": sid, "error": str(exc)})
	return {"ok": ok, "failed": fail, "processed": len(jobs), "langchain": HAS_LANGCHAIN}


def run_normalize_batch(
	limit: int = 5,
	model: str | None = None,
	*,
	source_ids: set[str] | None = None,
) -> dict[str, Any]:
	if model:
		import os

		os.environ["FOROPENCODE_GEMINI_MODEL"] = model
	norm = build_normalize_chain()
	ok: list[str] = []
	fail: list[dict[str, str]] = []
	pending_cards = 0
	with db_session() as conn:
		jobs = claim_jobs(conn, "normalize", limit, source_ids=source_ids)
		conn.commit()
	for job in jobs:
		sid = job["source_id"]
		try:
			with db_session() as conn:
				cand_row = conn.execute(
					"""
					SELECT payload_json FROM candidates
					WHERE source_id=? ORDER BY id DESC LIMIT 1
					""",
					(sid,),
				).fetchone()
				src = conn.execute(
					"SELECT topic, max_cards FROM sources WHERE id=?", (sid,)
				).fetchone()
			if not cand_row:
				raise RuntimeError("no candidates for source")
			payload = json.loads(cand_row["payload_json"])
			candidates = payload.get("candidates") or []
			topic = src["topic"] if src else job.get("topic") or "general"
			max_cards = int(src["max_cards"] if src else job.get("max_cards") or 1)
			written = 0
			with db_session() as conn:
				for i, cand in enumerate(candidates[:max_cards]):
					# Prefer stable ids for known Absolute topics in pilot
					card_id = None
					if topic == "a11y_absolute" and i == 0:
						card_id = "UX_A11Y_TARG_004"  # will stay frozen if already accepted
					nin = {
						"candidate": cand,
						"topic": topic,
						"source_id": sid,
						"card_id": card_id,
					}
					if HAS_LANGCHAIN:
						card = norm.invoke(nin)
					else:
						card = norm(nin)
					# Don't overwrite frozen accepted Absolute cards
					existing = conn.execute(
						"SELECT status, frozen FROM cards WHERE id=?", (card["id"],)
					).fetchone()
					if existing and existing["frozen"]:
						continue
					if existing and existing["status"] == "accepted" and topic == "a11y_absolute":
						continue
					# unique tmp ids per source candidate
					if card["id"].startswith("UX_TMP_"):
						card["id"] = f"UX_TMP_{sid[-8:].upper()}_{i+1:03d}"
					card["status"] = "pending_review"
					upsert_card(conn, card)
					written += 1
					pending_cards += 1
				finish_job(conn, job["job_id"], ok=True)
				conn.execute(
					"UPDATE sources SET status='extracted', updated_at=? WHERE id=?",
					(utcnow(), sid),
				)
			ok.append(sid)
		except Exception as exc:  # noqa: BLE001
			with db_session() as conn:
				finish_job(conn, job["job_id"], ok=False, error=str(exc)[:500])
			fail.append({"source_id": sid, "error": str(exc)})
	return {
		"ok": ok,
		"failed": fail,
		"processed": len(jobs),
		"pending_review_cards": pending_cards,
		"langchain": HAS_LANGCHAIN,
	}
