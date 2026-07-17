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
