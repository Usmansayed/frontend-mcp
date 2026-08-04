"""Wire UX KB retrieval into Engineering Strategy and Ship Council (contract v1)."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel

RETRIEVAL_SURFACES = frozenset({
	"landing",
	"dashboard",
	"forms",
	"checkout",
	"onboarding",
	"settings",
})

COORDINATOR_TO_RETRIEVAL = {
	"marketing": "landing",
	"settings_form": "forms",
	"data_table": "dashboard",
}


def _latest_intent(psm: ProjectSituationModel) -> str:
	for frame in reversed(psm.episode.intent_stack):
		text = (frame.intent or "").strip()
		if text:
			return text
	return ""


def infer_retrieval_surface(*, surface_type: str, intent: str) -> str | None:
	"""Map coordinator surface + intent to UX KB retrieval surface_type."""
	mapped = COORDINATOR_TO_RETRIEVAL.get(surface_type, surface_type)
	if mapped in RETRIEVAL_SURFACES:
		return mapped
	text = (intent or "").lower()
	if any(k in text for k in ("landing page", "landing", "marketing site", "homepage", "hero cta")):
		return "landing"
	if any(k in text for k in ("dashboard", "analytics", "kpi", "metrics overview")):
		return "dashboard"
	if any(k in text for k in ("checkout", "cart")):
		return "checkout"
	if any(k in text for k in ("onboarding", "first-run")):
		return "onboarding"
	if any(k in text for k in ("settings", "preferences")):
		return "settings"
	return None


def _retrieval_phase(task_scope: str) -> str:
	if task_scope in ("design_driven", "system_setup", "greenfield"):
		return "greenfield"
	if task_scope == "redesign":
		return "redesign"
	return "feature_incremental"


def should_recommend_ux_knowledge(
	*,
	psm: ProjectSituationModel,
	disc: dict[str, str],
	influence_level: str,
	engineering_phase: str,
	timing: str = "pre_implementation",
) -> bool:
	if influence_level in ("minimal", "maintenance"):
		return False
	task_scope = disc.get("task_scope") or "feature_incremental"
	if task_scope in ("hotfix", "surgical", "debug"):
		return False
	intent = _latest_intent(psm)
	surface = infer_retrieval_surface(
		surface_type=str(disc.get("surface_type") or "unknown"),
		intent=intent,
	)
	if not surface:
		return False
	if timing == "ship_council":
		return True
	return engineering_phase in ("design_orientation", "architecture", "implementation")


def compile_ux_knowledge_hint(
	psm: ProjectSituationModel,
	disc: dict[str, str],
	*,
	influence_level: str,
	engineering_phase: str,
	timing: str = "pre_implementation",
) -> dict[str, Any] | None:
	if not should_recommend_ux_knowledge(
		psm=psm,
		disc=disc,
		influence_level=influence_level,
		engineering_phase=engineering_phase,
		timing=timing,
	):
		return None
	intent = _latest_intent(psm)
	surface = infer_retrieval_surface(
		surface_type=str(disc.get("surface_type") or "unknown"),
		intent=intent,
	)
	if not surface:
		return None
	task_scope = disc.get("task_scope") or "feature_incremental"
	params: dict[str, Any] = {
		"intent": intent or f"Build {surface} UI",
		"surface_type": surface,
		"phase": _retrieval_phase(task_scope),
	}
	if "form" in intent.lower() or surface == "forms":
		params["ui_component"] = "form"
	if "hierarchy" in intent.lower() or surface == "dashboard":
		params["problem"] = "information hierarchy"
	if "conversion" in intent.lower() or surface == "landing":
		params["user_flow"] = "conversion"
	repo_root = getattr(psm.artifacts, "repo_root", None) or ""
	return {
		"tool": "perception_design_knowledge_query",
		"query_id": "ux.retrieve",
		"params": params,
		"repo_root": repo_root or None,
		"timing": timing,
		"capability_id": "design_knowledge_query",
		"rationale": (
			f"Retrieve deterministic UX playbook for {surface} "
		 f"({timing.replace('_', ' ')}) before locking layout decisions."
		),
	}


def augment_recommended_evidence(
	recommended: dict[str, Any] | None,
	ux_hint: dict[str, Any] | None,
) -> dict[str, Any] | None:
	if not ux_hint:
		return recommended
	if recommended and recommended.get("capability_id") not in (None, "design_knowledge_query"):
		return recommended
	return {
		"for_decision": "ux_playbook",
		"for_decision_title": "UX engineering playbook",
		"capability_id": "design_knowledge_query",
		"rationale": ux_hint.get("rationale", ""),
		"query_id": "ux.retrieve",
		"params": ux_hint.get("params"),
		"repo_root": ux_hint.get("repo_root"),
	}
