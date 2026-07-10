"""Orchestrate integration subsystems in strict sequence — single responsibility each."""
from __future__ import annotations

from pathlib import Path

from ..contracts import IntelligenceContracts
from ..integration_models import FoundationSelection, IntegrationArtifacts
from ..providers import ProviderManager
from .compatibility_resolver import resolve_compatibility
from .component_adapter import adapt_component
from .dependency_resolver import resolve_dependencies
from .documentation_reader import read_documentation
from .installation_planner import build_installation_plan
from .installer import Installer


class IntegrationPipeline:
	"""Documentation → plan → deps → compatibility → install → adapt."""

	def __init__(
		self,
		*,
		provider_manager: ProviderManager | None = None,
		contracts: IntelligenceContracts | None = None,
	) -> None:
		providers = provider_manager or ProviderManager()
		self._installer = Installer(provider_manager=providers)
		self._contracts = contracts

	async def run(
		self,
		selection: FoundationSelection,
		*,
		repo_root: Path,
		execute_install: bool = False,
	) -> IntegrationArtifacts:
		degraded: list[str] = []
		candidate = selection.chosen
		contracts = self._contracts

		documentation = await read_documentation(
			candidate,
			repo_root=repo_root,
			selection=selection,
			contracts=contracts,
		)
		degraded.extend(documentation.degraded)

		installation_plan = build_installation_plan(documentation, selection, repo_root=repo_root)
		degraded.extend(installation_plan.degraded)

		dependencies = resolve_dependencies(documentation, installation_plan, repo_root=repo_root)
		degraded.extend(dependencies.degraded)

		compatibility = resolve_compatibility(selection, documentation, repo_root=repo_root)
		degraded.extend(compatibility.degraded)

		if compatibility.blockers:
			return IntegrationArtifacts(
				documentation=documentation,
				installation_plan=installation_plan,
				dependencies=dependencies,
				compatibility=compatibility,
				degraded=degraded + ['integration_blocked'],
			)

		install_result = await self._installer.execute(
			installation_plan,
			dependencies,
			candidate,
			repo_root=repo_root,
			execute=execute_install,
		)
		degraded.extend(install_result.degraded)

		adaptations = adapt_component(
			selection,
			repo_root=repo_root,
			installed_files=install_result.installed_files,
		)

		return IntegrationArtifacts(
			documentation=documentation,
			installation_plan=installation_plan,
			dependencies=dependencies,
			compatibility=compatibility,
			install=install_result,
			adaptations=adaptations,
			degraded=list(dict.fromkeys(degraded)),
		)


# Backward-compatible alias
IntegrationEngine = IntegrationPipeline
