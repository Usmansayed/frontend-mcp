"""AI-centric effort right-sizing — agent decides, MCP recommends.

Evidence Pack Loop: agent-facing bands light|medium|heavy|very_heavy map onto
internal tiers. Default for normal UI is heavy (feature), not polish.
Ship / residue / full-page section checklist only *block* claim-done on
initiative (very_heavy). Hotfix/forms stay light.
"""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel, _utc_now

EFFORT_TIERS = ("touch_up", "polish", "feature", "initiative")
EVIDENCE_BANDS = ("light", "medium", "heavy", "very_heavy")
EFFORT_KEY = "effort_tier"
RIGHT_SIZING_RESOURCE = "perception://guide/right-sizing"

# Agent-facing band ↔ internal tier
_BAND_TO_TIER: dict[str, str] = {
	"light": "touch_up",
	"medium": "polish",
	"heavy": "feature",
	"very_heavy": "initiative",
}
_TIER_TO_BAND: dict[str, str] = {v: k for k, v in _BAND_TO_TIER.items()}

# What each tier pays / skips (agent-facing contract).
_TIER_CONTRACT: dict[str, dict[str, Any]] = {
    "touch_up": {
        "pay": ["browser_verify"],
        "skip": [
            "inspiration_workflow",
            "component_select",
            "design_snapshot",
            "visual_feedback",
            "ship_council",
            "residue_scan",
            "section_checklist",
        ],
        "arms_initiative": False,
        "requires_ship": False,
        "requires_full_sections": False,
        "summary": "One element, reversible, high confidence — hard verify only.",
    },
    "polish": {
        "pay": ["browser_observe", "visual_feedback", "browser_verify"],
        "skip": [
            "inspiration_workflow",
            "component_select",
            "ship_council",
            "residue_scan",
            "full_page_section_checklist",
        ],
        "arms_initiative": False,
        "requires_ship": False,
        "requires_full_sections": False,
        "summary": "Chrome / micro visual — look, judge, hard-verify the touched element.",
    },
    "feature": {
        "pay": ["browser_observe", "visual_feedback", "browser_verify", "component_select?"],
        "skip": ["inspiration_workflow", "full_greenfield_ladder"],
        "arms_initiative": False,
        "requires_ship": False,
        "requires_full_sections": False,
        "summary": "New block in an existing shell — observe + verify; foundation only if unpaid.",
    },
    "initiative": {
        "pay": [
            "inspiration_or_snapshot",
            "component_select",
            "browser_observe",
            "visual_feedback",
            "browser_verify",
            "section_checklist",
            "ship_council",
        ],
        "skip": [],
        "arms_initiative": True,
        "requires_ship": True,
        "requires_full_sections": True,
        "summary": "New page / redesign / rebrand — full evidence ladder.",
    },
}


def normalize_effort_tier(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "touchup": "touch_up",
        "touch": "touch_up",
        "micro": "touch_up",
        "hotfix": "touch_up",
        "surgical": "touch_up",
        "chrome": "polish",
        "css": "polish",
        "incremental": "feature",
        "greenfield": "initiative",
        "redesign": "initiative",
        "structural": "initiative",
        # Evidence Pack Loop bands
        "light": "touch_up",
        "medium": "polish",
        "heavy": "feature",
        "very_heavy": "initiative",
        "veryheavy": "initiative",
    }
    text = aliases.get(text, text)
    return text if text in EFFORT_TIERS else None


def tier_to_evidence_band(tier: str | None) -> str:
	"""Map internal effort tier → agent-facing evidence_band."""
	t = normalize_effort_tier(tier) or "feature"
	return _TIER_TO_BAND.get(t, "heavy")


def evidence_band_to_tier(band: str | None) -> str | None:
	"""Map agent-facing evidence_band → internal tier (or None if unknown)."""
	if band is None:
		return None
	text = str(band).strip().lower().replace("-", "_").replace(" ", "_")
	if text in _BAND_TO_TIER:
		return _BAND_TO_TIER[text]
	return normalize_effort_tier(text)


def get_declared_effort_tier(psm: ProjectSituationModel) -> str | None:
    raw = psm.episode.retry_counters.get(EFFORT_KEY)
    if isinstance(raw, dict):
        return normalize_effort_tier(raw.get("tier"))
    return normalize_effort_tier(raw)


def set_effort_tier(
    psm: ProjectSituationModel,
    tier: str,
    *,
    source: str = "agent",
) -> dict[str, Any]:
    """Persist an agent (or host) effort override on the episode."""
    normalized = normalize_effort_tier(tier)
    if not normalized:
        raise ValueError(f"effort_tier must be one of {EFFORT_TIERS}, got {tier!r}")
    record = {
        "tier": normalized,
        "source": str(source or "agent"),
        "at": _utc_now(),
    }
    psm.episode.retry_counters[EFFORT_KEY] = record
    return record


def maybe_apply_effort_tier_arg(
    psm: ProjectSituationModel,
    arguments: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """If the agent passed effort_tier on a tool call, store it. Returns record or None."""
    if not arguments:
        return None
    raw = arguments.get("effort_tier")
    if raw is None or str(raw).strip() == "":
        return None
    return set_effort_tier(psm, str(raw), source="agent")


def recommend_effort_tier(
    psm: ProjectSituationModel,
    *,
    task_scope: str | None = None,
    influence_level: str | None = None,
) -> dict[str, Any]:
    """Lightest-that-fits recommendation (advisory). Agent may override via effort_tier."""
    import re

    from navigation.coordination_intelligence.planning.situation_policy import sticky_design_scope

    scope = str(task_scope or "")
    sticky = sticky_design_scope(psm)
    if sticky in ("design_driven", "redesign", "system_setup"):
        scope = sticky

    intent_blob = " ".join(f.intent for f in (psm.episode.intent_stack or [])).lower()

    if scope in ("design_driven", "redesign", "system_setup"):
        tier = "initiative"
        why = f"task_scope={scope} is a design initiative — full ladder."
    elif scope in ("hotfix", "surgical", "debug"):
        tier = "touch_up"
        why = f"task_scope={scope} — hard verify is enough."
    elif scope == "feature_incremental":
        # Evidence Pack Loop: normal UI defaults to heavy (feature), not polish.
        if re.search(
            r"\b(add|new)\b.{0,48}\b(section|block|testimonials?|pricing|module)\b",
            intent_blob,
        ):
            tier = "feature"
            why = "add/new section|block on existing page — evidence_band=heavy."
        elif re.search(
            r"\b(polish|tighten spacing|spacing only|navbar only|chrome only|touch[\s-]?up)\b",
            intent_blob,
        ):
            tier = "polish"
            why = "explicit chrome/polish cues — evidence_band=medium."
        else:
            tier = "feature"
            why = (
                "incremental UI default evidence_band=heavy (observe+VF+verify+component?). "
                "Pass effort_tier=touch_up|light for surgical; initiative|very_heavy for full ladder."
            )
    else:
        tier = "feature"
        why = "unknown scope — default evidence_band=heavy (not light)."

    contract = _TIER_CONTRACT[tier]
    band = tier_to_evidence_band(tier)
    return {
        "tier": tier,
        "evidence_band": band,
        "source": "recommended",
        "why": why,
        "pay": list(contract["pay"]),
        "skip": list(contract["skip"]),
        "summary": contract["summary"],
        "resource": RIGHT_SIZING_RESOURCE,
    }


def resolve_effort_tier(
    psm: ProjectSituationModel,
    strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Declared agent tier wins; else lightest-that-fits recommendation."""
    strategy = strategy or {}
    recommended = recommend_effort_tier(
        psm,
        task_scope=str(strategy.get("task_scope") or "") or None,
        influence_level=str(strategy.get("influence_level") or "") or None,
    )
    declared = get_declared_effort_tier(psm)
    if declared:
        contract = _TIER_CONTRACT[declared]
        raw = psm.episode.retry_counters.get(EFFORT_KEY)
        source = "agent"
        if isinstance(raw, dict) and raw.get("source"):
            source = str(raw["source"])
        return {
            "tier": declared,
            "evidence_band": tier_to_evidence_band(declared),
            "source": source,
            "declared": True,
            "recommended_tier": recommended["tier"],
            "recommended_band": recommended.get("evidence_band")
            or tier_to_evidence_band(recommended["tier"]),
            "why": (
                f"Agent set effort_tier={declared}"
                + (
                    f" (MCP recommended {recommended['tier']})"
                    if recommended["tier"] != declared
                    else ""
                )
            ),
            "pay": list(contract["pay"]),
            "skip": list(contract["skip"]),
            "summary": contract["summary"],
            "resource": RIGHT_SIZING_RESOURCE,
        }
    return {
        **recommended,
        "declared": False,
        "recommended_tier": recommended["tier"],
        "recommended_band": recommended.get("evidence_band")
        or tier_to_evidence_band(recommended["tier"]),
    }


def effort_arms_initiative(tier: str | None) -> bool:
    t = normalize_effort_tier(tier) or "polish"
    return bool(_TIER_CONTRACT[t]["arms_initiative"])


def effort_requires_ship(tier: str | None) -> bool:
    t = normalize_effort_tier(tier) or "polish"
    return bool(_TIER_CONTRACT[t]["requires_ship"])


def effort_requires_full_sections(tier: str | None) -> bool:
    t = normalize_effort_tier(tier) or "polish"
    return bool(_TIER_CONTRACT[t]["requires_full_sections"])


def build_right_sizing_card(
    psm: ProjectSituationModel,
    strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compact card for agent_summary / episode_card."""
    resolved = resolve_effort_tier(psm, strategy)
    tier = str(resolved["tier"])
    band = str(resolved.get("evidence_band") or tier_to_evidence_band(tier))
    return {
        "tier": tier,
        "evidence_band": band,
        "declared": bool(resolved.get("declared")),
        "source": resolved.get("source"),
        "recommended_tier": resolved.get("recommended_tier") or tier,
        "recommended_band": resolved.get("recommended_band")
        or tier_to_evidence_band(str(resolved.get("recommended_tier") or tier)),
        "why": resolved.get("why"),
        "pay": list(resolved.get("pay") or []),
        "skip": list(resolved.get("skip") or []),
        "summary": resolved.get("summary"),
        "resource": RIGHT_SIZING_RESOURCE,
        "override_hint": (
            "Pass effort_tier=light|medium|heavy|very_heavy "
            "(or touch_up|polish|feature|initiative) on session_start / "
            "visual_feedback / verify to lock your judgment."
        ),
    }
