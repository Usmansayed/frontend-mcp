"""Decision influence log — what was retrieved and how the agent used it."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _log_path(repo_root: str | Path | None) -> Path:
	root = Path(repo_root or Path.cwd()).resolve()
	log_dir = root / "ForOpenCode" / "kb" / "logs"
	log_dir.mkdir(parents=True, exist_ok=True)
	return log_dir / "influence.jsonl"


def log_retrieval_influence(
	*,
	repo_root: str | Path | None,
	query_id: str,
	params: dict[str, Any],
	retrieval: dict[str, Any],
	agent_actions: list[dict[str, Any]] | None = None,
	source: str = "mcp",
) -> str:
	"""Append one influence record. Returns log file path."""
	entry = {
		"ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
		"source": source,
		"query_id": query_id,
		"params": params,
		"retrieved": {
			"request_id": retrieval.get("request_id"),
			"playbook_id": (retrieval.get("matched_playbook") or {}).get("id"),
			"pack_id": (retrieval.get("meta") or {}).get("pack_id"),
			"decisions": [d.get("label") for d in retrieval.get("decisions") or []],
			"patterns": [p.get("label") for p in (retrieval.get("patterns") or [])[:8]],
			"principles": [p.get("id") for p in retrieval.get("principles") or []],
			"conflicts": retrieval.get("conflicts") or [],
		},
		"agent_actions": agent_actions or [],
	}
	path = _log_path(repo_root)
	with path.open("a", encoding="utf-8") as f:
		f.write(json.dumps(entry, ensure_ascii=False) + "\n")
	return str(path)


def log_agent_decision(
	*,
	repo_root: str | Path | None,
	request_id: str,
	recommendation: str,
	followed: bool,
	reason: str = "",
) -> None:
	"""Record whether agent followed or overrode a recommendation."""
	entry = {
		"ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
		"type": "agent_decision",
		"request_id": request_id,
		"recommendation": recommendation,
		"followed": followed,
		"override_reason": reason if not followed else "",
	}
	path = _log_path(repo_root)
	with path.open("a", encoding="utf-8") as f:
		f.write(json.dumps(entry, ensure_ascii=False) + "\n")
