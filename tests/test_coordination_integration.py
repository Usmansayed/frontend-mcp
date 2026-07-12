"""P2 integration — invisible coordinator behind MCP tool envelopes."""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.integration.bridge import (
    CoordinatorBridge,
    coordinator_enabled,
    process_tool_envelope,
)
from navigation.coordination_intelligence.planning.cluster_resolver import ClusterResolver
from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.core.envelope import make_envelope


@pytest.fixture
def bridge() -> CoordinatorBridge:
    return CoordinatorBridge()


@pytest.mark.unit
def test_coordinator_disabled_preserves_envelope_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COORDINATION_DISABLED", "1")
    assert coordinator_enabled() is False
    env = make_envelope("perception_health", ok=True, url="http://localhost:5173")
    original = copy.deepcopy(env)
    out = process_tool_envelope("perception_health", {"url": "http://localhost:5173"}, env)
    assert out == original
    assert "coordinator" not in out.get("data", {})


@pytest.mark.unit
def test_session_start_auto_creates_psm_episode(bridge: CoordinatorBridge) -> None:
    env = make_envelope(
        "perception_session_start",
        ok=True,
        session_id="sess_auto",
        url="http://localhost:5173/form",
        data={"session_id": "sess_auto", "base_url": "http://localhost:5173/form"},
    )
    out = bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173/form"},
        env,
    )
    assert out["ok"] is True
    coord = out["data"]["coordinator"]
    assert coord["integrated"] is True
    episode_id = coord["episode_id"]
    psm = bridge.service.get_psm(episode_id)
    assert psm["artifacts"]["session_id"] == "sess_auto"
    assert psm["artifacts"]["website_url"] == "http://localhost:5173/form"


@pytest.mark.unit
def test_tool_envelope_adds_coordinator_without_breaking_contract(bridge: CoordinatorBridge) -> None:
    bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_contract",
            url="http://localhost:5173",
        ),
    )
    env = make_envelope(
        "perception_probe_form",
        ok=True,
        session_id="sess_contract",
        data={"agent_summary": {"blocking": [], "advisory": []}},
    )
    out = bridge.process("perception_probe_form", {"session_id": "sess_contract"}, env)
    assert out["tool"] == "perception_probe_form"
    assert out["ok"] is True
    assert out["session_id"] == "sess_contract"
    assert "coordinator" in out["data"]
    assert out["data"]["agent_summary"]["blocking"] == []


@pytest.mark.unit
def test_cluster_resolver_infers_form_pipeline_from_probe(bridge: CoordinatorBridge) -> None:
    bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_cluster",
            url="http://localhost:5173",
        ),
    )
    out = bridge.process(
        "perception_probe_form",
        {"session_id": "sess_cluster"},
        make_envelope(
            "perception_probe_form",
            ok=True,
            session_id="sess_cluster",
            data={"agent_summary": {"blocking": [], "advisory": []}},
        ),
    )
    episode_id = out["data"]["coordinator"]["episode_id"]
    psm = bridge.service.get_psm(episode_id)
    assert psm["situation"]["cluster_id"] == "cluster.feature.form_pipeline"
    assert psm["episode"]["active_playbook_id"] == "invalid_before_valid.form"
    assert "probe" in psm["episode"]["completed_step_ids"]


@pytest.mark.unit
def test_invisible_form_playbook_e2e_without_coordinator_tools(bridge: CoordinatorBridge) -> None:
    """Simulate AGENT_GUIDE form flow using only standard MCP tools + bridge."""
    bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173/form"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_form_e2e",
            url="http://localhost:5173/form",
        ),
    )

    probe_out = bridge.process(
        "perception_probe_form",
        {"session_id": "sess_form_e2e"},
        make_envelope(
            "perception_probe_form",
            ok=True,
            session_id="sess_form_e2e",
            data={"agent_summary": {"blocking": [], "advisory": []}},
        ),
    )
    assert probe_out["data"]["coordinator"]["suggested_semantic_action"] == "run_invalid_submit_check"

    invalid_out = bridge.process(
        "perception_verify",
        {"session_id": "sess_form_e2e", "criteria": {"text_contains": ["required"]}},
        make_envelope(
            "perception_verify",
            ok=True,
            session_id="sess_form_e2e",
            data={"agent_summary": {"blocking": [], "advisory": []}},
        ),
    )
    assert invalid_out["data"]["coordinator"]["suggested_semantic_action"] == "run_valid_submit_check"

    valid_out = bridge.process(
        "perception_verify",
        {"session_id": "sess_form_e2e", "criteria": {"text_absent": ["required"]}},
        make_envelope(
            "perception_verify",
            ok=True,
            session_id="sess_form_e2e",
            data={"agent_summary": {"blocking": [], "advisory": []}},
        ),
    )
    assert valid_out["data"]["coordinator"]["stop_reason"] == "playbook_complete"

    episode_id = valid_out["data"]["coordinator"]["episode_id"]
    psm = bridge.service.get_psm(episode_id)
    assert psm["episode"]["completed_step_ids"] == ["probe", "invalid_path", "valid_path"]
    assert psm["episode"]["verification_status"] == "passed"


@pytest.mark.unit
def test_governor_blocks_invalid_before_valid_sequence() -> None:
    svc = CoordinationIntelligenceService()
    psm = svc.episode_start(
        playbook_id="invalid_before_valid.form",
        session_id="sess_seq",
    )
    psm.episode.completed_step_ids = ["probe"]
    psm.episode.active_step_id = "valid_path"

    advanced = svc._governor.advance_if_satisfied(
        psm,
        capability_id="browser_verify",
        envelope=make_envelope("perception_verify", ok=True, session_id="sess_seq"),
    )
    assert advanced is False
    assert "valid_path" not in psm.episode.completed_step_ids


@pytest.mark.unit
def test_cluster_resolver_never_uses_research_state_ids() -> None:
    resolver = ClusterResolver(CoordinationIntelligenceService().runtime.bundle)
    svc = CoordinationIntelligenceService()
    psm = svc.episode_start(session_id="s1")
    psm.situation.leaf_hint = "saas.S05.new_feature.form_validation.v1"
    resolver.resolve(psm)
    assert psm.situation.cluster_id.startswith("cluster.")
    assert not psm.situation.cluster_id.startswith("saas.")


@pytest.mark.unit
def test_process_tool_envelope_module_entrypoint() -> None:
    os.environ.pop("COORDINATION_DISABLED", None)
    env = make_envelope("perception_health", ok=True, url="http://localhost:5173")
    out = process_tool_envelope("perception_health", {}, env)
    assert out["ok"] is True
