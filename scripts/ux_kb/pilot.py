"""Supervisor pilot — 10–20 URLs on forms + onboarding; verify budget + dedup."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .db import db_session, loads
from .paths import KB_ROOT, PILOT_QUEUE, REPORTS, TOPIC_BUDGETS
from .status import status_summary, write_run_report

PILOT_TOPICS = ("forms", "onboarding")


def load_pilot_queue(path: Path | None = None) -> list[dict[str, Any]]:
	data = yaml.safe_load((path or PILOT_QUEUE).read_text(encoding="utf-8"))
	return list(data.get("urls") or [])


def verify_pilot_state(*, topics: tuple[str, ...] = PILOT_TOPICS) -> dict[str, Any]:
	"""Check budget compliance, dedup clusters, and pilot source progress."""
	budgets = yaml.safe_load(TOPIC_BUDGETS.read_text(encoding="utf-8")).get("budgets") or {}
	checks: list[dict[str, Any]] = []
	all_ok = True

	with db_session() as conn:
		pilot_ids = {row["id"] for row in load_pilot_queue()}
		for topic in topics:
			budget = int(budgets.get(topic, 99))
			accepted = conn.execute(
				"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='accepted'",
				(topic,),
			).fetchone()["c"]
			over = conn.execute(
				"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='rejected_over_budget'",
				(topic,),
			).fetchone()["c"]
			pack = conn.execute(
				"SELECT card_ids_json FROM packs WHERE topic=?", (topic,)
			).fetchone()
			pack_ids = loads(pack["card_ids_json"] if pack else None, default=[])
			ok = accepted <= budget
			if not ok:
				all_ok = False
			checks.append(
				{
					"topic": topic,
					"budget": budget,
					"accepted": accepted,
					"rejected_over_budget": over,
					"pack_card_count": len(pack_ids),
					"within_budget": ok,
				}
			)

		clusters = conn.execute(
			"""
			SELECT topic, COUNT(*) AS c FROM principle_clusters
			WHERE topic IN ({})
			GROUP BY topic
			""".format(",".join("?" * len(topics))),
			topics,
		).fetchall()
		cluster_by_topic = {r["topic"]: r["c"] for r in clusters}

		pilot_sources = []
		for sid in pilot_ids:
			row = conn.execute(
				"SELECT id, topic, status, checksum_sha256, bytes FROM sources WHERE id=?",
				(sid,),
			).fetchone()
			if row:
				pilot_sources.append(dict(row))

		scraped = sum(1 for s in pilot_sources if s.get("checksum_sha256"))
		extracted = 0
		for sid in pilot_ids:
			c = conn.execute(
				"SELECT COUNT(*) AS c FROM candidates WHERE source_id=?", (sid,)
			).fetchone()["c"]
			if c:
				extracted += 1

	return {
		"pass": all_ok,
		"topics": checks,
		"principle_clusters": cluster_by_topic,
		"pilot_sources_total": len(pilot_ids),
		"pilot_sources_in_db": len(pilot_sources),
		"pilot_scraped": scraped,
		"pilot_extracted": extracted,
		"status": status_summary(),
	}


def run_pilot(
	*,
	full: bool = False,
	scrape_limit: int = 16,
	extract_limit: int = 16,
	normalize_limit: int = 16,
	model: str | None = None,
	skip_adc: bool = False,
) -> dict[str, Any]:
	"""Run pilot pipeline on forms + onboarding subset."""
	from .enqueue import enqueue_from_file

	report: dict[str, Any] = {
		"topics": list(PILOT_TOPICS),
		"full": full,
		"stages": {},
	}

	enqueue_result = enqueue_from_file(PILOT_QUEUE)
	report["stages"]["enqueue"] = enqueue_result

	if full and not skip_adc:
		from .scrape_worker import run_scrape_batch
		from .chains import run_extract_batch, run_normalize_batch
		from .dedup import run_dedup_batch
		from .accept_wave import run_accept_wave

		# Scrape only pilot sources (filter by re-enqueue pending jobs for pilot ids)
		pilot_ids = {row["id"] for row in load_pilot_queue()}
		scrape_result = run_scrape_batch(limit=scrape_limit, source_ids=pilot_ids)
		report["stages"]["scrape"] = scrape_result
		write_run_report("pilot_scrape", scrape_result)

		extract_result = run_extract_batch(limit=extract_limit, model=model, source_ids=pilot_ids)
		report["stages"]["extract"] = extract_result
		write_run_report("pilot_extract", extract_result)

		normalize_result = run_normalize_batch(limit=normalize_limit, model=model, source_ids=pilot_ids)
		report["stages"]["normalize"] = normalize_result
		write_run_report("pilot_normalize", normalize_result)

		dedup_result = run_dedup_batch(topic="forms", model=model, incremental=True)
		dedup_onb = run_dedup_batch(topic="onboarding", model=model, incremental=True)
		report["stages"]["dedup"] = {
			"forms": dedup_result,
			"onboarding": dedup_onb,
		}
		write_run_report("pilot_dedup", {"ok": dedup_result.get("ok", []) + dedup_onb.get("ok", []), "failed": []})

		accept_forms = run_accept_wave(wave="forms", model=model)
		accept_onb = run_accept_wave(wave="onboarding", model=model)
		report["stages"]["accept_wave"] = {"forms": accept_forms, "onboarding": accept_onb}
		write_run_report(
			"pilot_accept",
			{
				"ok": (accept_forms.get("accepted") or []) + (accept_onb.get("accepted") or []),
				"failed": (accept_forms.get("failed") or []) + (accept_onb.get("failed") or []),
			},
		)

	verification = verify_pilot_state()

	report["verification"] = verification
	report["pass"] = verification["pass"]

	REPORTS.mkdir(parents=True, exist_ok=True)
	out = REPORTS / "pilot_report.json"
	out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
	report["report_path"] = str(out)
	return report


def main() -> None:
	import argparse
	import sys

	parser = argparse.ArgumentParser(description="Run UX KB pilot on forms + onboarding")
	parser.add_argument("--full", action="store_true", help="Run scrape→extract→normalize→dedup→accept")
	parser.add_argument("--skip-adc", action="store_true", help="Verify only; no Gemini stages")
	parser.add_argument("--scrape-limit", type=int, default=16)
	parser.add_argument("--model", default=None)
	args = parser.parse_args()

	result = run_pilot(
		full=args.full,
		scrape_limit=args.scrape_limit,
		model=args.model,
		skip_adc=args.skip_adc,
	)
	print(json.dumps(result, indent=2))
	raise SystemExit(0 if result.get("pass") else 1)


if __name__ == "__main__":
	main()
