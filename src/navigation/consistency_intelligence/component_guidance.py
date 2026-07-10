"""Consistency Intelligence guidance — modifications only, never hard reject."""
from __future__ import annotations

from pathlib import Path

from navigation.component_intelligence.integration_models import ConsistencyGuidance, ModificationHint
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery


def evaluate_component(
	candidate: ComponentCandidate,
	*,
	repo_root: Path,
	parsed_query: ParsedQuery | None = None,
) -> ConsistencyGuidance:
	_ = parsed_query
	required: list[ModificationHint] = []
	tokens: list[ModificationHint] = []
	spacing: list[ModificationHint] = []
	typography: list[ModificationHint] = []
	colors: list[ModificationHint] = []
	radius: list[ModificationHint] = []
	shadows: list[ModificationHint] = []
	degraded = ['consistency_guidance_scaffold']

	if (repo_root / 'tailwind.config.ts').is_file() or (repo_root / 'tailwind.config.js').is_file():
		typography.append(
			ModificationHint(
				category='typography',
				description='Align component text scale with project Tailwind theme',
				file_glob='**/*.tsx',
				required=False,
			)
		)
		spacing.append(
			ModificationHint(
				category='spacing',
				description='Match spacing rhythm to project Tailwind spacing scale',
				file_glob='**/*.tsx',
				required=False,
			)
		)

	global_css = repo_root / 'src' / 'app' / 'globals.css'
	if not global_css.is_file():
		global_css = repo_root / 'src' / 'index.css'
	if global_css.is_file():
		tokens.append(
			ModificationHint(
				category='token',
				description='Map component colors to CSS variables in globals',
				file_glob=str(global_css.relative_to(repo_root)),
				required=False,
			)
		)
		colors.append(
			ModificationHint(
				category='color',
				description='Use semantic color tokens from globals.css',
				required=False,
			)
		)

	return ConsistencyGuidance(
		required_modifications=required,
		token_adjustments=tokens,
		spacing_adjustments=spacing,
		typography_adjustments=typography,
		color_adjustments=colors,
		radius_adjustments=radius,
		shadow_adjustments=shadows,
		degraded=degraded,
	)
