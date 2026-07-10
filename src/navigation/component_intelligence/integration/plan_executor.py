"""Execute installation plan steps — records commands; optional live execution."""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..integration_models import InstallationPlan, InstallationStep


def execute_plan_steps(
	plan: InstallationPlan,
	*,
	repo_root: Path,
	execute: bool = False,
) -> tuple[list[str], list[str]]:
	"""Walk ordered steps; return (executed_commands, step_log)."""
	executed: list[str] = []
	log: list[str] = []
	pm = _detect_package_manager(repo_root)

	for step in plan.steps:
		cmd = _step_to_command(step, package_manager=pm)
		if cmd:
			log.append(f'{step.action}:{step.target}')
			if execute:
				_run_command(cmd, repo_root=repo_root)
			executed.append(cmd)
		else:
			log.append(f'skipped:{step.action}:{step.target}')

	for cmd in plan.install_commands:
		if cmd not in executed:
			log.append(f'install_command:{cmd}')
			if execute:
				_run_command(cmd, repo_root=repo_root)
			executed.append(cmd)

	return list(dict.fromkeys(executed)), log


def _step_to_command(step: InstallationStep, *, package_manager: str) -> str | None:
	if step.action in ('install_package', 'install_peer_dependency'):
		return f'{package_manager} add {step.target}'
	if step.action == 'run_install_command':
		return step.target
	if step.action == 'install_icon_library' and step.target:
		return f'{package_manager} add {step.target}'
	return None


def _detect_package_manager(repo_root: Path) -> str:
	if (repo_root / 'pnpm-lock.yaml').is_file():
		return 'pnpm'
	if (repo_root / 'yarn.lock').is_file():
		return 'yarn'
	if (repo_root / 'bun.lockb').is_file():
		return 'bun'
	return 'npm'


def _run_command(command: str, *, repo_root: Path) -> None:
	subprocess.run(
		command,
		shell=True,
		cwd=repo_root,
		check=False,
		capture_output=True,
		text=True,
	)
