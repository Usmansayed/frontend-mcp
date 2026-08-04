"""Deterministic host-action gate derived from strategy and evidence outcomes."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel


STRUCTURAL_DECISIONS = frozenset({
    "design_reference",
    "component_foundation",
    "design_system",
})


def _workflow_resource(
    task_scope: str,
    blocking: list[str],
    *,
    next_capability: str | None = None,
    psm: ProjectSituationModel | None = None,
    effort_tier: str | None = None,
) -> str:
    from navigation.coordination_intelligence.planning.reference_routing import (
        design_reference_workflow_resource,
    )
    from navigation.coordination_intelligence.planning.right_sizing import (
        RIGHT_SIZING_RESOURCE,
    )

    if "design_reference" in blocking:
        routed = design_reference_workflow_resource(
            task_scope=task_scope,
            next_capability=next_capability,
            psm=psm,
        )
        if routed:
            return routed
        return "perception://guide/inspiration"
    if effort_tier in ("touch_up", "polish") and not blocking:
        return RIGHT_SIZING_RESOURCE
    if task_scope == "redesign":
        return "perception://redesign-workflow"
    if task_scope in ("hotfix", "surgical", "debug"):
        return "perception://bugfix-workflow"
    if task_scope in ("design_driven", "system_setup"):
        return "perception://design-workflow"
    if effort_tier in ("touch_up", "polish", "feature"):
        return RIGHT_SIZING_RESOURCE
    return "perception://frontend-methodology"


def compile_implementation_readiness(
    psm: ProjectSituationModel,
    *,
    influence_level: str,
    task_scope: str,
    unresolved_decisions: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """Compile an additive, machine-readable implementation boundary."""
    from navigation.coordination_intelligence.planning.evidence_plan_status import (
        open_evidence_plan_items,
    )
    from navigation.coordination_intelligence.planning.residue_scan import residue_required
    from navigation.coordination_intelligence.planning.right_sizing import (
        build_right_sizing_card,
        effort_requires_full_sections,
    )
    from navigation.coordination_intelligence.planning.section_checklist import (
        episode_needs_section_checklist,
        get_section_checklist,
        incomplete_sections,
    )
    from navigation.coordination_intelligence.planning.ship_council import (
        episode_needs_ship_council,
    )
    from navigation.coordination_intelligence.planning.surface_type import design_scope_applies

    strategy = {
        "influence_level": influence_level,
        "task_scope": task_scope,
    }
    right_sizing = build_right_sizing_card(psm, strategy)
    effort_tier = str(right_sizing.get("tier") or "polish")

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

    if (
        influence_level == "minimal"
        or task_scope in ("hotfix", "surgical", "debug")
        or effort_tier in ("touch_up", "polish")
    ):
        state = "maintenance"
    elif blocking and influence_level == "structural":
        state = "blocked"
    elif unresolved_decisions:
        state = "provisional"
    else:
        state = "ready"

    from navigation.coordination_intelligence.planning.reference_routing import (
        order_design_reference_capabilities,
        prefer_snapshot_first,
        snapshot_reference_paid,
    )

    evidence_plan: list[dict[str, Any]] = []
    for decision in unresolved_decisions:
        capabilities = list(decision.get("resolving_capabilities") or [])
        decision_id = str(decision.get("decision_id") or "")
        if decision_id == "design_reference":
            capabilities = order_design_reference_capabilities(
                capabilities,
                task_scope=task_scope,
                psm=psm,
            )
        if decision_id == "component_foundation":
            # Stage: plan → select. Plan alone must not close the decision.
            from navigation.coordination_intelligence.planning.evidence_plan_status import (
                _ledger_usable,
            )

            if _ledger_usable(psm, "component_select"):
                capabilities = []
            elif _ledger_usable(psm, "component_search_plan"):
                capabilities = ["component_select"]
            else:
                capabilities = ["component_search_plan", "component_select"]
        if capabilities:
            evidence_plan.append({
                "decision_id": decision.get("decision_id"),
                "capability_id": capabilities[0],
                "completion_criteria": (
                    "usable evidence, valid skip reason, or superseded by stronger evidence"
                    if decision_id != "component_foundation"
                    else "component_select (or integrate) — plan alone does not resolve foundation"
                ),
            })

    failed_caps = {str(item["capability_id"]) for item in failures}
    next_capability = evidence_plan[0]["capability_id"] if evidence_plan else None
    if "inspiration_workflow" in failed_caps and "design_reference" in blocking:
        next_capability = "browser_observe"
    # Hard prefer: redesign with unpaid snapshot must not tip gate.next to gallery.
    if (
        prefer_snapshot_first(task_scope)
        and not snapshot_reference_paid(psm)
        and "design_reference" in blocking
        and next_capability == "inspiration_workflow"
    ):
        next_capability = "design_snapshot"
        for item in evidence_plan:
            if item.get("decision_id") == "design_reference":
                item["capability_id"] = "design_snapshot"
                break
    required_resource = _workflow_resource(
        task_scope,
        blocking,
        next_capability=str(next_capability) if next_capability else None,
        psm=psm,
        effort_tier=effort_tier,
    )

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

    # Never allow claim-done before hard verify — maintenance/ready used to leave
    # prohibited empty, so agent_summary.card.claim_ok flipped true too early.
    if psm.episode.verification_status != "passed":
        prohibited = list(dict.fromkeys([*prohibited, "claim_complete"]))

    section_required = episode_needs_section_checklist(psm, strategy)
    ship_required = episode_needs_ship_council(psm, strategy)
    open_sections = incomplete_sections(psm) if section_required else []
    checklist = get_section_checklist(psm)
    initiative_scope = design_scope_applies(psm, strategy)
    residue_needed = initiative_scope and residue_required(psm)
    open_plan = open_evidence_plan_items(psm, evidence_plan) if initiative_scope else []
    evidence_incomplete = bool(open_plan)

    # Advisory-only when light tier demotes what would have been blocking ceremony.
    ship_advisory = False
    sections_advisory = False
    if effort_tier not in ("initiative",) and not ship_required:
        if (
            psm.artifacts.snapshot_id
            and psm.episode.verification_status == "passed"
            and influence_level in ("structural", "balanced")
            and task_scope not in ("hotfix", "surgical", "debug")
        ):
            ship_advisory = True
    if effort_tier not in ("initiative",) and not section_required:
        seeded = get_section_checklist(psm)
        if seeded and seeded.get("required") and not effort_requires_full_sections(effort_tier):
            sections_advisory = True

    # Priority: structural block → section checklist → residue → ship → evidence plan → ready.
    if section_required:
        prohibited = list(dict.fromkeys([*prohibited, "claim_complete"]))
        next_capability = "browser_verify"
        required_resource = "perception://verification-guide"
        allowed = list(dict.fromkeys([*allowed, "gather_evidence", "verify"]))
    elif residue_needed:
        prohibited = list(dict.fromkeys([*prohibited, "claim_complete"]))
        next_capability = "design_snapshot"
        required_resource = "perception://verification-guide"
        allowed = list(dict.fromkeys([*allowed, "gather_evidence"]))
    elif ship_required:
        prohibited = list(dict.fromkeys([*prohibited, "claim_complete"]))
        next_capability = "design_review"
        required_resource = "perception://ship-council"
        if "gather_evidence" not in allowed:
            allowed = list(dict.fromkeys([*allowed, "gather_evidence"]))
    elif evidence_incomplete and state != "blocked":
        prohibited = list(dict.fromkeys([*prohibited, "claim_complete"]))
        next_capability = str(open_plan[0].get("capability_id") or next_capability)
        if (
            prefer_snapshot_first(task_scope)
            and not snapshot_reference_paid(psm)
            and "design_reference" in blocking
            and next_capability == "inspiration_workflow"
        ):
            next_capability = "design_snapshot"
            for item in evidence_plan:
                if item.get("decision_id") == "design_reference":
                    item["capability_id"] = "design_snapshot"
                    break
            for item in open_plan:
                if item.get("decision_id") == "design_reference":
                    item["capability_id"] = "design_snapshot"
                    break
        required_resource = _workflow_resource(
            task_scope,
            blocking,
            next_capability=str(next_capability) if next_capability else None,
            psm=psm,
            effort_tier=effort_tier,
        )
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
    elif residue_needed:
        completion = (
            "RESIDUE SCAN: remeasure with perception_build_design_snapshot once, "
            "then dispose any new ship challenges. One pass only."
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
    elif evidence_incomplete:
        open_ids = ", ".join(str(i.get("decision_id")) for i in open_plan[:4])
        completion = (
            "Evidence plan still open for: "
            f"{open_ids}. Complete usable evidence, skip with a valid reason, or supersede — "
            "do not call tools only to satisfy the gate."
        )
    elif effort_tier in ("touch_up", "polish") and psm.episode.verification_status == "passed":
        completion = (
            f"effort_tier={effort_tier}: hard verify passed — claim-done allowed. "
            "Ship/sections are advisory only; pass effort_tier=initiative if this was structural."
        )
    elif effort_tier in ("touch_up", "polish"):
        completion = (
            f"effort_tier={effort_tier}: pay {', '.join(right_sizing.get('pay') or [])}; "
            f"skip {', '.join((right_sizing.get('skip') or [])[:4])}. "
            f"Read {right_sizing.get('resource')}."
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
        "ship_council_required": ship_required and not section_required and not residue_needed,
        "residue_scan_required": residue_needed,
        "evidence_plan_incomplete": evidence_incomplete,
        "ship_council_advisory": ship_advisory,
        "section_checklist_advisory": sections_advisory,
        "right_sizing": right_sizing,
        "completion_criteria": completion,
    }
    return gate, evidence_plan, required_resource
