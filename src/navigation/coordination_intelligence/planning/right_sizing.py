"""AI-centric effort right-sizing — agent decides, MCP recommends.

Default: lightest-that-fits. Heavy Done-ladder gates (ship / residue / full-page
section checklist) only *block* claim-done on initiative tier. Lower tiers keep
the same measurements available as advisory.
"""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel, _utc_now

EFFORT_TIERS = ("touch_up", "polish", "feature", "initiative")
EFFORT_KEY = "effort_tier"
RIGHT_SIZING_RESOURCE = "perception://guide/right-sizing"

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
    }
    text = aliases.get(text, text)
    return text if text in EFFORT_TIERS else None


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
    from navigation.coordination_intelligence.planning.situation_policy import sticky_design_scope

    scope = str(task_scope or "")
    sticky = sticky_design_scope(psm)
    if sticky in ("design_driven", "redesign", "system_setup"):
        scope = sticky

    if scope in ("design_driven", "redesign", "system_setup"):
        tier = "initiative"
        why = f"task_scope={scope} is a design initiative — full ladder."
    elif scope in ("hotfix", "surgical", "debug"):
        tier = "touch_up"
        why = f"task_scope={scope} — hard verify is enough."
    elif scope == "feature_incremental":
        # Default light for incremental work: polish, not ship/residue ceremony.
        # Agent upgrades to feature/initiative when blast radius is larger.
        band = str(getattr(psm.situation, "lifecycle_stage", "") or "")
        early = band in ("S01_intent", "S02_discovery", "S03_design", "S04_architecture")
        foundation = psm.evidence.capability_ledger.get("component_select") or {}
        foundation_unpaid = foundation.get("status") not in ("succeeded", "provisional")
        if early and foundation_unpaid and influence_level == "structural":
            tier = "feature"
            why = "early feature with unpaid foundation — pay observe + foundation?, not ship."
        else:
            tier = "polish"
            why = (
                "incremental / chrome-scale default (lightest-that-fits). "
                "Upgrade effort_tier if blast radius is a new block or full page."
            )
    else:
        tier = "polish"
        why = "unknown scope — default polish (lightest-that-fits)."

    contract = _TIER_CONTRACT[tier]
    return {
        "tier": tier,
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
            "source": source,
            "declared": True,
            "recommended_tier": recommended["tier"],
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
    return {
        "tier": tier,
        "declared": bool(resolved.get("declared")),
        "source": resolved.get("source"),
        "recommended_tier": resolved.get("recommended_tier") or tier,
        "why": resolved.get("why"),
        "pay": list(resolved.get("pay") or []),
        "skip": list(resolved.get("skip") or []),
        "summary": resolved.get("summary"),
        "resource": RIGHT_SIZING_RESOURCE,
        "override_hint": (
            "Pass effort_tier=touch_up|polish|feature|initiative on session_start / "
            "visual_feedback / verify to lock your judgment."
        ),
    }
