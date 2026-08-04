"""Tests for UX KB strategy integration."""
from __future__ import annotations

from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel, _utc_now
from navigation.coordination_intelligence.planning.engineering_strategy import compile_engineering_strategy
from navigation.coordination_intelligence.planning.situation_policy import derive_discriminators
from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.ux_knowledge.strategy_integration import (
	compile_ux_knowledge_hint,
	infer_retrieval_surface,
)


def test_infer_retrieval_surface_landing() -> None:
	assert infer_retrieval_surface(surface_type="marketing", intent="Build landing page") == "landing"


def test_infer_retrieval_surface_dashboard() -> None:
	assert infer_retrieval_surface(surface_type="dashboard", intent="Build analytics dashboard") == "dashboard"


def test_compile_ux_hint_for_greenfield_dashboard() -> None:
	psm = ProjectSituationModel()
	psm.episode.intent_stack.append(
		IntentFrame(intent="Build SaaS analytics dashboard with KPI hierarchy", pushed_at=_utc_now())
	)
	psm.episode.surface_type = "dashboard"
	disc = derive_discriminators(psm)
	hint = compile_ux_knowledge_hint(
		psm,
		disc,
		influence_level="structural",
		engineering_phase="design_orientation",
	)
	assert hint is not None
	assert hint["query_id"] == "ux.retrieve"
	assert hint["params"]["surface_type"] == "dashboard"


def test_engineering_strategy_includes_ux_hint() -> None:
	bundle = load_runtime_artifacts()
	psm = ProjectSituationModel()
	psm.episode.intent_stack.append(
		IntentFrame(intent="Build marketing landing page with hero CTA", pushed_at=_utc_now())
	)
	psm.situation.situation_class = "inspiration_needed"
	psm.situation.project_maturity = "M1"
	psm.situation.lifecycle_stage = "S03_design"
	strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog)
	out = strategy.to_dict()
	assert out.get("ux_knowledge_hint") is not None
	assert out["ux_knowledge_hint"]["params"]["surface_type"] in ("landing", "marketing")
