"""Surface-type discriminator — episode context for coordination judgments."""
from __future__ import annotations

import re
from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel

SURFACE_TYPES = frozenset({
    "dashboard",
    "settings_form",
    "auth",
    "marketing",
    "data_table",
    "mixed",
    "unknown",
})


def derive_surface_type(
    intent: str,
    *,
    snapshot: dict[str, Any] | None = None,
) -> str:
    """Deterministic surface classification from intent (+ optional snapshot cues)."""
    text = (intent or "").lower()
    scores: dict[str, float] = {
        "dashboard": 0.0,
        "settings_form": 0.0,
        "auth": 0.0,
        "marketing": 0.0,
        "data_table": 0.0,
    }

    if any(k in text for k in ("settings", "preferences", "account settings", "workspace settings")):
        scores["settings_form"] += 3.0
    if any(k in text for k in ("login", "sign in", "sign-up", "signup", "auth", "forgot password")):
        scores["auth"] += 3.0
    if any(
        k in text
        for k in (
            "landing",
            "marketing",
            "homepage",
            "hero",
            "promo",
            "portfolio",
            "about page",
            "about ",
            " personal",
            "personal site",
            "my journey",
            "builder",
            "artful",
        )
    ):
        scores["marketing"] += 3.0
    # Bare "about" (path or short intent)
    if re.search(r"(^|[\s/#])about([\s/#]|$)", text):
        scores["marketing"] += 2.5
    if any(k in text for k in ("dashboard", "analytics", "kpi", "metrics overview")):
        scores["dashboard"] += 2.5
    if any(k in text for k in ("customers table", "crm", "data table", "records list")):
        scores["data_table"] += 2.5
    if "redesign" in text and scores["dashboard"] == 0 and scores["marketing"] == 0:
        scores["dashboard"] += 0.5

    if snapshot:
        layout = snapshot.get("layout") if isinstance(snapshot.get("layout"), dict) else {}
        regions = list(layout.get("regions") or [])
        roles = [str(r.get("role") or "").lower() for r in regions if isinstance(r, dict)]
        if roles.count("form") >= 1 and "main" in roles:
            scores["settings_form"] += 1.0
            scores["auth"] += 0.5
        section_count = sum(1 for r in roles if r == "section")
        has_aside = any(r in roles for r in ("aside", "sidebar", "navigation", "nav", "complementary"))
        # Multi-section alone ≠ dashboard — marketing about/journey pages also use sections.
        if section_count >= 3 and has_aside:
            scores["dashboard"] += 1.2
        elif section_count >= 3 and scores["marketing"] == 0:
            scores["dashboard"] += 0.4
        if section_count >= 2 and not has_aside:
            scores["marketing"] += 0.6
        main = next((r for r in regions if str(r.get("role") or "").lower() == "main"), None)
        if isinstance(main, dict):
            rect = main.get("rect") if isinstance(main.get("rect"), dict) else {}
            w = float(rect.get("w") or rect.get("width") or 0)
            vw = float((layout.get("viewport") or {}).get("width") or 0)
            if vw > 0 and w / vw <= 0.72:
                scores["marketing"] += 0.8
                scores["settings_form"] += 0.3
        # Page title / hierarchy cues
        hierarchy = snapshot.get("hierarchy") if isinstance(snapshot.get("hierarchy"), dict) else {}
        labels = " ".join(
            str(p.get("label") or "")
            for p in list(hierarchy.get("prominence_scores") or [])[:8]
            if isinstance(p, dict)
        ).lower()
        page_bits = f"{snapshot.get('url') or ''} {labels}"
        if any(k in page_bits for k in ("journey", "about", "portfolio", "work", "essays", "get in touch")):
            scores["marketing"] += 1.5
        if "/dashboard" in page_bits or "kpi" in labels:
            scores["dashboard"] += 1.5

    best = max(scores, key=scores.get)
    if scores[best] < 1.0:
        return "unknown"
    # Near-ties → mixed
    ranked = sorted(scores.values(), reverse=True)
    if len(ranked) >= 2 and ranked[0] >= 2.0 and ranked[0] - ranked[1] < 0.6:
        return "mixed"
    return best


def apply_surface_type(
    psm: ProjectSituationModel,
    *,
    intent: str | None = None,
    snapshot: dict[str, Any] | None = None,
    force: bool = False,
) -> str:
    """Sticky apply onto EpisodeState.surface_type (never retry_counters)."""
    intent_text = intent
    if intent_text is None:
        intent_text = " ".join(f.intent for f in psm.episode.intent_stack)
    derived = derive_surface_type(intent_text, snapshot=snapshot)
    current = str(getattr(psm.episode, "surface_type", None) or "unknown")
    if force or current in ("", "unknown"):
        if derived != "unknown":
            psm.episode.surface_type = derived
        return psm.episode.surface_type or "unknown"
    if derived == "mixed" and current != "mixed":
        psm.episode.surface_type = "mixed"
        return "mixed"
    return current


def design_scope_applies(psm: ProjectSituationModel, strategy: dict[str, Any] | None = None) -> bool:
    """v1 initiative layer only on design-driven / redesign / structural paths.

    Right-sizing: polish / touch_up / feature tiers do not arm the initiative
    machine (ship / residue / full-page checklist) even when influence is balanced.
    """
    from navigation.coordination_intelligence.planning.right_sizing import (
        effort_arms_initiative,
        resolve_effort_tier,
    )
    from navigation.coordination_intelligence.planning.situation_policy import sticky_design_scope

    strategy = strategy or {}
    resolved = resolve_effort_tier(psm, strategy)
    if not effort_arms_initiative(str(resolved.get("tier"))):
        return False
    scope = str(strategy.get("task_scope") or sticky_design_scope(psm) or "")
    sticky = sticky_design_scope(psm)
    if sticky in ("design_driven", "redesign", "system_setup"):
        scope = sticky
    if scope in ("hotfix", "surgical", "debug"):
        return False
    influence = str(strategy.get("influence_level") or "")
    if scope in ("design_driven", "redesign", "system_setup"):
        return True
    return influence in ("structural", "balanced") and scope not in ("hotfix", "surgical", "debug")
