"""Batch regression — consistency overlap + task_scope routing (Test 10 leftovers)."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.consistency_intelligence.service import ConsistencyIntelligenceService
from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.situation_policy import _derive_task_scope
from navigation.design_snapshot_engine import DesignSnapshotEngine

FIXTURE = {
	"url": "http://127.0.0.1:3000/about",
	"viewport": {"width": 1280, "height": 720},
	"document": {"scrollWidth": 1280, "scrollHeight": 900},
	"css_variables": {},
	"elements": [
		{
			"tag": "section",
			"selector": "section.hero",
			"text": "About",
			"classes": ["hero"],
			"style": {"padding": "24px", "fontSize": "18px", "color": "#111"},
		},
	],
}


@pytest.mark.unit
def test_consistency_audit_not_phase1_stub_when_graph_populated() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		service = ConsistencyIntelligenceService(repo_root=Path(tmp))
		snapshot = DesignSnapshotEngine().capture_from_fixture(FIXTURE)
		asyncio.run(
			service.refresh_graph(
				project_id="batch_a11y",
				design_snapshot=snapshot,
				enabled_sources=frozenset({"snapshot"}),
			)
		)
		detail = service.audit_snapshot_detail(snapshot, project_id="batch_a11y")
		degraded = list(detail.get("degraded") or [])
		assert "knowledge_query_stub_phase1" not in degraded
		assert "discovery_pipeline_phase2" not in degraded
		# Real assess path — either findings or a clean pass, not Phase-1 stub messaging.
		assert "stub" not in str(detail.get("summary") or "").lower()
		assert int(detail.get("elements_audited") or 0) >= 1


@pytest.mark.unit
def test_component_foundation_intent_not_system_setup() -> None:
	psm = ProjectSituationModel()
	assert (
		_derive_task_scope("select component foundation for shadcn about page", "", "", psm)
		!= "system_setup"
	)
	assert _derive_task_scope("redesign artful portfolio about page", "", "", psm) == "redesign"
	assert _derive_task_scope("set up design system tokens and theme setup", "", "", psm) == "system_setup"
	assert _derive_task_scope("portfolio about page polish", "", "", psm) == "design_driven"
	# Landing + foundation must not sticky-route to system_setup via bare "foundation".
	assert (
		_derive_task_scope("landing page component foundation select", "", "", psm)
		== "design_driven"
	)
