"""Stable Browser Intelligence contract for Component Intelligence validation."""
from __future__ import annotations

from pathlib import Path

from navigation.component_intelligence.integration_models import ValidationReport

MODULE_NAME = 'visual_browser_intelligence'


class BrowserIntelligenceAdapter:
	"""Public contract surface — wires to Visual Browser Intelligence when available."""

	module_name = MODULE_NAME

	async def validate_component_integration(
		self,
		*,
		preview_url: str | None,
		repo_root: Path,
		installed_files: list[str] | None = None,
	) -> ValidationReport:
		checks = {
			'console': False,
			'runtime': False,
			'hydration': False,
			'rendering': False,
			'responsive': False,
			'accessibility': False,
			'visual': False,
		}
		blocking: list[str] = []
		warnings: list[str] = []
		degraded = ['browser_validation_heuristic']

		if not preview_url:
			return ValidationReport(
				passed=False,
				blocking=['preview_url_required_for_validation'],
				checks=checks,
				degraded=degraded,
			)

		files_exist = _installed_files_exist(repo_root, installed_files or [])
		if files_exist:
			checks['rendering'] = True
			warnings.append('file_presence_check_only_until_observe_wired')

		# Future: VisualBrowserService.collect_observation + verify on preview_url
		try:
			from navigation.visual_browser_intelligence.service import VisualBrowserService

			_ = VisualBrowserService
			warnings.append('observe_verify_not_invoked_yet_set_session_for_live_validation')
		except ImportError:
			degraded.append('visual_browser_service_unavailable')

		passed = all(checks.values()) and not blocking
		if not passed and not blocking:
			blocking.append('browser_validation_incomplete')

		return ValidationReport(
			passed=passed,
			blocking=blocking,
			warnings=warnings,
			checks=checks,
			degraded=degraded,
		)


def _installed_files_exist(repo_root: Path, installed_files: list[str]) -> bool:
	if not installed_files:
		return False
	return any((repo_root / f).is_file() for f in installed_files)
