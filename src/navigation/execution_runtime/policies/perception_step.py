"""perception_step — run card.next in one call (Tier-0 spine)."""
from __future__ import annotations

from typing import Any


def resolve_step_target(
	arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
	"""Resolve which tool perception_step should dispatch.

	Returns keys:
	  status: dispatch | done | error
	  tool / args when dispatch
	  card always when available
	"""
	args = dict(arguments or {})
	from navigation.execution_runtime.policies.implement_hard_gate import (
		resolve_episode_for_gate,
	)

	episode_id, face = resolve_episode_for_gate(args)
	if face is None:
		return {
			"status": "error",
			"error": (
				"perception_step needs a bound episode — "
				"perception_health → perception_session_start({intent}) first"
			),
			"card": None,
			"episode_id": episode_id,
		}

	next_tool = str(face.get("next") or "").strip()
	next_args = dict(face.get("next_args") or {})
	claim_ok = bool(face.get("claim_ok"))

	if not next_tool:
		return {
			"status": "done",
			"card": face,
			"episode_id": episode_id,
			"claim_ok": claim_ok,
			"hint": (
				"card.next empty — claim done"
				if claim_ok
				else "card.next empty but claim_ok=false — clear finish[] / unpaid first"
			),
		}

	if next_tool == "perception_step":
		return {
			"status": "error",
			"error": "card.next is perception_step (loop) — refuse",
			"card": face,
			"episode_id": episode_id,
		}

	# Merge: card next_args, then host overrides (except reserved keys).
	merged = dict(next_args)
	reserved = {
		"override_tool",
		"force_tool",
		"dry_run",
		"episode_id",
	}
	for key, val in args.items():
		if key in reserved:
			continue
		if val is None:
			continue
		# Fill placeholders / always allow session_id etc.
		existing = merged.get(key)
		if existing is None or (
			isinstance(existing, str) and existing.startswith("<")
		):
			merged[key] = val
		elif key in {"session_id", "repo_root", "project_id", "scan_id", "url", "base_url"}:
			merged[key] = val

	# Explicit override for tests / power users
	force = str(args.get("override_tool") or args.get("force_tool") or "").strip()
	if force:
		next_tool = force

	# Ensure session/episode propagate
	if args.get("session_id") and not merged.get("session_id"):
		merged["session_id"] = args["session_id"]
	if episode_id and not merged.get("episode_id"):
		merged["episode_id"] = episode_id

	return {
		"status": "dispatch",
		"tool": next_tool,
		"args": merged,
		"card": face,
		"episode_id": episode_id,
		"then": next_args.get("then"),
	}


def step_done_envelope(*, card: dict[str, Any], hint: str, claim_ok: bool) -> dict[str, Any]:
	return {
		"contract_version": "1.0",
		"tool": "perception_step",
		"ok": True,
		"error": None,
		"data": {
			"step": {
				"status": "done",
				"claim_ok": claim_ok,
				"hint": hint,
			},
			"agent_summary": {
				"card": card,
				"recommended_next": "",
				"advisory": [hint],
			},
		},
	}


def step_error_envelope(*, error: str, card: dict[str, Any] | None = None) -> dict[str, Any]:
	return {
		"contract_version": "1.0",
		"tool": "perception_step",
		"ok": False,
		"error": error,
		"data": {
			"step": {"status": "error"},
			"agent_summary": {
				"card": card,
				"blocking": [error],
				"recommended_next": "perception_session_start"
				if not card
				else (card.get("next") or "perception_step"),
			},
		},
	}
