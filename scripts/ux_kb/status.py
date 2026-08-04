"""Supervisor status + sample review + run reports."""
from __future__ import annotations

import json
from typing import Any

from .db import db_session, dumps, utcnow
from .paths import REPORTS


def status_summary() -> dict[str, Any]:
	with db_session() as conn:
		sources = {
			r["status"]: r["c"]
			for r in conn.execute(
				"SELECT status, COUNT(*) AS c FROM sources GROUP BY status"
			).fetchall()
		}
		jobs = {
			f"{r['job_type']}:{r['status']}": r["c"]
			for r in conn.execute(
				"SELECT job_type, status, COUNT(*) AS c FROM jobs GROUP BY job_type, status"
			).fetchall()
		}
		cards = {
			r["status"]: r["c"]
			for r in conn.execute(
				"SELECT status, COUNT(*) AS c FROM cards GROUP BY status"
			).fetchall()
		}
		failed_jobs = [
			dict(r)
			for r in conn.execute(
				"""
				SELECT id, source_id, job_type, error, finished_at
				FROM jobs WHERE status='failed' ORDER BY id DESC LIMIT 20
				"""
			).fetchall()
		]
		pending_review = [
			dict(r)
			for r in conn.execute(
				"""
				SELECT id, topic, title, status FROM cards
				WHERE status='pending_review' ORDER BY updated_at DESC LIMIT 20
				"""
			).fetchall()
		]
		clusters = conn.execute("SELECT COUNT(*) AS c FROM principle_clusters").fetchone()
		multi_merge = conn.execute(
			"""
			SELECT COUNT(*) AS c FROM principle_clusters
			WHERE json_array_length(member_ids_json) > 1
			"""
		).fetchone()
	return {
		"sources": sources,
		"jobs": jobs,
		"cards": cards,
		"principle_clusters": int(clusters["c"] if clusters else 0),
		"multi_member_merges": int(multi_merge["c"] if multi_merge else 0),
		"failed_jobs": failed_jobs,
		"pending_review_sample": pending_review,
	}


def sample_review(n: int = 3) -> list[dict[str, Any]]:
	with db_session() as conn:
		rows = conn.execute(
			"""
			SELECT id, topic, title, rule, detect, when_to_apply, when_not_to_apply,
			       tradeoff, quote, status, evidence_class, confidence
			FROM cards
			WHERE status='pending_review'
			ORDER BY updated_at DESC
			LIMIT ?
			""",
			(n,),
		).fetchall()
	return [dict(r) for r in rows]


def write_run_report(stage: str, result: dict[str, Any]) -> str:
	REPORTS.mkdir(parents=True, exist_ok=True)
	started = utcnow()
	ok_count = len(result.get("ok") or [])
	fail_count = len(result.get("failed") or [])
	pending = int(result.get("pending_review_cards") or 0)
	with db_session() as conn:
		cur = conn.execute(
			"""
			INSERT INTO runs (stage, ok_count, fail_count, pending_review_count, summary_json, started_at, finished_at)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			""",
			(stage, ok_count, fail_count, pending, dumps(result), started, utcnow()),
		)
		run_id = cur.lastrowid
	path = REPORTS / f"run_{run_id}_{stage}.json"
	path.write_text(json.dumps({"run_id": run_id, "stage": stage, **result}, indent=2), encoding="utf-8")
	return str(path)


def accept_pending(*, topic: str | None = None, limit: int = 50) -> dict[str, Any]:
	"""Promote pending_review → accepted (respect frozen Absolute)."""
	accepted: list[str] = []
	with db_session() as conn:
		q = "SELECT id, topic, frozen FROM cards WHERE status='pending_review'"
		params: list[Any] = []
		if topic:
			q += " AND topic=?"
			params.append(topic)
		q += " ORDER BY updated_at LIMIT ?"
		params.append(limit)
		rows = conn.execute(q, params).fetchall()
		for row in rows:
			if row["frozen"]:
				continue
			# budget check
			pack = conn.execute(
				"SELECT budget, card_ids_json FROM packs WHERE topic=?", (row["topic"],)
			).fetchone()
			if pack:
				ids = json.loads(pack["card_ids_json"] or "[]")
				accepted_count = conn.execute(
					"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='accepted'",
					(row["topic"],),
				).fetchone()["c"]
				if accepted_count >= int(pack["budget"]):
					conn.execute(
						"UPDATE cards SET status='rejected_over_budget', updated_at=? WHERE id=?",
						(utcnow(), row["id"]),
					)
					continue
				if row["id"] not in ids:
					ids.append(row["id"])
					conn.execute(
						"UPDATE packs SET card_ids_json=?, updated_at=? WHERE topic=?",
						(dumps(ids), utcnow(), row["topic"]),
					)
			conn.execute(
				"UPDATE cards SET status='accepted', updated_at=? WHERE id=?",
				(utcnow(), row["id"]),
			)
			accepted.append(row["id"])
	return {"accepted": accepted, "count": len(accepted)}
