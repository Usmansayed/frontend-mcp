"""Install → validate → consult → fix → re-validate loop."""
from __future__ import annotations

from pathlib import Path

from ..contracts import IntelligenceContracts
from ..integration_models import (
	FoundationSelection,
	IntegrationArtifacts,
	IntegrationRequest,
	RepairAttempt,
	ValidationReport,
)
from .browser_validator import validate_integration
from .fix_applier import apply_fix_plan
from .fix_planner import plan_fix


class RepairLoop:
	def __init__(self, *, contracts: IntelligenceContracts | None = None) -> None:
		self._contracts = contracts

	async def run(
		self,
		selection: FoundationSelection,
		artifacts: IntegrationArtifacts,
		request: IntegrationRequest,
	) -> tuple[IntegrationArtifacts, ValidationReport, list[RepairAttempt]]:
		contracts = self._contracts
		attempts: list[RepairAttempt] = []
		current = artifacts
		installed = current.install.installed_files if current.install else []
		validation = await validate_integration(
			preview_url=request.preview_url,
			repo_root=request.repo_root,
			installed_files=installed,
			contracts=contracts,
		)
		repo_root = Path(request.repo_root) if request.repo_root else Path.cwd()

		for attempt in range(1, request.max_repair_attempts + 1):
			if validation.passed:
				break

			issue = validation.blocking[0] if validation.blocking else 'validation_failed'
			fix_plan = await plan_fix(
				issue,
				selection,
				artifacts.documentation,
				repo_root=repo_root,
				validation=validation,
				contracts=contracts,
			)

			attempts.append(
				RepairAttempt(attempt=attempt, issue=issue, fix_plan=fix_plan, validation=validation)
			)

			if fix_plan.actions and fix_plan.actions[0].startswith('stop:'):
				break

			current, _applied = apply_fix_plan(
				fix_plan,
				current,
				repo_root=repo_root,
				execute=request.execute_repairs,
			)

			validation = await validate_integration(
				preview_url=request.preview_url,
				repo_root=request.repo_root,
				installed_files=current.install.installed_files if current.install else installed,
				contracts=contracts,
			)

		return current, validation, attempts
