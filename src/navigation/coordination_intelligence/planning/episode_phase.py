"""Episode phase — narrow decision state for host agents.

Not the 150-state research corpus. Compiles face class + unpaid pack + claim
ladder into one of ~7 phases so agents know where they are in the creation loop:

  intent → flow → layout → sections → components → verify → ship
"""
from __future__ import annotations

from typing import Any

EPISODE_PHASES: tuple[str, ...] = (
	"intent",
	"flow",
	"layout",
	"sections",
	"components",
	"verify",
	"ship",
)

_PHASE_HINT: dict[str, str] = {
	"intent": "Clarify job; bootstrap health → session_start with intent.",
	"flow": "Forms/guards — probe before inventing UI.",
	"layout": "Direction — inspiration and/or snapshot + LOOK before large layout code.",
	"sections": "Section chrome — resources (fonts/patterns/motion) + consistency + section LOOK.",
	"components": "Select foundations — component intelligence before hand-rolling.",
	"verify": "Browser truth — observe/verify (capture packs OK); fix until verified.",
	"ship": "Ship Council / claim ladder — finish claim_extra then claim.",
}


def resolve_episode_phase(
	*,
	face_class: str,
	strategy: dict[str, Any] | None = None,
	owed: list[dict[str, Any]] | None = None,
	pack: dict[str, Any] | None = None,
	claim_extra: list[str] | None = None,
	claim_ok: bool = False,
) -> dict[str, Any]:
	"""Compile a single phase + hint for agent_summary.card."""
	strategy = strategy or {}
	face = str(face_class or "hotfix").strip().lower()
	extra = list(claim_extra or [])
	owed_fams = {
		str(o.get("family"))
		for o in (owed or [])
		if isinstance(o, dict) and o.get("family")
	}
	portfolio = strategy.get("episode_portfolio") or {}
	unpaid = {
		str(u.get("family"))
		for u in (portfolio.get("unpaid") or [])
		if isinstance(u, dict) and u.get("family")
	}
	remaining = {
		str(x)
		for x in ((pack or {}).get("remaining") or [])
		if x
	}
	open_fams = owed_fams | unpaid | remaining
	verified = str(strategy.get("verification_status") or "").lower() == "passed"

	if claim_ok and verified and not extra:
		phase = "ship"
	elif "ship_council" in extra or "section_checklist" in extra or "spec_revision" in extra:
		if verified or "verify" not in open_fams:
			phase = "ship"
		else:
			phase = "verify"
	elif face == "forms" and ("forms" in open_fams or not verified):
		phase = "flow"
	elif face in {"greenfield", "redesign", "mockup"}:
		if open_fams & {"inspiration", "inspiration_extract", "snapshot"}:
			phase = "layout"
		elif "visual_feedback" in open_fams and not (
			open_fams & {"inspiration", "snapshot"}
		):
			phase = "layout"
		elif open_fams & {"resources", "sections", "residue"}:
			phase = "sections"
		elif "component" in open_fams:
			phase = "components"
		elif not verified or "verify" in open_fams:
			phase = "verify"
		else:
			phase = "ship"
	elif face == "feature":
		if "observe" in open_fams and "component" not in unpaid:
			phase = "verify"
		elif "component" in open_fams:
			phase = "components"
		elif "resources" in open_fams:
			phase = "sections"
		elif not verified or "verify" in open_fams:
			phase = "verify"
		else:
			phase = "ship"
	else:  # hotfix / polish / unknown
		if not open_fams and not verified:
			phase = "intent"
		elif not verified or open_fams & {"observe", "verify", "visual_feedback"}:
			phase = "verify"
		else:
			phase = "ship"

	if phase not in EPISODE_PHASES:
		phase = "verify"
	return {
		"phase": phase,
		"hint": _PHASE_HINT.get(phase, ""),
		"phases": list(EPISODE_PHASES),
	}
