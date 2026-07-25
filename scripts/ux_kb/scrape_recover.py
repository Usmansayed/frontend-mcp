"""Recover blocked scrapes: alternates + headed slow browser."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .browser_scrape import browser_available, fetch_with_browser
from .db import db_session, utcnow
from .paths import RAW, REPORTS
from .scrape_fallbacks import build_candidate_urls, write_fallbacks_yaml
from .scrape_worker import fetch as httpx_fetch
from .scrape_worker import html_to_text


def _save_snapshot(source_id: str, url: str, data: bytes, *, via: str) -> dict[str, Any]:
	dest = RAW / source_id
	dest.mkdir(parents=True, exist_ok=True)
	path = dest / "snapshot.md"
	# Prepend scrape metadata
	header = f"<!-- scraped_via: {via} -->\n"
	payload = header.encode("utf-8") + data
	path.write_bytes(payload)
	checksum = hashlib.sha256(payload).hexdigest()
	return {
		"path": str(path),
		"bytes": len(payload),
		"checksum_sha256": checksum,
		"via": via,
		"url_used": url,
	}


def _try_fetch(url: str, *, use_browser: bool, headed: bool) -> tuple[str, bytes, str]:
	"""Returns (text, bytes, via)."""
	try:
		text, data = httpx_fetch(url)
		if len(data) >= 800:
			return text, data, "httpx"
	except Exception:
		pass

	if not use_browser or not browser_available():
		raise RuntimeError(f"httpx failed and browser unavailable for {url}")

	text, data = fetch_with_browser(url, headless=not headed)
	return text, data, "browser_headed" if headed else "browser"


def recover_blocked_sources(
	*,
	limit: int = 30,
	use_browser: bool = True,
	headed: bool = True,
	topics: list[str] | None = None,
	source_ids: set[str] | None = None,
) -> dict[str, Any]:
	"""Retry blocked sources with alternates and slow browser."""
	write_fallbacks_yaml()
	ok: list[dict[str, Any]] = []
	fail: list[dict[str, Any]] = []

	with db_session() as conn:
		q = "SELECT id, url, topic, error FROM sources WHERE status='blocked'"
		params: list[Any] = []
		if topics:
			q += f" AND topic IN ({','.join('?' * len(topics))})"
			params.extend(topics)
		if source_ids:
			q += f" AND id IN ({','.join('?' * len(source_ids))})"
			params.extend(sorted(source_ids))
		q += " ORDER BY topic, id LIMIT ?"
		params.append(limit)
		rows = conn.execute(q, params).fetchall()

	for row in rows:
		sid = row["id"]
		primary = row["url"]
		attempts: list[dict[str, str]] = []
		last_error = ""

		for cand in build_candidate_urls(sid, primary):
			url = cand["url"]
			via_label = cand["via"]
			try:
				_text, data, method = _try_fetch(url, use_browser=use_browser, headed=headed)
				via = f"{via_label}:{method}"
				result = _save_snapshot(sid, url, data, via=via)
				with db_session() as conn:
					conn.execute(
						"""
						UPDATE sources SET url=?, checksum_sha256=?, snapshot_path=?, bytes=?,
						  status='scraped', error=NULL, updated_at=?
						WHERE id=?
						""",
						(
							url,
							result["checksum_sha256"],
							result["path"],
							result["bytes"],
							utcnow(),
							sid,
						),
					)
					# Enqueue extract if none pending
					existing = conn.execute(
						"SELECT id FROM jobs WHERE source_id=? AND job_type='extract' AND status='pending'",
						(sid,),
					).fetchone()
					if not existing:
						conn.execute(
							"INSERT INTO jobs (source_id, job_type, status, created_at) VALUES (?, 'extract', 'pending', ?)",
							(sid, utcnow()),
						)
				ok.append({"source_id": sid, "url": url, "via": via, "bytes": result["bytes"]})
				break
			except Exception as exc:  # noqa: BLE001
				last_error = str(exc)[:300]
				attempts.append({"url": url, "via": via_label, "error": last_error})
		else:
			fail.append({"source_id": sid, "primary": primary, "attempts": attempts, "error": last_error})

	report = {
		"recovered": len(ok),
		"still_blocked": len(fail),
		"browser_available": browser_available(),
		"headed": headed,
		"ok": ok,
		"failed": fail,
	}
	REPORTS.mkdir(parents=True, exist_ok=True)
	out = REPORTS / "scrape_recovery.json"
	out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
	report["report_path"] = str(out)
	return report


def main() -> None:
	import argparse

	parser = argparse.ArgumentParser(description="Recover blocked UX KB scrapes")
	parser.add_argument("--limit", type=int, default=30)
	parser.add_argument("--headed", action="store_true", default=True)
	parser.add_argument("--headless", action="store_true", help="Force headless browser")
	parser.add_argument("--no-browser", action="store_true", help="httpx + alternates only")
	parser.add_argument("--topics", default=None, help="Comma-separated topic filter")
	parser.add_argument("--ids", default=None, help="Comma-separated source ids")
	args = parser.parse_args()

	topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
	ids = {i.strip() for i in args.ids.split(",")} if args.ids else None
	report = recover_blocked_sources(
		limit=args.limit,
		use_browser=not args.no_browser,
		headed=not args.headless,
		topics=topics,
		source_ids=ids,
	)
	print(json.dumps({"recovered": report["recovered"], "still_blocked": report["still_blocked"], "report_path": report["report_path"]}, indent=2))
	raise SystemExit(0 if report["recovered"] else 1)


if __name__ == "__main__":
	main()
