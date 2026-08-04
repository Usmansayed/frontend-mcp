"""Execute expansion wave: ADC ingest for gap-cluster topics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .paths import EXPANSION_PLANS, GAP_CLUSTERS, REPORTS, URL_QUEUE
from .status import status_summary, write_run_report


def _load_plans(path: Path | None = None) -> dict[str, Any]:
	p = path or EXPANSION_PLANS
	if not p.exists():
		from .expansion_planner import plan_expansion

		return plan_expansion()
	return yaml.safe_load(p.read_text(encoding="utf-8"))


def _source_ids_for_topics(topics: list[str], plans: dict[str, Any]) -> set[str]:
	ids: set[str] = set()
	for plan in plans.get("plans") or []:
		if plan["topic"] in topics:
			ids.update(plan.get("source_ids") or [])
	return ids


def _write_expansion_queue(topics: list[str], plans: dict[str, Any]) -> Path:
	from .paths import KB_ROOT

	queue_path = KB_ROOT / "expansion_queue.yaml"
	all_urls = yaml.safe_load(URL_QUEUE.read_text(encoding="utf-8"))
	url_by_id = {u["id"]: u for u in all_urls.get("urls") or []}
	selected: list[dict[str, Any]] = []
	for plan in plans.get("plans") or []:
		if plan["topic"] not in topics:
			continue
		for sid in plan.get("source_ids") or []:
			if sid in url_by_id:
				selected.append(url_by_id[sid])
	out = {
		"version": 1,
		"description": f"Expansion wave for topics: {', '.join(topics)}",
		"urls": selected,
	}
	queue_path.write_text(yaml.dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
	return queue_path


def run_expand_wave(
	*,
	topics: list[str] | None = None,
	full: bool = True,
	scrape_limit: int = 40,
	extract_limit: int = 40,
	normalize_limit: int = 40,
	model: str | None = None,
	skip_adc: bool = False,
	complete_phases: bool = True,
) -> dict[str, Any]:
	plans = _load_plans()
	wave_topics = topics or plans.get("wave_topics") or []
	if not wave_topics:
		# Default first wave — gap topics with URLs
		wave_topics = [
			t
			for t in ("typography", "motion", "auth", "data_tables", "search", "notifications", "agentic_ux")
			if any(p["topic"] == t for p in plans.get("plans") or [])
		]

	report: dict[str, Any] = {
		"topics": wave_topics,
		"full": full,
		"stages": {},
	}

	source_ids = _source_ids_for_topics(wave_topics, plans)
	report["source_ids_count"] = len(source_ids)

	if not source_ids:
		report["error"] = "no source_ids for selected topics"
		return report

	queue_path = _write_expansion_queue(wave_topics, plans)
	report["expansion_queue"] = str(queue_path)

	from .enqueue import enqueue_from_file

	report["stages"]["enqueue"] = enqueue_from_file(queue_path)

	if full and not skip_adc:
		from .accept_wave import run_accept_wave
		from .chains import run_extract_batch, run_normalize_batch
		from .dedup import run_dedup_batch
		from .scrape_worker import run_scrape_batch

		scrape_result = run_scrape_batch(limit=scrape_limit, source_ids=source_ids)
		report["stages"]["scrape"] = scrape_result
		write_run_report("expand_scrape", scrape_result)

		extract_result = run_extract_batch(limit=extract_limit, model=model, source_ids=source_ids)
		report["stages"]["extract"] = extract_result
		write_run_report("expand_extract", extract_result)

		normalize_result = run_normalize_batch(limit=normalize_limit, model=model, source_ids=source_ids)
		report["stages"]["normalize"] = normalize_result
		write_run_report("expand_normalize", normalize_result)

		dedup_results: dict[str, Any] = {}
		for topic in wave_topics:
			dedup_results[topic] = run_dedup_batch(topic=topic, model=model, incremental=True)
		report["stages"]["dedup"] = dedup_results
		write_run_report("expand_dedup", {"ok": wave_topics, "failed": []})

		accept_results: dict[str, Any] = {}
		for topic in wave_topics:
			accept_results[topic] = run_accept_wave(topic=topic, model=model)
		report["stages"]["accept"] = accept_results
		all_accepted = []
		for r in accept_results.values():
			all_accepted.extend(r.get("accepted") or [])
		write_run_report("expand_accept", {"ok": all_accepted, "failed": []})

		if complete_phases:
			from .graph_pipeline import run_complete_phases

			cp = run_complete_phases(model=model, skip_accept=True)
			report["stages"]["complete_phases"] = cp
			write_run_report("expand_complete_phases", cp)

	# Post-wave verification
	topic_stats: list[dict[str, Any]] = []
	from .db import db_session
	from .paths import TOPIC_BUDGETS

	budgets = yaml.safe_load(TOPIC_BUDGETS.read_text(encoding="utf-8")).get("budgets") or {}

	with db_session() as conn:
		for topic in wave_topics:
			accepted = conn.execute(
				"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='accepted'",
				(topic,),
			).fetchone()["c"]
			pending = conn.execute(
				"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='pending_review'",
				(topic,),
			).fetchone()["c"]
			scraped = conn.execute(
				"""
				SELECT COUNT(*) AS c FROM sources
				WHERE topic=? AND checksum_sha256 IS NOT NULL AND checksum_sha256 != ''
				""",
				(topic,),
			).fetchone()["c"]
			budget = int(budgets.get(topic, 99))
			topic_stats.append(
				{
					"topic": topic,
					"budget": budget,
					"accepted": accepted,
					"pending_review": pending,
					"scraped": scraped,
					"within_budget": accepted <= budget,
				}
			)

	report["topic_stats"] = topic_stats
	report["status"] = status_summary()
	report["pass"] = all(s["within_budget"] for s in topic_stats)

	REPORTS.mkdir(parents=True, exist_ok=True)
	out = REPORTS / "expand_wave_report.json"
	out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
	report["report_path"] = str(out)
	return report


def main() -> None:
	import argparse

	parser = argparse.ArgumentParser(description="Run UX KB expansion wave")
	parser.add_argument("--topics", default=None, help="Comma-separated topics")
	parser.add_argument("--full", action="store_true", default=True)
	parser.add_argument("--skip-adc", action="store_true")
	parser.add_argument("--scrape-limit", type=int, default=40)
	parser.add_argument("--extract-limit", type=int, default=40)
	parser.add_argument("--normalize-limit", type=int, default=40)
	parser.add_argument("--model", default=None)
	parser.add_argument("--no-complete-phases", action="store_true")
	args = parser.parse_args()

	topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
	result = run_expand_wave(
		topics=topics,
		full=args.full,
		scrape_limit=args.scrape_limit,
		extract_limit=args.extract_limit,
		normalize_limit=args.normalize_limit,
		model=args.model,
		skip_adc=args.skip_adc,
		complete_phases=not args.no_complete_phases,
	)
	print(json.dumps(result, indent=2))
	raise SystemExit(0 if result.get("pass", True) else 1)


if __name__ == "__main__":
	main()
