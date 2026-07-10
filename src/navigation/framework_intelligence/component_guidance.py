"""Framework Intelligence guidance for component selection."""
from __future__ import annotations

from pathlib import Path

from navigation.component_intelligence.integration_models import FrameworkGuidance
from navigation.component_intelligence.models import ComponentCandidate

from .detector import detect_project


async def evaluate_component(
	candidate: ComponentCandidate,
	*,
	repo_root: Path,
) -> FrameworkGuidance:
	meta = detect_project(repo_root)
	issues: list[str] = []
	warnings: list[str] = []
	degraded = ['framework_guidance_heuristic']

	framework = (meta.framework or '').lower()
	candidate_fw = (candidate.framework or 'react').lower()

	compatible = True
	if framework and candidate_fw and framework not in candidate_fw and candidate_fw not in framework:
		if framework not in ('react', 'next', 'next.js') or candidate_fw != 'react':
			warnings.append(f'framework_mismatch:{framework}_vs_{candidate_fw}')

	if meta.framework_version:
		warnings.append(f'verify_peer_deps_for_{meta.primary_package}_{meta.framework_version}')

	peer_deps = [str(d) for d in (candidate.metadata.get('registry_dependencies') or [])]
	required_config: list[str] = []
	if (repo_root / 'components.json').is_file():
		required_config.append('components.json')
	else:
		warnings.append('components_json_missing_for_shadcn_install')

	if meta.router_mode == 'app' and candidate.category == 'block':
		warnings.append('verify_client_component_boundaries_for_app_router')

	if meta.rendering_mode and 'server' in (meta.rendering_mode or '').lower():
		warnings.append('check_server_component_compatibility')

	return FrameworkGuidance(
		compatible=compatible and not issues,
		issues=issues,
		compatibility_warnings=warnings,
		required_dependencies=peer_deps,
		peer_dependencies=peer_deps,
		required_configuration=required_config,
		degraded=degraded,
	)
