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
def test_bootstrap_greenfield_dashboard_is_structurally_blocked(
    bundle: RuntimeArtifactBundle,
) -> None:
    strategy = compile_bootstrap_strategy(
        bundle.situation_policy_catalog,
        intent="build a new SaaS analytics dashboard",
    )
    assert strategy["influence_level"] == "structural"
    assert strategy["implementation_gate"]["state"] == "blocked"
    assert strategy["recommended_resource"] in {
        "perception://inspiration-guide",
        "perception://guide/inspiration",
        "perception://spine/greenfield",
    }


@pytest.mark.unit
def test_surface_engineering_strategy_on_agent_summary() -> None:
    envelope: dict = {"data": {}, "agent_summary": {"blocking": []}}
    strategy = {
        "summary": "Test headline",
        "influence_level": "balanced",
        "host_action": "Run inspiration collect",
    }
    surface_engineering_strategy(envelope, strategy)
    assert envelope["data"]["engineering_strategy"] == strategy
    # dev41+: agent_summary carries a compact projection, not the full strategy.
    compact = envelope["agent_summary"]["engineering_strategy"]
    assert compact["summary"] == "Test headline"
    assert compact["influence_level"] == "balanced"
    assert compact["host_action"] == "Run inspiration collect"
    assert compact["_full_strategy_path"] == "data.engineering_strategy"
    assert envelope["agent_summary"]["coordinator_headline"] == "Test headline"
    assert envelope["agent_summary"]["coordinator"]["host_action"] == "Run inspiration collect"
    face = envelope["agent_summary"]["card"]
    assert face["schema"] == "agent_face_card.v1"
    assert face["next"]
    assert envelope["agent_summary"]["recommended_next"] == face["next"]
    assert envelope["data"]["coordinator"]["schema"] == "coordinator_card.v1"


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


@pytest.mark.unit
def test_design_driven_verify_keeps_ship_eligible_influence(bundle: RuntimeArtifactBundle) -> None:
    """First green verify must not collapse design-driven work to maintenance."""
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_ship_influence",
        intent="build a new SaaS analytics dashboard",
        lifecycle_stage="S05_implementation",
        project_maturity="M1",
    )
    psm.artifacts.snapshot_id = "snap_dash"
    psm.episode.verification_status = "passed"
    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    assert strategy["task_scope"] == "design_driven"
    assert strategy["influence_level"] in ("structural", "balanced")
    from navigation.coordination_intelligence.planning.ship_council import ship_council_hint

    hint = ship_council_hint(strategy, psm)
    assert hint is not None
    assert hint["mode"] == "ship"


@pytest.mark.unit
def test_strategy_surfaces_bound_reference_spec_coverage(bundle: RuntimeArtifactBundle) -> None:
    """After snapshot bind, observe/verify recompiles must not reset Spec to empty bootstrap."""
    from navigation.engineering_knowledge.reference_binding import bind_reference_spec

    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_spec_bind",
        intent="redesign dashboard hierarchy",
        lifecycle_stage="S05_implementation",
    )
    bound = {
        "catalog_version": "v1_pareto",
        "source_kind": "design_snapshot",
        "coverage": {
            "total": 30,
            "resolved": 14,
            "unresolved_or_partial": 16,
            "coverage_ratio": 0.4667,
        },
        "decisions": {
            "layout.archetype": {
                "decision_id": "layout.archetype",
                "group": "layout",
                "status": "resolved",
                "value": "dashboard",
                "confidence": 0.8,
                "importance": "critical",
                "impact_weight": 0.98,
                "evidence": [],
                "constraints": {},
                "why": "measured",
                "why_code": "measured",
                "provenance": {},
                "raw_refs": [],
            }
        },
        "unresolved_by_impact": [],
    }
    bind_reference_spec(bound, psm=psm, source="design_snapshot")
    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    spec = strategy.get("engineering_spec") or {}
    assert float((spec.get("coverage") or {}).get("coverage_ratio") or 0) >= 0.4
    assert spec.get("source_kind") == "design_snapshot"


@pytest.mark.unit
def test_seo_capabilities_absent_from_strategy_surface(bundle: RuntimeArtifactBundle) -> None:
    """Intent mentioning SEO must not surface seo_* decisions, evidence, or deferred families."""
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_seo_park",
        intent="Test 6 full-stack pass — SEO excluded; confirm SEO parked on marketing site",
        lifecycle_stage="S05_implementation",
    )
    strategy = psm.briefing.engineering_strategy or {}
    unresolved = strategy.get("unresolved_decisions") or []
    assert not any(d.get("decision_id") == "seo_baseline" for d in unresolved)
    plan = strategy.get("evidence_plan") or []
    assert not any(
        str(item.get("capability_id") or "").startswith("seo_")
        or item.get("decision_id") == "seo_baseline"
        for item in plan
    )
    next_cap = (strategy.get("implementation_gate") or {}).get("next_required_capability")
    assert next_cap not in ("seo_readiness", "seo_evidence_collect")
    deferred = (strategy.get("episode_portfolio") or {}).get("deferred") or []
    assert not any(d.get("family") in ("seo", "figma") for d in deferred)


@pytest.mark.unit
def test_visual_feedback_unpaid_on_design_scope_and_pays_on_look(bundle: RuntimeArtifactBundle) -> None:
    """Structural design episodes owe LOOK; perception_visual_feedback pays the family."""
    from navigation.coordination_intelligence.psm.normalize import apply_envelope

    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_look",
        intent="redesign marketing landing homepage hero",
        lifecycle_stage="S03_design",
    )
    strategy = psm.briefing.engineering_strategy or {}
    unpaid = (strategy.get("episode_portfolio") or {}).get("unpaid") or []
    assert any(u.get("family") == "visual_feedback" for u in unpaid)
    assert any(
        u.get("suggested") == "perception_visual_feedback"
        for u in unpaid
        if u.get("family") == "visual_feedback"
    )

    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_visual_feedback",
            "data": {
                "purpose": "design",
                "feedback_schema": {"type": "object"},
                "visual_evidence": {"viewport": True},
                "visual_feedback": {"judgment": "needs_work", "notes": "hero weak"},
                "next_actions": [{"action": "edit_then_remeasure"}],
            },
            "blocking": [],
        },
        bundle,
    )
    strategy2 = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    unpaid2 = (strategy2.get("episode_portfolio") or {}).get("unpaid") or []
    paid2 = (strategy2.get("episode_portfolio") or {}).get("paid") or []
    assert any(p.get("family") == "visual_feedback" for p in paid2)
    assert not any(u.get("family") == "visual_feedback" for u in unpaid2)


@pytest.mark.unit
def test_bootstrap_catalog_not_actionable_board(bundle: RuntimeArtifactBundle) -> None:
    """Bootstrap engineering_spec must not present 0/30 unresolved as an agent backlog."""
    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_catalog",
        intent="incremental feature polish on existing marketing portfolio",
        lifecycle_stage="S05_implementation",
    )
    strategy = psm.briefing.engineering_strategy or {}
    spec = strategy.get("engineering_spec") or {}
    assert spec.get("catalog_status") == "awaiting_design_snapshot"
    assert (spec.get("coverage") or {}).get("actionable") is False
    assert spec.get("unresolved_by_impact") == []
    wm = strategy.get("what_matters_now") or []
    assert not any(str(p).startswith("Resolve: layout.") for p in wm)


@pytest.mark.unit
def test_measured_spec_advances_catalog_status(bundle: RuntimeArtifactBundle) -> None:
    """After store_measured_spec, strategy shows measured catalog (not bootstrap board)."""
    from navigation.engineering_knowledge.reference_binding import store_measured_spec

    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_measured",
        intent="incremental feature polish on existing marketing portfolio",
        lifecycle_stage="S05_implementation",
    )
    measured = {
        "catalog_version": "v1_pareto",
        "source_kind": "live_dom",
        "coverage": {
            "total": 30,
            "resolved": 12,
            "not_applicable": 1,
            "unresolved_or_partial": 17,
            "coverage_ratio": 0.4333,
        },
        "decisions": {
            "layout.archetype": {
                "decision_id": "layout.archetype",
                "group": "layout",
                "status": "resolved",
                "value": "marketing_landing",
                "confidence": 0.8,
                "importance": "critical",
                "impact_weight": 0.98,
                "evidence": ["observe"],
                "constraints": {},
                "why": "measured",
                "why_code": "measured",
                "provenance": {},
                "raw_refs": [],
            }
        },
        "unresolved_by_impact": [],
    }
    store_measured_spec(measured, psm=psm, source="live_dom", scan_id="scan_x")
    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    spec = strategy.get("engineering_spec") or {}
    assert spec.get("source_kind") == "live_dom"
    assert spec.get("catalog_status") == "measured"
    assert (spec.get("coverage") or {}).get("actionable") is True
    assert float((spec.get("coverage") or {}).get("coverage_ratio") or 0) >= 0.4


@pytest.mark.unit
def test_budget_once_per_capability_and_floor(bundle: RuntimeArtifactBundle) -> None:
    """Suite-sized pass should not exhaust budget via double-debit."""
    from navigation.coordination_intelligence.planning.effort_allocator import (
        debit_budget,
        evaluate_allocation,
    )
    from navigation.coordination_intelligence.planning.situation_policy import capability_cost

    svc = CoordinationIntelligenceService(bundle=bundle)
    psm = svc.episode_start(
        session_id="sess_budget",
        intent="full capability pass observe verify inspiration consistency",
        lifecycle_stage="S05_implementation",
    )
    catalog = bundle.situation_policy_catalog
    decision = evaluate_allocation(psm, catalog, capability_id="browser_observe")
    assert decision.budget_total >= 32
    caps = [
        "browser_observe",
        "browser_verify",
        "design_graph_manage",
        "design_consistency_assess",
        "inspiration_workflow",
        "browser_diff",
        "browser_act",
    ]
    for cap in caps:
        cost = capability_cost(catalog, cap)
        debit_budget(psm, cost, cap)
        debit_budget(psm, cost, cap)
    spent = int(psm.episode.retry_counters.get("intelligence_spent") or 0)
    total = int(psm.episode.retry_counters.get("intelligence_budget_total") or 0)
    assert spent <= total
    assert spent < total
    again = evaluate_allocation(psm, catalog, capability_id="browser_verify")
    assert again.stop_reason != "budget_exhausted"
