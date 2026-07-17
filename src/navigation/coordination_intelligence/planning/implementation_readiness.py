"""Deterministic host-action gate derived from strategy and evidence outcomes."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel


STRUCTURAL_DECISIONS = frozenset({
    "design_reference",
    "component_foundation",
    "design_system",
})


def _workflow_resource(task_scope: str, blocking: list[str]) -> str:
    if "design_reference" in blocking:
        return "perception://inspiration-guide"
    if task_scope == "redesign":
        return "perception://redesign-workflow"
    if task_scope in ("hotfix", "surgical", "debug"):
        return "perception://bugfix-workflow"
    if task_scope in ("design_driven", "system_setup"):
        return "perception://design-workflow"
    return "perception://frontend-methodology"


def compile_implementation_readiness(
    psm: ProjectSituationModel,
    *,
    influence_level: str,
    task_scope: str,
    unresolved_decisions: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """Compile an additive, machine-readable implementation boundary."""
    from navigation.coordination_intelligence.planning.section_checklist import (
        episode_needs_section_checklist,
        get_section_checklist,
        incomplete_sections,
    )
    from navigation.coordination_intelligence.planning.ship_council import (
        episode_needs_ship_council,
    )

    blocking = [
        str(decision.get("decision_id"))
        for decision in unresolved_decisions
        if str(decision.get("decision_id")) in STRUCTURAL_DECISIONS
    ]
    failures = [
        {
            "capability_id": capability_id,
            "reason": outcome.get("failure_reason"),
        }
        for capability_id, outcome in psm.evidence.capability_ledger.items()
        if outcome.get("status") == "failed"
    ]

    if influence_level == "minimal" or task_scope in ("hotfix", "surgical", "debug"):
        state = "maintenance"
    elif blocking and influence_level == "structural":
        state = "blocked"
    elif unresolved_decisions:
        state = "provisional"
    else:
        state = "ready"

    evidence_plan: list[dict[str, Any]] = []
    for decision in unresolved_decisions:
        capabilities = list(decision.get("resolving_capabilities") or [])
        if capabilities:
            evidence_plan.append({
                "decision_id": decision.get("decision_id"),
                "capability_id": capabilities[0],
                "completion_criteria": "usable evidence outcome with advancement_eligible=true",
            })

    failed_caps = {str(item["capability_id"]) for item in failures}
    next_capability = evidence_plan[0]["capability_id"] if evidence_plan else None
    if "inspiration_workflow" in failed_caps and "design_reference" in blocking:
        next_capability = "browser_observe"
    required_resource = _workflow_resource(task_scope, blocking)

    if state == "blocked":
        allowed = ["read_required_resource", "gather_evidence", "scaffold_runtime", "start_dev_server"]
        prohibited = [
            "broad_visual_implementation",
            "lock_design_decisions",
            "claim_complete",
        ]
    elif state == "provisional":
        allowed = ["read_required_resource", "gather_evidence", "bounded_draft"]
        prohibited = ["lock_design_decisions", "claim_complete"]
    else:
        allowed = ["implement", "verify"]
        prohibited = []

    strategy = {
        "influence_level": influence_level,
        "task_scope": task_scope,
    }
    section_required = episode_needs_section_checklist(psm, strategy)
    ship_required = episode_needs_ship_council(psm, strategy)
    open_sections = incomplete_sections(psm) if section_required else []
    checklist = get_section_checklist(psm)

    # Priority: structural block → section checklist → ship council → ready.
    if section_required:
        prohibited = list(dict.fromkeys([*prohibited, "claim_complete"]))
        next_capability = "browser_verify"
        required_resource = "perception://verification-guide"
        allowed = list(dict.fromkeys([*allowed, "gather_evidence", "verify"]))
    elif ship_required:
        prohibited = list(dict.fromkeys([*prohibited, "claim_complete"]))
        next_capability = "design_review"
        required_resource = "perception://ship-council"
        if "gather_evidence" not in allowed:
            allowed = list(dict.fromkeys([*allowed, "gather_evidence"]))

    if state == "blocked" and not section_required:
        completion = (
            "Resolve blocking decisions with usable evidence before broad visual implementation."
        )
    elif section_required:
        remaining = ", ".join(open_sections[:5]) or "seeded sections"
        completion = (
            "SECTION CHECKLIST incomplete. For each section: observe (look at screenshot) -> "
            f"perception_verify with section_id. Remaining: {remaining}."
        )
    elif state == "blocked":
        completion = (
            "Resolve blocking decisions with usable evidence before broad visual implementation."
        )
    elif ship_required:
        completion = (
            "Run perception_design_review(mode=ship); dispose challenges; "
            "claim-done only when ship_gate.council_clear and verify passed."
        )
    else:
        completion = "Follow the evidence plan, then verify the implemented surface."

    gate = {
        "state": state,
        "blocking_decisions": blocking,
        "evidence_failures": failures,
        "allowed_actions": allowed,
        "prohibited_actions": prohibited,
        "next_required_capability": next_capability,
        "required_resource": required_resource,
        "section_checklist_required": section_required,
        "section_checklist": checklist,
        "incomplete_sections": open_sections,
        "ship_council_required": ship_required and not section_required,
        "completion_criteria": completion,
    }
    return gate, evidence_plan, required_resource
