"""Resolve npm dependencies from documentation and installation plan."""
from __future__ import annotations

import json
from pathlib import Path

from ..integration_models import DependencyPlan, DocumentationBundle, InstallationPlan


def resolve_dependencies(
	documentation: DocumentationBundle,
	plan: InstallationPlan,
	*,
	repo_root: Path,
) -> DependencyPlan:
	degraded = ['dependency_resolver_partial']
	packages = list(documentation.required_dependencies)
	peer_packages = [p for p in documentation.peer_dependencies if p not in packages]
	commands = list(plan.install_commands)
	conflicts: list[str] = []

	pkg_json = repo_root / 'package.json'
	pm = _detect_package_manager(repo_root)
	if pkg_json.is_file():
		try:
			data = json.loads(pkg_json.read_text(encoding='utf-8'))
			existing = set((data.get('dependencies') or {}).keys()) | set((data.get('devDependencies') or {}).keys())
			missing = [p for p in packages + peer_packages if _pkg_name(p) not in existing and p not in existing]
			if missing and pm:
				commands.append(f'{pm} add {" ".join(missing)}')
		except (json.JSONDecodeError, OSError):
			degraded.append('package_json_unreadable')

	return DependencyPlan(
		packages=packages,
		peer_packages=peer_packages,
		install_commands=list(dict.fromkeys(commands)),
		conflicts=conflicts,
		degraded=degraded,
	)


def _detect_package_manager(repo_root: Path) -> str:
	if (repo_root / 'pnpm-lock.yaml').is_file():
		return 'pnpm'
	if (repo_root / 'yarn.lock').is_file():
		return 'yarn'
	if (repo_root / 'bun.lockb').is_file():
		return 'bun'
	return 'npm'


def _pkg_name(spec: str) -> str:
	return spec.split('/')[-1].split('@')[0]
