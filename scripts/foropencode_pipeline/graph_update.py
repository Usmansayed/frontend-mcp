"""Patch knowledge graph for new claim cards."""
from __future__ import annotations

import json
from typing import Any

from .paths import GRAPHS, NORMALIZED

PASS1_CLAIMS = [
	"UX_HCI_STEER_011",
	"UX_VIS_GEST_006",
	"UX_HFE_TLX_001",
]

PASS2_CLAIMS = [
	"UX_HCI_KLM_008",
	"UX_VIS_READ_014",
	"UX_DS_DENS_002",
	"UX_DS_TOKEN_001",
]

PASS_EDGES: dict[int, list[dict[str, Any]]] = {
	1: [
		{
			"id": "e_steer_complements_fitts",
			"source": "UX_HCI_STEER_011",
			"target": "UX_HCI_FITTS_001",
			"type": "COMPLEMENTS",
			"notes": "Steering extends Fitts to path-constrained movement",
		},
		{
			"id": "e_gestalt_conflicts_hick_density",
			"source": "UX_VIS_GEST_006",
			"target": "UX_COG_HICK_002",
			"type": "RELATED",
			"notes": "Proximity grouping vs choice entropy / density tradeoffs",
		},
		{
			"id": "e_tlx_related_hick",
			"source": "UX_HFE_TLX_001",
			"target": "UX_COG_HICK_002",
			"type": "RELATED",
			"notes": "Workload measurement vs cognitive load from choice",
		},
		{
			"id": "e_steer_composed_hierarchy",
			"source": "UX_HCI_STEER_011",
			"target": "guide_hierarchy_density",
			"type": "COMPOSED_IN",
			"notes": "Pass1 hierarchy density playbook",
		},
		{
			"id": "e_gest_composed_hierarchy",
			"source": "UX_VIS_GEST_006",
			"target": "guide_hierarchy_density",
			"type": "COMPOSED_IN",
			"notes": "Pass1 hierarchy density playbook",
		},
	],
	2: [
		{
			"id": "e_klm_complements_fitts",
			"source": "UX_HCI_KLM_008",
			"target": "UX_HCI_FITTS_001",
			"type": "COMPLEMENTS",
			"notes": "KLM predicts expert sequence time; Fitts predicts pointing within it",
		},
		{
			"id": "e_dens_related_token",
			"source": "UX_DS_DENS_002",
			"target": "UX_DS_TOKEN_001",
			"type": "RELATED",
			"notes": "Enterprise density and semantic tokens co-govern DS surfaces",
		},
		{
			"id": "e_dens_conflicts_gestalt",
			"source": "UX_DS_DENS_002",
			"target": "UX_VIS_GEST_006",
			"type": "CONFLICTS_WITH",
			"notes": "High density can collapse proximity grouping whitespace",
		},
		{
			"id": "e_read_related_gestalt",
			"source": "UX_VIS_READ_014",
			"target": "UX_VIS_GEST_006",
			"type": "RELATED",
			"notes": "Reading flow and proximity jointly shape scan paths",
		},
		{
			"id": "e_token_composed_ds_guide",
			"source": "UX_DS_TOKEN_001",
			"target": "guide_design_systems",
			"type": "COMPOSED_IN",
			"notes": "Pass2 design systems playbook",
		},
		{
			"id": "e_dens_composed_ds_guide",
			"source": "UX_DS_DENS_002",
			"target": "guide_design_systems",
			"type": "COMPOSED_IN",
			"notes": "Pass2 design systems playbook",
		},
	],
}


def upsert_nodes(claim_ids: list[str] | None = None, pass_num: int = 1) -> list[str]:
	if claim_ids is None:
		claim_ids = PASS1_CLAIMS if pass_num == 1 else PASS2_CLAIMS
	nodes_path = GRAPHS / "nodes.json"
	nodes: list[dict[str, Any]] = json.loads(nodes_path.read_text(encoding="utf-8"))
	by_id = {n["id"]: n for n in nodes}
	changed: list[str] = []
	for cid in claim_ids:
		card_path = NORMALIZED / f"{cid}.json"
		if not card_path.exists():
			continue
		card = json.loads(card_path.read_text(encoding="utf-8"))
		node = {
			"id": cid,
			"type": "claim",
			"label": card.get("name", cid),
			"ref": f"06_corpus/normalized/{cid}.json",
			"metadata": {
				"evidence_class": card.get("evidence_class"),
				"confidence": card.get("confidence"),
			},
		}
		if cid in by_id:
			by_id[cid].update(node)
			changed.append(f"updated:{cid}")
		else:
			nodes.append(node)
			by_id[cid] = node
			changed.append(f"added:{cid}")
	nodes_path.write_text(json.dumps(nodes, indent=2) + "\n", encoding="utf-8")
	return changed


def upsert_edges(pass_num: int = 1) -> list[str]:
	edges_path = GRAPHS / "edges.json"
	edges: list[dict[str, Any]] = json.loads(edges_path.read_text(encoding="utf-8"))
	wanted = PASS_EDGES.get(pass_num, [])
	by_id = {e.get("id"): e for e in edges if e.get("id")}
	changed = []
	nodes = json.loads((GRAPHS / "nodes.json").read_text(encoding="utf-8"))
	for edge in wanted:
		src_ok = (NORMALIZED / f"{edge['source']}.json").exists() or edge["source"].startswith(
			"guide_"
		)
		tgt = edge["target"]
		tgt_ok = (
			(NORMALIZED / f"{tgt}.json").exists()
			or tgt.startswith("guide_")
			or any(n.get("id") == tgt for n in nodes)
		)
		if not (src_ok and tgt_ok):
			continue
		if edge["id"] in by_id:
			by_id[edge["id"]].update(edge)
			changed.append(f"updated:{edge['id']}")
		else:
			edges.append(edge)
			by_id[edge["id"]] = edge
			changed.append(f"added:{edge['id']}")
	edges_path.write_text(json.dumps(edges, indent=2) + "\n", encoding="utf-8")
	return changed
