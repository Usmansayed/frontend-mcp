"""Aggregate probe failures, budget gaps, and taxonomy into expansion clusters."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .db import db_session
from .paths import GAP_CLUSTERS, KB_ROOT, REPORTS, TOPIC_BUDGETS, URL_QUEUE


def _load_probe() -> dict[str, Any]:
	path = REPORTS / "coverage_probe.json"
	if not path.exists():
		from .coverage_probe import run_coverage_probe

		return run_coverage_probe()
	return json.loads(path.read_text(encoding="utf-8"))


def _budget_gaps() -> dict[str, dict[str, Any]]:
	budgets = yaml.safe_load(TOPIC_BUDGETS.read_text(encoding="utf-8")).get("budgets") or {}
	gaps: dict[str, dict[str, Any]] = {}
	with db_session() as conn:
		for topic, budget in budgets.items():
			accepted = conn.execute(
				"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='accepted'",
				(topic,),
			).fetchone()["c"]
			pending = conn.execute(
				"SELECT COUNT(*) AS c FROM cards WHERE topic=? AND status='pending_review'",
				(topic,),
			).fetchone()["c"]
			fill = accepted / max(1, int(budget))
			if fill < 0.5 or accepted == 0:
				gaps[topic] = {
					"budget": int(budget),
					"accepted": accepted,
					"pending_review": pending,
					"fill_ratio": round(fill, 3),
					"deficit": max(0, int(budget) - accepted),
				}
	return gaps


def _urls_by_topic() -> dict[str, list[dict[str, Any]]]:
	if not URL_QUEUE.exists():
		return {}
	data = yaml.safe_load(URL_QUEUE.read_text(encoding="utf-8"))
	by_topic: dict[str, list[dict[str, Any]]] = {}
	for row in data.get("urls") or []:
		if row.get("status") in ("skipped",):
			continue
		tp = row.get("topic") or "general"
		by_topic.setdefault(tp, []).append(row)
	for tp in by_topic:
		by_topic[tp].sort(key=lambda r: (r.get("priority") or "Z", r.get("id", "")))
	return by_topic


def _probe_failures_by_topic(probe: dict[str, Any]) -> dict[str, dict[str, int]]:
	out: dict[str, dict[str, int]] = {}
	for r in probe.get("results") or []:
		if r.get("status") == "ok":
			continue
		th = r.get("topic_hint") or "unknown"
		out.setdefault(th, {})
		st = r["status"]
		out[th][st] = out[th].get(st, 0) + 1
	return out


def _priority_score(
	topic: str,
	probe_fails: dict[str, int],
	budget_gap: dict[str, Any] | None,
	url_count: int,
) -> float:
	score = 0.0
	if probe_fails:
		score += probe_fails.get("misroute", 0) * 2
		score += probe_fails.get("no_playbook", 0) * 3
		score += probe_fails.get("thin", 0) * 1.5
		score += probe_fails.get("partial", 0) * 2.5
	if budget_gap:
		score += budget_gap.get("deficit", 0) * 1.2
		if budget_gap.get("accepted", 0) == 0:
			score += 10
	if url_count == 0:
		score -= 5  # can't expand without URLs
	else:
		score += min(5, url_count * 0.5)
	# Boost known gap topics
	if topic in ("typography", "motion", "auth", "data_tables", "search", "notifications", "agentic_ux"):
		score += 8
	return round(score, 2)


def run_gap_cluster(*, top_n: int = 15) -> dict[str, Any]:
	probe = _load_probe()
	budget_gaps = _budget_gaps()
	urls_by_topic = _urls_by_topic()
	probe_by_topic = _probe_failures_by_topic(probe)

	all_topics = set(probe_by_topic) | set(budget_gaps) | set(urls_by_topic)
	clusters: list[dict[str, Any]] = []

	for topic in all_topics:
		pf = probe_by_topic.get(topic, {})
		bg = budget_gaps.get(topic)
		urls = urls_by_topic.get(topic, [])
		if not pf and not bg:
			continue
		score = _priority_score(topic, pf, bg, len(urls))
		clusters.append(
			{
				"topic": topic,
				"priority_score": score,
				"probe_failures": pf,
				"probe_fail_total": sum(pf.values()),
				"budget": bg,
				"url_candidates": len(urls),
				"url_ids": [u["id"] for u in urls[:12]],
				"needs_playbook": topic in (
					"typography",
					"motion",
					"auth",
					"data_tables",
					"search",
					"notifications",
					"responsive",
					"agentic_ux",
				),
				"expansion_action": "scrape_extract_accept" if urls else "curate_urls_first",
			}
		)

	clusters.sort(key=lambda c: -c["priority_score"])
	clusters = clusters[:top_n]

	output = {
		"version": 1,
		"probe_queries": probe.get("queries"),
		"probe_gap_signal_pct": probe.get("gap_signal_pct"),
		"clusters_total": len(clusters),
		"clusters": clusters,
	}
	KB_ROOT.mkdir(parents=True, exist_ok=True)
	GAP_CLUSTERS.write_text(yaml.dump(output, sort_keys=False, allow_unicode=True), encoding="utf-8")
	REPORTS.mkdir(parents=True, exist_ok=True)
	(REPORTS / "gap_clusters.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
	output["path"] = str(GAP_CLUSTERS)
	return output


def main() -> None:
	result = run_gap_cluster()
	print(
		json.dumps(
			{
				"clusters": result["clusters_total"],
				"path": result["path"],
				"top5": [c["topic"] for c in result["clusters"][:5]],
			},
			indent=2,
		)
	)


if __name__ == "__main__":
	main()
