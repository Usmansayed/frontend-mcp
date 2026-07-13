"""Tests for R12 Situation Policy Catalog and Engineering Investment allocator."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

yaml = pytest.importorskip("yaml")

from navigation.coordination_intelligence.artifacts.loader import (
    RuntimeArtifactBundle,
    load_runtime_artifacts,
)
from navigation.coordination_intelligence.planning.effort_allocator import evaluate_allocation
from navigation.coordination_intelligence.planning.situation_policy import (
    derive_discriminators,
    match_policy,
)
from navigation.coordination_intelligence.service import CoordinationIntelligenceService


@pytest.fixture
def bundle() -> RuntimeArtifactBundle:
    load_runtime_artifacts.cache_clear()
    return RuntimeArtifactBundle.load()


@pytest.mark.unit
def test_r12_catalog_loads(bundle: RuntimeArtifactBundle) -> None:
    catalog = bundle.situation_policy_catalog
    assert catalog.get("schema_version") == "1.0"
    assert len(catalog.get("policies") or []) >= 8
    assert "inspiration_workflow" in (catalog.get("cost_classes") or {})


@pytest.mark.unit
def test_surgical_forbids_inspiration(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        playbook_id="observe_reason_act_verify.loop",
        session_id="sess_s",
        intent="fix one button padding from 14px to 15px",
    )
    disc = derive_discriminators(psm)
    assert disc["task_scope"] == "surgical"
    policy = match_policy(bundle.situation_policy_catalog, disc)
    assert policy["policy_id"] == "surgical.low"
    decision = evaluate_allocation(psm, bundle.situation_policy_catalog, capability_id="inspiration_workflow")
    assert decision.recommend is False
    assert decision.stop_reason in (
        "policy_forbid_capability",
        "impact_ceiling_suppresses_heavy",
        "roi_below_threshold",
    )


@pytest.mark.unit
def test_design_driven_allows_inspiration(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        playbook_id="observe_reason_act_verify.loop",
        session_id="sess_d",
        intent="build a new landing page marketing site from scratch",
        lifecycle_stage="S03_design",
        project_maturity="M2",
    )
    # Force early stage for policy match
    psm.situation.lifecycle_stage = "S03_design"
    psm.situation.project_maturity = "M2"
    disc = derive_discriminators(psm)
    assert disc["task_scope"] in ("design_driven", "redesign")
    decision = evaluate_allocation(
        psm, bundle.situation_policy_catalog, capability_id="inspiration_workflow"
    )
    assert decision.recommend is True
    assert decision.eqg >= 5


@pytest.mark.unit
def test_briefing_includes_investment_rationale(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        playbook_id="observe_reason_act_verify.loop",
        session_id="sess_b",
        cluster_id="cluster.discovery.bootstrap",
    )
    briefing = svc.briefing(psm.episode_id)
    data = briefing.to_dict()
    assert data.get("routing_rationale")
    assert data.get("investment")
    assert "policy_id" in data["investment"]
    assert "budget_remaining" in data["investment"]


@pytest.mark.unit
def test_no_research_leaf_ids_in_r12(bundle: RuntimeArtifactBundle) -> None:
    import re

    text = yaml.dump(bundle.situation_policy_catalog)
    assert not re.search(r"landing\.S03\.", text)
    assert not re.search(r"marketing\.S11\.", text)
