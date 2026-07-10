"""Build a complete installation execution plan before touching the project."""
from __future__ import annotations

from pathlib import Path

from ..integration_models import DocumentationBundle, FoundationSelection, InstallationPlan, InstallationStep


def build_installation_plan(
	documentation: DocumentationBundle,
	selection: FoundationSelection,
	*,
	repo_root: Path,
) -> InstallationPlan:
	degraded = ['installation_planner_partial']
	steps: list[InstallationStep] = []
	commands: list[str] = []
	config_updates: list[dict] = []
	css_updates: list[dict] = []

	for dep in documentation.required_dependencies:
		steps.append(InstallationStep(action='install_package', target=dep))
	for dep in documentation.peer_dependencies:
		if dep not in documentation.required_dependencies:
			steps.append(InstallationStep(action='install_peer_dependency', target=dep))

	for cmd in documentation.installation_steps:
		commands.append(cmd)
		steps.append(InstallationStep(action='run_install_command', target=cmd))

	for plugin in documentation.tailwind_plugins:
		steps.append(InstallationStep(action='update_tailwind_config', target=plugin, details={'plugin': plugin}))
		config_updates.append({'file': 'tailwind.config', 'add_plugin': plugin})

	for var in documentation.css_variables:
		steps.append(InstallationStep(action='register_css_variable', target=var))
		css_updates.append({'file': 'globals.css', 'variable': var})

	if documentation.fonts:
		steps.append(InstallationStep(action='install_fonts', target=','.join(documentation.fonts)))
	if documentation.icons:
		steps.append(InstallationStep(action='install_icon_library', target=documentation.icons[0]))

	if (repo_root / 'postcss.config.js').is_file() or (repo_root / 'postcss.config.mjs').is_file():
		steps.append(InstallationStep(action='verify_postcss_config', target='postcss'))

	for hint in selection.guidance.codebase.preferred_implementations:
		steps.append(InstallationStep(action='apply_codebase_preference', target=hint))

	return InstallationPlan(
		steps=steps,
		install_commands=commands,
		config_updates=config_updates,
		css_updates=css_updates,
		degraded=degraded,
	)
