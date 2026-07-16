"""Tests for decision-centric Engineering Strategy compiler."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

yaml = pytest.importorskip("yaml")

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle, load_runtime_artifacts
from navigation.coordination_intelligence.planning.engineering_strategy import (
    compile_bootstrap_strategy,
    compile_engineering_strategy,
    surface_engineering_strategy,
)
from navigation.coordination_intelligence.service import CoordinationIntelligenceService


@pytest.fixture
def bundle() -> RuntimeArtifactBundle:
    load_runtime_artifacts.cache_clear()
    return RuntimeArtifactBundle.load()


@pytest.mark.unit
def test_greenfield_landing_structural_influence(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_landing",
        intent="build a new landing page marketing site from scratch",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    strategy = psm.briefing.engineering_strategy
    assert strategy is not None
    assert strategy["influence_level"] == "structural"
    assert strategy["task_scope"] in ("design_driven", "redesign")
    assert any(
        "hierarchy" in d["title"].lower() or "reference" in d["title"].lower()
        for d in strategy["unresolved_decisions"]
    )
    assert strategy["summary"].startswith("Design reference") or "unresolved" in strategy["summary"].lower()


@pytest.mark.unit
def test_hotfix_minimal_influence(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_hotfix",
        intent="production hotfix for broken login button",
        situation_class="hotfix",
    )
    strategy = psm.briefing.engineering_strategy
    assert strategy is not None
    assert strategy["influence_level"] == "minimal"
    assert strategy["engineering_phase"] == "hotfix_remediation"
    design_unresolved = [
        d for d in strategy["unresolved_decisions"] if d["decision_id"] == "design_reference"
    ]
    assert not design_unresolved


@pytest.mark.unit
def test_surgical_minimal_influence(bundle: RuntimeArtifactBundle) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_surgical",
        intent="fix one button padding from 14px to 15px",
    )
    strategy = psm.briefing.engineering_strategy
    assert strategy["influence_level"] == "minimal"


@pytest.mark.unit
def test_bootstrap_without_intent(bundle: RuntimeArtifactBundle) -> None:
    catalog = bundle.situation_policy_catalog
    stub = compile_bootstrap_strategy(catalog, intent=None)
    assert stub["influence_level"] == "unknown"
    assert "intent" in stub["host_action"].lower()


@pytest.mark.unit
def test_surface_engineering_strategy_on_agent_summary() -> None:
    envelope: dict = {"data": {}, "agent_summary": {"blocking": []}}
    strategy = {"summary": "Test headline", "influence_level": "balanced"}
    surface_engineering_strategy(envelope, strategy)
    assert envelope["data"]["engineering_strategy"] == strategy
    assert envelope["agent_summary"]["engineering_strategy"] == strategy
    assert envelope["agent_summary"]["coordinator_headline"] == "Test headline"


@pytest.mark.unit
def test_inspiration_recommended_evidence_has_suggested_queries(
    bundle: RuntimeArtifactBundle,
) -> None:
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_insp_queries",
        intent="build a SaaS analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    strategy = psm.briefing.engineering_strategy
    assert strategy is not None
    rec = strategy.get("recommended_evidence") or {}
    if rec.get("capability_id") == "inspiration_workflow":
        assert isinstance(rec.get("suggested_queries"), list)
        assert len(rec["suggested_queries"]) >= 1
        assert rec.get("mode") == "image_first"
        assert rec.get("target_image_refs", 0) >= 3
        assert "browser_fallback" in rec

    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_dash",
        intent="build a saas dashboard from scratch",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    strategy = psm.briefing.engineering_strategy
    assert strategy is not None
    assert "inspiration" not in strategy["summary"].lower()
    assert strategy["what_matters_now"]
    assert strategy["what_matters_now"][0].startswith("Resolve:")
