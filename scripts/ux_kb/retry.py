"""Re-queue failed or stuck pipeline jobs for retry."""
from __future__ import annotations

from typing import Any

from .db import db_session, utcnow


def retry_failed_jobs(
	*,
	job_type: str | None = None,
	limit: int = 50,
) -> dict[str, Any]:
	"""Reset failed jobs to pending so workers can reclaim them."""
	types = [job_type] if job_type else ["extract", "normalize", "scrape"]
	requeued: list[dict[str, Any]] = []
	with db_session() as conn:
		for jt in types:
			rows = conn.execute(
				"""
				SELECT id, source_id, job_type, error
				FROM jobs
				WHERE job_type=? AND status='failed'
				ORDER BY id
				LIMIT ?
				""",
				(jt, limit),
			).fetchall()
			for row in rows:
				conn.execute(
					"""
					UPDATE jobs
					SET status='pending', error=NULL, claimed_at=NULL, finished_at=NULL
					WHERE id=?
					""",
					(row["id"],),
				)
				requeued.append(
					{
						"job_id": row["id"],
						"source_id": row["source_id"],
						"job_type": row["job_type"],
						"prior_error": (row["error"] or "")[:120],
					}
				)
	return {"requeued": requeued, "count": len(requeued)}


def pending_job_counts() -> dict[str, int]:
	with db_session() as conn:
		rows = conn.execute(
			"""
			SELECT job_type, status, COUNT(*) AS c
			FROM jobs
			WHERE status IN ('pending', 'failed')
			GROUP BY job_type, status
			ORDER BY job_type, status
			"""
		).fetchall()
	return {f"{r['job_type']}:{r['status']}": r["c"] for r in rows}
