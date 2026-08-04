"""Run 3 hardcore leftovers — integrate None guidance + graph summary share."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from navigation.component_intelligence.integration.installation_planner import build_installation_plan
from navigation.component_intelligence.integration_models import (
	DocumentationBundle,
	FoundationSelection,
)
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery
from navigation.component_intelligence.selection.selector import select_foundation
from navigation.consistency_intelligence.graph.persistence import clear_process_graph_stores
from navigation.consistency_intelligence.service import ConsistencyIntelligenceService
from navigation.coordination_intelligence.planning.engineering_strategy import (
	surface_engineering_strategy,
)


@pytest.mark.unit
def test_library_lock_without_starter_has_guidance() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(root / "package.json").write_text(
			json.dumps({"dependencies": {"@once-ui-system/core": "1.0.0", "next": "16.0.0"}}),
			encoding="utf-8",
		)
		selection = asyncio.run(
			select_foundation(
				[],
				repo_root=root,
				parsed_query=ParsedQuery(raw="select foundation"),
			)
		)
		assert selection.usable is True
		assert selection.library_id == "@once-ui-system"
		assert selection.guidance is not None
		assert selection.guidance.codebase is not None


@pytest.mark.unit
def test_installation_plan_tolerates_none_guidance() -> None:
	chosen = ComponentCandidate(
		id="lib:@once-ui-system",
		provider="once_ui",
		provider_group="once_ui",
		name="@once-ui-system",
		title="Once UI",
		category="library",
		description="library lock",
		registry="@once-ui-system",
	)
	selection = FoundationSelection(chosen=chosen, guidance=None, usable=True, library_id="@once-ui-system")
	plan = build_installation_plan(
		DocumentationBundle.from_candidate(chosen),
		selection,
		repo_root=Path("."),
	)
	assert isinstance(plan.steps, list)


@pytest.mark.unit
def test_graph_summary_sees_refresh_across_service_instances() -> None:
	clear_process_graph_stores()
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(root / "package.json").write_text("{}", encoding="utf-8")
		# Seed via refresh on service A
		svc_a = ConsistencyIntelligenceService(repo_root=root)
		graph = svc_a.load_graph("default")
		from navigation.consistency_intelligence.graph.model import ComponentNode

		graph.components["btn"] = ComponentNode(name="Button")
		svc_a._store.save(graph)

		# Fresh service B must see the same process store / disk
		svc_b = ConsistencyIntelligenceService(repo_root=root)
		summary = svc_b.graph_summary(project_id="default")
		assert "graph_empty" not in summary.degraded
		payload = summary.to_dict()
		# Knowledge responses vary; assert via load
		loaded = svc_b.load_graph("default")
		assert len(loaded.components) >= 1


@pytest.mark.unit
def test_agent_summary_strategy_is_compact_not_full_duplicate() -> None:
	full = {
		"summary": "test",
		"host_action": "observe",
		"influence_level": "balanced",
		"policy_id": "feature.mid.balanced",
		"what_matters_now": ["a", "b", "c", "d", "e"],
		"implementation_gate": {"state": "provisional"},
		"episode_portfolio": {"paid": [], "unpaid": ["inspiration"]},
		"giant_blob": "x" * 5000,
	}
	env = surface_engineering_strategy({"data": {}, "ok": True}, full)
	assert env["data"]["engineering_strategy"]["giant_blob"] == "x" * 5000
	compact = env["agent_summary"]["engineering_strategy"]
	assert "giant_blob" not in compact
	assert compact.get("_full_strategy_path") == "data.engineering_strategy"
	assert len(compact.get("what_matters_now") or []) <= 4
