"""Decision layer: Playbook → Decision → Pattern (parsed from guide sections)."""
from __future__ import annotations

import re
from typing import Any

from .db import db_session, utcnow
from .graph_pipeline import PLAYBOOK_SPECS, _slug, upsert_graph_edge, upsert_graph_node
from .paths import GUIDES


def _parse_sections(md: str) -> list[dict[str, Any]]:
	"""Extract ### sections under ## Sections with principle id lists."""
	block = re.search(r"## Sections\s*\n(.*?)(?=\n## |\Z)", md, re.S)
	if not block:
		return []
	body = block.group(1).strip()
	if not body:
		return []
	parts = re.split(r"\n### ", body)
	sections: list[dict[str, Any]] = []
	for i, part in enumerate(parts):
		text = part.strip()
		if not text:
			continue
		if i == 0 and not text.startswith("#"):
			# first chunk may lack ### prefix
			pass
		lines = text.split("\n")
		title = lines[0].strip().lstrip("#").strip()
		principles: list[str] = []
		for line in lines[1:]:
			pm = re.match(r"Principles:\s*(.+)", line.strip())
			if pm:
				principles = re.findall(r"UX_[A-Z0-9_]+", pm.group(1))
		if title and principles:
			sections.append({"title": title, "principle_ids": principles})
	return sections


def _patterns_for_principles(conn, principle_ids: list[str]) -> list[str]:
	if not principle_ids:
		return []
	placeholders = ",".join("?" * len(principle_ids))
	rows = conn.execute(
		f"""
		SELECT DISTINCT source_id FROM graph_edges
		WHERE relation='pattern_of' AND target_id IN ({placeholders})
		ORDER BY source_id
		""",
		principle_ids,
	).fetchall()
	return [r["source_id"] for r in rows]


def sync_decision_nodes(*, replace: bool = True) -> dict[str, Any]:
	"""Build decision nodes from playbook section headings + principle→pattern links."""
	created = 0
	edges = 0
	skipped: list[str] = []

	with db_session() as conn:
		if replace:
			old = conn.execute("SELECT id FROM graph_nodes WHERE node_type='decision'").fetchall()
			old_ids = [r["id"] for r in old]
			if old_ids:
				ph = ",".join("?" * len(old_ids))
				conn.execute(
					f"DELETE FROM graph_edges WHERE source_id IN ({ph}) OR target_id IN ({ph})",
					old_ids + old_ids,
				)
				conn.execute(
					f"DELETE FROM graph_nodes WHERE id IN ({ph})",
					old_ids,
				)

		for spec in PLAYBOOK_SPECS:
			pb_id = spec["id"]
			slug = spec["slug"]
			guide_path = GUIDES / f"guide_{slug}.md"
			if not guide_path.exists():
				skipped.append(pb_id)
				continue

			md = guide_path.read_text(encoding="utf-8")
			sections = _parse_sections(md)
			if not sections:
				skipped.append(pb_id)
				continue

			for idx, sec in enumerate(sections):
				dec_id = f"dec_{slug}_{_slug(sec['title'], 20)}_{idx + 1:02d}"
				pattern_ids = _patterns_for_principles(conn, sec["principle_ids"])
				upsert_graph_node(
					conn,
					node_id=dec_id,
					node_type="decision",
					label=sec["title"],
					ref=f"07_guides/guide_{slug}.md#section-{idx + 1}",
					metadata={
						"playbook_id": pb_id,
						"principle_ids": sec["principle_ids"],
						"order": idx + 1,
					},
					payload={"pattern_ids": pattern_ids},
				)
				upsert_graph_edge(
					conn,
					source_id=pb_id,
					target_id=dec_id,
					relation="decision_in",
					context=sec["title"],
				)
				edges += 1
				created += 1
				for pid in pattern_ids:
					upsert_graph_edge(
						conn,
						source_id=dec_id,
						target_id=pid,
						relation="selects_pattern",
						context=sec["title"],
					)
					edges += 1

	return {
		"decisions_created": created,
		"edges_created": edges,
		"playbooks_skipped": skipped,
	}
