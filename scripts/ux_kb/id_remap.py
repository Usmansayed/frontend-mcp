"""Remap accepted UX_TMP_* card ids to canonical ids; fix graph references."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .db import db_session, dumps, loads, utcnow
from .dedup import _next_canonical_id, _slug, _union_sources
from .graph_pipeline import export_graph_json, run_distill, sync_principle_nodes, upsert_graph_edge
from .paths import GUIDES
from .seed import upsert_card

# old_id -> new_id (merge target) or None to auto-generate from title
REMAP_TARGETS: dict[str, str | None] = {
	"UX_TMP_TS_YORKU_001": "UX_HCI_FITTS_001",  # merge — Shannon Fitts extension
	"UX_TMP_ROXIMITY_001": "UX_VIS_PROXWHITES_001",
	"UX_TMP_ING_FLOW_001": "UX_VIS_FZPATTERN_001",
	"UX_TMP_LOT_FOGG_001": "UX_PRD_BMAPDIAGN_001",
}

CONFLICT_EDGES: list[tuple[str, str, str]] = [
	(
		"UX_A11Y_TARG_004",
		"UX_COG_HICK_002",
		"Large targets reduce visible choice count; Hick favors fewer options on screen",
	),
	(
		"UX_COG_HICK_002",
		"UX_HCI_FITTS_001",
		"Enlarging each option shrinks how many choices fit without scrolling",
	),
]


def _card_dict(row) -> dict[str, Any]:
	d = dict(row)
	d["source_ids"] = loads(d.pop("source_ids_json"), [])
	d["supersedes"] = loads(d.pop("supersedes_json"), [])
	d["conflicts_with"] = loads(d.pop("conflicts_with_json"), [])
	return d


def _replace_id_in_json_blob(blob: str, old_id: str, new_id: str) -> str:
	if not blob or old_id not in blob:
		return blob
	try:
		data = json.loads(blob)
	except json.JSONDecodeError:
		return blob.replace(old_id, new_id)

	def walk(obj):
		if isinstance(obj, list):
			return [new_id if x == old_id else walk(x) for x in obj]
		if isinstance(obj, dict):
			return {k: walk(v) for k, v in obj.items()}
		if obj == old_id:
			return new_id
		return obj

	return dumps(walk(data))


def _replace_id_everywhere(conn, old_id: str, new_id: str, *, merge: bool = False) -> dict[str, int]:
	counts: dict[str, int] = {}

	def bump(key: str, n: int) -> None:
		counts[key] = counts.get(key, 0) + n

	bump(
		"graph_edges_source",
		conn.execute(
			"UPDATE graph_edges SET source_id=? WHERE source_id=?", (new_id, old_id)
		).rowcount,
	)
	bump(
		"graph_edges_target",
		conn.execute(
			"UPDATE graph_edges SET target_id=? WHERE target_id=?", (new_id, old_id)
		).rowcount,
	)
	for row in conn.execute("SELECT id, context FROM graph_edges WHERE context LIKE ?", (f"%{old_id}%",)).fetchall():
		conn.execute(
			"UPDATE graph_edges SET context=? WHERE id=?",
			(row["context"].replace(old_id, new_id), row["id"]),
		)
		bump("graph_edges_context", 1)
	if merge:
		bump(
			"graph_nodes_deleted",
			conn.execute("DELETE FROM graph_nodes WHERE id=?", (old_id,)).rowcount,
		)
	else:
		bump(
			"graph_nodes",
			conn.execute("UPDATE graph_nodes SET id=? WHERE id=?", (new_id, old_id)).rowcount,
		)
	bump(
		"conflicts_a",
		conn.execute("UPDATE conflicts SET card_a=? WHERE card_a=?", (new_id, old_id)).rowcount,
	)
	bump(
		"conflicts_b",
		conn.execute("UPDATE conflicts SET card_b=? WHERE card_b=?", (new_id, old_id)).rowcount,
	)
	bump(
		"clusters_canonical",
		conn.execute(
			"UPDATE principle_clusters SET canonical_card_id=? WHERE canonical_card_id=?",
			(new_id, old_id),
		).rowcount,
	)

	for row in conn.execute("SELECT id, member_ids_json FROM principle_clusters").fetchall():
		members = loads(row["member_ids_json"], [])
		if old_id in members:
			updated = [new_id if m == old_id else m for m in members]
			conn.execute(
				"UPDATE principle_clusters SET member_ids_json=? WHERE id=?",
				(dumps(updated), row["id"]),
			)
			bump("clusters_members", 1)

	for row in conn.execute(
		"SELECT id, conflicts_with_json, supersedes_json FROM cards"
	).fetchall():
		updates: dict[str, str] = {}
		for col in ("conflicts_with_json", "supersedes_json"):
			val = row[col]
			if val and old_id in val:
				updates[col] = _replace_id_in_json_blob(val, old_id, new_id)
		if updates:
			sets = ", ".join(f"{k}=?" for k in updates)
			conn.execute(
				f"UPDATE cards SET {sets}, updated_at=? WHERE id=?",
				(*updates.values(), utcnow(), row["id"]),
			)
			bump("cards_json", 1)

	for row in conn.execute(
		"SELECT id, payload_json, metadata_json FROM graph_nodes"
	).fetchall():
		updates: dict[str, str] = {}
		for col in ("payload_json", "metadata_json"):
			val = row[col] or ""
			if old_id in val:
				updates[col] = _replace_id_in_json_blob(val, old_id, new_id)
		if updates:
			sets = ", ".join(f"{k}=?" for k in updates)
			conn.execute(
				f"UPDATE graph_nodes SET {sets}, updated_at=? WHERE id=?",
				(*updates.values(), utcnow(), row["id"]),
			)
			bump("graph_payload", 1)

	return counts


def _replace_id_in_guides(old_id: str, new_id: str) -> int:
	n = 0
	for path in GUIDES.glob("*.md"):
		text = path.read_text(encoding="utf-8")
		if old_id not in text:
			continue
		path.write_text(text.replace(old_id, new_id), encoding="utf-8")
		n += 1
	return n


def _merge_into(conn, old_id: str, target_id: str) -> dict[str, Any]:
	old_row = conn.execute("SELECT * FROM cards WHERE id=?", (old_id,)).fetchone()
	target_row = conn.execute("SELECT * FROM cards WHERE id=?", (target_id,)).fetchone()
	if not old_row or not target_row:
		raise ValueError(f"merge missing card: old={old_id} target={target_id}")

	old = _card_dict(old_row)
	target = _card_dict(target_row)
	merged_sources = _union_sources([old, target])
	target["source_ids"] = merged_sources
	target["confidence"] = max(float(old["confidence"]), float(target["confidence"]))
	supersedes = list(dict.fromkeys((target.get("supersedes") or []) + [old_id]))
	target["supersedes"] = supersedes
	upsert_card(conn, target)

	ref_counts = _replace_id_everywhere(conn, old_id, target_id, merge=True)
	conn.execute(
		"UPDATE cards SET status='merged', supersedes_json=?, updated_at=? WHERE id=?",
		(dumps([target_id]), utcnow(), old_id),
	)
	guide_files = _replace_id_in_guides(old_id, target_id)
	return {
		"action": "merge",
		"old_id": old_id,
		"new_id": target_id,
		"ref_updates": ref_counts,
		"guide_files": guide_files,
	}


def _rename_card(conn, old_id: str, new_id: str) -> dict[str, Any]:
	if conn.execute("SELECT 1 FROM cards WHERE id=?", (new_id,)).fetchone():
		raise ValueError(f"target id already exists: {new_id}")

	old_row = conn.execute("SELECT * FROM cards WHERE id=?", (old_id,)).fetchone()
	if not old_row:
		raise ValueError(f"source card not found: {old_id}")

	card = _card_dict(old_row)
	card["id"] = new_id
	card["supersedes"] = list(dict.fromkeys((card.get("supersedes") or []) + [old_id]))
	card["status"] = "accepted"
	upsert_card(conn, card)

	ref_counts = _replace_id_everywhere(conn, old_id, new_id)
	conn.execute(
		"UPDATE cards SET status='merged', supersedes_json=?, updated_at=? WHERE id=?",
		(dumps([new_id]), utcnow(), old_id),
	)
	guide_files = _replace_id_in_guides(old_id, new_id)
	return {
		"action": "rename",
		"old_id": old_id,
		"new_id": new_id,
		"ref_updates": ref_counts,
		"guide_files": guide_files,
	}


def _resolve_new_id(conn, old_id: str, card: dict[str, Any], explicit: str | None) -> str:
	if explicit:
		return explicit
	principle_key = _slug(card["title"])
	return _next_canonical_id(conn, card["topic"], principle_key.lower())


def add_missing_conflict_edges() -> list[dict[str, str]]:
	added: list[dict[str, str]] = []
	with db_session() as conn:
		for a, b, hint in CONFLICT_EDGES:
			for src, tgt in ((a, b), (b, a)):
				exists = conn.execute(
					"""
					SELECT 1 FROM graph_edges
					WHERE relation='contradicts' AND source_id=? AND target_id=?
					""",
					(src, tgt),
				).fetchone()
				if exists:
					continue
				upsert_graph_edge(conn, source_id=src, target_id=tgt, relation="contradicts", context=hint)
				added.append({"source": src, "target": tgt, "context": hint})
	return added


def _cleanup_self_loop_edges(conn) -> int:
	return conn.execute(
		"DELETE FROM graph_edges WHERE source_id=target_id AND relation NOT IN ('contradicts')"
	).rowcount


def run_tmp_id_remap(*, refresh_graph: bool = True) -> dict[str, Any]:
	results: list[dict[str, Any]] = []

	with db_session() as conn:
		for old_id, target in REMAP_TARGETS.items():
			row = conn.execute("SELECT * FROM cards WHERE id=?", (old_id,)).fetchone()
			if not row:
				results.append({"old_id": old_id, "skipped": True, "reason": "not_found"})
				continue
			if row["status"] != "accepted":
				results.append(
					{"old_id": old_id, "skipped": True, "reason": f"status={row['status']}"}
				)
				continue

			card = _card_dict(row)
			if target and target != old_id:
				if conn.execute("SELECT 1 FROM cards WHERE id=?", (target,)).fetchone():
					results.append(_merge_into(conn, old_id, target))
				else:
					results.append(_rename_card(conn, old_id, target))
			else:
				new_id = _resolve_new_id(conn, old_id, card, target)
				results.append(_rename_card(conn, old_id, new_id))

	out: dict[str, Any] = {"remaps": results, "conflicts_added": add_missing_conflict_edges()}

	with db_session() as conn:
		out["self_loops_removed"] = _cleanup_self_loop_edges(conn)

	if refresh_graph:
		out["principle_nodes"] = sync_principle_nodes()
		from .graph_pipeline import sync_topic_nodes

		out["topic_nodes"] = sync_topic_nodes()
		from .decisions import sync_decision_nodes

		out["decisions"] = sync_decision_nodes()
		out["export"] = export_graph_json()
		out["distill"] = run_distill()

	return out
