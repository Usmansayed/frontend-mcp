"""Phase 1 quality audit: principles, graph, packs, playbooks."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .db import db_session, loads
from .paths import GRAPHS, GUIDES, KB_ROOT, RUNTIME

EVIDENCE_RANK = {"standard": 5, "law": 4, "empirical": 3, "heuristic": 2, "opinion": 1}


def _load_graph() -> tuple[list[dict], list[dict]]:
	nodes = json.loads((GRAPHS / "nodes.json").read_text(encoding="utf-8"))
	edges = json.loads((GRAPHS / "edges.json").read_text(encoding="utf-8"))
	return nodes, edges


def _load_packs() -> list[dict[str, Any]]:
	out = []
	for p in RUNTIME.glob("pack_*.json"):
		try:
			out.append(json.loads(p.read_text(encoding="utf-8")))
		except Exception:
			pass
	return out


def _principle_quality_score(row: dict) -> dict[str, Any]:
	rule = (row.get("rule") or "").strip()
	detect = (row.get("detect") or "").strip()
	sources = loads(row.get("source_ids_json"), [])
	ec = row.get("evidence_class") or "heuristic"
	conf = float(row.get("confidence") or 0)
	flags: list[str] = []
	score = 100

	if len(rule) < 40:
		flags.append("thin_rule")
		score -= 25
	if len(detect) < 30:
		flags.append("weak_detect")
		score -= 20
	if len(sources) < 2 and ec not in ("standard", "law"):
		flags.append("single_source_heuristic")
		score -= 15
	if conf < 0.75:
		flags.append("low_confidence")
		score -= 10
	if ec == "opinion":
		flags.append("opinion_class")
		score -= 20
	if row.get("id", "").startswith("UX_TMP_"):
		flags.append("tmp_id_leak")
		score -= 30
	vague = re.search(
		r"\b(make it usable|user-friendly|intuitive|clean|simple|better ux)\b",
		rule.lower(),
	)
	if vague:
		flags.append("vague_wording")
		score -= 15

	return {
		"id": row["id"],
		"topic": row["topic"],
		"title": row["title"],
		"quality_score": max(0, score),
		"flags": flags,
		"source_count": len(sources),
		"confidence": conf,
		"evidence_class": ec,
	}


def audit_suspicious_edges(nodes: list[dict], edges: list[dict]) -> list[dict[str, Any]]:
	node_ids = {n["id"] for n in nodes}
	suspicious: list[dict[str, Any]] = []

	for e in edges:
		s, t, rel = e.get("source"), e.get("target"), e.get("relation")
		reasons: list[str] = []
		if s not in node_ids:
			reasons.append("missing_source_node")
		if t not in node_ids:
			reasons.append("missing_target_node")
		if s == t and rel not in ("contradicts",):
			reasons.append("self_loop")
		if rel == "contradicts" and s.startswith("ap_") and not t.startswith("UX_"):
			reasons.append("anti_pattern_wrong_target")
		if rel in ("supports", "related_to") and s.startswith("ap_"):
			reasons.append("anti_pattern_as_support")
		if rel == "playbook_of" and not s.startswith("pb_"):
			reasons.append("playbook_of_wrong_direction")
		if s.startswith("topic_") and t.startswith("topic_"):
			reasons.append("topic_to_topic_only")
		ctx = (e.get("context") or "").lower()
		if rel == "contradicts" and len(ctx) < 8:
			reasons.append("contradicts_no_context")
		if reasons:
			suspicious.append(
				{
					"edge_id": e.get("id"),
					"source": s,
					"target": t,
					"relation": rel,
					"context": e.get("context"),
					"reasons": reasons,
					"severity": len(reasons),
				}
			)

	suspicious.sort(key=lambda x: (-x["severity"], x["relation"]))
	return suspicious[:25]


def audit_duplicate_conflicts(
	nodes: list[dict], edges: list[dict], principles: list[dict]
) -> dict[str, Any]:
	principle_ids = {p["id"] for p in principles}
	title_map: dict[str, list[str]] = defaultdict(list)
	for p in principles:
		key = re.sub(r"[^a-z0-9]+", "", (p.get("title") or "").lower())[:40]
		if key:
			title_map[key].append(p["id"])

	near_dup_titles = [{k: v} for k, v in title_map.items() if len(v) > 1]

	# principles citing each other as conflicts vs graph
	graph_conflicts = {
		(frozenset({e["source"], e["target"]}))
		for e in edges
		if e.get("relation") in ("contradicts", "CONFLICTS_WITH")
		and e["source"].startswith("UX_")
		and e["target"].startswith("UX_")
	}
	card_conflicts: set[frozenset[str]] = set()
	for p in principles:
		for cid in loads(p.get("conflicts_with_json"), []):
			if cid in principle_ids:
				card_conflicts.add(frozenset({p["id"], cid}))

	missing_in_graph = [list(x) for x in card_conflicts - graph_conflicts]
	missing_in_cards = [list(x) for x in graph_conflicts - card_conflicts]

	# bidirectional contradicts (may be ok but flag)
	pairs = Counter()
	for e in edges:
		if e.get("relation") == "contradicts":
			pairs[(min(e["source"], e["target"]), max(e["source"], e["target"]))] += 1
	bidirectional = [k for k, v in pairs.items() if v > 1]

	# merged/tmp ids referenced in packs
	packs = _load_packs()
	stale_refs: list[dict] = []
	for pack in packs:
		for stub in pack.get("claim_stubs") or []:
			cid = stub.get("claim_id")
			if cid and (cid.startswith("UX_TMP_") or cid not in principle_ids):
				stale_refs.append({"pack": pack.get("pack_id"), "claim_id": cid})
		for rid in pack.get("related_principle_ids") or []:
			if rid.startswith("UX_TMP_") or (rid.startswith("UX_") and rid not in principle_ids):
				stale_refs.append({"pack": pack.get("pack_id"), "related_id": rid})

	return {
		"near_duplicate_titles": near_dup_titles[:10],
		"conflicts_in_cards_not_graph": missing_in_graph[:10],
		"conflicts_in_graph_not_cards": missing_in_cards[:10],
		"bidirectional_contradicts": bidirectional[:10],
		"stale_pack_references": stale_refs[:20],
	}


def audit_weak_principles(limit: int = 20) -> list[dict[str, Any]]:
	with db_session() as conn:
		rows = conn.execute(
			"""
			SELECT id, topic, title, rule, detect, source_ids_json,
			       evidence_class, confidence, status
			FROM cards WHERE status='accepted'
			ORDER BY topic, title
			"""
		).fetchall()
	scored = [_principle_quality_score(dict(r)) for r in rows]
	candidates = [s for s in scored if s["quality_score"] < 90 or s["flags"]]
	candidates.sort(key=lambda x: (x["quality_score"], -x["confidence"]))
	return candidates[:limit]


def audit_over_budget_candidates(limit: int = 15) -> list[dict[str, Any]]:
	with db_session() as conn:
		rows = conn.execute(
			"""
			SELECT id, topic, title, rule, detect, source_ids_json,
			       evidence_class, confidence
			FROM cards WHERE status='rejected_over_budget'
			ORDER BY confidence DESC, topic
			LIMIT ?
			""",
			(limit,),
		).fetchall()
	return [_principle_quality_score(dict(r)) for r in rows]


def audit_playbooks() -> list[dict[str, Any]]:
	issues = []
	for path in sorted(GUIDES.glob("guide_*.md")):
		text = path.read_text(encoding="utf-8")
		slug = path.stem.replace("guide_", "")
		principle_refs = re.findall(r"`(UX_[A-Z0-9_]+)`", text)
		empty_sections = []
		for heading in ["Core philosophy", "Decision framework", "Anti-patterns"]:
			m = re.search(
				rf"## {re.escape(heading)}\s*\n\s*\n\s*##",
				text,
			)
			if m:
				empty_sections.append(heading)
		if len(principle_refs) < 3:
			issues.append(
				{
					"guide": path.name,
					"issue": "few_principle_citations",
					"count": len(principle_refs),
				}
			)
		if empty_sections:
			issues.append({"guide": path.name, "issue": "empty_sections", "sections": empty_sections})
		if len(text) < 500:
			issues.append({"guide": path.name, "issue": "thin_playbook", "bytes": len(text)})
	return issues


def audit_graph_coverage(nodes: list[dict], edges: list[dict]) -> dict[str, Any]:
	principle_nodes = [n for n in nodes if n.get("type") == "principle"]
	principle_ids = {n["id"] for n in principle_nodes}
	incoming = Counter(e["target"] for e in edges)
	outgoing = Counter(e["source"] for e in edges)
	orphans = [pid for pid in principle_ids if incoming[pid] == 0 and outgoing[pid] == 0]
	no_pattern = [
		pid
		for pid in principle_ids
		if not any(
			e.get("relation") == "pattern_of" and e.get("target") == pid for e in edges
		)
	]
	relation_counts = Counter(e.get("relation") for e in edges)
	return {
		"principle_count": len(principle_ids),
		"orphan_principles": orphans[:15],
		"orphan_count": len(orphans),
		"principles_without_pattern": len(no_pattern),
		"relation_counts": dict(relation_counts),
		"missing_decision_nodes": False,
		"missing_evidence_nodes": True,
	}


def run_quality_audit() -> dict[str, Any]:
	nodes, edges = _load_graph()
	with db_session() as conn:
		accepted = [dict(r) for r in conn.execute(
			"SELECT id, topic, title FROM cards WHERE status='accepted'"
		).fetchall()]

	suspicious = audit_suspicious_edges(nodes, edges)
	with db_session() as conn:
		principle_rows = [
			dict(r)
			for r in conn.execute(
				"""
				SELECT id, topic, title, rule, detect, source_ids_json,
				       evidence_class, confidence, conflicts_with_json
				FROM cards WHERE status='accepted'
				"""
			).fetchall()
		]

	report = {
		"summary": {
			"accepted_principles": len(accepted),
			"graph_nodes": len(nodes),
			"graph_edges": len(edges),
			"suspicious_edges": len(suspicious),
			"playbook_issues": len(audit_playbooks()),
		},
		"top_suspicious_edges": suspicious[:15],
		"duplicate_and_conflict_anomalies": audit_duplicate_conflicts(
			nodes, edges, principle_rows
		),
		"weak_principles_demote_candidates": audit_weak_principles(20),
		"over_budget_promote_candidates": audit_over_budget_candidates(15),
		"playbook_issues": audit_playbooks(),
		"graph_coverage_gaps": audit_graph_coverage(nodes, edges),
		"recommendations": [
			"Add decision nodes between playbook and pattern (Navigation Strategy → Sticky Sidebar).",
			"Add evidence nodes linked via cites from each accepted principle.",
			"Fix stale UX_TMP_* references in runtime pack related_principle_ids.",
			"Increase applies_to and prerequisite edges (currently sparse).",
			"Manually review 20 rejected_over_budget cards before raising topic budgets.",
			"Regenerate pb_landing playbook if guide_landing.md is thin.",
			"Do not integrate MCP until retrieval contract v1 is signed off.",
		],
	}
	return report


def write_audit_report() -> Path:
	report = run_quality_audit()
	out_dir = KB_ROOT / "reports"
	out_dir.mkdir(parents=True, exist_ok=True)
	path = out_dir / "quality_audit_phase1.json"
	path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
	return path
