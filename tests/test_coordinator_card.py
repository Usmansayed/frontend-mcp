# tests/test_coordinator_card.py
from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.coordinator_card import (
    build_coordinator_card,
    strategy_fingerprint,
)

@pytest.mark.unit
def test_build_coordinator_card_schema_and_slim_keys():
    strategy = {
        "host_action": "BLOCKED: read perception://getting-started",
        "implementation_gate": {
            "state": "blocked",
            "next_required_capability": "inspiration_workflow",
            "prohibited_actions": ["claim_complete"],
        },
        "episode_confidence": {"score": 0.2, "band": "low"},
        "episode_portfolio": {
            "paid": [{"family": "verify"}],
            "unpaid": [{"family": "inspiration"}, {"family": "snapshot"}],
        },
        "evidence_quality_alerts": ["EVIDENCE THIN: last snapshot advanced"],
        "recommended_resource": "perception://getting-started",
    }
    card = build_coordinator_card(
        episode_id="ep1",
        strategy=strategy,
        suggested_capability="inspiration_workflow",
        suggested_semantic_action="follow_gate:inspiration_workflow",
        stop_reason=None,
    )
    assert card["schema"] == "coordinator_card.v1"
    assert card["episode_id"] == "ep1"
    assert card["integrated"] is True
    assert card["host_action"].startswith("BLOCKED")
    assert card["gate"]["state"] == "blocked"
    assert card["implementation_gate"]["state"] == "blocked"  # alias
    assert "briefing" not in card
    assert "evidence_plan" not in card
    assert card["portfolio"]["paid"] == ["verify"]
    assert card["portfolio"]["unpaid"] == ["inspiration", "snapshot"]
    assert card["evidence_quality_alerts"][0].startswith("EVIDENCE THIN")
    assert card["confidence"]["band"] == "low"


@pytest.mark.unit
def test_strategy_fingerprint_stable_for_same_psm():
    psm = ProjectSituationModel()
    psm.evidence.capability_ledger["design_snapshot"] = {
        "status": "succeeded",
        "advancement_eligible": True,
        "quality": {"thin": True, "revision_required": False},
    }
    psm.episode.verification_status = "passed"
    a = strategy_fingerprint(psm)
    b = strategy_fingerprint(psm)
    assert a == b
    assert isinstance(a, str) and len(a) >= 8


@pytest.mark.unit
def test_strategy_fingerprint_changes_when_thin_flips() -> None:
    psm = ProjectSituationModel()
    psm.evidence.capability_ledger["design_snapshot"] = {
        "status": "succeeded",
        "advancement_eligible": True,
        "quality": {"thin": True},
    }
    before = strategy_fingerprint(psm)
    psm.evidence.capability_ledger["design_snapshot"]["quality"]["thin"] = False
    after = strategy_fingerprint(psm)
    assert before != after


@pytest.mark.unit
def test_strategy_fingerprint_changes_when_sections_complete() -> None:
    psm = ProjectSituationModel()
    psm.episode.retry_counters["section_checklist"] = {
        "complete": False,
        "sections": [
            {"section_id": "main:0", "observed": True, "verified": False},
        ],
    }
    before = strategy_fingerprint(psm)
    psm.episode.retry_counters["section_checklist"]["complete"] = True
    psm.episode.retry_counters["section_checklist"]["sections"][0]["verified"] = True
    after = strategy_fingerprint(psm)
    assert before != after


@pytest.mark.unit
def test_build_episode_card_adds_what_matters_and_schema() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_episode_card,
    )

    strategy = {
        "host_action": "BLOCKED: gather inspiration",
        "what_matters_now": ["Next (ROI): Bind design reference"],
        "surface_type": "dashboard",
        "influence_level": "structural",
        "implementation_gate": {
            "state": "blocked",
            "next_required_capability": "inspiration_workflow",
            "prohibited_actions": ["claim_complete"],
        },
        "episode_confidence": {"score": 0.1, "band": "low"},
        "episode_portfolio": {"paid": [], "unpaid": [{"family": "inspiration"}]},
        "evidence_quality_alerts": [],
        "recommended_resource": "perception://getting-started",
    }
    card = build_episode_card(episode_id="ep2", strategy=strategy)
    assert card["schema"] == "episode_card.v1"
    assert card["what_matters"].startswith("Next (ROI)")
    assert card["surface_type"] == "dashboard"
    assert card["influence_level"] == "structural"
    assert card["gate"]["state"] == "blocked"
    assert "briefing" not in card


@pytest.mark.unit
def test_enrich_envelope_surfaces_episode_card_on_agent_summary() -> None:
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService
    from navigation.core.envelope import make_envelope

    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_ep_card",
        intent="redesign Meridian analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    out = service.on_tool_envelope(
        psm.episode_id,
        "perception_build_design_snapshot",
        {"session_id": "sess_ep_card"},
        make_envelope(
            "perception_build_design_snapshot",
            ok=True,
            session_id="sess_ep_card",
            data={"snapshot_id": "s_ep"},
        ),
    )
    card = (out.get("agent_summary") or {}).get("episode_card") or {}
    assert card.get("schema") == "episode_card.v1"
    assert card.get("what_matters")
    assert (out.get("data") or {}).get("episode_card", {}).get("schema") == "episode_card.v1"
    assert (out.get("data") or {}).get("coordinator", {}).get("schema") == "coordinator_card.v1"


@pytest.mark.unit
def test_enrich_envelope_uses_coordinator_card_v1_not_full_briefing() -> None:
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService
    from navigation.core.envelope import make_envelope

    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_card_v1",
        intent="redesign Meridian analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    envelope = make_envelope(
        "perception_build_design_snapshot",
        ok=True,
        session_id="sess_card_v1",
        data={"snapshot_id": "thin_card"},
    )
    out = service.on_tool_envelope(
        psm.episode_id,
        "perception_build_design_snapshot",
        {"session_id": "sess_card_v1"},
        envelope,
    )
    card = (out.get("data") or {}).get("coordinator") or {}
    assert card.get("schema") == "coordinator_card.v1"
    assert "briefing" not in card
    assert "evidence_plan" not in card
    assert "psm_summary" not in card
    agent_summary = out.get("agent_summary") or {}
    assert agent_summary.get("engineering_strategy") or (out.get("data") or {}).get(
        "engineering_strategy"
    )


@pytest.mark.unit
def test_compile_skipped_when_fingerprint_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    from navigation.coordination_intelligence import service as service_mod
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService

    calls = {"n": 0}
    real = service_mod.compile_engineering_strategy

    def wrapped(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(service_mod, "compile_engineering_strategy", wrapped)
    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_fp_skip",
        intent="redesign Meridian analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    psm = service.runtime.require(psm.episode_id)
    first = calls["n"]
    assert first >= 1
    service._compile_engineering_strategy(psm)
    service._compile_engineering_strategy(psm)
    assert calls["n"] == first
