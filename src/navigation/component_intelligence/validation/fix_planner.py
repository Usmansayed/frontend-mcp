"""Consult intelligence modules via stable contracts to plan a fix after validation failure."""
from __future__ import annotations

from pathlib import Path

from ..contracts import IntelligenceContracts
from ..integration_models import DocumentationBundle, FixPlan, FoundationSelection, ValidationReport


async def plan_fix(
	issue: str,
	selection: FoundationSelection,
	documentation: DocumentationBundle | None,
	*,
	repo_root: Path,
	validation: ValidationReport | None = None,
	contracts: IntelligenceContracts | None = None,
) -> FixPlan:
	c = contracts or IntelligenceContracts.default()
	consulted: list[str] = []
	actions: list[str] = []
	doc_refs: list[str] = []
	degraded: list[str] = []

	fw_plan = await c.framework.plan_framework_repairs(
		issue,
		selection=selection,
		documentation=documentation,
		repo_root=repo_root,
	)
	consulted.extend(fw_plan.consulted_modules)
	actions.extend(fw_plan.actions)
	doc_refs.extend(fw_plan.documentation_refs)
	degraded.extend(fw_plan.degraded)

	consulted.append(c.codebase.module_name)
	actions.extend(
		c.codebase.plan_codebase_repairs(issue, selection=selection, repo_root=repo_root)
	)

	consulted.append(c.design_sense.module_name)
	actions.extend(c.design_sense.plan_design_repairs(issue, selection=selection))

	consulted.append(c.consistency.module_name)
	actions.extend(
		c.consistency.plan_consistency_repairs(issue, selection=selection, repo_root=repo_root)
	)

	if documentation:
		consulted.append('documentation_reader')
		for note in documentation.common_issues[:2]:
			actions.append(f'check_known_issue:{note}')

	if validation and validation.checks:
		failed = [k for k, ok in validation.checks.items() if not ok]
		if failed:
			actions.append('re_validate_checks:' + ','.join(failed))

	if issue == 'preview_url_required_for_validation':
		return FixPlan(
			issue=issue,
			actions=['stop:provide_preview_url'],
			consulted_modules=list(dict.fromkeys(consulted)),
			documentation_refs=doc_refs,
			degraded=degraded or ['fix_planner_contract'],
		)

	return FixPlan(
		issue=issue,
		actions=actions or ['read_docs_and_retry'],
		consulted_modules=list(dict.fromkeys(consulted)),
		documentation_refs=doc_refs,
		degraded=degraded or ['fix_planner_contract'],
	)
