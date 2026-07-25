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
def test_session_start_without_intent_advises(bridge: CoordinatorBridge) -> None:
    out = bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_no_intent",
            url="http://localhost:5173",
        ),
    )
    advisory = out["agent_summary"].get("advisory") or []
    assert any("intent_missing" in str(a) for a in advisory)
    assert out["agent_summary"].get("coordinator")
    assert out["agent_summary"].get("recommended_next")

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
def test_structural_strategy_promotes_required_resource_and_readiness_gate(
    bridge: CoordinatorBridge,
) -> None:
    out = bridge.process(
        "perception_session_start",
        {
            "base_url": "http://localhost:5173",
            "intent": "build a new SaaS analytics dashboard",
        },
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_structural_contract",
            url="http://localhost:5173",
        ),
    )
    coordinator = out["data"]["coordinator"]
    summary = out["agent_summary"]
    assert coordinator["implementation_gate"]["state"] == "blocked"
    assert coordinator["recommended_resource"] == "perception://inspiration-guide"
    assert summary["implementation_gate"] == coordinator["implementation_gate"]
    assert summary["required_resource"] == "perception://inspiration-guide"
    assert summary["coordinator"]["episode_id"] == coordinator["episode_id"]
    assert summary.get("recommended_next")


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


@pytest.mark.unit
def test_new_session_start_does_not_reuse_prior_episode(bridge: CoordinatorBridge) -> None:
    """Unbound session_id must not fall through to project/default (stale episode leak)."""
    first = bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173", "intent": "first task"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_first",
            url="http://localhost:5173",
        ),
    )
    ep1 = first["data"]["coordinator"]["episode_id"]
    # Seed stale checklist residue on ep1
    psm1 = bridge.service.runtime.require(ep1)
    psm1.artifacts.persistent["section_checklist"] = {
        "required": True,
        "sections": [{"section_id": "aside:0", "observed": True, "verified": False}],
        "complete": False,
    }
    bridge.service.runtime.save(psm1)

    second = bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173", "intent": "fresh redesign episode"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_second",
            url="http://localhost:5173",
        ),
    )
    ep2 = second["data"]["coordinator"]["episode_id"]
    assert ep2 != ep1
    psm2 = bridge.service.runtime.require(ep2)
    assert (psm2.artifacts.persistent or {}).get("section_checklist") in (None, {})


@pytest.mark.unit
def test_unbound_session_resolve_does_not_return_default() -> None:
    from navigation.coordination_intelligence.integration.episode_binding import (
        EpisodeBindingStore,
    )

    store = EpisodeBindingStore()
    store.bind_project("default", "ep_old")
    assert store.resolve(session_id="sess_new") is None
    assert store.resolve(project_id="default") == "ep_old"
    assert store.resolve_session("sess_new") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coordinator_episode_start_binds_project_for_sessionless_tools() -> None:
    from navigation.coordination_intelligence.integration.bridge import get_coordinator_bridge
    from navigation.mcp.coordination_handlers import handle_coordinator_episode_start

    bridge = get_coordinator_bridge()
    bridge._bindings.clear()
    # Stale default episode via session_start
    bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_bind_a",
            url="http://localhost:5173",
        ),
    )
    old_default = bridge._bindings.resolve(project_id="default")

    out = await handle_coordinator_episode_start(
        {
            "project_id": "default",
            "session_id": "sess_bind_b",
            "intent": "fresh episode for resolve_route",
            "website_url": "http://localhost:5173",
        }
    )
    new_ep = out["data"]["episode_id"]
    assert new_ep != old_default
    assert bridge._bindings.resolve(project_id="default") == new_ep
    assert bridge._bindings.resolve(session_id="sess_bind_b") == new_ep
    # Session-less path (project only) now hits the fresh episode
    assert bridge._bindings.resolve(session_id=None, project_id="default") == new_ep


@pytest.mark.unit
def test_failed_design_review_does_not_mint_orphan_episode(bridge: CoordinatorBridge) -> None:
    """Unbound session_id on failed ship must not create ep_* or rebind project/default."""
    live = bridge.process(
        "perception_session_start",
        {"base_url": "http://localhost:5173", "intent": "live redesign"},
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="sess_live",
            url="http://localhost:5173",
        ),
    )
    live_ep = live["data"]["coordinator"]["episode_id"]
    before_default = bridge._bindings.resolve(project_id="default")
    assert before_default == live_ep
    before_count = len(bridge.service.runtime._episodes)

    out = bridge.process(
        "perception_design_review",
        {"session_id": "sess_dead_stale", "mode": "ship", "snapshot_id": "snap_gone"},
        make_envelope(
            "perception_design_review",
            ok=False,
            session_id="sess_dead_stale",
            error="unknown snapshot_id: snap_gone",
            degraded=["registry_lost_rebootstrap"],
        ),
    )
    assert out.get("ok") is False
    assert bridge._bindings.resolve(session_id="sess_dead_stale") is None
    assert bridge._bindings.resolve(project_id="default") == live_ep
    assert len(bridge.service.runtime._episodes) == before_count
    assert bridge._bindings.resolve(session_id="sess_live") == live_ep
