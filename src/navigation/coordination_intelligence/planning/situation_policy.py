"""Situation policy matching (R12) — discriminators + policy selection. No leaf state IDs."""
from __future__ import annotations

import re
from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel

LIFECYCLE_TO_BAND = {
    "S01_intent": "early",
    "S02_discovery": "early",
    "S03_design": "early",
    "S04_architecture": "early",
    "S05_implementation": "mid",
    "S06_integration": "mid",
    "S07_verification": "mid",
    "S08_quality": "late",
    "S09_consistency": "late",
    "S10_release": "late",
    "S11_production": "production",
    "S12_evolution": "production",
    "Sxx_any": "production",
}

MATURITY_TO_BAND = {
    "M0": "greenfield",
    "M1": "greenfield",
    "M2": "greenfield",
    "M3": "growing",
    "M4": "growing",
    "M5": "mature",
    "M6": "mature",
}

_HEAVY_CAPS = frozenset(
    {
        "inspiration_workflow",
        "design_review",
        "design_consistency_audit",
        "seo_evidence_collect",
        "quality_audit",
        "resource_workflow",
        "component_select",
        "design_snapshot",
    }
)


def lifecycle_band(stage: str) -> str:
    return LIFECYCLE_TO_BAND.get(stage, "mid")


def maturity_band(maturity: str) -> str:
    return MATURITY_TO_BAND.get(maturity, "growing")


def derive_discriminators(psm: ProjectSituationModel) -> dict[str, str]:
    """Derive situation discriminators from live PSM — never from research leaf IDs."""
    intent_text = " ".join(f.intent for f in psm.episode.intent_stack).lower()
    situation = psm.situation.situation_class.lower()
    cluster = psm.situation.cluster_id.lower()

    task_scope = _derive_task_scope(intent_text, situation, cluster, psm)
    design_ref = _derive_design_reference_posture(psm, intent_text)
    system = _derive_system_posture(psm)
    foundation = _derive_foundation_posture(psm)
    polish = str(psm.episode.retry_counters.get("polish_saturation") or "none")

    return {
        "task_scope": task_scope,
        "lifecycle_band": lifecycle_band(psm.situation.lifecycle_stage),
        "maturity_band": maturity_band(psm.situation.project_maturity),
        "design_reference_posture": design_ref,
        "system_posture": system,
        "foundation_posture": foundation,
        "polish_saturation": polish if polish in ("none", "soft", "hard") else "none",
    }


def _derive_task_scope(
    intent_text: str,
    situation: str,
    cluster: str,
    psm: ProjectSituationModel,
) -> str:
    if situation in ("hotfix",) or "hotfix" in intent_text or "incident" in cluster:
        return "hotfix"
    if situation in ("functional_bug",) or "debug" in cluster or "bug" in intent_text:
        return "debug"
    if any(
        k in intent_text
        for k in (
            "padding",
            "margin",
            "fix typo",
            "one button",
            "single button",
            "tweak",
            "color of",
            "rename",
        )
    ):
        return "surgical"
    if any(k in intent_text for k in ("design system", "token", "foundation", "theme setup")):
        return "system_setup"
    if any(
        k in intent_text
        for k in ("redesign", "rebrand", "new landing", "marketing site", "homepage hero")
    ):
        return "redesign" if "redesign" in intent_text or "rebrand" in intent_text else "design_driven"
    if "landing" in intent_text or "dashboard" in intent_text and "new" in intent_text:
        return "design_driven"
    if situation in ("redesign", "inspiration_needed"):
        return "design_driven"
    if "design.reference" in cluster or "design.figma" in cluster:
        return "design_driven"
    return "feature_incremental"


def _derive_design_reference_posture(psm: ProjectSituationModel, intent_text: str) -> str:
    persistent = psm.artifacts.persistent or {}
    if persistent.get("figma_connected") or "figma" in intent_text:
        return "figma"
    design = psm.evidence.domains.get("design_source")
    assets = psm.evidence.domains.get("assets")
    attempts = psm.episode.retry_counters.get("capability_attempts") or {}
    if int(attempts.get("inspiration_workflow", 0)) >= 1 or (
        design and design.posture not in ("unknown",)
    ):
        return "inspiration"
    if assets and assets.posture not in ("unknown",):
        return "agreed_with_refs"
    if any(k in intent_text for k in ("no reference", "no inspiration", "from scratch")):
        return "agreed_no_refs"
    return "none"


def _derive_system_posture(psm: ProjectSituationModel) -> str:
    ds = psm.evidence.domains.get("design_system")
    if ds is None or ds.posture == "unknown":
        return "no_ds"
    if ds.posture in ("verified", "known"):
        return "mature_ds"
    return "partial_ds"


def _derive_foundation_posture(psm: ProjectSituationModel) -> str:
    attempts = psm.episode.retry_counters.get("capability_attempts") or {}
    if int(attempts.get("component_integrate", 0)) >= 1:
        return "integrated"
    if int(attempts.get("component_select", 0)) >= 1:
        return "selected"
    return "unknown"


def match_policy(
    catalog: dict[str, Any],
    discriminators: dict[str, str],
) -> dict[str, Any]:
    """Pick highest-priority policy whose match allows the current discriminators."""
    policies = list(catalog.get("policies") or [])
    policies.sort(key=lambda p: int(p.get("priority") or 0), reverse=True)
    for policy in policies:
        if _match_allows(policy.get("match") or {}, discriminators):
            return policy
    return policies[-1] if policies else {}


def _match_allows(match: dict[str, Any], disc: dict[str, str]) -> bool:
    if not match:
        return True
    for key, allowed in match.items():
        value = disc.get(key)
        if value is None:
            continue
        if isinstance(allowed, list):
            if value not in allowed:
                return False
        elif value != allowed:
            return False
    return True


def capability_cost(catalog: dict[str, Any], capability_id: str) -> int:
    costs = catalog.get("cost_classes") or {}
    if capability_id in costs:
        return int(costs[capability_id])
    if capability_id in _HEAVY_CAPS:
        return 8
    return 3


def intent_suggests_stage(intent: str) -> str | None:
    """Optional lifecycle hint from host intent keywords."""
    t = intent.lower()
    if re.search(r"\b(hotfix|production incident|pager)\b", t):
        return "S11_production"
    if re.search(r"\b(new landing|from scratch|greenfield|redesign homepage)\b", t):
        return "S03_design"
    if re.search(r"\b(seo audit|lighthouse|cwv)\b", t):
        return "S08_quality"
    if re.search(r"\b(consistency|design system audit)\b", t):
        return "S09_consistency"
    return None
