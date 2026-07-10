"""Rule metadata — ported from Design Lint organization (meta.ts + RULE_META pattern)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RuleLevel = Literal['error', 'warning', 'info']
RuleSeverity = Literal['blocking', 'major', 'minor', 'advisory']


@dataclass(frozen=True, slots=True)
class RuleMeta:
	id: str
	category: str
	level: RuleLevel
	default_severity: RuleSeverity
	title: str
	description: str
	rationale: str
	when_triggered: str


RULE_META: tuple[RuleMeta, ...] = (
	RuleMeta(
		'missing-text-style',
		'typography',
		'warning',
		'minor',
		'Text without design token / style class',
		'Text element uses ad-hoc font properties instead of theme typography',
		'Design Lint checks text layers for missing text styles (design tokens)',
		'Computed font-size/family not mapped to project typography scale',
	),
	RuleMeta(
		'missing-color-token',
		'color',
		'warning',
		'minor',
		'Color not from design token',
		'Fill or text color uses raw hex/rgb instead of CSS variables or token classes',
		'Design Lint checkFills — layers should use paint/color styles',
		'Hardcoded color value detected on element',
	),
	RuleMeta(
		'off-scale-spacing',
		'spacing',
		'warning',
		'minor',
		'Spacing off design scale',
		'Margin or padding value not on project spacing scale',
		'Ported from spacing rhythm validation in design systems',
		'Non-standard spacing value in computed styles',
	),
	RuleMeta(
		'off-scale-radius',
		'radius',
		'warning',
		'advisory',
		'Border radius off token scale',
		'Border radius not matching allowed radius tokens',
		'Design Lint checkRadius',
		'Custom radius value outside token set',
	),
	RuleMeta(
		'off-scale-shadow',
		'shadow',
		'info',
		'advisory',
		'Shadow not from token',
		'Box shadow not matching design system elevation tokens',
		'Design Lint checkEffects',
		'Non-token box-shadow detected',
	),
	RuleMeta(
		'stroke-without-token',
		'style',
		'info',
		'advisory',
		'Border without token',
		'Border width/color not from design system',
		'Design Lint checkStrokes',
		'Raw border properties on element',
	),
)

RULE_BY_ID = {r.id: r for r in RULE_META}
