"""CLI: python scripts/run_ux_kb.py <command>"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description="UX KB supervisor pipeline")
	sub = parser.add_subparsers(dest="cmd", required=True)

	sub.add_parser("init", help="Create SQLite schema")
	sub.add_parser("build-url-queue", help="Regenerate url_queue.yaml from curated bibliography")
	p_pilot = sub.add_parser("pilot", help="Pilot forms+onboarding (16 URLs); verify budget/dedup")
	p_pilot.add_argument("--full", action="store_true", help="Run scrape→extract→normalize→dedup→accept")
	p_pilot.add_argument("--skip-adc", action="store_true", help="Verify state only; no Gemini stages")
	p_pilot.add_argument("--scrape-limit", type=int, default=16)
	p_pilot.add_argument("--model", default=None)
	sub.add_parser("seed-import", help="Import ForOpenCode normalized cards")
	p_enqueue = sub.add_parser("enqueue", help="Load url_queue.yaml into SQLite jobs")
	p_enqueue.add_argument(
		"--from",
		dest="from_file",
		default=None,
		help="Alternate queue YAML (e.g. pilot_queue.yaml)",
	)
	sub.add_parser("status", help="Counts + failures (supervisor view)")
	p_sample = sub.add_parser("sample-review", help="Show N pending_review cards")
	p_sample.add_argument("--n", type=int, default=3)
	p_run = sub.add_parser("run", help="Run a worker stage")
	p_run.add_argument(
		"--stage",
		required=True,
		choices=[
			"scrape",
			"extract",
			"normalize",
			"dedup",
			"accept-wave",
			"relationships",
			"patterns",
			"playbooks",
			"decisions",
			"evidence",
			"export-graph",
			"distill",
		],
	)
	p_run.add_argument("--limit", type=int, default=5)
	p_run.add_argument("--model", default=None)
	p_accept = sub.add_parser("accept", help="Accept pending_review cards")
	p_accept.add_argument("--topic", default=None)
	p_accept.add_argument("--limit", type=int, default=50)
	p_accept_wave = sub.add_parser("accept-wave", help="Gemini-scored acceptance for topic or wave")
	p_accept_wave.add_argument("--topic", default=None)
	p_accept_wave.add_argument("--wave", default=None)
	p_accept_wave.add_argument("--model", default=None)
	p_dedup = sub.add_parser("dedup-review", help="Principle clusters + merge summary")
	p_dedup.add_argument("--limit", type=int, default=20)
	p_dedup_run = sub.add_parser("dedup", help="Run principle-identity dedup on pending cards")
	p_dedup_run.add_argument("--topic", default=None)
	p_dedup_run.add_argument("--model", default=None)
	p_dedup_run.add_argument("--dry-run", action="store_true")
	p_dedup_run.add_argument(
		"--incremental",
		action="store_true",
		help="Only dedup new UX_TMP_* raw cards; merge into existing canonicals",
	)
	p_retry = sub.add_parser("retry-failed", help="Re-queue failed scrape/extract/normalize jobs")
	p_retry.add_argument("--job-type", choices=["scrape", "extract", "normalize"], default=None)
	p_retry.add_argument("--limit", type=int, default=50)
	p_recover = sub.add_parser(
		"recover-scrapes",
		help="Retry blocked sources: alternates + headed slow browser (Playwright)",
	)
	p_recover.add_argument("--limit", type=int, default=40)
	p_recover.add_argument("--headed", action="store_true", default=True)
	p_recover.add_argument("--headless", action="store_true")
	p_recover.add_argument("--no-browser", action="store_true", help="Alternates/wayback via httpx only")
	p_recover.add_argument("--topics", default=None)
	p_recover.add_argument("--ids", default=None)
	p_recover.add_argument("--then-extract", action="store_true", help="Run extract batch after recovery")
	p_recover.add_argument("--extract-limit", type=int, default=40)
	p_recover.add_argument("--model", default=None)
	p_complete = sub.add_parser("complete-phases", help="Accept → graph → patterns → playbooks → distill")
	p_complete.add_argument("--model", default=None)
	p_complete.add_argument("--skip-accept", action="store_true")
	sub.add_parser("quality-audit", help="Phase 1 audit: edges, conflicts, weak principles, gaps")
	p_remap = sub.add_parser("remap-tmp-ids", help="Rename accepted UX_TMP_* cards + refresh graph/packs")
	p_remap.add_argument("--no-refresh", action="store_true", help="Skip export/distill after remap")
	sub.add_parser("signoff-review", help="Generate HUMAN_SIGNOFF.md for Phase 1 gate")
	sub.add_parser("apply-signoff", help="Apply default Phase 1 sign-off decisions")
	sub.add_parser("query-battery", help="Run 30 dev retrieval queries (micro→macro)")
	sub.add_parser("generate-query-catalog", help="Build ~400 probe queries from taxonomy matrix")
	sub.add_parser("probe-coverage", help="Run catalog through retrieve; classify gaps")
	p_gap = sub.add_parser("gap-cluster", help="Aggregate probe + budget gaps → gap_clusters.yaml")
	p_gap.add_argument("--top", type=int, default=15, help="Max clusters")
	sub.add_parser("plan-expansion", help="Build expansion_plans.yaml from gap clusters + url_queue")
	p_expand = sub.add_parser("expand-wave", help="ADC ingest for gap topics (scrape→accept→graph)")
	p_expand.add_argument("--topics", default=None, help="Comma-separated topics (default: wave from plans)")
	p_expand.add_argument("--full", action="store_true", help="Run ADC pipeline")
	p_expand.add_argument("--skip-adc", action="store_true", help="Enqueue + verify only")
	p_expand.add_argument("--scrape-limit", type=int, default=40)
	p_expand.add_argument("--extract-limit", type=int, default=40)
	p_expand.add_argument("--normalize-limit", type=int, default=40)
	p_expand.add_argument("--model", default=None)
	p_expand.add_argument("--no-complete-phases", action="store_true")
	p_expand_all = sub.add_parser("expand", help="Full expansion loop: catalog→probe→cluster→plan→wave")
	p_expand_all.add_argument("--skip-adc", action="store_true")
	p_expand_all.add_argument("--topics", default=None)
	p_expand_all.add_argument("--scrape-limit", type=int, default=40)
	p_expand_all.add_argument("--model", default=None)
	sub.add_parser("evaluate-runtime", help="Offline pack matching + retrieval engine eval")
	p_retrieve = sub.add_parser("retrieve", help="Run deterministic retrieval (JSON request)")
	p_retrieve.add_argument("--request", default=None, help="Path to JSON request file")
	p_retrieve.add_argument("--example", action="store_true", help="Run built-in dashboard example")

	args = parser.parse_args(argv)

	if args.cmd == "init":
		from ux_kb.db import init_db
		from ux_kb.paths import DB_PATH

		path = init_db()
		print(json.dumps({"ok": True, "db": str(path), "exists": DB_PATH.exists()}))
		return 0

	if args.cmd == "seed-import":
		from ux_kb.seed import seed_import

		print(json.dumps(seed_import(), indent=2))
		return 0

	if args.cmd == "build-url-queue":
		from ux_kb.build_url_queue import main as build_queue_main

		build_queue_main()
		return 0

	if args.cmd == "pilot":
		from ux_kb.pilot import run_pilot

		result = run_pilot(
			full=args.full,
			scrape_limit=args.scrape_limit,
			model=args.model,
			skip_adc=args.skip_adc,
		)
		print(json.dumps(result, indent=2))
		return 0 if result.get("pass") else 1

	if args.cmd == "enqueue":
		from ux_kb.enqueue import enqueue_from_file, enqueue_from_queue
		from ux_kb.paths import PILOT_QUEUE, URL_QUEUE

		if args.from_file:
			path = Path(args.from_file)
			if not path.is_absolute():
				path = URL_QUEUE.parent / path
			result = enqueue_from_file(path)
		else:
			result = enqueue_from_queue()
		print(json.dumps(result, indent=2))
		return 0

	if args.cmd == "status":
		from ux_kb.status import status_summary

		print(json.dumps(status_summary(), indent=2))
		return 0

	if args.cmd == "sample-review":
		from ux_kb.status import sample_review

		print(json.dumps(sample_review(args.n), indent=2))
		return 0

	if args.cmd == "accept":
		from ux_kb.status import accept_pending

		print(json.dumps(accept_pending(topic=args.topic, limit=args.limit), indent=2))
		return 0

	if args.cmd == "accept-wave":
		from ux_kb.accept_wave import run_accept_wave

		result = run_accept_wave(wave=args.wave, topic=args.topic, model=args.model)
		print(json.dumps(result, indent=2))
		return 0 if not result.get("failed") else 1

	if args.cmd == "dedup-review":
		from ux_kb.dedup import dedup_review

		print(json.dumps(dedup_review(limit=args.limit), indent=2))
		return 0

	if args.cmd == "dedup":
		from ux_kb.dedup import run_dedup_batch
		from ux_kb.status import write_run_report

		result = run_dedup_batch(
			topic=args.topic,
			model=args.model,
			dry_run=args.dry_run,
			incremental=args.incremental,
		)
		report = write_run_report("dedup", result)
		print(json.dumps({**result, "report": report}, indent=2))
		return 0 if not result.get("failed") else 1

	if args.cmd == "retry-failed":
		from ux_kb.retry import pending_job_counts, retry_failed_jobs

		result = retry_failed_jobs(job_type=args.job_type, limit=args.limit)
		result["pending_after"] = pending_job_counts()
		print(json.dumps(result, indent=2))
		return 0

	if args.cmd == "recover-scrapes":
		from ux_kb.scrape_recover import recover_blocked_sources

		topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
		ids = {i.strip() for i in args.ids.split(",")} if args.ids else None
		report = recover_blocked_sources(
			limit=args.limit,
			use_browser=not args.no_browser,
			headed=not args.headless,
			topics=topics,
			source_ids=ids,
		)
		if args.then_extract and report.get("ok"):
			from ux_kb.chains import run_extract_batch

			recovered_ids = {r["source_id"] for r in report["ok"]}
			extract = run_extract_batch(limit=args.extract_limit, model=args.model, source_ids=recovered_ids)
			report["extract"] = extract
		print(json.dumps(report, indent=2))
		return 0 if report.get("recovered") else 1

	if args.cmd == "remap-tmp-ids":
		from ux_kb.id_remap import run_tmp_id_remap

		result = run_tmp_id_remap(refresh_graph=not args.no_refresh)
		print(json.dumps(result, indent=2))
		return 0

	if args.cmd == "quality-audit":
		from ux_kb.quality_audit import write_audit_report

		path = write_audit_report()
		report = json.loads(path.read_text(encoding="utf-8"))
		print(json.dumps({"report_path": str(path), **report["summary"]}, indent=2))
		return 0

	if args.cmd == "complete-phases":
		from ux_kb.graph_pipeline import run_complete_phases
		from ux_kb.status import write_run_report

		result = run_complete_phases(model=args.model, skip_accept=args.skip_accept)
		report = write_run_report("complete_phases", {"ok": [k for k in result], "failed": [], **result})
		print(json.dumps(result, indent=2))
		return 0

	if args.cmd == "run":
		from ux_kb.status import write_run_report

		if args.stage == "scrape":
			from ux_kb.scrape_worker import run_scrape_batch

			result = run_scrape_batch(limit=args.limit)
		elif args.stage == "extract":
			from ux_kb.chains import run_extract_batch

			result = run_extract_batch(limit=args.limit, model=args.model)
		elif args.stage == "dedup":
			from ux_kb.dedup import run_dedup_batch

			result = run_dedup_batch(model=args.model, incremental=True)
		elif args.stage == "accept-wave":
			from ux_kb.accept_wave import run_accept_wave

			result = run_accept_wave(model=args.model)
		elif args.stage == "relationships":
			from ux_kb.graph_pipeline import run_relationships, sync_principle_nodes

			sync_principle_nodes()
			result = run_relationships(model=args.model)
		elif args.stage == "patterns":
			from ux_kb.graph_pipeline import run_patterns

			result = run_patterns(model=args.model)
		elif args.stage == "playbooks":
			from ux_kb.graph_pipeline import run_playbooks

			result = run_playbooks(model=args.model)
		elif args.stage == "decisions":
			from ux_kb.graph_pipeline import export_graph_json
			from ux_kb.decisions import sync_decision_nodes

			result = sync_decision_nodes()
			result["export"] = export_graph_json()
		elif args.stage == "evidence":
			from ux_kb.graph_pipeline import export_graph_json
			from ux_kb.evidence import sync_evidence_nodes

			result = sync_evidence_nodes()
			result["export"] = export_graph_json()
		elif args.stage == "export-graph":
			from ux_kb.graph_pipeline import export_graph_json

			result = export_graph_json()
		elif args.stage == "distill":
			from ux_kb.graph_pipeline import run_distill

			result = run_distill()
		elif args.stage == "normalize":
			from ux_kb.chains import run_normalize_batch

			result = run_normalize_batch(limit=args.limit, model=args.model)
		else:
			raise ValueError(f"unknown stage: {args.stage}")
		report = write_run_report(args.stage, result)
		print(json.dumps({**result, "report": report}, indent=2))
		return 0 if not result.get("failed") else 1

	if args.cmd == "signoff-review":
		from ux_kb.signoff_review import write_signoff_review

		path = write_signoff_review()
		print(json.dumps({"signoff_path": str(path)}, indent=2))
		return 0

	if args.cmd == "apply-signoff":
		from ux_kb.apply_signoff import apply_default_signoff

		result = apply_default_signoff()
		print(json.dumps(result, indent=2))
		return 0

	if args.cmd == "retrieve":
		from ux_kb.retrieve import retrieve

		if args.example:
			req = {
				"intent": "Build analytics dashboard with sidebar nav",
				"surface_type": "dashboard",
				"task": "build analytics dashboard",
				"phase": "greenfield",
				"ui_component": "sidebar",
				"problem": "information hierarchy",
			}
		elif args.request:
			req = json.loads(Path(args.request).read_text(encoding="utf-8"))
		else:
			print(json.dumps({"error": "Use --example or --request path.json"}))
			return 1
		print(json.dumps(retrieve(req), indent=2, ensure_ascii=False))
		return 0

	if args.cmd == "query-battery":
		from ux_kb.query_battery import main as battery_main

		battery_main()
		return 0

	if args.cmd == "generate-query-catalog":
		from ux_kb.query_catalog import generate_query_catalog

		catalog = generate_query_catalog()
		print(json.dumps({"total": catalog["total"], "by_tier": catalog["by_tier"]}, indent=2))
		return 0

	if args.cmd == "probe-coverage":
		from ux_kb.coverage_probe import run_coverage_probe

		report = run_coverage_probe()
		print(
			json.dumps(
				{
					"queries": report["queries"],
					"classification": report["classification"],
					"coverage_ok_pct": report["coverage_ok_pct"],
					"gap_signal_pct": report["gap_signal_pct"],
					"report_md": report["report_md"],
				},
				indent=2,
			)
		)
		return 0

	if args.cmd == "gap-cluster":
		from ux_kb.gap_cluster import run_gap_cluster

		result = run_gap_cluster(top_n=args.top)
		print(json.dumps({"clusters": result["clusters_total"], "top5": [c["topic"] for c in result["clusters"][:5]]}, indent=2))
		return 0

	if args.cmd == "plan-expansion":
		from ux_kb.expansion_planner import plan_expansion

		result = plan_expansion()
		print(json.dumps({"plans": len(result["plans"]), "wave_topics": result["wave_topics"]}, indent=2))
		return 0

	if args.cmd == "expand-wave":
		from ux_kb.expand_wave import run_expand_wave

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
		return 0 if result.get("pass", True) and not result.get("error") else 1

	if args.cmd == "expand":
		from ux_kb.coverage_probe import run_coverage_probe
		from ux_kb.expand_wave import run_expand_wave
		from ux_kb.gap_cluster import run_gap_cluster
		from ux_kb.expansion_planner import plan_expansion
		from ux_kb.query_catalog import generate_query_catalog

		print("=== generate-query-catalog ===", flush=True)
		catalog = generate_query_catalog()
		print(json.dumps({"total": catalog["total"]}, indent=2), flush=True)

		print("=== probe-coverage ===", flush=True)
		probe = run_coverage_probe()
		print(json.dumps({"classification": probe["classification"], "gap_signal_pct": probe["gap_signal_pct"]}, indent=2), flush=True)

		print("=== gap-cluster ===", flush=True)
		gaps = run_gap_cluster(top_n=15)
		print(json.dumps({"clusters": gaps["clusters_total"], "top5": [c["topic"] for c in gaps["clusters"][:5]]}, indent=2), flush=True)

		print("=== plan-expansion ===", flush=True)
		plans = plan_expansion()
		print(json.dumps({"wave_topics": plans["wave_topics"]}, indent=2), flush=True)

		print("=== expand-wave ===", flush=True)
		topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
		wave = run_expand_wave(
			topics=topics,
			full=not args.skip_adc,
			scrape_limit=args.scrape_limit,
			model=args.model,
			skip_adc=args.skip_adc,
		)
		print(json.dumps({"pass": wave.get("pass"), "topic_stats": wave.get("topic_stats")}, indent=2), flush=True)
		return 0 if wave.get("pass", True) and not wave.get("error") else 1

	if args.cmd == "e2e-validation":
		from ux_kb.e2e_validation import main as e2e_main

		e2e_main()
		return 0

	if args.cmd == "evaluate-runtime":
		from ux_kb.evaluate_runtime import evaluate_and_write

		path = evaluate_and_write()
		print(json.dumps({"report_path": str(path)}, indent=2))
		return 0

	if args.cmd == "smoke":
		return cmd_smoke(args.model if hasattr(args, "model") else None)

	return 1


def cmd_smoke(model: str | None = None) -> int:
	"""Prerequisite smoke test for supervisor confidence."""
	from ux_kb.db import init_db, db_session
	from ux_kb.enqueue import enqueue_from_queue
	from ux_kb.seed import seed_import
	from ux_kb.scrape_worker import run_scrape_batch
	from ux_kb.status import status_summary, write_run_report

	print("=== init ===", flush=True)
	init_db()
	print("=== seed-import ===", flush=True)
	print(json.dumps(seed_import()), flush=True)
	print("=== enqueue ===", flush=True)
	print(json.dumps(enqueue_from_queue()), flush=True)

	# Gemini ADC smoke
	print("=== gemini adc ===", flush=True)
	sys.path.insert(0, str(Path(__file__).resolve().parent))
	from foropencode_pipeline import gemini_client

	try:
		text = gemini_client.smoke_test(model=model or gemini_client.DEFAULT_MODEL)
		print(json.dumps({"gemini": "ok", "response": text}), flush=True)
	except Exception as exc:  # noqa: BLE001
		print(json.dumps({"gemini": "fail", "error": str(exc)}), flush=True)
		return 1

	print("=== scrape limit 1 ===", flush=True)
	scrape_result = run_scrape_batch(limit=1)
	write_run_report("scrape", scrape_result)
	print(json.dumps(scrape_result), flush=True)
	if scrape_result.get("failed") and not scrape_result.get("ok"):
		return 1

	print("=== status ===", flush=True)
	print(json.dumps(status_summary(), indent=2), flush=True)

	with db_session() as conn:
		cards = conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"]
		sources = conn.execute("SELECT COUNT(*) AS c FROM sources").fetchone()["c"]
	print(json.dumps({"smoke": "ok", "cards": cards, "sources": sources}), flush=True)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
