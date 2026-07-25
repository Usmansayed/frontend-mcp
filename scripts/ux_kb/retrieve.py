"""Deterministic UX knowledge retrieval engine — graph traversal, no embeddings."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .db import db_session, loads
from .evaluate_runtime import load_packs, score_pack
from .paths import GRAPHS, RUNTIME

EVIDENCE_STARS = {"standard": 5, "law": 4, "empirical": 3, "heuristic": 2, "opinion": 1}


@dataclass
class RetrievalRequest:
	intent: str = ""
	surface_type: str | None = None
	task: str | None = None
	phase: str | None = None
	ui_component: str | None = None
	user_flow: str | None = None
	product_type: str | None = None
	platform: str | None = None
	problem: str | None = None
	psychology_category: str | None = None
	max_depth: int = 3
	max_principles: int = 12
	max_patterns: int = 8
	max_conflicts: int = 5
	include_evidence: bool = True

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> RetrievalRequest:
		limits = data.get("limits") or {}
		inc = data.get("include") or {}
		return cls(
			intent=data.get("intent") or "",
			surface_type=data.get("surface_type"),
			task=data.get("task"),
			phase=data.get("phase"),
			ui_component=data.get("ui_component"),
			user_flow=data.get("user_flow"),
			product_type=data.get("product_type"),
			platform=data.get("platform"),
			problem=data.get("problem"),
			psychology_category=data.get("psychology_category"),
			max_depth=int(data.get("max_depth") or 3),
			max_principles=int(limits.get("max_principles") or 12),
			max_patterns=int(limits.get("max_patterns") or 8),
			max_conflicts=int(limits.get("max_conflicts") or 5),
			include_evidence=bool(inc.get("evidence", True)),
		)

	def to_filters(self) -> dict[str, list[str]]:
		out: dict[str, list[str]] = {}
		for key in (
			"surface_type",
			"phase",
			"ui_component",
			"user_flow",
			"product_type",
			"platform",
			"problem",
			"psychology_category",
		):
			val = getattr(self, key, None)
			if val:
				out[key] = [val] if isinstance(val, str) else list(val)
		return out


def _load_graph() -> tuple[dict[str, dict], list[dict]]:
	nodes = {
		n["id"]: n
		for n in json.loads((GRAPHS / "nodes.json").read_text(encoding="utf-8"))
	}
	edges = json.loads((GRAPHS / "edges.json").read_text(encoding="utf-8"))
	return nodes, edges


def _edges_from(edges: list[dict], source: str, relation: str | None = None) -> list[dict]:
	out = [e for e in edges if e.get("source") == source]
	if relation:
		out = [e for e in out if e.get("relation") == relation]
	return out


def _edges_to(edges: list[dict], target: str, relation: str | None = None) -> list[dict]:
	out = [e for e in edges if e.get("target") == target]
	if relation:
		out = [e for e in out if e.get("relation") == relation]
	return out


def _principle_strength(ec: str, source_count: int) -> int:
	base = EVIDENCE_STARS.get(ec or "heuristic", 2)
	return min(5, base + min(2, max(0, source_count - 1)))


def _load_principle_cards(ids: list[str]) -> dict[str, dict]:
	if not ids:
		return {}
	with db_session() as conn:
		ph = ",".join("?" * len(ids))
		rows = conn.execute(
			f"""
			SELECT id, title, rule, detect, when_to_apply, when_not_to_apply,
			       quote, source_ids_json, evidence_class, confidence
			FROM cards WHERE id IN ({ph})
			""",
			ids,
		).fetchall()
	out = {}
	for r in rows:
		d = dict(r)
		d["source_ids"] = loads(d.pop("source_ids_json"), [])
		out[d["id"]] = d
	return out


def retrieve(req: RetrievalRequest | dict[str, Any]) -> dict[str, Any]:
	if isinstance(req, dict):
		req = RetrievalRequest.from_dict(req)

	request_id = str(uuid.uuid4())[:8]
	traversal: list[str] = ["filter"]
	filters = req.to_filters()
	packs = load_packs()
	nodes, edges = _load_graph()

	# 1. Filter → best pack
	scored = sorted(((score_pack(p, filters), p) for p in packs), key=lambda x: (-x[0], x[1].get("pack_id", "")))
	best_score, best_pack = scored[0] if scored else (0, None)
	pack_id = best_pack.get("pack_id") if best_pack else None
	pb_id = best_pack.get("playbook_id") if best_pack else None
	stopped_reason = "limits_reached"

	if not best_pack or best_score < 3:
		stopped_reason = "no_match_fallback"
		return {
			"request_id": request_id,
			"matched_playbook": {"id": "", "title": "No match", "match_score": 0},
			"decisions": [],
			"patterns": [],
			"principles": [],
			"conflicts": [],
			"anti_patterns": [],
			"evidence": [],
			"meta": {
				"pack_id": None,
				"traversal_path": traversal,
				"stopped_reason": stopped_reason,
				"filter_keys_used": filters,
			},
		}

	traversal.append("playbook")
	pb_node = nodes.get(pb_id or "", {})
	matched_playbook = {
		"id": pb_id or "",
		"title": pb_node.get("label") or best_pack.get("title", ""),
		"guide_ref": pb_node.get("ref") or "",
		"match_score": round(best_score / 10, 2),
	}

	# 2. Playbook → decisions (ordered)
	decision_ids = [
		e["target"]
		for e in _edges_from(edges, pb_id or "", "decision_in")
	]
	decision_ids.sort(
		key=lambda did: (nodes.get(did, {}).get("metadata") or {}).get("order", 99)
	)
	decisions_out: list[dict[str, Any]] = []
	pattern_ids_ordered: list[str] = []
	seen_patterns: set[str] = set()

	for did in decision_ids[: req.max_depth + 2]:
		dnode = nodes.get(did, {})
		pats = [
			e["target"]
			for e in _edges_from(edges, did, "selects_pattern")
		]
		decisions_out.append(
			{
				"id": did,
				"label": dnode.get("label") or did,
				"pattern_ids": pats,
			}
		)
		for pid in pats:
			if pid not in seen_patterns:
				seen_patterns.add(pid)
				pattern_ids_ordered.append(pid)

	if decisions_out:
		traversal.append("decisions")

	# Fallback: pack pattern_refs if no decision layer
	if not pattern_ids_ordered:
		pattern_ids_ordered = list(best_pack.get("pattern_refs") or [])[: req.max_patterns]

	traversal.append("patterns")
	patterns_out: list[dict[str, Any]] = []
	principle_ids_ordered: list[str] = []
	seen_principles: set[str] = set()

	for pid in pattern_ids_ordered[: req.max_patterns]:
		pnode = nodes.get(pid, {})
		meta = pnode.get("metadata") or {}
		princ_id = meta.get("principle_id")
		if not princ_id:
			for e in _edges_from(edges, pid, "pattern_of"):
				princ_id = e["target"]
				break
		patterns_out.append(
			{
				"id": pid,
				"label": pnode.get("label") or pid,
				"implementation": meta.get("implementation") or "",
				"detect": meta.get("detect") or "",
				"principle_id": princ_id or "",
				"implementation_difficulty": meta.get("implementation_difficulty") or "",
			}
		)
		if princ_id and princ_id not in seen_principles:
			seen_principles.add(princ_id)
			principle_ids_ordered.append(princ_id)

	# Enrich principles from pack claim_stubs (topic slice)
	stub_ids = [s.get("claim_id") for s in best_pack.get("claim_stubs") or [] if s.get("claim_id")]
	for sid in stub_ids:
		if sid not in seen_principles:
			seen_principles.add(sid)
			principle_ids_ordered.append(sid)

	principle_ids_ordered = principle_ids_ordered[: req.max_principles]
	traversal.append("principles")
	cards = _load_principle_cards(principle_ids_ordered)
	principles_out: list[dict[str, Any]] = []
	for pid in principle_ids_ordered:
		c = cards.get(pid)
		if not c:
			continue
		src_n = len(c.get("source_ids") or [])
		principles_out.append(
			{
				"id": pid,
				"title": c["title"],
				"rule": c["rule"],
				"detect": c.get("detect") or "",
				"when_to_apply": c.get("when_to_apply") or "",
				"when_not_to_apply": c.get("when_not_to_apply") or "",
				"confidence": float(c.get("confidence") or 0),
				"evidence_strength": _principle_strength(c.get("evidence_class"), src_n),
				"source_ids": c.get("source_ids") or [],
			}
		)

	# Conflicts among retrieved principles
	traversal.append("conflicts")
	princ_set = set(principle_ids_ordered)
	conflicts_out: list[dict[str, Any]] = []
	for e in edges:
		if e.get("relation") not in ("contradicts", "CONFLICTS_WITH"):
			continue
		a, b = e.get("source"), e.get("target")
		if a in princ_set and b in princ_set:
			conflicts_out.append(
				{
					"a": a,
					"b": b,
					"decision_hint": e.get("context") or "",
				}
			)
	if len(conflicts_out) < req.max_conflicts:
		for cp in best_pack.get("conflict_pairs") or []:
			a, b = cp.get("a"), cp.get("b")
			if a in princ_set or b in princ_set:
				entry = {
					"a": a,
					"b": b,
					"decision_hint": cp.get("decision_hint") or "",
				}
				if entry not in conflicts_out:
					conflicts_out.append(entry)
	conflicts_out = conflicts_out[: req.max_conflicts]

	# Anti-patterns linked to principles
	anti_out: list[dict[str, Any]] = []
	for e in edges:
		if e.get("relation") != "contradicts":
			continue
		src, tgt = e.get("source"), e.get("target")
		if src.startswith("ap_") and tgt in princ_set:
			anti_out.append(
				{
					"id": src,
					"label": nodes.get(src, {}).get("label") or src,
					"violates_principle_id": tgt,
				}
			)

	# Evidence
	evidence_out: list[dict[str, Any]] = []
	if req.include_evidence:
		traversal.append("evidence")
		for pid in principle_ids_ordered:
			for e in _edges_from(edges, pid, "cites"):
				ev_id = e["target"]
				if not ev_id.startswith("ev_"):
					continue
				ev_node = nodes.get(ev_id, {})
				payload = ev_node.get("metadata") or {}
				# quote stored in payload_json in DB export - check ref
				quote = ""
				c = cards.get(pid)
				if c:
					quote = (c.get("quote") or "")[:500]
				evidence_out.append(
					{
						"principle_id": pid,
						"quote": quote,
						"source_ids": [payload.get("source_id") or e.get("context") or ""],
						"evidence_id": ev_id,
					}
				)

	return {
		"request_id": request_id,
		"matched_playbook": matched_playbook,
		"decisions": decisions_out,
		"patterns": patterns_out,
		"principles": principles_out,
		"related_principles": [],
		"conflicts": conflicts_out,
		"anti_patterns": anti_out[:10],
		"evidence": evidence_out,
		"meta": {
			"pack_id": pack_id,
			"traversal_path": traversal,
			"stopped_reason": stopped_reason,
			"filter_keys_used": filters,
			"pack_score": best_score,
		},
	}


def retrieve_from_json(path: Path | str) -> dict[str, Any]:
	data = json.loads(Path(path).read_text(encoding="utf-8"))
	return retrieve(data)
