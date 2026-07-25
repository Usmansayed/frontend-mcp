"""Build per-cluster expansion plans from gap_clusters + url_queue (deterministic)."""
from __future__ import annotations

import json
from typing import Any

import yaml

from .paths import EXPANSION_PLANS, GAP_CLUSTERS, KB_ROOT, REPORTS, URL_QUEUE

PLAYBOOK_DRAFTS: dict[str, dict[str, Any]] = {
	"typography": {
		"playbook_id": "pb_typography",
		"pack_id": "pack_typography",
		"title": "Typography & Readability Playbook",
		"retrieval_keys": {
			"problem": ["typography", "readability", "line height", "font size", "heading scale"],
			"surface_type": ["landing", "app_shell", "settings", "marketing"],
		},
	},
	"motion": {
		"playbook_id": "pb_motion",
		"pack_id": "pack_motion",
		"title": "Motion & Animation UX Playbook",
		"retrieval_keys": {
			"problem": ["motion", "animation", "transition", "reduced motion"],
			"phase": ["polish", "feature"],
		},
	},
	"auth": {
		"playbook_id": "pb_auth",
		"pack_id": "pack_auth",
		"title": "Authentication & Session UX Playbook",
		"retrieval_keys": {
			"problem": ["authentication", "login", "session", "oauth"],
			"user_flow": ["login", "signup"],
			"surface_type": ["forms", "app_shell"],
		},
	},
	"data_tables": {
		"playbook_id": "pb_data_tables",
		"pack_id": "pack_data_tables",
		"title": "Data Tables & Grids Playbook",
		"retrieval_keys": {
			"problem": ["table usability", "density", "data grid"],
			"ui_component": ["data_table"],
			"surface_type": ["admin", "dashboard", "analytics"],
		},
	},
	"search": {
		"playbook_id": "pb_search",
		"pack_id": "pack_search",
		"title": "Search & Findability Playbook",
		"retrieval_keys": {
			"problem": ["search UX", "findability", "autocomplete"],
			"user_flow": ["search", "browse"],
			"ui_component": ["search_input"],
		},
	},
	"notifications": {
		"playbook_id": "pb_notifications",
		"pack_id": "pack_notifications",
		"title": "Notifications & Feedback Surfaces Playbook",
		"retrieval_keys": {
			"problem": ["notifications", "toast", "alert", "feedback"],
			"ui_component": ["toast", "modal"],
		},
	},
	"agentic_ux": {
		"playbook_id": "pb_agentic",
		"pack_id": "pack_agentic",
		"title": "Agentic & AI UX Playbook",
		"retrieval_keys": {
			"problem": ["agentic", "AI copilot", "generative UI"],
			"surface_type": ["app_shell", "dashboard"],
		},
	},
}


def _load_url_queue() -> list[dict[str, Any]]:
	data = yaml.safe_load(URL_QUEUE.read_text(encoding="utf-8"))
	return list(data.get("urls") or [])


def plan_expansion(*, max_clusters: int = 10, urls_per_topic: int = 8) -> dict[str, Any]:
	if not GAP_CLUSTERS.exists():
		from .gap_cluster import run_gap_cluster

		run_gap_cluster(top_n=max_clusters)

	gap_data = yaml.safe_load(GAP_CLUSTERS.read_text(encoding="utf-8"))
	clusters = (gap_data.get("clusters") or [])[:max_clusters]
	all_urls = _load_url_queue()
	url_index = {u["id"]: u for u in all_urls}

	plans: list[dict[str, Any]] = []
	for cluster in clusters:
		topic = cluster["topic"]
		selected_ids = (cluster.get("url_ids") or [])[:urls_per_topic]
		selected_urls = [url_index[i] for i in selected_ids if i in url_index]
		plan: dict[str, Any] = {
			"topic": topic,
			"priority_score": cluster.get("priority_score"),
			"target_principles": (cluster.get("budget") or {}).get("deficit") or 5,
			"source_ids": selected_ids,
			"urls": [
				{
					"id": u["id"],
					"url": u["url"],
					"priority": u.get("priority"),
					"get": u.get("get"),
				}
				for u in selected_urls
			],
			"pipeline": ["enqueue", "scrape", "extract", "normalize", "dedup", "accept", "complete_phases"],
			"needs_playbook": cluster.get("needs_playbook", False),
		}
		if topic in PLAYBOOK_DRAFTS:
			plan["playbook_spec"] = PLAYBOOK_DRAFTS[topic]
		plans.append(plan)

	output = {
		"version": 1,
		"plans": plans,
		"wave_topics": [p["topic"] for p in plans if p.get("urls")],
	}
	KB_ROOT.mkdir(parents=True, exist_ok=True)
	EXPANSION_PLANS.write_text(yaml.dump(output, sort_keys=False, allow_unicode=True), encoding="utf-8")
	REPORTS.mkdir(parents=True, exist_ok=True)
	(REPORTS / "expansion_plans.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
	output["path"] = str(EXPANSION_PLANS)
	return output


def main() -> None:
	result = plan_expansion()
	print(
		json.dumps(
			{
				"plans": len(result["plans"]),
				"wave_topics": result["wave_topics"],
				"path": result["path"],
			},
			indent=2,
		)
	)


if __name__ == "__main__":
	main()
