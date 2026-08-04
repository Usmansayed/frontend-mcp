"""ROI-ranked episode backlog — whole-episode next action."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel


def _roi_for_kind(kind: str, *, priority: float = 0.5, surface_boost: float = 0.0) -> float:
    base = {
        "structural_decision": 0.9,
        "section": 0.82,
        "ship_challenge": 0.78,
        "residue": 0.74,
        "evidence_gap": 0.7,
    }.get(kind, 0.5)
    return round(min(1.0, base * (0.7 + 0.3 * priority) + surface_boost), 4)


def _align_ranked_with_gate(
    ranked: list[dict[str, Any]],
    gate_next_capability: str | None,
) -> list[dict[str, Any]]:
    """Prefer items that match gate.next so backlog.top does not contradict the gate."""
    if not gate_next_capability or not ranked:
        return ranked
    matching = [
        item
        for item in ranked
        if str(item.get("suggested_capability") or "") == gate_next_capability
    ]
    if not matching:
        return ranked
    rest = [
        item
        for item in ranked
        if str(item.get("suggested_capability") or "") != gate_next_capability
    ]
    return [*matching, *rest]


def compile_episode_backlog(
    *,
    psm: ProjectSituationModel,
    unresolved_decisions: list[dict[str, Any]],
    incomplete_sections: list[str] | None = None,
    open_ship_signals: list[str] | None = None,
    open_evidence_items: list[dict[str, Any]] | None = None,
    residue_required: bool = False,
    surface_type: str = "unknown",
    gate_next_capability: str | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    open_sections = list(incomplete_sections or [])

    for decision in unresolved_decisions:
        did = str(decision.get("decision_id") or "")
        priority = float(decision.get("priority") or 5) / 10.0
        caps = list(decision.get("resolving_capabilities") or [])
        suggested = caps[0] if caps else None
        if did == "component_foundation":
            from navigation.coordination_intelligence.planning.evidence_plan_status import (
                _ledger_usable,
            )

            if _ledger_usable(psm, "component_select"):
                suggested = "component_select"
            elif _ledger_usable(psm, "component_search_plan"):
                suggested = "component_select"
            else:
                suggested = "component_search_plan"
        items.append({
            "id": f"decision:{did}",
            "kind": "structural_decision",
            "title": str(decision.get("title") or did),
            "roi_score": _roi_for_kind("structural_decision", priority=priority),
            "why_now": str(decision.get("why_it_matters") or "Unresolved structural decision"),
            "suggested_capability": suggested,
            "surface_type": surface_type,
            "decision_id": did,
        })

    for section_id in open_sections:
        items.append({
            "id": f"section:{section_id}",
            "kind": "section",
            "title": f"Verify section {section_id}",
            # Claim-done blocker — must outrank open structural ROI tips (align with gate).
            "roi_score": max(
                _roi_for_kind("section", priority=0.85),
                0.95 if open_sections else 0.0,
            ),
            "why_now": "Section checklist incomplete — claim-done blocked",
            "suggested_capability": "browser_verify",
            "surface_type": surface_type,
        })

    for signal in open_ship_signals or []:
        boost = 0.05 if surface_type == "settings_form" and "settings_" in signal else 0.0
        items.append({
            "id": f"ship:{signal}",
            "kind": "ship_challenge",
            "title": f"Ship challenge: {signal}",
            "roi_score": _roi_for_kind("ship_challenge", priority=0.8, surface_boost=boost),
            "why_now": "Open Ship Council challenge before claim-done",
            "suggested_capability": "design_review",
            "surface_type": surface_type,
            "signal": signal,
        })

    for gap in open_evidence_items or []:
        did = str(gap.get("decision_id") or "evidence")
        items.append({
            "id": f"evidence:{did}",
            "kind": "evidence_gap",
            "title": f"Close evidence plan: {did}",
            "roi_score": _roi_for_kind("evidence_gap", priority=0.75),
            "why_now": "Evidence-plan item still open (complete, skip with reason, or supersede)",
            "suggested_capability": gap.get("capability_id"),
            "surface_type": surface_type,
            "decision_id": did,
        })

    if residue_required:
        items.append({
            "id": "residue:scan",
            "kind": "residue",
            "title": "Residue scan — remeasure before ship clear",
            "roi_score": _roi_for_kind("residue", priority=0.88),
            "why_now": "One-pass residue required (thin coverage or dense UI with empty ship)",
            "suggested_capability": "design_snapshot",
            "surface_type": surface_type,
        })

    # Dedupe by id keeping higher ROI
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        key = str(item["id"])
        prev = merged.get(key)
        if prev is None or float(item["roi_score"]) > float(prev["roi_score"]):
            merged[key] = item
    ranked = sorted(merged.values(), key=lambda i: (-float(i["roi_score"]), str(i["id"])))
    ranked = _align_ranked_with_gate(ranked, gate_next_capability)
    ranked = ranked[:8]
    top = ranked[0] if ranked else None
    return {
        "top": top,
        "items": ranked,
        "answered_next": "What is the single highest-impact thing to do next?",
    }
