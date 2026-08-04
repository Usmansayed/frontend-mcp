"""Gemini compose: comparison + guide playbooks."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from . import gemini_client
from .paths import COMPARISONS, GUIDES, NORMALIZED, SCHEMAS
from .validate import write_or_draft

PASS_COMPOSE: dict[int, dict[str, Any]] = {
	1: {
		"claim_ids": [
			"UX_HCI_STEER_011",
			"UX_VIS_GEST_006",
			"UX_HFE_TLX_001",
			"UX_HCI_FITTS_001",
			"UX_COG_HICK_002",
		],
		"cluster_id": "cl_density_vs_spacing",
		"taxonomy_path": ["Visual Perception", "Hierarchy", "density_spacing"],
		"cluster_topic": "density vs spacing / motor-cognitive tradeoffs",
		"guide_id": "guide_hierarchy_density",
		"guide_title": "Hierarchy & Density Engineering Playbook",
		"guide_slug": "hierarchy-density",
	},
	2: {
		"claim_ids": [
			"UX_HCI_KLM_008",
			"UX_VIS_READ_014",
			"UX_DS_DENS_002",
			"UX_DS_TOKEN_001",
			"UX_HCI_FITTS_001",
			"UX_VIS_GEST_006",
			"UX_COG_HICK_002",
		],
		"cluster_id": "cl_design_systems_density",
		"taxonomy_path": ["Design Systems", "Density", "tokens"],
		"cluster_topic": "enterprise density vs semantic tokens vs reading flow / KLM cost",
		"guide_id": "guide_design_systems",
		"guide_title": "Design Systems Density & Tokens Playbook",
		"guide_slug": "design-systems-density-tokens",
	},
}


def _load_cards(claim_ids: list[str]) -> dict[str, Any]:
	cards = {}
	for cid in claim_ids:
		path = NORMALIZED / f"{cid}.json"
		if path.exists():
			cards[cid] = json.loads(path.read_text(encoding="utf-8"))
	return cards


def compose_comparison(
	pass_num: int = 1,
	*,
	client=None,
	model: str | None = None,
) -> dict[str, Any]:
	cfg = PASS_COMPOSE[pass_num]
	schema = (SCHEMAS / "comparison.schema.json").read_text(encoding="utf-8")
	cards = _load_cards(cfg["claim_ids"])
	cluster_id = cfg["cluster_id"]
	prompt = f"""Create a topic comparison cluster for {cfg['cluster_topic']}.

cluster_id must be: {cluster_id}
taxonomy_path: {json.dumps(cfg['taxonomy_path'])}
compared_at: {date.today().isoformat()}
extract_ids: list extract refs from the cards' extract_ids fields.
Include consensus items and at least one conflict where sources disagree on density/space/cost.
duplicates may be [].

JSON SCHEMA:
{schema}

CARDS:
{json.dumps(cards, indent=2)}
"""
	data = gemini_client.generate_json(prompt=prompt, temperature=0.2, client=client, model=model)
	data["cluster_id"] = cluster_id
	data.setdefault("compared_at", date.today().isoformat())
	data.setdefault("duplicates", [])
	ok, errors = write_or_draft(
		COMPARISONS / f"{cluster_id}.json",
		data,
		"comparison.schema.json",
		label=f"cmp_{cluster_id}",
	)
	if not ok:
		retry = prompt + "\n\nVALIDATION ERRORS:\n" + "\n".join(errors)
		data = gemini_client.generate_json(
			prompt=retry, temperature=0.1, client=client, model=model
		)
		data["cluster_id"] = cluster_id
		data.setdefault("duplicates", [])
		ok, errors = write_or_draft(
			COMPARISONS / f"{cluster_id}.json",
			data,
			"comparison.schema.json",
			label=f"cmp_{cluster_id}",
		)
	return {"ok": ok, "errors": errors, "cluster_id": cluster_id}


def compose_guide(
	pass_num: int = 1,
	*,
	client=None,
	model: str | None = None,
) -> dict[str, Any]:
	cfg = PASS_COMPOSE[pass_num]
	guide_schema = (SCHEMAS / "guide.schema.json").read_text(encoding="utf-8")
	cards = _load_cards(cfg["claim_ids"])
	guide_id = cfg["guide_id"]
	prompt = f"""Produce ONE JSON object with keys:
- metadata: guide metadata matching the guide schema
- markdown: engineering playbook markdown

metadata.guide_id = {guide_id}
metadata.title = {cfg['guide_title']}
metadata.slug = {cfg['guide_slug']}
metadata.claim_ids MUST only cite claim IDs that exist in CARDS (subset of keys).
metadata.status = draft
metadata.created_at = {date.today().isoformat()}
metadata.checklist_passed = false

markdown rules:
- Every Rule section must cite claim IDs like (UX_…)
- Practical detect → apply → when-not → tradeoff
- No invented Absolute a11y rewrites

GUIDE METADATA SCHEMA:
{guide_schema}

CARDS:
{json.dumps(cards, indent=2)}
"""
	data = gemini_client.generate_json(prompt=prompt, temperature=0.2, client=client, model=model)
	meta = data.get("metadata") or data
	if "guide_id" in data and "metadata" not in data:
		meta = {k: data[k] for k in data if k != "markdown"}
	markdown = data.get("markdown") or data.get("body") or ""
	meta["guide_id"] = guide_id
	meta.setdefault("created_at", date.today().isoformat())
	meta.setdefault("status", "draft")
	meta.setdefault("slug", cfg["guide_slug"])
	meta.setdefault("title", cfg["guide_title"])
	existing = set(cards)
	meta["claim_ids"] = [c for c in (meta.get("claim_ids") or []) if c in existing] or list(existing)[
		:5
	]
	ok, errors = write_or_draft(
		GUIDES / f"{guide_id}.json",
		meta,
		"guide.schema.json",
		label=guide_id,
	)
	md_path = GUIDES / f"{guide_id}.md"
	if ok and markdown:
		md_path.write_text(markdown.strip() + "\n", encoding="utf-8")
	elif ok and not markdown:
		lines = [
			f"# {meta['title']}",
			"",
			f"Generated by foropencode_pipeline Pass{pass_num}.",
			"",
			"## Claims",
			"",
		]
		for cid in meta["claim_ids"]:
			lines.append(f"- {cid}: {cards[cid].get('name', cid)}")
		md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
	return {"ok": ok, "errors": errors, "has_markdown": bool(markdown), "guide_id": guide_id}
