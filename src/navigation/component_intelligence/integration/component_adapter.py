"""Adapt installed component using Design Sense, Consistency, and Codebase guidance."""
from __future__ import annotations

from pathlib import Path

from ..integration_models import AdaptationPatch, FoundationSelection


def adapt_component(
	selection: FoundationSelection,
	*,
	repo_root: Path,
	installed_files: list[str] | None = None,
) -> list[AdaptationPatch]:
	_ = repo_root
	patches: list[AdaptationPatch] = []
	files = installed_files or [f'components/{selection.chosen.name}.tsx']
	g = selection.guidance

	for mod in g.consistency.all_adjustments():
		for file_path in files:
			patches.append(
				AdaptationPatch(
					file_path=file_path,
					description=mod.description,
					source_guidance='consistency_intelligence',
					diff_preview=f'{mod.category}: {mod.from_value or "?"} → {mod.to_value or "?"}',
					applied_modifications=[mod.category],
				)
			)

	if g.design_sense.layout_recommendation:
		patches.append(
			AdaptationPatch(
				file_path=files[0],
				description=g.design_sense.layout_recommendation,
				source_guidance='design_sense_intelligence',
				applied_modifications=['layout'],
			)
		)
	if g.design_sense.interaction_recommendation:
		patches.append(
			AdaptationPatch(
				file_path=files[0],
				description=g.design_sense.interaction_recommendation,
				source_guidance='design_sense_intelligence',
				applied_modifications=['interaction'],
			)
		)

	for pref in g.codebase.preferred_implementations:
		patches.append(
			AdaptationPatch(
				file_path=files[0],
				description=pref,
				source_guidance='codebase_intelligence',
				applied_modifications=['codebase_pattern'],
			)
		)

	if not patches:
		patches.append(
			AdaptationPatch(
				file_path=files[0],
				description='No adaptations queued — adapter awaiting implementation',
				source_guidance='component_intelligence',
			)
		)
	return patches
