"""Episode portfolio — paid / unpaid / deferred intelligence families (advisory)."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel

# capability_id → family
CAPABILITY_FAMILY: dict[str, str] = {
    "browser_observe": "observe",
    "visual_feedback": "visual_feedback",
    "browser_verify": "verify",
    "inspiration_workflow": "inspiration",
    "design_snapshot": "snapshot",
    "component_select": "component",
    "component_search_plan": "component",
    "design_review": "design_review",
    "resource_workflow": "resources",
    "design_consistency_audit": "consistency",
    "design_consistency_assess": "consistency",
    "design_consistency_review": "consistency",
    "chrome_fidelity": "fidelity",
    "resolver_route": "resolve",
    "resolver_component": "resolve",
    "form_probe": "forms",
    "guard_probe": "guards",
}

DEFERRED_DEFAULT: tuple[str, ...] = ()


def _family_for_capability(capability_id: str) -> str:
    return CAPABILITY_FAMILY.get(capability_id, capability_id or "unknown")


def _ledger_paid(psm: ProjectSituationModel) -> list[dict[str, Any]]:
    paid: list[dict[str, Any]] = []
    for cap, outcome in (psm.evidence.capability_ledger or {}).items():
        status = str(outcome.get("status") or "")
        eligible = outcome.get("advancement_eligible")
        if status in ("failed", "noop"):
            continue
        if status in ("succeeded", "provisional") or eligible is True:
            paid.append({
                "family": _family_for_capability(str(cap)),
                "capability_id": str(cap),
                "status": status or ("succeeded" if eligible else "unknown"),
            })
    # Dedupe by family keep first
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in paid:
        fam = row["family"]
        if fam in seen:
            continue
        seen.add(fam)
        out.append(row)
    return out


def compile_episode_portfolio(
    *,
    psm: ProjectSituationModel,
    unresolved_decisions: list[dict[str, Any]],
    implementation_gate: dict[str, Any],
    initiative_on: bool,
    task_scope: str | None = None,
) -> dict[str, Any]:
    """Unified view of which intelligence families are paid vs still owed."""
    if not initiative_on:
        return {
            "paid": [],
            "unpaid": [],
            "deferred": list(DEFERRED_DEFAULT),
            "note": "N/A outside design scope",
        }

    from navigation.coordination_intelligence.planning.reference_routing import (
        prefer_snapshot_first,
        snapshot_reference_paid,
    )

    paid = _ledger_paid(psm)
    paid_families = {p["family"] for p in paid}
    unpaid: list[dict[str, Any]] = []
    scope = task_scope or str(
        (implementation_gate or {}).get("task_scope")
        or getattr(psm.episode, "situation_class", None)
        or ""
    )

    def add_unpaid(family: str, reason: str, suggested: str | None) -> None:
        if family in paid_families:
            return
        if any(u["family"] == family for u in unpaid):
            return
        unpaid.append({
            "family": family,
            "reason": reason,
            "suggested": suggested,
        })

    for decision in unresolved_decisions:
        did = str(decision.get("decision_id") or "")
        if did == "design_reference":
            # Snapshot can supersede inspiration — don't nag both.
            stronger = paid_families & {"snapshot"}
            snapshot_first = prefer_snapshot_first(scope) and not snapshot_reference_paid(psm)
            if snapshot_first:
                # Redesign path: snapshot owes first; leave inspiration *acquire* off unpaid
                # so gate.next / scoreboard don't tunnel into galleries.
                if "snapshot" not in paid_families:
                    add_unpaid(
                        "snapshot",
                        "redesign — measure / bind Design Snapshot before gallery",
                        "perception_build_design_snapshot",
                    )
                # But if a pack was already collected, digest is still owed (LOOK many refs).
                insp_q = (
                    (psm.evidence.capability_ledger or {}).get("inspiration_workflow") or {}
                ).get("quality") or {}
                vf_q = (
                    (psm.evidence.capability_ledger or {}).get("visual_feedback") or {}
                ).get("quality") or {}
                look_paid = bool(insp_q.get("direction_locked")) or (
                    vf_q.get("purpose") == "inspiration" and bool(vf_q.get("look_locked"))
                )
                if "inspiration" in paid_families and not look_paid:
                    add_unpaid(
                        "inspiration_extract",
                        "refs collected — LOOK ≥3–5 blobs + structured borrow/primary_ref_ids before inventing UI",
                        "perception_visual_feedback",
                    )
            else:
                if not stronger and "inspiration" not in paid_families:
                    add_unpaid(
                        "inspiration",
                        "design reference undecided",
                        "perception_inspiration_collect",
                    )
                # Collect alone ≠ direction — owe LOOK + structured look_lock/borrow
                insp_q = (
                    (psm.evidence.capability_ledger or {}).get("inspiration_workflow") or {}
                ).get("quality") or {}
                vf_q = (
                    (psm.evidence.capability_ledger or {}).get("visual_feedback") or {}
                ).get("quality") or {}
                look_paid = bool(insp_q.get("direction_locked")) or (
                    vf_q.get("purpose") == "inspiration" and bool(vf_q.get("look_locked"))
                )
                if "inspiration" in paid_families and not look_paid:
                    add_unpaid(
                        "inspiration_extract",
                        "refs collected — LOOK ≥3–5 blobs + structured borrow/primary_ref_ids before inventing UI",
                        "perception_visual_feedback",
                    )
                if "snapshot" not in paid_families:
                    add_unpaid(
                        "snapshot",
                        "no measured design snapshot yet (can supersede inspiration)",
                        "perception_build_design_snapshot",
                    )
        if did == "component_foundation":
            from navigation.coordination_intelligence.planning.evidence_plan_status import (
                _ledger_usable,
            )

            planned = _ledger_usable(psm, "component_search_plan")
            reason = (
                "foundation planned but not selected — run perception_select_component_foundation"
                if planned
                else "foundation undecided"
            )
            # Plan may have paid the component family; keep foundation unpaid until select.
            if not any(u["family"] == "component" for u in unpaid):
                unpaid.append({
                    "family": "component",
                    "reason": reason,
                    "suggested": "perception_select_component_foundation",
                })
            continue
        if did == "verification_outcome":
            add_unpaid("verify", "verification not passed", "perception_verify")
        if did == "layout_shell" and "observe" not in paid_families:
            add_unpaid("observe", "live layout not observed", "perception_navigate_and_observe")

    # Collect without digest: always owe extract even if design_reference already closed.
    insp_q = (
        (psm.evidence.capability_ledger or {}).get("inspiration_workflow") or {}
    ).get("quality") or {}
    vf_q = (
        (psm.evidence.capability_ledger or {}).get("visual_feedback") or {}
    ).get("quality") or {}
    look_paid = bool(insp_q.get("direction_locked")) or (
        vf_q.get("purpose") == "inspiration" and bool(vf_q.get("look_locked"))
    )
    if "inspiration" in paid_families and not look_paid:
        add_unpaid(
            "inspiration_extract",
            "refs collected — LOOK ≥3–5 blobs + structured borrow/primary_ref_ids before inventing UI",
            "perception_visual_feedback",
        )

    gate = implementation_gate or {}
    if gate.get("section_checklist_required"):
        # Distinct family — page verify can be paid while sections remain open.
        if not any(u["family"] == "sections" for u in unpaid):
            unpaid.insert(0, {
                "family": "sections",
                "reason": "section checklist incomplete — page verify is not enough",
                "suggested": "perception_verify",
            })
    if gate.get("residue_scan_required"):
        # Distinct from snapshot — remasure can be owed even when a prior snapshot is paid.
        if not any(u["family"] == "residue" for u in unpaid):
            unpaid.insert(0, {
                "family": "residue",
                "reason": "one-pass residue remasure required before ship may clear",
                "suggested": "perception_build_design_snapshot",
            })
    if gate.get("ship_council_required"):
        add_unpaid("design_review", "Ship Council not clear", "perception_design_review")

    # Structural design scopes owe a LOOK before locking UI (advisory unpaid).
    scope_l = scope.lower()
    structural_look = any(
        token in scope_l
        for token in (
            "design_driven",
            "redesign",
            "greenfield",
            "mockup",
            "polish",
            "landing",
            "dashboard",
        )
    )
    design_copy = any(
        token in scope_l
        for token in (
            "design_driven",
            "redesign",
            "greenfield",
            "mockup",
            "landing",
            "dashboard",
        )
    )
    if structural_look or gate.get("state") in ("blocked", "provisional"):
        if (
            "visual_feedback" not in paid_families
            and not gate.get("section_checklist_required")
            and not gate.get("ship_council_required")
        ):
            add_unpaid(
                "visual_feedback",
                "LOOK not paid — perception_visual_feedback before locking structural UI",
                "perception_visual_feedback",
            )
        # Creative assets — claim-critical on design heavy packs (pack.critical).
        if "resources" not in paid_families and design_copy:
            add_unpaid(
                "resources",
                "creative assets unpaid — perception_creative_assets (fonts/patterns/gradients/motion/graphics); APPLY them, do not only call",
                "perception_creative_assets",
            )
        # Consistency intelligence — audit after design_graph_refresh if needed.
        if "consistency" not in paid_families and design_copy:
            add_unpaid(
                "consistency",
                "consistency unpaid — perception_design_graph_refresh then perception_consistency_audit (parallel-safe with resources)",
                "perception_consistency_audit",
            )
        # Chrome fidelity 80–90% vs locked refs — paid only when VF stamps fidelity_locked.
        fidelity_paid = "fidelity" in paid_families
        if not fidelity_paid:
            vf_q = (
                (psm.evidence.capability_ledger or {}).get("visual_feedback") or {}
            ).get("quality") or {}
            fid_q = (
                (psm.evidence.capability_ledger or {}).get("chrome_fidelity") or {}
            ).get("quality") or {}
            fidelity_paid = bool(vf_q.get("fidelity_locked") or fid_q.get("fidelity_locked"))
            if fidelity_paid:
                paid.append(
                    {
                        "family": "fidelity",
                        "capability_id": "chrome_fidelity",
                        "status": "succeeded",
                    }
                )
                paid_families.add("fidelity")
        if design_copy and not fidelity_paid:
            add_unpaid(
                "fidelity",
                "chrome fidelity unpaid — LOOK refs + live UI; fill chrome_fidelity zones (nav|aside|main|composer) at 80–90% copy",
                "perception_visual_feedback",
            )

    # Observe nudge only when not mid section/ship ladder (avoid drowning the portfolio).
    if (
        "observe" not in paid_families
        and not gate.get("section_checklist_required")
        and not gate.get("ship_council_required")
        and gate.get("state") in ("blocked", "provisional", "ready")
    ):
        if "inspiration" in paid_families or "snapshot" in paid_families:
            add_unpaid("observe", "no live observe in episode yet", "perception_navigate_and_observe")

    deferred = [
        {
            "family": fam,
            "reason": "low ROI for this episode unless user asks",
        }
        for fam in DEFERRED_DEFAULT
    ]

    return {
        "paid": paid,
        "unpaid": unpaid,
        "deferred": deferred,
        "note": (
            "Episode portfolio — coordination view of all intelligence families. "
            "Advisory; backlog.top is the ROI next. Do not tunnel on one family."
        ),
    }


def initiative_from_portfolio(portfolio: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible initiative.unpaid_families from portfolio."""
    return {
        "unpaid_families": list(portfolio.get("unpaid") or []),
        "note": portfolio.get("note")
        or "Advisory portfolio — not a gate.",
    }
