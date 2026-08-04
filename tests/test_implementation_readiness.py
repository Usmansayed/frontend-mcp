"""Runtime governance for evidence-driven frontend implementation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.core.envelope import make_envelope


def _structural_episode(service: CoordinationIntelligenceService):
    return service.episode_start(
        session_id="sess_readiness",
        intent="build a new SaaS analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )


@pytest.mark.unit
def test_failed_inspiration_is_evidence_failure_and_keeps_implementation_blocked() -> None:
    service = CoordinationIntelligenceService()
    psm = _structural_episode(service)

    service.on_tool_envelope(
        psm.episode_id,
        "perception_inspiration_collect",
        {"session_id": "sess_readiness"},
        make_envelope(
            "perception_inspiration_collect",
            ok=False,
            session_id="sess_readiness",
            error="image blobs could not be materialized",
        ),
    )

    updated = service.runtime.require(psm.episode_id)
    outcome = updated.evidence.capability_ledger["inspiration_workflow"]
    gate = updated.briefing.engineering_strategy["implementation_gate"]

    assert outcome["status"] == "failed"
    assert outcome["failure_reason"] == "image blobs could not be materialized"
    assert gate["state"] == "blocked"
    assert "design_reference" in gate["blocking_decisions"]
    assert gate["next_required_capability"] == "browser_observe"
    assert "broad_visual_implementation" in gate["prohibited_actions"]


@pytest.mark.unit
def test_noop_evidence_does_not_advance_matching_playbook_capability() -> None:
    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_noop",
        playbook_id="discover_collect_cleanup.inspiration_resource",
        cluster_id="cluster.design.reference_gathering",
    )
    psm.episode.active_playbook_id = "discover_collect_cleanup.inspiration_resource"
    psm.episode.active_step_id = "discover"
    psm.episode.completed_step_ids = []
    service.runtime.save(psm)

    envelope = make_envelope(
        "perception_inspiration_session_end",
        ok=True,
        session_id="sess_noop",
        data={
            "coordination_evidence": {
                "outcome": "noop",
                "operation": "cleanup",
                "advancement_eligible": False,
            }
        },
    )
    assert service._governor.evaluate_step_advancement(
        psm,
        capability_id="inspiration_workflow",
        envelope=envelope,
    ) is False


@pytest.mark.unit
def test_image_urls_without_materialized_refs_remain_provisional() -> None:
    service = CoordinationIntelligenceService()
    psm = _structural_episode(service)
    out = service.on_tool_envelope(
        psm.episode_id,
        "perception_inspiration_collect",
        {"session_id": "sess_readiness"},
        make_envelope(
            "perception_inspiration_collect",
            ok=True,
            session_id="sess_readiness",
            data={
                "inspiration_collection": {
                    "hits": [
                        {"preview_url": f"https://cdn.example/{index}.jpg"}
                        for index in range(3)
                    ]
                },
                "agent_summary": {"blocking": [], "advisory": []},
            },
        ),
    )
    outcome = out["data"]["coordination_evidence"]
    gate = out["data"]["coordinator"]["implementation_gate"]
    assert outcome["status"] == "provisional"
    assert outcome["advancement_eligible"] is False
    assert outcome["quality"]["usable_image_refs"] == 0
    assert gate["state"] == "blocked"


@pytest.mark.unit
def test_redesign_prefers_snapshot_over_inspiration_gate() -> None:
    """Live redesign must tip gate.next to design_snapshot, not gallery inspiration."""
    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_redesign_route",
        intent=(
            "Redesign the Pulse Maze sandbox dashboard home for clearer hierarchy: "
            "one primary focus, less equal-weight KPI noise"
        ),
        lifecycle_stage="S05_implementation",
        project_maturity="M2",
    )
    strategy = psm.briefing.engineering_strategy
    assert strategy is not None
    assert strategy["task_scope"] == "redesign"
    gate = strategy["implementation_gate"]
    assert gate["next_required_capability"] == "design_snapshot"
    assert gate["required_resource"] == "perception://redesign-workflow"
    assert strategy["recommended_resource"] == "perception://redesign-workflow"
    rec = strategy.get("recommended_evidence") or {}
    assert rec.get("capability_id") == "design_snapshot"
    unpaid = [
        u["family"]
        for u in (strategy.get("episode_portfolio") or {}).get("unpaid") or []
    ]
    assert "snapshot" in unpaid
    assert "inspiration" not in unpaid
    assert "inspiration_workflow" not in (strategy.get("host_action") or "")
    assert "design_snapshot" in (strategy.get("host_action") or "")


@pytest.mark.unit
def test_greenfield_still_routes_inspiration_first() -> None:
    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_greenfield_route",
        intent="build a new SaaS analytics dashboard from scratch",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    gate = psm.briefing.engineering_strategy["implementation_gate"]
    assert gate["next_required_capability"] == "inspiration_workflow"
    assert gate["required_resource"] == "perception://inspiration-guide"


@pytest.mark.unit
def test_usable_component_selection_resolves_foundation_evidence() -> None:
    service = CoordinationIntelligenceService()
    psm = _structural_episode(service)
    out = service.on_tool_envelope(
        psm.episode_id,
        "perception_select_component_foundation",
        {"session_id": "sess_readiness"},
        make_envelope(
            "perception_select_component_foundation",
            ok=True,
            session_id="sess_readiness",
            data={
                "foundation_selection": {
                    "chosen": {"candidate_id": "shadcn-card", "name": "Card"}
                },
                "agent_summary": {"blocking": [], "advisory": []},
            },
        ),
    )
    updated = service.runtime.require(psm.episode_id)
    assert out["data"]["coordination_evidence"]["status"] == "succeeded"
    assert updated.evidence.domains["design_system"].posture == "known"
    decisions = {
        item["decision_id"]
        for item in updated.briefing.engineering_strategy["unresolved_decisions"]
    }
    assert "component_foundation" not in decisions


@pytest.mark.unit
def test_component_plan_does_not_resolve_foundation() -> None:
    """Plan pays progress but foundation stays open and next tips select (Test 9)."""
    from navigation.coordination_intelligence.models import ProjectSituationModel
    from navigation.coordination_intelligence.planning.episode_portfolio import (
        compile_episode_portfolio,
    )
    from navigation.coordination_intelligence.planning.evidence_plan_status import (
        get_plan_status_map,
        open_evidence_plan_items,
    )
    from navigation.coordination_intelligence.planning.implementation_readiness import (
        compile_implementation_readiness,
    )

    psm = ProjectSituationModel()
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    psm.evidence.capability_ledger["component_search_plan"] = {
        "status": "succeeded",
        "advancement_eligible": True,
    }
    unresolved = [
        {
            "decision_id": "component_foundation",
            "title": "Component foundation selection",
            "priority": 9,
            "structural": True,
            "resolving_capabilities": ["component_search_plan", "component_select"],
        }
    ]
    gate, evidence_plan, _ = compile_implementation_readiness(
        psm,
        influence_level="structural",
        task_scope="design_driven",
        unresolved_decisions=unresolved,
    )
    assert evidence_plan
    assert evidence_plan[0]["capability_id"] == "component_select"
    assert "plan alone" in str(evidence_plan[0].get("completion_criteria") or "").lower()
    open_items = open_evidence_plan_items(psm, evidence_plan)
    assert open_items
    assert open_items[0]["capability_id"] == "component_select"
    status = get_plan_status_map(psm)
    assert (status.get("component_foundation") or {}).get("state") not in (
        "completed",
        "skipped",
        "superseded",
    )
    assert gate["next_required_capability"] == "component_select"
    portfolio = compile_episode_portfolio(
        psm=psm,
        unresolved_decisions=unresolved,
        implementation_gate=gate,
        initiative_on=True,
        task_scope="design_driven",
    )
    component_unpaid = [u for u in portfolio["unpaid"] if u.get("family") == "component"]
    assert component_unpaid
    assert "not selected" in str(component_unpaid[0].get("reason") or "").lower()
    assert component_unpaid[0].get("suggested") == "perception_select_component_foundation"
