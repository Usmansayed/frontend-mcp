"""Resolve Tailwind, React, Next.js, icons, and config incompatibilities."""
from __future__ import annotations

from pathlib import Path

from ..integration_models import CompatibilityPlan, DocumentationBundle, FoundationSelection


def resolve_compatibility(
	selection: FoundationSelection,
	documentation: DocumentationBundle,
	*,
	repo_root: Path,
) -> CompatibilityPlan:
	degraded = ['compatibility_resolver_partial']
	resolutions: list[str] = []
	adaptations: list[str] = []
	blockers: list[str] = []
	config_patches: list[dict] = []

	if not selection.guidance.framework.compatible:
		blockers.extend(selection.guidance.framework.issues or ['framework_incompatible'])

	tailwind_v4 = (repo_root / 'tailwind.config.ts').is_file() and _file_mentions(
		repo_root / 'package.json', 'tailwindcss', '4.'
	)
	if tailwind_v4:
		resolutions.append('tailwind_v4_class_mapping_may_be_required')
		adaptations.append('map_legacy_tailwind_utilities_if_needed')

	if 'lucide-react' in selection.guidance.codebase.existing_libraries:
		adaptations.append('swap_icon_imports_to_lucide-react')
	elif documentation.icons:
		resolutions.append(f'install_icon_library:{documentation.icons[0]}')

	if 'framer-motion' in selection.guidance.codebase.existing_libraries:
		adaptations.append('prefer_framer_motion_for_animations')

	for mod in selection.guidance.consistency.all_adjustments():
		adaptations.append(f'{mod.category}:{mod.description}')

	if (repo_root / 'components.json').is_file():
		resolutions.append('align_imports_with_components_json_aliases')
	else:
		adaptations.append('create_or_update_components_json_before_shadcn_add')

	return CompatibilityPlan(
		resolutions=resolutions,
		adaptations=adaptations,
		config_patches=config_patches,
		blockers=blockers,
		degraded=degraded,
	)


def _file_mentions(path: Path, package: str, version_prefix: str) -> bool:
	if not path.is_file():
		return False
	try:
		text = path.read_text(encoding='utf-8')
		return package in text and version_prefix in text
	except OSError:
		return False
