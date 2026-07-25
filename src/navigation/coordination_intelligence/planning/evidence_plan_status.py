"""Evidence-plan terminal states — completed | skipped | superseded (no ritual calls)."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel, _utc_now

STATUS_KEY = "evidence_plan_status"

VALID_SKIP_REASONS = frozenset({
    "out_of_scope_for_surface",
    "user_directed_skip",
    "blocked_external",
    "already_satisfied_by_code",
    "diminishing_returns",
})

# If any of these capabilities succeed with usable evidence, mark design_reference superseded.
SUPERSEDE_DESIGN_REFERENCE = frozenset({
    "figma_integration",
    "design_snapshot",
    "component_select",
})

TERMINAL = frozenset({"completed", "skipped", "superseded"})


def get_plan_status_map(psm: ProjectSituationModel) -> dict[str, Any]:
    raw = psm.episode.retry_counters.get(STATUS_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def set_plan_item_status(
    psm: ProjectSituationModel,
    decision_id: str,
    *,
    state: str,
    reason: str | None = None,
    via_capability: str | None = None,
) -> dict[str, Any]:
    if state == "skipped" and reason not in VALID_SKIP_REASONS:
        raise ValueError(f"invalid skip reason: {reason!r}")
    if state not in TERMINAL:
        raise ValueError(f"invalid terminal state: {state!r}")
    status = get_plan_status_map(psm)
    status[str(decision_id)] = {
        "state": state,
        "reason": reason,
        "via_capability": via_capability,
        "at": _utc_now(),
    }
    psm.episode.retry_counters[STATUS_KEY] = status
    return status[str(decision_id)]


def _ledger_usable(psm: ProjectSituationModel, capability_id: str) -> bool:
    outcome = psm.evidence.capability_ledger.get(capability_id) or {}
    if outcome.get("advancement_eligible") is True:
        return True
    return str(outcome.get("status") or "") == "succeeded"


# Decision must not complete on stage precursors (plan alone ≠ foundation select).
DECISION_COMPLETION_CAPS: dict[str, frozenset[str]] = {
    "component_foundation": frozenset({"component_select", "component_integrate"}),
}


def refresh_plan_completions(
    psm: ProjectSituationModel,
    evidence_plan: list[dict[str, Any]],
) -> None:
    """Mark completed/superseded from ledger without forcing new tool calls."""
    status = get_plan_status_map(psm)
    for item in evidence_plan:
        decision_id = str(item.get("decision_id") or "")
        capability_id = str(item.get("capability_id") or "")
        if not decision_id:
            continue
        existing = status.get(decision_id) if isinstance(status.get(decision_id), dict) else {}
        if existing.get("state") in TERMINAL:
            continue
        completing = DECISION_COMPLETION_CAPS.get(decision_id)
        if completing is not None:
            for cap in completing:
                if _ledger_usable(psm, cap):
                    set_plan_item_status(
                        psm,
                        decision_id,
                        state="completed",
                        via_capability=cap,
                    )
                    break
            continue
        if capability_id and _ledger_usable(psm, capability_id):
            set_plan_item_status(
                psm,
                decision_id,
                state="completed",
                via_capability=capability_id,
            )
            continue
        # Supersede design_reference when stronger visual evidence landed.
        if decision_id == "design_reference":
            for cap in SUPERSEDE_DESIGN_REFERENCE:
                if _ledger_usable(psm, cap):
                    set_plan_item_status(
                        psm,
                        decision_id,
                        state="superseded",
                        reason="stronger_visual_evidence",
                        via_capability=cap,
                    )
                    break


def open_evidence_plan_items(
    psm: ProjectSituationModel,
    evidence_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refresh_plan_completions(psm, evidence_plan)
    status = get_plan_status_map(psm)
    open_items: list[dict[str, Any]] = []
    for item in evidence_plan:
        decision_id = str(item.get("decision_id") or "")
        entry = status.get(decision_id) if isinstance(status.get(decision_id), dict) else {}
        if entry.get("state") in TERMINAL:
            continue
        open_items.append(dict(item))
    return open_items


def evidence_plan_coverage(
    psm: ProjectSituationModel,
    evidence_plan: list[dict[str, Any]],
) -> float:
    if not evidence_plan:
        return 1.0
    refresh_plan_completions(psm, evidence_plan)
    status = get_plan_status_map(psm)
    done = 0
    for item in evidence_plan:
        decision_id = str(item.get("decision_id") or "")
        entry = status.get(decision_id) if isinstance(status.get(decision_id), dict) else {}
        if entry.get("state") in TERMINAL:
            done += 1
    return done / max(len(evidence_plan), 1)
