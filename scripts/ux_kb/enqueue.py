"""Enqueue URLs from url_queue.yaml into SQLite + jobs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .db import db_session, init_db, utcnow
from .paths import TOPIC_BUDGETS, URL_QUEUE


def load_budgets() -> dict[str, int]:
	data = yaml.safe_load(TOPIC_BUDGETS.read_text(encoding="utf-8"))
	return dict(data.get("budgets") or {})


def load_url_queue(path: Path | None = None) -> list[dict[str, Any]]:
	queue_path = path or URL_QUEUE
	data = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
	return list(data.get("urls") or [])


def enqueue_from_file(
	queue_path: Path,
	*,
	only_queued: bool = True,
) -> dict[str, int]:
	"""Enqueue sources from an arbitrary queue YAML (e.g. pilot_queue.yaml)."""
	init_db()
	urls = load_url_queue(queue_path)
	return _enqueue_urls(urls, only_queued=only_queued, queue_label=str(queue_path.name))


def enqueue_from_queue(*, only_queued: bool = True) -> dict[str, int]:
	init_db()
	urls = load_url_queue(URL_QUEUE)
	return _enqueue_urls(urls, only_queued=only_queued, queue_label="url_queue.yaml")


def _enqueue_urls(
	urls: list[dict[str, Any]],
	*,
	only_queued: bool,
	queue_label: str,
) -> dict[str, int]:
	budgets = load_budgets()
	now = utcnow()
	added_sources = 0
	added_jobs = 0
	with db_session() as conn:
		for topic, budget in budgets.items():
			conn.execute(
				"""
				INSERT INTO packs (topic, budget, card_ids_json, updated_at)
				VALUES (?, ?, '[]', ?)
				ON CONFLICT(topic) DO UPDATE SET budget=excluded.budget, updated_at=excluded.updated_at
				""",
				(topic, int(budget), now),
			)
		for row in urls:
			if only_queued and row.get("status") not in (None, "queued"):
				continue
			sid = row["id"]
			existing = conn.execute("SELECT id FROM sources WHERE id=?", (sid,)).fetchone()
			if existing:
				conn.execute(
					"""
					UPDATE sources SET url=?, topic=?, priority=?, get_notes=?, skip_notes=?,
					  max_cards=?, status=?, updated_at=?
					WHERE id=?
					""",
					(
						row["url"],
						row["topic"],
						row.get("priority") or "B",
						row.get("get") or "",
						row.get("skip") or "",
						int(row.get("max_cards") or 1),
						row.get("status") or "queued",
						now,
						sid,
					),
				)
			else:
				conn.execute(
					"""
					INSERT INTO sources (
					  id, url, topic, priority, get_notes, skip_notes, max_cards,
					  status, created_at, updated_at
					) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
					""",
					(
						sid,
						row["url"],
						row["topic"],
						row.get("priority") or "B",
						row.get("get") or "",
						row.get("skip") or "",
						int(row.get("max_cards") or 1),
						"queued",
						now,
						now,
					),
				)
				added_sources += 1
			# ensure scrape job pending if not already done/running
			pending = conn.execute(
				"""
				SELECT id FROM jobs
				WHERE source_id=? AND job_type='scrape' AND status IN ('pending','running')
				""",
				(sid,),
			).fetchone()
			if not pending:
				# only enqueue scrape if no successful scrape yet
				src = conn.execute(
					"SELECT checksum_sha256 FROM sources WHERE id=?", (sid,)
				).fetchone()
				if not (src and src["checksum_sha256"]):
					conn.execute(
						"""
						INSERT INTO jobs (source_id, job_type, status, created_at)
						VALUES (?, 'scrape', 'pending', ?)
						""",
						(sid, now),
					)
					added_jobs += 1
	return {
		"sources_added": added_sources,
		"jobs_added": added_jobs,
		"urls_seen": len(urls),
		"queue": queue_label,
	}
