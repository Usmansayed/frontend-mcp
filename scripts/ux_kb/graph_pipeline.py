"""Graph enrichment + patterns + playbooks + runtime distill (Gemini ADC + deterministic export)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .db import db_session, dumps, loads, utcnow
from .paths import GRAPHS, GUIDES, RUNTIME

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))

from foropencode_pipeline import gemini_client  # noqa: E402

EVIDENCE_STARS = {"standard": 5, "law": 4, "empirical": 3, "heuristic": 2, "opinion": 1}

PLAYBOOK_SPECS: list[dict[str, Any]] = [
	{
		"id": "pb_accessibility",
		"slug": "accessibility",
		"title": "Accessibility Engineering Playbook",
		"topics": ["a11y_absolute", "motor_ergonomics"],
		"retrieval_keys": {
			"surface_type": ["all"],
			"user_flow": ["general", "forms", "navigation"],
			"psychology_category": ["motor_ergonomics", "a11y_absolute"],
			"problem": ["accessibility", "a11y", "contrast", "focus", "target size", "keyboard"],
			"phase": ["hotfix", "polish"],
		},
		"target_surfaces": ["perception://verification-guide", "perception://ship-council", "hotfix", "polish"],
		"pack_id": "pack_accessibility",
	},
	{
		"id": "pb_forms",
		"slug": "forms",
		"title": "Form Design & Validation Playbook",
		"topics": ["forms"],
		"retrieval_keys": {
			"surface_type": ["forms", "checkout"],
			"user_flow": ["data_entry", "checkout", "signup"],
			"ui_component": ["textfield", "checkbox", "radio", "select"],
		},
		"target_surfaces": ["perception://guide/forms", "forms", "feature"],
		"pack_id": "pack_forms",
	},
	{
		"id": "pb_navigation",
		"slug": "navigation",
		"title": "Navigation & Wayfinding Playbook",
		"topics": ["hierarchy_density", "reading_flow"],
		"retrieval_keys": {
			"surface_type": ["marketing", "app_shell", "dashboard"],
			"user_flow": ["navigation", "browse"],
			"ui_component": ["nav", "sidebar", "mega_menu", "menu", "breadcrumb"],
			"product_type": ["ecommerce"],
			"problem": ["navigation", "wayfinding", "information hierarchy"],
		},
		"target_surfaces": ["perception://guide/feature", "feature", "redesign"],
		"pack_id": "pack_navigation",
	},
	{
		"id": "pb_information_architecture",
		"slug": "information_architecture",
		"title": "Information Architecture Playbook",
		"topics": ["settings", "general", "cognitive_load"],
		"retrieval_keys": {
			"surface_type": ["settings", "enterprise"],
			"user_flow": ["configuration", "browse"],
			"product_type": ["enterprise", "saas"],
			"problem": ["information architecture", "settings", "configuration", "IA"],
		},
		"target_surfaces": ["perception://guide/greenfield", "greenfield", "feature"],
		"pack_id": "pack_information_architecture",
	},
	{
		"id": "pb_psychology",
		"slug": "psychology",
		"title": "UX Psychology & Cognitive Load Playbook",
		"topics": ["cognitive_load", "aesthetic_usability", "human_factors"],
		"retrieval_keys": {
			"psychology_category": ["cognitive_load", "human_factors", "aesthetic_usability"],
		},
		"target_surfaces": ["perception://guide/feature", "feature", "redesign"],
		"pack_id": "pack_psychology",
	},
	{
		"id": "pb_dashboard",
		"slug": "dashboard",
		"title": "SaaS Dashboard Playbook",
		"topics": ["feedback_systems", "hierarchy_density", "design_tokens"],
		"retrieval_keys": {
			"surface_type": ["dashboard", "admin", "analytics"],
			"product_type": ["saas", "enterprise"],
			"problem": ["feedback", "information hierarchy", "density", "KPI", "data table"],
			"ui_component": ["sidebar", "data_table", "chart"],
		},
		"target_surfaces": ["perception://guide/feature", "feature", "greenfield"],
		"pack_id": "pack_dashboard",
	},
	{
		"id": "pb_onboarding",
		"slug": "onboarding",
		"title": "Onboarding & First-Use Playbook",
		"topics": ["onboarding", "checkout"],
		"retrieval_keys": {
			"surface_type": ["onboarding", "landing"],
			"user_flow": ["onboarding", "signup", "checkout"],
		},
		"target_surfaces": ["perception://guide/greenfield", "greenfield", "feature"],
		"pack_id": "pack_onboarding",
	},
	{
		"id": "pb_landing",
		"slug": "landing",
		"title": "Landing Page & Reading Flow Playbook",
		"topics": ["reading_flow", "onboarding", "hierarchy_density"],
		"retrieval_keys": {
			"surface_type": ["landing", "marketing"],
			"user_flow": ["conversion"],
			"problem": ["reading flow", "conversion", "CTA", "scannability", "hero"],
			"platform": ["mobile", "responsive"],
		},
		"target_surfaces": ["perception://guide/greenfield", "greenfield", "mockup"],
		"pack_id": "pack_landing",
	},
]

TOPIC_LABELS: dict[str, str] = {
	"a11y_absolute": "Accessibility (Absolute)",
	"motor_ergonomics": "Motor Ergonomics",
	"cognitive_load": "Cognitive Load",
	"hierarchy_density": "Hierarchy & Density",
	"forms": "Forms",
	"onboarding": "Onboarding",
	"checkout": "Checkout",
	"feedback_systems": "Feedback Systems",
	"design_tokens": "Design Tokens",
	"reading_flow": "Reading Flow",
	"human_factors": "Human Factors",
	"settings": "Settings & IA",
	"aesthetic_usability": "Aesthetic Usability",
	"agentic_ux": "Agentic UX",
	"general": "General UX",
}


def sync_topic_nodes() -> int:
	"""Ensure topic_* nodes exist for playbook_of edges and retrieval filters."""
	topics: set[str] = set()
	for spec in PLAYBOOK_SPECS:
		topics.update(spec.get("topics") or [])
	try:
		import yaml
		from .paths import TOPIC_BUDGETS

		if TOPIC_BUDGETS.exists():
			data = yaml.safe_load(TOPIC_BUDGETS.read_text(encoding="utf-8")) or {}
			topics.update((data.get("budgets") or {}).keys())
	except Exception:  # noqa: BLE001
		pass

	count = 0
	with db_session() as conn:
		for tp in sorted(topics):
			node_id = f"topic_{tp}"
			label = TOPIC_LABELS.get(tp, tp.replace("_", " ").title())
			upsert_graph_node(
				conn,
				node_id=node_id,
				node_type="topic",
				label=label,
				ref=f"02_taxonomy/TOPIC_TAXONOMY.yaml#{tp}",
				metadata={"topic_slug": tp},
			)
			count += 1
	return count


def _slug(s: str, n: int = 24) -> str:
	x = re.sub(r"[^a-zA-Z0-9]+", "_", s.lower()).strip("_")
	return x[:n] or "node"


def _edge_id(source: str, relation: str, target: str) -> str:
	return f"e_{_slug(source, 16)}_{relation}_{_slug(target, 16)}"[:80]


def _load_principles(*, status: str = "accepted") -> list[dict[str, Any]]:
	with db_session() as conn:
		rows = conn.execute(
			"""
			SELECT id, topic, title, rule, detect, when_to_apply, when_not_to_apply,
			       tradeoff, quote, source_ids_json, evidence_class, confidence,
			       conflicts_with_json, supersedes_json
			FROM cards WHERE status=?
			ORDER BY topic, title
			""",
			(status,),
		).fetchall()
	out = []
	for r in rows:
		d = dict(r)
		d["source_ids"] = loads(d.pop("source_ids_json"), [])
		d["conflicts_with"] = loads(d.pop("conflicts_with_json"), [])
		d.pop("supersedes_json", None)
		out.append(d)
	return out


def _compact_principle(p: dict[str, Any]) -> dict[str, Any]:
	src_n = len(p.get("source_ids") or [])
	ec = p.get("evidence_class") or "heuristic"
	stars = min(5, EVIDENCE_STARS.get(ec, 2) + min(2, max(0, src_n - 1)))
	return {
		"id": p["id"],
		"topic": p["topic"],
		"title": p["title"],
		"rule": (p.get("rule") or "")[:300],
		"evidence_class": ec,
		"confidence": p.get("confidence"),
		"evidence_strength": stars,
		"source_count": src_n,
	}


def upsert_graph_node(
	conn,
	*,
	node_id: str,
	node_type: str,
	label: str,
	ref: str | None = None,
	metadata: dict | None = None,
	payload: dict | None = None,
	status: str = "accepted",
) -> None:
	now = utcnow()
	conn.execute(
		"""
		INSERT INTO graph_nodes (id, node_type, label, ref, metadata_json, payload_json, status, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
		  node_type=excluded.node_type,
		  label=excluded.label,
		  ref=excluded.ref,
		  metadata_json=excluded.metadata_json,
		  payload_json=excluded.payload_json,
		  status=excluded.status,
		  updated_at=excluded.updated_at
		""",
		(
			node_id,
			node_type,
			label,
			ref or "",
			dumps(metadata or {}),
			dumps(payload or {}),
			status,
			now,
			now,
		),
	)


def upsert_graph_edge(
	conn,
	*,
	source_id: str,
	target_id: str,
	relation: str,
	context: str | None = None,
	confidence: float = 0.8,
) -> None:
	eid = _edge_id(source_id, relation, target_id)
	conn.execute(
		"""
		INSERT INTO graph_edges (id, source_id, target_id, relation, context, confidence, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
		  context=excluded.context,
		  confidence=excluded.confidence
		""",
		(eid, source_id, target_id, relation, context or "", confidence, utcnow()),
	)


def sync_principle_nodes(principles: list[dict[str, Any]] | None = None) -> int:
	principles = principles or _load_principles()
	count = 0
	with db_session() as conn:
		for p in principles:
			meta = {
				"topic": p["topic"],
				"evidence_class": p["evidence_class"],
				"confidence": p["confidence"],
				"evidence_strength": _compact_principle(p)["evidence_strength"],
				"source_count": len(p.get("source_ids") or []),
			}
			upsert_graph_node(
				conn,
				node_id=p["id"],
				node_type="principle",
				label=p["title"],
				ref=f"kb://cards/{p['id']}",
				metadata=meta,
				payload={
					"rule": p["rule"],
					"detect": p["detect"],
					"when_to_apply": p["when_to_apply"],
					"when_not_to_apply": p["when_not_to_apply"],
					"tradeoff": p["tradeoff"],
					"source_ids": p.get("source_ids") or [],
				},
			)
			count += 1
	return count


def run_relationships(*, model: str | None = None, batch_topics: bool = True) -> dict[str, Any]:
	"""Infer principle-to-principle edges via Gemini."""
	if model:
		import os

		os.environ["FOROPENCODE_GEMINI_MODEL"] = model

	principles = _load_principles()
	sync_principle_nodes(principles)
	by_topic: dict[str, list[dict]] = {}
	for p in principles:
		by_topic.setdefault(p["topic"], []).append(p)

	all_edges: list[dict] = []
	fail: list[dict] = []

	for topic, group in by_topic.items():
		if len(group) < 2:
			continue
		compact = [_compact_principle(p) for p in group]
		prompt = f"""Build explicit knowledge-graph edges between UX principles (topic: {topic}).

Principles:
{json.dumps(compact, indent=2)}

Return JSON:
{{
  "edges": [
    {{
      "source": "principle_id",
      "target": "principle_id",
      "relation": "supports|contradicts|prerequisite|related_to|applies_to",
      "context": "brief why",
      "confidence": 0.0-1.0
    }}
  ]
}}

Rules:
- Only use ids from the list. No invented ids.
- contradicts = genuine tradeoff (both valid in different contexts)
- supports = one strengthens/corroborates the other
- related_to = same domain, not duplicate
- Max 15 edges per batch. Prefer high-signal links.
"""
		try:
			data = gemini_client.generate_json(prompt=prompt, temperature=0.05, model=model)
			edges = data.get("edges") or []
			ids = {p["id"] for p in group}
			with db_session() as conn:
				for e in edges:
					s, t = e.get("source"), e.get("target")
					if s not in ids or t not in ids or s == t:
						continue
					rel = e.get("relation") or "related_to"
					upsert_graph_edge(
						conn,
						source_id=s,
						target_id=t,
						relation=rel,
						context=e.get("context"),
						confidence=float(e.get("confidence") or 0.75),
					)
					all_edges.append(e)
					if rel == "contradicts":
						conn.execute(
							"""
							UPDATE cards SET conflicts_with_json=?, updated_at=?
							WHERE id=?
							""",
							(
								dumps(list(set(loads(
									conn.execute(
										"SELECT conflicts_with_json FROM cards WHERE id=?", (s,)
									).fetchone()[0],
									[],
								) + [t]))),
								utcnow(),
								s,
							),
						)
		except Exception as exc:  # noqa: BLE001
			fail.append({"topic": topic, "error": str(exc)[:300]})

	return {"edges_written": len(all_edges), "edges_sample": all_edges[:10], "failed": fail}


def run_patterns(*, model: str | None = None) -> dict[str, Any]:
	"""Generate implementation patterns for accepted principles."""
	if model:
		import os

		os.environ["FOROPENCODE_GEMINI_MODEL"] = model

	principles = _load_principles()
	patterns_written = 0
	fail: list[dict] = []

	by_topic: dict[str, list] = {}
	for p in principles:
		by_topic.setdefault(p["topic"], []).append(p)

	for topic, group in by_topic.items():
		compact = [_compact_principle(p) for p in group[:20]]
		prompt = f"""For each UX principle below, produce 0-1 implementation PATTERN (concrete UI/code recipe).

Topic: {topic}
Principles:
{json.dumps(compact, indent=2)}

Return JSON:
{{
  "patterns": [
    {{
      "id": "pat_snake_case_id",
      "principle_id": "UX_...",
      "label": "Pattern Name",
      "implementation": "how to implement",
      "detect": "how to verify in code/UI",
      "anti_pattern": "what to avoid",
      "metadata": {{
        "surface_type": ["dashboard|forms|..."],
        "ui_component": ["modal|button|..."],
        "implementation_difficulty": "low|medium|high"
      }}
    }}
  ]
}}

Skip principles that don't need a distinct pattern. Max 1 pattern per principle.
"""
		try:
			data = gemini_client.generate_json(prompt=prompt, temperature=0.1, model=model)
			with db_session() as conn:
				for pat in data.get("patterns") or []:
					pid = pat.get("id") or f"pat_{_slug(pat.get('label', 'pattern'))}"
					princ_id = pat.get("principle_id")
					if not princ_id:
						continue
					upsert_graph_node(
						conn,
						node_id=pid,
						node_type="pattern",
						label=pat.get("label") or pid,
						ref=f"kb://patterns/{pid}",
						metadata=pat.get("metadata") or {},
						payload={
							"implementation": pat.get("implementation"),
							"detect": pat.get("detect"),
							"anti_pattern": pat.get("anti_pattern"),
							"principle_id": princ_id,
						},
					)
					upsert_graph_edge(
						conn,
						source_id=pid,
						target_id=princ_id,
						relation="pattern_of",
						context=pat.get("label"),
					)
					if pat.get("anti_pattern"):
						ap_id = f"ap_{_slug(pat['anti_pattern'][:40])}"
						upsert_graph_node(
							conn,
							node_id=ap_id,
							node_type="anti_pattern",
							label=pat["anti_pattern"][:120],
							payload={"violates": princ_id},
						)
						upsert_graph_edge(
							conn,
							source_id=ap_id,
							target_id=princ_id,
							relation="contradicts",
							context="anti-pattern",
						)
					patterns_written += 1
		except Exception as exc:  # noqa: BLE001
			fail.append({"topic": topic, "error": str(exc)[:300]})

	return {"patterns_written": patterns_written, "failed": fail}


def run_playbooks(*, model: str | None = None) -> dict[str, Any]:
	"""Generate situation playbooks from principles + patterns."""
	if model:
		import os

		os.environ["FOROPENCODE_GEMINI_MODEL"] = model

	principles = _load_principles()
	principle_by_id = {p["id"]: p for p in principles}
	written = 0
	fail: list[dict] = []

	for spec in PLAYBOOK_SPECS:
		relevant = [p for p in principles if p["topic"] in spec["topics"]]
		if not relevant:
			continue
		compact = [_compact_principle(p) for p in relevant[:25]]
		prompt = f"""Compose an engineering playbook for: {spec['title']}

Relevant principles:
{json.dumps(compact, indent=2)}

Return JSON:
{{
  "core_philosophy": "2-3 sentences",
  "principle_order": ["UX_...", "..."],
  "sections": [
    {{"heading": "...", "body": "...", "principle_ids": ["UX_..."]}}
  ],
  "decision_framework": ["When X choose Y because Z"],
  "anti_patterns": [{{"title": "...", "why": "...", "principle_id": "UX_..."}}]
}}

Order principles by application priority for this situation. Cite only ids from the list.
"""
		try:
			data = gemini_client.generate_json(prompt=prompt, temperature=0.15, model=model)
			pb_id = spec["id"]
			GUIDES.mkdir(parents=True, exist_ok=True)
			md_path = GUIDES / f"guide_{spec['slug']}.md"
			sections_md = "\n\n".join(
				f"### {s.get('heading', 'Section')}\n\n{s.get('body', '')}\n\nPrinciples: {', '.join(s.get('principle_ids') or [])}"
				for s in data.get("sections") or []
			)
			anti_md = "\n".join(
				f"- **{a.get('title')}**: {a.get('why')} ({a.get('principle_id')})"
				for a in data.get("anti_patterns") or []
			)
			decision_md = "\n".join(f"- {d}" for d in data.get("decision_framework") or [])
			principle_order = data.get("principle_order") or [p["id"] for p in relevant[:12]]
			md = f"""# {spec['title']}

## Core philosophy

{data.get('core_philosophy') or ''}

## Principles (priority order)

{chr(10).join(f'1. `{pid}`' for pid in principle_order)}

## Sections

{sections_md}

## Decision framework

{decision_md}

## Anti-patterns

{anti_md}

## References

Playbook id: `{pb_id}`
"""
			md_path.write_text(md, encoding="utf-8")
			with db_session() as conn:
				upsert_graph_node(
					conn,
					node_id=pb_id,
					node_type="playbook",
					label=spec["title"],
					ref=f"07_guides/guide_{spec['slug']}.md",
					metadata={
						**spec.get("retrieval_keys", {}),
						"target_surfaces": spec.get("target_surfaces", []),
					},
					payload=data,
				)
				for tp in spec["topics"]:
					upsert_graph_edge(
						conn,
						source_id=pb_id,
						target_id=f"topic_{tp}",
						relation="playbook_of",
						context=tp,
					)
				for pid in principle_order:
					if pid in principle_by_id:
						upsert_graph_edge(
							conn,
							source_id=pb_id,
							target_id=pid,
							relation="composed_in",
							context="playbook principle",
						)
			written += 1
		except Exception as exc:  # noqa: BLE001
			fail.append({"playbook": spec["id"], "error": str(exc)[:300]})

	return {"playbooks_written": written, "failed": fail}


def export_graph_json() -> dict[str, Any]:
	"""Export SQLite graph to 08_graphs/nodes.json + edges.json."""
	GRAPHS.mkdir(parents=True, exist_ok=True)
	with db_session() as conn:
		nodes = []
		for r in conn.execute(
			"SELECT id, node_type, label, ref, metadata_json, payload_json FROM graph_nodes ORDER BY node_type, id"
		).fetchall():
			meta = loads(r["metadata_json"], {})
			payload = loads(r["payload_json"], {})
			if r["node_type"] == "pattern" and payload:
				meta = {**meta, **{k: payload[k] for k in ("implementation", "detect", "principle_id", "anti_pattern") if k in payload}}
			if r["node_type"] == "evidence" and payload:
				meta = {**meta, **payload}
			nodes.append(
				{
					"id": r["id"],
					"type": r["node_type"],
					"label": r["label"],
					"ref": r["ref"] or None,
					"metadata": meta,
				}
			)
		edges = []
		for r in conn.execute(
			"SELECT id, source_id, target_id, relation, context, confidence FROM graph_edges ORDER BY relation, id"
		).fetchall():
			edges.append(
				{
					"id": r["id"],
					"source": r["source_id"],
					"target": r["target_id"],
					"relation": r["relation"],
					"context": r["context"],
					"confidence": r["confidence"],
				}
			)
	nodes_path = GRAPHS / "nodes.json"
	edges_path = GRAPHS / "edges.json"
	nodes_path.write_text(json.dumps(nodes, indent=2, ensure_ascii=False), encoding="utf-8")
	edges_path.write_text(json.dumps(edges, indent=2, ensure_ascii=False), encoding="utf-8")
	return {"nodes": len(nodes), "edges": len(edges), "nodes_path": str(nodes_path), "edges_path": str(edges_path)}


def run_distill() -> dict[str, Any]:
	"""Build runtime knowledge packs from playbooks + accepted principles."""
	RUNTIME.mkdir(parents=True, exist_ok=True)
	principles = _load_principles()
	principle_by_id = {p["id"]: p for p in principles}
	packs_written: list[str] = []

	with db_session() as conn:
		for spec in PLAYBOOK_SPECS:
			relevant = [p for p in principles if p["topic"] in spec["topics"]]
			if not relevant:
				continue
			relevant.sort(key=lambda x: (-float(x.get("confidence") or 0), x["title"]))
			stubs = []
			for p in relevant[:20]:
				stubs.append(
					{
						"claim_id": p["id"],
						"name": p["title"],
						"engineering_meaning": p["rule"],
						"how_to_detect_violations": p["detect"],
						"when_to_apply": p["when_to_apply"],
						"when_not_to_apply": p["when_not_to_apply"],
						"confidence": float(p["confidence"]),
						"source_ids": p.get("source_ids") or [],
						"full_card_path": f"kb://cards/{p['id']}",
					}
				)
			pids = [p["id"] for p in relevant]
			conflicts = []
			if pids:
				placeholders = ",".join("?" * len(pids))
				for r in conn.execute(
					f"""
					SELECT source_id, target_id, context FROM graph_edges
					WHERE relation IN ('contradicts', 'CONFLICTS_WITH')
					AND (source_id IN ({placeholders}) OR target_id IN ({placeholders}))
					""",
					pids + pids,
				).fetchall():
					conflicts.append(
						{"a": r["source_id"], "b": r["target_id"], "decision_hint": r["context"] or ""}
					)
			related: list[str] = []
			if pids:
				placeholders = ",".join("?" * len(pids))
				for r in conn.execute(
					f"""
					SELECT DISTINCT target_id FROM graph_edges
					WHERE relation IN ('related_to', 'supports')
					AND source_id IN ({placeholders})
					LIMIT 15
					""",
					pids,
				).fetchall():
					related.append(r["target_id"])
			pattern_refs = [
				r["id"]
				for r in conn.execute(
					"SELECT id FROM graph_nodes WHERE node_type='pattern' ORDER BY id"
				).fetchall()
			][:12]
			pack = {
				"pack_id": spec["pack_id"],
				"title": spec["title"],
				"target_surfaces": spec.get("target_surfaces", []),
				"retrieval_keys": spec.get("retrieval_keys", {}),
				"playbook_id": spec["id"],
				"pattern_refs": pattern_refs,
				"related_principle_ids": related,
				"claim_stubs": stubs,
				"conflict_pairs": conflicts[:10],
				"budgets": {"max_claim_stubs": 20, "max_rationale_tokens": 2500},
				"created_at": utcnow()[:10],
				"notes": "Graph-slice pack — deterministic retrieval, no embeddings.",
			}
			path = RUNTIME / f"{spec['pack_id']}.json"
			path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
			packs_written.append(spec["pack_id"])
			upsert_graph_node(
				conn,
				node_id=spec["pack_id"],
				node_type="runtime_pack",
				label=spec["title"],
				ref=f"09_runtime/{spec['pack_id']}.json",
				metadata=spec.get("retrieval_keys", {}),
			)
			upsert_graph_edge(conn, source_id=spec["pack_id"], target_id=spec["id"], relation="packed_in")

	return {"packs_written": packs_written, "count": len(packs_written)}


def run_complete_phases(*, model: str | None = None, skip_accept: bool = False) -> dict[str, Any]:
	"""Run accept → relationships → patterns → playbooks → export → distill."""
	from .accept_wave import run_accept_wave

	results: dict[str, Any] = {}
	if not skip_accept:
		results["accept"] = run_accept_wave(model=model, auto_accept=True)
	results["principle_nodes"] = sync_principle_nodes()
	results["relationships"] = run_relationships(model=model)
	results["patterns"] = run_patterns(model=model)
	results["playbooks"] = run_playbooks(model=model)
	from .decisions import sync_decision_nodes

	results["decisions"] = sync_decision_nodes()
	from .evidence import sync_evidence_nodes

	results["evidence"] = sync_evidence_nodes()
	results["topic_nodes"] = sync_topic_nodes()
	results["export"] = export_graph_json()
	results["distill"] = run_distill()
	return results
