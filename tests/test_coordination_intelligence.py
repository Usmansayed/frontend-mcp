"""Unit tests for Coordination Intelligence P1 — PSM Runtime and planning layer."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

yaml = pytest.importorskip("yaml")

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.planning.capability_router import CapabilityRouter
from navigation.coordination_intelligence.planning.playbook_selector import PlaybookSelector
from navigation.coordination_intelligence.planning.step_compiler import StepCompiler
from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.core.envelope import make_envelope


@pytest.fixture
def bundle() -> RuntimeArtifactBundle:
    return RuntimeArtifactBundle.load()


@pytest.fixture
def service() -> CoordinationIntelligenceService:
    return CoordinationIntelligenceService()


@pytest.mark.unit
def test_runtime_artifacts_load(bundle: RuntimeArtifactBundle) -> None:
    assert len(bundle.capability_by_id) == 32
    assert "invalid_before_valid.form" in bundle.playbook_by_id
    assert bundle.tool_to_capability["perception_probe_form"] == "form_probe"


@pytest.mark.unit
def test_cluster_signature_includes_capability_posture(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        playbook_id="invalid_before_valid.form",
        cluster_id="cluster.feature.form_pipeline",
        session_id="sess_1",
        website_url="http://localhost:5173",
    )
    sig1 = psm.situation.cluster_signature
    svc.briefing(psm.episode_id)
    sig2 = svc.runtime.require(psm.episode_id).situation.cluster_signature
    assert len(sig1) == 64
    assert sig2 != "0" * 64


@pytest.mark.unit
def test_capability_router_gates_missing_session(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(playbook_id="invalid_before_valid.form")
    psm.artifacts.session_id = None
    router = CapabilityRouter(bundle)
    gate = router.gate(psm, "form_probe")
    assert not gate.allowed
    assert gate.gather_first == "browser_session_manage"


@pytest.mark.unit
def test_step_compiler_resolves_session_id(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        playbook_id="invalid_before_valid.form",
        session_id="sess_abc",
    )
    compiler = StepCompiler(bundle)
    compiled = compiler.compile_step(
        psm,
        semantic_action="probe_form_rules",
        capability_id="form_probe",
        step_id="probe",
    )
    assert compiled is not None
    assert compiled.tools[0]["tool"] == "perception_probe_form"
    assert compiled.tools[0]["arguments"]["session_id"] == "sess_abc"


@pytest.mark.unit
def test_playbook_selector_sequence_constraint(bundle: RuntimeArtifactBundle) -> None:
    selector = PlaybookSelector(bundle)
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        playbook_id="invalid_before_valid.form",
        session_id="s1",
    )
    step = selector.current_step(psm)
    assert step is not None
    assert step["step_id"] == "probe"

    selector.mark_step_complete(psm, "probe")
    selector.mark_step_complete(psm, "invalid_path")
    step = selector.current_step(psm)
    assert step is not None
    assert step["step_id"] == "valid_path"


@pytest.mark.unit
def test_apply_envelope_updates_psm_not_raw(service: CoordinationIntelligenceService) -> None:
    psm = service.episode_start(
        playbook_id="invalid_before_valid.form",
        session_id="sess_1",
        website_url="http://localhost:5173",
    )
    envelope = make_envelope(
        "perception_probe_form",
        ok=True,
        session_id="sess_1",
        data={"agent_summary": {"blocking": [], "advisory": []}},
    )
    service.apply_envelope(psm.episode_id, envelope, capability_id="form_probe")
    updated = service.runtime.require(psm.episode_id)
    assert updated.evidence.domains["ui_runtime"].posture in ("partial", "known")
    assert "probe" in updated.episode.completed_step_ids


@pytest.mark.unit
def test_invalid_before_valid_form_playbook_e2e(service: CoordinationIntelligenceService) -> None:
    """Coordinator drives invalid_before_valid.form through PSM Runtime only."""
    psm = service.episode_start(
        playbook_id="invalid_before_valid.form",
        cluster_id="cluster.feature.form_pipeline",
        session_id="sess_form",
        website_url="http://localhost:5173/form",
    )
    episode_id = psm.episode_id

    b1 = service.briefing(episode_id)
    assert b1.suggested_capability == "form_probe"
    assert b1.suggested_semantic_action == "probe_form_rules"
    assert b1.compiled_step is not None
    assert b1.compiled_step.tools[0]["tool"] == "perception_probe_form"

    service.apply_envelope(
        episode_id,
        make_envelope(
            "perception_probe_form",
            ok=True,
            session_id="sess_form",
            data={"agent_summary": {"blocking": [], "advisory": []}},
        ),
        capability_id="form_probe",
    )

    b2 = service.briefing(episode_id)
    assert b2.suggested_capability == "browser_verify"
    assert b2.suggested_semantic_action == "run_invalid_submit_check"

    service.apply_envelope(
        episode_id,
        make_envelope(
            "perception_verify",
            ok=True,
            session_id="sess_form",
            data={"agent_summary": {"blocking": [], "advisory": []}},
        ),
        capability_id="browser_verify",
    )

    b3 = service.briefing(episode_id)
    assert b3.suggested_semantic_action == "run_valid_submit_check"

    service.apply_envelope(
        episode_id,
        make_envelope(
            "perception_verify",
            ok=True,
            session_id="sess_form",
            data={"agent_summary": {"blocking": [], "advisory": []}},
        ),
        capability_id="browser_verify",
    )

    b4 = service.briefing(episode_id)
    assert b4.stop_reason == "playbook_complete"
    assert b4.suggested_capability is None

    final = service.runtime.require(episode_id)
    assert final.episode.completed_step_ids == ["probe", "invalid_path", "valid_path"]
    assert final.episode.verification_status == "passed"


@pytest.mark.unit
def test_coordinator_mcp_handlers() -> None:
    import asyncio

    from navigation.mcp.coordination_handlers import (
        handle_coordinator_apply_envelope,
        handle_coordinator_briefing,
        handle_coordinator_episode_start,
    )

    start = asyncio.run(
        handle_coordinator_episode_start(
            {
                "playbook_id": "invalid_before_valid.form",
                "session_id": "s1",
                "website_url": "http://localhost:5173",
            }
        )
    )
    assert start["ok"] is True
    episode_id = start["data"]["episode_id"]
    assert start["data"]["coordinator_briefing"]["suggested_capability"] == "form_probe"

    briefing = asyncio.run(handle_coordinator_briefing({"episode_id": episode_id}))
    assert briefing["ok"] is True
    assert "psm" in briefing["data"]

    applied = asyncio.run(
        handle_coordinator_apply_envelope(
            {
                "episode_id": episode_id,
                "envelope": make_envelope(
                    "perception_probe_form",
                    ok=True,
                    session_id="s1",
                    data={"agent_summary": {"blocking": [], "advisory": []}},
                ),
                "capability_id": "form_probe",
            }
        )
    )
    assert applied["ok"] is True
    assert "probe" in applied["data"]["psm"]["episode"]["completed_step_ids"]
