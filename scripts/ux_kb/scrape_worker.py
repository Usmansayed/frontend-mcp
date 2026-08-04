"""Deterministic scrape worker for UX KB."""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Reuse patterns; keep self-contained to avoid import path pain
from .db import db_session, utcnow
from .paths import RAW

USER_AGENT = (
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
	"(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def html_to_text(html: str, url: str) -> str:
	soup = BeautifulSoup(html, "html.parser")
	for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
		tag.decompose()
	title = (soup.title.string or "").strip() if soup.title else ""
	main = soup.find("main") or soup.find("article") or soup.body or soup
	text = main.get_text("\n", strip=True)
	text = re.sub(r"\n{3,}", "\n\n", text)
	return f"# {title or urlparse(url).path}\n\nSource: {url}\n\n{text}"


def fetch(url: str) -> tuple[str, bytes]:
	headers = {
		"User-Agent": USER_AGENT,
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.9",
	}
	with httpx.Client(follow_redirects=True, timeout=45.0, headers=headers) as client:
		resp = client.get(url)
		resp.raise_for_status()
		ctype = resp.headers.get("content-type", "text/html")
		body = resp.content
		if "html" in ctype or body.lstrip().startswith(b"<"):
			text = html_to_text(body.decode("utf-8", errors="replace"), url)
			return text, text.encode("utf-8")
		return body.decode("utf-8", errors="replace"), body


def scrape_source(source_id: str, url: str) -> dict[str, Any]:
	text, data = fetch(url)
	if len(data) < 800:
		raise RuntimeError(f"snapshot too small: {len(data)} bytes")
	dest = RAW / source_id
	dest.mkdir(parents=True, exist_ok=True)
	path = dest / "snapshot.md"
	path.write_bytes(data)
	checksum = hashlib.sha256(data).hexdigest()
	return {
		"path": str(path),
		"bytes": len(data),
		"checksum_sha256": checksum,
	}


def claim_jobs(
	conn,
	job_type: str,
	limit: int,
	*,
	source_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
	query = """
		SELECT j.id AS job_id, j.source_id, s.url, s.topic, s.get_notes, s.skip_notes, s.max_cards
		FROM jobs j
		JOIN sources s ON s.id = j.source_id
		WHERE j.job_type=? AND j.status='pending'
	"""
	params: list[Any] = [job_type]
	if source_ids:
		placeholders = ",".join("?" * len(source_ids))
		query += f" AND j.source_id IN ({placeholders})"
		params.extend(sorted(source_ids))
	query += " ORDER BY j.id LIMIT ?"
	params.append(limit)
	rows = conn.execute(query, params).fetchall()
	out = []
	now = utcnow()
	for row in rows:
		conn.execute(
			"UPDATE jobs SET status='running', attempts=attempts+1, claimed_at=? WHERE id=?",
			(now, row["job_id"]),
		)
		out.append(dict(row))
	return out


def finish_job(conn, job_id: int, *, ok: bool, error: str | None = None) -> None:
	conn.execute(
		"""
		UPDATE jobs SET status=?, error=?, finished_at=?
		WHERE id=?
		""",
		("done" if ok else "failed", error, utcnow(), job_id),
	)


def run_scrape_batch(
	limit: int = 10,
	*,
	source_ids: set[str] | None = None,
) -> dict[str, Any]:
	ok_ids: list[str] = []
	fail: list[dict[str, str]] = []
	with db_session() as conn:
		jobs = claim_jobs(conn, "scrape", limit, source_ids=source_ids)
		# commit claims early
		conn.commit()
	for job in jobs:
		sid = job["source_id"]
		try:
			result = scrape_source(sid, job["url"])
			with db_session() as conn:
				conn.execute(
					"""
					UPDATE sources SET checksum_sha256=?, snapshot_path=?, bytes=?,
					  status='scraped', error=NULL, updated_at=?
					WHERE id=?
					""",
					(
						result["checksum_sha256"],
						result["path"],
						result["bytes"],
						utcnow(),
						sid,
					),
				)
				# enqueue extract job
				conn.execute(
					"""
					INSERT INTO jobs (source_id, job_type, status, created_at)
					VALUES (?, 'extract', 'pending', ?)
					""",
					(sid, utcnow()),
				)
				finish_job(conn, job["job_id"], ok=True)
			ok_ids.append(sid)
		except Exception as exc:  # noqa: BLE001
			with db_session() as conn:
				conn.execute(
					"UPDATE sources SET status='blocked', error=?, updated_at=? WHERE id=?",
					(str(exc)[:500], utcnow(), sid),
				)
				finish_job(conn, job["job_id"], ok=False, error=str(exc)[:500])
			fail.append({"source_id": sid, "error": str(exc)})
	return {"ok": ok_ids, "failed": fail, "processed": len(jobs)}
