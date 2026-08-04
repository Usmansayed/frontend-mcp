"""Regression: verify-fail must not clear Done ladder on design episodes."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel, _utc_now
from navigation.coordination_intelligence.planning.cluster_resolver import ClusterResolver
from navigation.coordination_intelligence.planning.engineering_strategy import (
    compile_engineering_strategy,
)
from navigation.coordination_intelligence.planning.implementation_readiness import (
    compile_implementation_readiness,
)
from navigation.coordination_intelligence.planning.section_checklist import (
    build_section_verify_assertions,
    seed_section_checklist_from_regions,
)
from navigation.coordination_intelligence.planning.situation_policy import (
    derive_discriminators,
    sticky_design_scope,
)
from navigation.coordination_intelligence.psm.normalize import apply_envelope
from navigation.coordination_intelligence.service import CoordinationIntelligenceService


@pytest.mark.unit
def test_verify_fail_does_not_collapse_design_episode_claim_gate() -> None:
    """DEBUG_ON_VERIFY_FAIL used to flip design_driven → debug and allow claim_complete."""
    bundle = load_runtime_artifacts()
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_collapse",
        intent="build a new SaaS analytics dashboard from scratch",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    assert sticky_design_scope(psm) == "design_driven"
    assert derive_discriminators(psm)["task_scope"] == "design_driven"

    psm.artifacts.snapshot_id = "snap_live"
    seed_section_checklist_from_regions(
        psm,
        [
            {"role": "aside", "label": "sidebar", "rect": {"w": 230, "h": 800}},
            {"role": "main", "rect": {"w": 900, "h": 800}},
        ],
    )

    # Simulate failed section verify (as live hard-sim did).
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_verify",
            "data": {
                "verified": False,
                "section_id": "aside:0",
                "reasons": ["js assertion failed"],
            },
        },
        bundle,
    )
    psm.episode.retry_counters["last_capability"] = "browser_verify"
    psm.episode.retry_counters["last_tool"] = "perception_verify"

    ClusterResolver(bundle).resolve(psm)
    disc = derive_discriminators(psm)
    assert disc["task_scope"] == "design_driven", disc
    assert "debug" not in (psm.situation.cluster_id or "") or sticky_design_scope(psm)

    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    gate = strategy["implementation_gate"]
    assert gate.get("section_checklist_required") is True
    assert "claim_complete" in gate["prohibited_actions"]
    assert "SECTION CHECKLIST" in (strategy.get("host_action") or "")
    assert not any("verify_passed_sufficient" in s for s in strategy.get("stop_conditions") or [])


@pytest.mark.unit
def test_debug_cluster_alone_does_not_override_sticky_design_scope() -> None:
    psm = ProjectSituationModel()
    psm.episode.intent_stack = [
        IntentFrame(intent="build a new landing page", pushed_at=_utc_now()),
    ]
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    psm.situation.cluster_id = "cluster.debug.signal_class"
    psm.episode.verification_status = "failed"
    assert derive_discriminators(psm)["task_scope"] == "design_driven"

    psm.artifacts.snapshot_id = "snap_x"
    seed_section_checklist_from_regions(psm, [{"role": "main", "rect": {"w": 800, "h": 600}}])
    gate, _, _ = compile_implementation_readiness(
        psm,
        influence_level="minimal",  # collapsed influence still must block claim
        task_scope="debug",  # even if caller passes debug, sticky in episode_needs wins
        unresolved_decisions=[],
    )
    # episode_needs_* uses sticky; claim still prohibited when checklist incomplete
    assert gate.get("section_checklist_required") is True
    assert "claim_complete" in gate["prohibited_actions"]


@pytest.mark.unit
def test_explicit_bug_intent_still_allows_debug_scope() -> None:
    psm = ProjectSituationModel()
    psm.episode.intent_stack = [
        IntentFrame(intent="fix login bug on dashboard", pushed_at=_utc_now()),
    ]
    psm.situation.cluster_id = "cluster.debug.signal_class"
    assert derive_discriminators(psm)["task_scope"] == "debug"


@pytest.mark.unit
def test_sidebar_section_assertions_accept_nav_not_only_aside() -> None:
    asserts = build_section_verify_assertions({"role": "aside", "section_id": "aside:0"})
    assert asserts
    assert "nav" in asserts[0]
    assert "aside" in asserts[0]
