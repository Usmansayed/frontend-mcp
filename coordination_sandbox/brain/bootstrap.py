"""Catalog + project bootstrap for sandbox episodes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from coordination_sandbox.brain.models import ProjectSituationModel
from coordination_sandbox.brain.situation_policy import intent_suggests_stage

CATALOG_PATH = Path(__file__).resolve().parent / "catalog" / "situation_policy_catalog.v1.yaml"


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    target = path or CATALOG_PATH
    with target.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def bootstrap_project(
    intent: str,
    *,
    project_maturity: str | None = None,
    lifecycle_stage: str | None = None,
    situation_class: str | None = None,
    existing_product: bool = False,
    figma: bool = False,
) -> ProjectSituationModel:
    """Create a synthetic PSM from a natural-language engineering prompt."""
    psm = ProjectSituationModel()
    psm.push_intent(intent)
    t = intent.lower()

    if situation_class:
        psm.situation.situation_class = situation_class
    elif "hotfix" in t or "production incident" in t:
        psm.situation.situation_class = "hotfix"
    elif "bug" in t or "responsive" in t and "fix" in t:
        psm.situation.situation_class = "functional_bug"
    elif "redesign" in t:
        psm.situation.situation_class = "redesign"
    else:
        psm.situation.situation_class = "new_feature"

    if project_maturity:
        psm.situation.project_maturity = project_maturity
    elif existing_product or any(
        k in t for k in ("existing", "improve this", "production", "hotfix", "accessibility")
    ):
        psm.situation.project_maturity = "M4"
    elif any(k in t for k in ("build", "from scratch", "new landing", "saas dashboard")):
        psm.situation.project_maturity = "M1"
    else:
        psm.situation.project_maturity = "M3"

    if lifecycle_stage:
        psm.situation.lifecycle_stage = lifecycle_stage
    else:
        hinted = intent_suggests_stage(intent)
        if hinted:
            psm.situation.lifecycle_stage = hinted
        elif psm.situation.situation_class == "hotfix":
            psm.situation.lifecycle_stage = "S11_production"
        elif existing_product:
            psm.situation.lifecycle_stage = "S05_implementation"
        else:
            psm.situation.lifecycle_stage = "S03_design"

    if figma or "figma" in t:
        psm.artifacts.persistent["figma_connected"] = True

    if existing_product or "existing" in t or "improve this" in t:
        # Simulate known runtime surface
        psm.artifacts.scan_id = "sim_scan_existing"
        psm.evidence.domains["ui_runtime"].posture = "partial"
        psm.evidence.domains["codebase"].posture = "known"
        if "dashboard" in t:
            psm.evidence.domains["design_system"].posture = "partial"

    return psm


def apply_capability_effects(psm: ProjectSituationModel, capability_id: str) -> list[str]:
    """Simulate evidence / lifecycle side-effects of accepting a capability (no tools)."""
    notes: list[str] = []
    attempts = psm.episode.retry_counters.setdefault("capability_attempts", {})
    attempts[capability_id] = int(attempts.get(capability_id, 0)) + 1
    psm.episode.completed_step_ids.append(f"sim::{capability_id}::{attempts[capability_id]}")

    if capability_id == "browser_observe":
        psm.artifacts.scan_id = psm.artifacts.scan_id or f"sim_scan_{attempts[capability_id]}"
        psm.evidence.domains["ui_runtime"].posture = "partial"
        psm.evidence.domains["ui_runtime"].source_capability = capability_id
        notes.append("ui_runtime -> partial; scan_id set")
        if psm.situation.lifecycle_stage in ("S02_discovery", "S03_design"):
            psm.situation.lifecycle_stage = "S05_implementation"
            notes.append("lifecycle -> S05_implementation (painted UI)")

    elif capability_id == "inspiration_workflow":
        psm.evidence.domains["design_source"].posture = "known"
        psm.evidence.domains["assets"].posture = "partial"
        notes.append("design_source -> known (inspiration gathered)")

    elif capability_id == "component_select":
        psm.evidence.domains["design_system"].posture = "partial"
        notes.append("design_system -> partial (foundation selected)")
        if psm.situation.lifecycle_stage in (
            "S01_intent",
            "S02_discovery",
            "S03_design",
        ):
            psm.situation.lifecycle_stage = "S04_architecture"
            notes.append("lifecycle -> S04_architecture")

    elif capability_id == "design_review":
        psm.evidence.domains["quality"].posture = "partial"
        notes.append("quality -> partial (critique)")

    elif capability_id == "design_consistency_audit":
        psm.evidence.domains["design_system"].posture = "known"
        psm.situation.lifecycle_stage = "S09_consistency"
        notes.append("lifecycle -> S09_consistency")

    elif capability_id == "quality_audit":
        psm.evidence.domains["quality"].posture = "known"
        psm.situation.lifecycle_stage = "S08_quality"
        notes.append("lifecycle -> S08_quality")

    elif capability_id == "seo_evidence_collect":
        psm.evidence.domains["seo"].posture = "known"
        notes.append("seo -> known")

    elif capability_id == "browser_verify":
        psm.episode.verification_status = "passed"
        psm.evidence.domains["ui_runtime"].posture = "verified"
        notes.append("verification_status -> passed")
        if psm.situation.lifecycle_stage not in ("S11_production", "Sxx_any"):
            psm.situation.lifecycle_stage = "S07_verification"
            notes.append("lifecycle -> S07_verification")

    elif capability_id == "browser_diff":
        notes.append("diff evidence recorded (simulated)")

    elif capability_id == "runtime_diagnosis":
        notes.append("runtime diagnosis evidence recorded (simulated)")

    return notes
