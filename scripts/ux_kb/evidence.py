"""Evidence + source nodes: Principle → cites → Evidence → source."""
from __future__ import annotations

import re
from typing import Any

from .db import db_session, loads
from .graph_pipeline import _slug, upsert_graph_edge, upsert_graph_node


def _source_label(source_id: str, url: str | None) -> str:
	if url:
		# domain + path tail
		m = re.search(r"https?://([^/]+)(/[^?#]*)?", url)
		if m:
			host = m.group(1).replace("www.", "")
			path = (m.group(2) or "")[:40]
			return f"{host}{path}"
	return source_id


def sync_evidence_nodes(*, replace: bool = True) -> dict[str, Any]:
	"""Create evidence + source nodes from accepted principles and sources table."""
	evidence_created = 0
	sources_created = 0
	edges_created = 0

	with db_session() as conn:
		if replace:
			for row in conn.execute(
				"SELECT id FROM graph_nodes WHERE node_type IN ('evidence', 'source')"
			).fetchall():
				nid = row["id"]
				conn.execute(
					"DELETE FROM graph_edges WHERE source_id=? OR target_id=?",
					(nid, nid),
				)
			conn.execute("DELETE FROM graph_nodes WHERE node_type IN ('evidence', 'source')")

		# Index sources table
		source_rows = {
			r["id"]: dict(r)
			for r in conn.execute("SELECT id, url, topic FROM sources").fetchall()
		}

		principles = conn.execute(
			"""
			SELECT id, title, quote, source_ids_json, evidence_class
			FROM cards WHERE status='accepted'
			"""
		).fetchall()

		seen_sources: set[str] = set()

		for pr in principles:
			pid = pr["id"]
			source_ids = loads(pr["source_ids_json"], [])
			quote = (pr["quote"] or "").strip()

			for i, sid in enumerate(source_ids):
				# Ensure source node exists
				if sid not in seen_sources:
					url = source_rows.get(sid, {}).get("url")
					topic = source_rows.get(sid, {}).get("topic", "")
					upsert_graph_node(
						conn,
						node_id=sid,
						node_type="source",
						label=_source_label(sid, url),
						ref=url or f"kb://sources/{sid}",
						metadata={"topic": topic, "url": url or ""},
					)
					seen_sources.add(sid)
					sources_created += 1

				ev_id = f"ev_{_slug(pid, 20)}_{_slug(sid, 12)}_{i + 1:02d}"
				upsert_graph_node(
					conn,
					node_id=ev_id,
					node_type="evidence",
					label=f"Evidence for {pr['title'][:60]}",
					ref=f"kb://cards/{pid}#source-{i + 1}",
					metadata={
						"principle_id": pid,
						"source_id": sid,
						"evidence_class": pr["evidence_class"],
					},
					payload={"quote": quote, "source_id": sid},
				)
				evidence_created += 1

				upsert_graph_edge(
					conn,
					source_id=pid,
					target_id=ev_id,
					relation="cites",
					context=sid,
				)
				edges_created += 1
				upsert_graph_edge(
					conn,
					source_id=ev_id,
					target_id=sid,
					relation="cites",
					context="grounded_in",
				)
				edges_created += 1

	return {
		"evidence_created": evidence_created,
		"sources_created": sources_created,
		"edges_created": edges_created,
	}
