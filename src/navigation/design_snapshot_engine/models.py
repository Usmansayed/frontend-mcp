"""Unified design snapshot — structured facts for all intelligence modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TypographySnapshot:
	"""Typography report — fonts, scale, samples."""

	font_families: list[str] = field(default_factory=list)
	font_sizes_px: list[float] = field(default_factory=list)
	line_heights: list[float] = field(default_factory=list)
	heading_levels: list[dict[str, Any]] = field(default_factory=list)
	body_samples: list[dict[str, Any]] = field(default_factory=list)
	scale_on_grid: bool = False
	issues: list[dict[str, Any]] = field(default_factory=list)
	element_count: int = 0

	def to_dict(self) -> dict[str, Any]:
		return {
			'font_families': list(self.font_families),
			'font_sizes_px': list(self.font_sizes_px),
			'line_heights': list(self.line_heights),
			'heading_levels': list(self.heading_levels),
			'body_samples': list(self.body_samples),
			'scale_on_grid': self.scale_on_grid,
			'issues': list(self.issues),
			'element_count': self.element_count,
		}


@dataclass(slots=True)
class SpacingSnapshot:
	"""Spacing matrix — padding, margin, gap values."""

	padding_values_px: list[float] = field(default_factory=list)
	margin_values_px: list[float] = field(default_factory=list)
	gap_values_px: list[float] = field(default_factory=list)
	base_unit_px: int | None = None
	off_scale_count: int = 0
	matrix: list[dict[str, Any]] = field(default_factory=list)
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'padding_values_px': list(self.padding_values_px),
			'margin_values_px': list(self.margin_values_px),
			'gap_values_px': list(self.gap_values_px),
			'base_unit_px': self.base_unit_px,
			'off_scale_count': self.off_scale_count,
			'matrix': list(self.matrix),
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class ColorSnapshot:
	"""Color palette — foreground, background, semantic usage."""

	palette: list[dict[str, Any]] = field(default_factory=list)
	text_colors: list[str] = field(default_factory=list)
	background_colors: list[str] = field(default_factory=list)
	accent_colors: list[str] = field(default_factory=list)
	contrast_pairs: list[dict[str, Any]] = field(default_factory=list)
	contrast_matrix: list[dict[str, Any]] = field(default_factory=list)
	wcag_failures: list[dict[str, Any]] = field(default_factory=list)
	raw_color_count: int = 0
	token_backed_ratio: float = 0.0
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'palette': list(self.palette),
			'text_colors': list(self.text_colors),
			'background_colors': list(self.background_colors),
			'accent_colors': list(self.accent_colors),
			'contrast_pairs': list(self.contrast_pairs),
			'contrast_matrix': list(self.contrast_matrix),
			'wcag_failures': list(self.wcag_failures),
			'raw_color_count': self.raw_color_count,
			'token_backed_ratio': self.token_backed_ratio,
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class LayoutSnapshot:
	"""Layout report — viewport, overflow, regions, interactive map."""

	viewport: dict[str, int] = field(default_factory=dict)
	document_size: dict[str, int] = field(default_factory=dict)
	visual_insights: dict[str, Any] = field(default_factory=dict)
	layout_tree: list[dict[str, Any]] = field(default_factory=list)
	regions: list[dict[str, Any]] = field(default_factory=list)
	interactive_boxes: list[dict[str, Any]] = field(default_factory=list)
	overflow_issues: list[dict[str, Any]] = field(default_factory=list)
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'viewport': dict(self.viewport),
			'document_size': dict(self.document_size),
			'visual_insights': dict(self.visual_insights),
			'layout_tree': list(self.layout_tree),
			'regions': list(self.regions),
			'interactive_boxes': list(self.interactive_boxes),
			'overflow_issues': list(self.overflow_issues),
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class GridSnapshot:
	"""Grid structure — columns, alignment hints."""

	detected_grids: list[dict[str, Any]] = field(default_factory=list)
	column_counts: list[int] = field(default_factory=list)
	alignment_score: float = 0.0
	gutter_px: list[float] = field(default_factory=list)
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'detected_grids': list(self.detected_grids),
			'column_counts': list(self.column_counts),
			'alignment_score': self.alignment_score,
			'gutter_px': list(self.gutter_px),
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class HierarchySnapshot:
	"""Visual hierarchy graph — heading order, prominence."""

	heading_tree: list[dict[str, Any]] = field(default_factory=list)
	prominence_scores: list[dict[str, Any]] = field(default_factory=list)
	skipped_levels: list[str] = field(default_factory=list)
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'heading_tree': list(self.heading_tree),
			'prominence_scores': list(self.prominence_scores),
			'skipped_levels': list(self.skipped_levels),
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class ComponentSnapshot:
	"""Component tree — clustered UI patterns."""

	nodes: list[dict[str, Any]] = field(default_factory=list)
	patterns: list[dict[str, Any]] = field(default_factory=list)
	interactive_count: int = 0
	form_controls: list[dict[str, Any]] = field(default_factory=list)
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'nodes': list(self.nodes),
			'patterns': list(self.patterns),
			'interactive_count': self.interactive_count,
			'form_controls': list(self.form_controls),
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class MotionSnapshot:
	"""Animation report — transitions, durations, reduced-motion."""

	transitions: list[dict[str, Any]] = field(default_factory=list)
	animations: list[dict[str, Any]] = field(default_factory=list)
	duration_ms: list[float] = field(default_factory=list)
	prefers_reduced_motion: bool = False
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'transitions': list(self.transitions),
			'animations': list(self.animations),
			'duration_ms': list(self.duration_ms),
			'prefers_reduced_motion': self.prefers_reduced_motion,
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class AccessibilitySnapshot:
	"""Accessibility facts — roles, labels, focus, contrast refs."""

	roles: list[dict[str, Any]] = field(default_factory=list)
	unlabeled_interactive: list[dict[str, Any]] = field(default_factory=list)
	focusable_count: int = 0
	aria_usage: list[str] = field(default_factory=list)
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'roles': list(self.roles),
			'unlabeled_interactive': list(self.unlabeled_interactive),
			'focusable_count': self.focusable_count,
			'aria_usage': list(self.aria_usage),
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class DesignTokenSnapshot:
	"""Design token report — CSS variables and inferred scales."""

	css_variables: dict[str, str] = field(default_factory=dict)
	spacing_scale: list[int] = field(default_factory=list)
	radius_scale: list[int] = field(default_factory=list)
	typography_scale: list[int] = field(default_factory=list)
	color_tokens: dict[str, str] = field(default_factory=dict)
	source: str = 'computed'
	issues: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'css_variables': dict(self.css_variables),
			'spacing_scale': list(self.spacing_scale),
			'radius_scale': list(self.radius_scale),
			'typography_scale': list(self.typography_scale),
			'color_tokens': dict(self.color_tokens),
			'source': self.source,
			'issues': list(self.issues),
		}


@dataclass(slots=True)
class DesignSnapshot:
	"""Unified design snapshot — common language for all intelligence modules."""

	url: str = ''
	captured_at: str = field(default_factory=_utc_now)
	scan_id: str | None = None
	typography: TypographySnapshot = field(default_factory=TypographySnapshot)
	spacing: SpacingSnapshot = field(default_factory=SpacingSnapshot)
	colors: ColorSnapshot = field(default_factory=ColorSnapshot)
	layout: LayoutSnapshot = field(default_factory=LayoutSnapshot)
	grid: GridSnapshot = field(default_factory=GridSnapshot)
	hierarchy: HierarchySnapshot = field(default_factory=HierarchySnapshot)
	components: ComponentSnapshot = field(default_factory=ComponentSnapshot)
	motion: MotionSnapshot = field(default_factory=MotionSnapshot)
	accessibility: AccessibilitySnapshot = field(default_factory=AccessibilitySnapshot)
	design_tokens: DesignTokenSnapshot = field(default_factory=DesignTokenSnapshot)
	provenance: dict[str, Any] = field(default_factory=dict)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'url': self.url,
			'captured_at': self.captured_at,
			'scan_id': self.scan_id,
			'typography': self.typography.to_dict(),
			'spacing': self.spacing.to_dict(),
			'colors': self.colors.to_dict(),
			'layout': self.layout.to_dict(),
			'grid': self.grid.to_dict(),
			'hierarchy': self.hierarchy.to_dict(),
			'components': self.components.to_dict(),
			'motion': self.motion.to_dict(),
			'accessibility': self.accessibility.to_dict(),
			'design_tokens': self.design_tokens.to_dict(),
			'provenance': dict(self.provenance),
			'degraded': list(self.degraded),
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> DesignSnapshot:
		"""Rehydrate from serialized snapshot (e.g. reference registry)."""
		return cls(
			url=str(data.get('url') or ''),
			captured_at=str(data.get('captured_at') or _utc_now()),
			scan_id=data.get('scan_id'),
			typography=TypographySnapshot(**(data.get('typography') or {})),
			spacing=SpacingSnapshot(**(data.get('spacing') or {})),
			colors=ColorSnapshot(**(data.get('colors') or {})),
			layout=LayoutSnapshot(**(data.get('layout') or {})),
			grid=GridSnapshot(**(data.get('grid') or {})),
			hierarchy=HierarchySnapshot(**(data.get('hierarchy') or {})),
			components=ComponentSnapshot(**(data.get('components') or {})),
			motion=MotionSnapshot(**(data.get('motion') or {})),
			accessibility=AccessibilitySnapshot(**(data.get('accessibility') or {})),
			design_tokens=DesignTokenSnapshot(**(data.get('design_tokens') or {})),
			provenance=dict(data.get('provenance') or {}),
			degraded=list(data.get('degraded') or []),
		)
