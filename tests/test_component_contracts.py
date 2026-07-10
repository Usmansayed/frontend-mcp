"""Tests for stable intelligence contracts and contract-driven orchestration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.component_intelligence.contracts import (
	CONTRACT_VERSION,
	IntelligenceContracts,
)
from navigation.component_intelligence.integration_models import (
	CodebaseGuidance,
	ConsistencyGuidance,
	DesignSenseGuidance,
	FixPlan,
	FrameworkGuidance,
	FoundationSelection,
	IntegrationRequest,
	ValidationReport,
)
from navigation.component_intelligence.models import ComponentCandidate
from navigation.component_intelligence.orchestrator import ComponentOrchestrator
from navigation.component_intelligence.validation.fix_planner import plan_fix


def _candidate() -> ComponentCandidate:
	return ComponentCandidate(
		id='shadcn_ecosystem:shadcn:input',
		provider='shadcn_ecosystem',
		provider_group='shadcn_ecosystem',
		name='input',
		title='Input',
		category='component',
		description='',
		framework='react',
		install_method='npx shadcn@latest add input',
	)


def test_contract_version() -> None:
	assert CONTRACT_VERSION == '1.0'


def test_default_contracts_satisfy_protocols() -> None:
	contracts = IntelligenceContracts.default()
	assert contracts.framework.module_name == 'framework_intelligence'
	assert contracts.codebase.module_name == 'codebase_intelligence'
	assert contracts.design_sense.module_name == 'design_sense_intelligence'
	assert contracts.consistency.module_name == 'consistency_intelligence'
	assert contracts.browser.module_name == 'visual_browser_intelligence'


async def test_framework_evaluate_via_contract() -> None:
	contracts = IntelligenceContracts.default()
	guidance = await contracts.framework.evaluate_component(_candidate(), repo_root=ROOT)
	assert isinstance(guidance, FrameworkGuidance)
	assert guidance.compatible


async def test_fix_planner_consults_all_modules() -> None:
	contracts = IntelligenceContracts.default()
	candidate = _candidate()
	fw = await contracts.framework.evaluate_component(candidate, repo_root=ROOT)
	from navigation.component_intelligence.integration_models import CandidateGuidance
	from navigation.component_intelligence.guidance.synthesis import synthesize_guidance

	syn = synthesize_guidance(candidate, fw, CodebaseGuidance(), DesignSenseGuidance(), ConsistencyGuidance())
	selection = FoundationSelection(
		chosen=candidate,
		guidance=CandidateGuidance(
			candidate_id=candidate.id,
			framework=fw,
			codebase=CodebaseGuidance(),
			design_sense=DesignSenseGuidance(),
			consistency=ConsistencyGuidance(),
			synthesis=syn,
		),
	)
	plan = await plan_fix(
		'import_error',
		selection,
		None,
		repo_root=ROOT,
		validation=ValidationReport(passed=False, checks={'console': False}),
		contracts=contracts,
	)
	assert 'framework_intelligence' in plan.consulted_modules
	assert 'codebase_intelligence' in plan.consulted_modules
	assert 'design_sense_intelligence' in plan.consulted_modules
	assert 'consistency_intelligence' in plan.consulted_modules
	assert plan.actions


async def test_orchestrator_integrate_with_candidate_id() -> None:
	orch = ComponentOrchestrator()
	request = IntegrationRequest(
		candidate_id='shadcn_ecosystem:shadcn:input',
		repo_root=str(ROOT),
	)
	result = await orch.integrate(request)
	assert result.selection is not None
	assert result.integration is not None
	assert result.integration.installation_plan is not None
	assert result.integration.install is not None
	assert result.validation is not None


async def main_async() -> int:
	test_contract_version()
	test_default_contracts_satisfy_protocols()
	await test_framework_evaluate_via_contract()
	await test_fix_planner_consults_all_modules()
	await test_orchestrator_integrate_with_candidate_id()
	print('component contracts: PASS')
	return 0


def main() -> int:
	import asyncio

	return asyncio.run(main_async())


if __name__ == '__main__':
	raise SystemExit(main())
