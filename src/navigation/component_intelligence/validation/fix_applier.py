"""Apply repair actions from FixPlan — structured execution, safe by default."""
from __future__ import annotations

from pathlib import Path

from ..integration_models import FixPlan, IntegrationArtifacts


def apply_fix_plan(
	fix_plan: FixPlan,
	artifacts: IntegrationArtifacts,
	*,
	repo_root: Path,
	execute: bool = False,
) -> tuple[IntegrationArtifacts, list[str]]:
	"""Record and optionally apply repair actions. Returns updated artifacts and applied log."""
	_ = repo_root
	applied: list[str] = []

	for action in fix_plan.actions:
		if action.startswith('stop:'):
			applied.append(action)
			break
		applied.append(action)
		if execute:
			_apply_action(action, artifacts)

	degraded = list(artifacts.degraded)
	if applied:
		degraded.append(f'repair_actions_recorded:{len(applied)}')
	if not execute:
		degraded.append('repair_apply_dry_run')

	return IntegrationArtifacts(
		documentation=artifacts.documentation,
		installation_plan=artifacts.installation_plan,
		dependencies=artifacts.dependencies,
		compatibility=artifacts.compatibility,
		install=artifacts.install,
		adaptations=list(artifacts.adaptations),
		degraded=list(dict.fromkeys(degraded)),
	), applied


def _apply_action(action: str, artifacts: IntegrationArtifacts) -> None:
	"""Future: deterministic file patches per action type."""
	_ = action
	_ = artifacts
