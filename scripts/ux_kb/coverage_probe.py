"""Run query catalog through deterministic retrieval; classify coverage gaps."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .paths import QUERY_CATALOG, REPORTS
from .retrieve import retrieve


def classify_result(
	result: dict[str, Any],
	*,
	expect_pack: str | None,
	min_principles: int = 3,
	min_patterns: int = 2,
) -> tuple[str, list[str]]:
	meta = result.get("meta") or {}
	pb = result.get("matched_playbook") or {}
	pack_id = meta.get("pack_id")
	pb_id = pb.get("id")
	principles = len(result.get("principles") or [])
	patterns = len(result.get("patterns") or [])
	reasons: list[str] = []

	if meta.get("stopped_reason") == "no_match_fallback" or not pb_id:
		return "no_playbook", ["no_playbook_match"]

	if expect_pack is None:
		# Gap topic — any generic pack is a misroute
		if pack_id and pack_id not in ("pack_information_architecture",):
			return "misroute", [f"gap_topic_routed_to:{pack_id}"]
		if principles < min_principles:
			return "thin", [f"principles<{min_principles}"]
		return "partial", ["gap_topic_no_dedicated_pack"]

	if pack_id != expect_pack:
		reasons.append(f"pack: expected {expect_pack}, got {pack_id}")
		return "misroute", reasons

	if principles < min_principles:
		reasons.append(f"principles<{min_principles}")
		return "thin", reasons
	if patterns < min_patterns:
		reasons.append(f"patterns<{min_patterns}")
		return "thin", reasons

	return "ok", []


def run_coverage_probe(
	*,
	catalog_path: Path | None = None,
	min_principles: int = 3,
	min_patterns: int = 2,
) -> dict[str, Any]:
	path = catalog_path or QUERY_CATALOG
	if not path.exists():
		from .query_catalog import generate_query_catalog

		generate_query_catalog()

	data = yaml.safe_load(path.read_text(encoding="utf-8"))
	queries = data.get("queries") or []
	results: list[dict[str, Any]] = []
	counts: dict[str, int] = {}
	by_topic: dict[str, dict[str, int]] = {}

	for q in queries:
		req = {"intent": q["intent"], **(q.get("params") or {})}
		ret = retrieve(req)
		status, reasons = classify_result(
			ret,
			expect_pack=q.get("expect_pack"),
			min_principles=min_principles,
			min_patterns=min_patterns,
		)
		counts[status] = counts.get(status, 0) + 1
		th = q.get("topic_hint") or "unknown"
		by_topic.setdefault(th, {})
		by_topic[th][status] = by_topic[th].get(status, 0) + 1

		meta = ret.get("meta") or {}
		pb = ret.get("matched_playbook") or {}
		results.append(
			{
				"id": q["id"],
				"tier": q.get("tier"),
				"intent": q["intent"],
				"topic_hint": th,
				"expect_pack": q.get("expect_pack"),
				"status": status,
				"reasons": reasons,
				"pack_id": meta.get("pack_id"),
				"playbook_id": pb.get("id"),
				"principles": len(ret.get("principles") or []),
				"patterns": len(ret.get("patterns") or []),
				"source": q.get("source"),
			}
		)

	report = {
		"queries": len(queries),
		"classification": counts,
		"coverage_ok_pct": round(counts.get("ok", 0) / max(1, len(queries)), 3),
		"gap_signal_pct": round(
			(counts.get("no_playbook", 0) + counts.get("misroute", 0) + counts.get("thin", 0) + counts.get("partial", 0))
			/ max(1, len(queries)),
			3,
		),
		"by_topic_hint": by_topic,
		"by_tier": {},
		"results": results,
	}
	for tier in ("micro", "meso", "macro"):
		tier_results = [r for r in results if r["tier"] == tier]
		if tier_results:
			report["by_tier"][tier] = {
				"total": len(tier_results),
				"ok": sum(1 for r in tier_results if r["status"] == "ok"),
			}

	REPORTS.mkdir(parents=True, exist_ok=True)
	json_path = REPORTS / "coverage_probe.json"
	json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

	md_lines = [
		"# Coverage Probe Report",
		"",
		f"**{counts.get('ok', 0)}/{len(queries)} ok** · "
		f"thin {counts.get('thin', 0)} · misroute {counts.get('misroute', 0)} · "
		f"no_playbook {counts.get('no_playbook', 0)} · partial {counts.get('partial', 0)}",
		"",
		"## By topic (failures)",
		"",
	]
	for topic, stats in sorted(by_topic.items(), key=lambda x: -(x[1].get("misroute", 0) + x[1].get("thin", 0) + x[1].get("partial", 0))):
		fail = stats.get("misroute", 0) + stats.get("thin", 0) + stats.get("no_playbook", 0) + stats.get("partial", 0)
		if fail:
			md_lines.append(f"- **{topic}**: ok={stats.get('ok', 0)} fail={fail} ({stats})")

	md_path = REPORTS / "COVERAGE_PROBE.md"
	md_path.write_text("\n".join(md_lines), encoding="utf-8")
	report["report_json"] = str(json_path)
	report["report_md"] = str(md_path)
	return report


def main() -> None:
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


if __name__ == "__main__":
	main()
