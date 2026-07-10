"""Execute installation plan — no ad-hoc decisions during install."""
from __future__ import annotations

from pathlib import Path

from ..integration_models import DependencyPlan, InstallResult, InstallationPlan
from ..models import ComponentCandidate
from ..providers import ProviderManager
from .plan_executor import execute_plan_steps


class Installer:
	def __init__(self, *, provider_manager: ProviderManager | None = None) -> None:
		self._providers = provider_manager or ProviderManager()

	async def execute(
		self,
		plan: InstallationPlan,
		dependencies: DependencyPlan,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
		execute: bool = False,
	) -> InstallResult:
		degraded: list[str] = []

		plan_commands, step_log = execute_plan_steps(plan, repo_root=repo_root, execute=execute)
		executed = list(dependencies.install_commands)
		for cmd in plan_commands:
			if cmd not in executed:
				executed.append(cmd)

		if not execute:
			degraded.append('installer_dry_run')

		provider_status = 'skipped_dry_run'
		provider_error: str | None = None
		installed_files: list[str] = []

		if execute:
			try:
				provider_result = await self._providers.install(candidate.id)
				provider_status = str(provider_result.get('status', 'not_executed'))
				if provider_result.get('error'):
					provider_error = str(provider_result.get('error'))
					degraded.append('provider_install_failed')
				files = provider_result.get('installed_files')
				if isinstance(files, list):
					installed_files = [str(f) for f in files]
			except Exception as exc:
				provider_status = 'error'
				provider_error = str(exc)
				degraded.append('provider_install_failed')
		else:
			installed_files = [f'components/{candidate.name}.tsx']

		if provider_error:
			return InstallResult(
				status='error',
				executed_commands=executed,
				installed_files=installed_files,
				error=provider_error,
				degraded=degraded,
			)

		status = 'planned' if not execute else provider_status
		if step_log:
			degraded.append(f'plan_steps:{len(step_log)}')

		return InstallResult(
			status=status,
			executed_commands=executed,
			installed_files=installed_files,
			degraded=list(dict.fromkeys(degraded)),
		)
