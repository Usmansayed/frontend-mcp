"""Hard implement gate — machine refuse while card.implement_blocked.

Deterministic: no LLM. Blocks page-mutation / integrate tools until pack
critical unpaid is cleared. Host IDE edits cannot be blocked; MCP mutations can.
"""
from __future__ import annotations

from typing import Any

# Tools that mutate live UI or install into the repo — refuse while blocked.
IMPLEMENT_MUTATION_TOOLS: frozenset[str] = frozenset(
	{
		"perception_execute_script",
		"perception_execute_actions",
		"perception_integrate_component",
	}
)

# Ship while structural pack still unpaid is also an implement-class fail.
_SHIP_TOOL = "perception_design_review"


def is_implement_mutation_tool(tool: str, arguments: dict[str, Any] | None = None) -> bool:
	name = str(tool or "").strip()
	if name in IMPLEMENT_MUTATION_TOOLS:
		return True
	if name == _SHIP_TOOL:
		mode = str((arguments or {}).get("mode") or "").strip().lower()
		return mode == "ship"
	return False


def resolve_episode_for_gate(
	arguments: dict[str, Any] | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
	"""Return (episode_id, face_card) when an episode is bound; else (None, None)."""
	args = dict(arguments or {})
	try:
		from navigation.coordination_intelligence.integration.bridge import (
			get_coordinator_bridge,
		)
		from navigation.coordination_intelligence.planning.coordinator_card import (
			build_agent_face_card,
		)
	except Exception:
		return None, None

	bridge = get_coordinator_bridge()
	session_id = str(args.get("session_id") or "").strip() or None
	project_id = str(args.get("project_id") or "default")
	episode_id = str(args.get("episode_id") or "").strip() or None
	if not episode_id:
		episode_id = bridge._bindings.resolve(
			session_id=session_id,
			project_id=project_id,
			episode_id=None,
		)
	if not episode_id:
		return None, None
	try:
		psm = bridge.service.runtime.get(episode_id)
		if psm is None:
			return episode_id, None
		strategy = psm.briefing.engineering_strategy
		if not strategy:
			bridge.service.briefing(episode_id)
			psm = bridge.service.runtime.require(episode_id)
			strategy = psm.briefing.engineering_strategy or {}
		face = build_agent_face_card(
			episode_id=episode_id,
			strategy=strategy if isinstance(strategy, dict) else {},
		)
		return episode_id, face
	except Exception:
		return episode_id, None


def evaluate_implement_hard_gate(
	tool: str,
	arguments: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
	"""Return a refuse payload if tool must not run; else None (allow)."""
	if not is_implement_mutation_tool(tool, arguments):
		return None
	_episode_id, face = resolve_episode_for_gate(arguments)
	if not face:
		# No card yet — cannot assert blocked; allow (session_start path).
		return None
	if not bool(face.get("implement_blocked")):
		return None

	owed = list(face.get("owed") or [])
	owed_top = owed[0] if owed else None
	pack = face.get("pack") if isinstance(face.get("pack"), dict) else {}
	critical_unpaid = list(pack.get("critical_unpaid") or [])
	family = None
	if isinstance(owed_top, dict):
		family = owed_top.get("family")
	elif critical_unpaid:
		family = critical_unpaid[0]

	reason = (
		f"implement_blocked — refuse {tool}. "
		f"Pay owed first"
		+ (f" (top: {family})" if family else "")
		+ ". Call perception_step or card.next; do not mutate UI yet."
	)
	return {
		"implement_blocked": True,
		"blocked_tool": str(tool),
		"owed_top": owed_top,
		"critical_unpaid": critical_unpaid[:6],
		"next": face.get("next"),
		"next_args": face.get("next_args") or {},
		"class": face.get("class"),
		"evidence_band": face.get("evidence_band"),
		"error": "implement_blocked",
		"hint": reason,
	}


def blocked_envelope(tool: str, gate: dict[str, Any]) -> dict[str, Any]:
	"""Short refuse envelope — one blocking signal, not an essay."""
	return {
		"contract_version": "1.0",
		"tool": tool,
		"ok": False,
		"error": str(gate.get("hint") or gate.get("error") or "implement_blocked"),
		"data": {
			"implement_blocked": True,
			"blocked_tool": gate.get("blocked_tool") or tool,
			"owed_top": gate.get("owed_top"),
			"critical_unpaid": list(gate.get("critical_unpaid") or []),
			"next": gate.get("next"),
			"next_args": gate.get("next_args") or {},
			"agent_summary": {
				"blocking": [str(gate.get("hint") or "implement_blocked")],
				"recommended_next": gate.get("next") or "perception_step",
				"recommended_next_args": gate.get("next_args") or {},
				"card": {
					"implement_blocked": True,
					"next": gate.get("next"),
					"next_args": gate.get("next_args") or {},
					"owed": [gate["owed_top"]] if gate.get("owed_top") else [],
				},
			},
		},
		"degraded": ["implement_hard_gate"],
	}
