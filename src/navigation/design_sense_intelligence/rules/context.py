"""Lint context — DOM / computed style target (replaces Figma node in Design Lint)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StyleSnapshot:
	selector: str
	tag: str
	font_size: str | None = None
	font_family: str | None = None
	color: str | None = None
	background_color: str | None = None
	margin: str | None = None
	padding: str | None = None
	border_radius: str | None = None
	box_shadow: str | None = None
	border: str | None = None
	classes: list[str] = field(default_factory=list)
	uses_css_var: bool = False
	text: str = ''

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> StyleSnapshot:
		classes = data.get('classes') or []
		if isinstance(classes, str):
			classes = classes.split()
		style = data.get('style') or data
		combined = ' '.join(str(v) for v in style.values()) if isinstance(style, dict) else ''
		return cls(
			selector=str(data.get('selector', '')),
			tag=str(data.get('tag', 'unknown')),
			font_size=_pick(style, 'fontSize', 'font-size'),
			font_family=_pick(style, 'fontFamily', 'font-family'),
			color=_pick(style, 'color'),
			background_color=_pick(style, 'backgroundColor', 'background-color'),
			margin=_pick(style, 'margin'),
			padding=_pick(style, 'padding'),
			border_radius=_pick(style, 'borderRadius', 'border-radius'),
			box_shadow=_pick(style, 'boxShadow', 'box-shadow'),
			border=_pick(style, 'border'),
			classes=list(classes),
			uses_css_var='var(--' in combined,
			text=str(data.get('text', ''))[:80],
		)


def _pick(style: Any, *keys: str) -> str | None:
	if not isinstance(style, dict):
		return None
	for key in keys:
		val = style.get(key)
		if val is not None and str(val).strip():
			return str(val)
	return None


@dataclass(slots=True)
class LintContext:
	elements: list[StyleSnapshot] = field(default_factory=list)
	design_tokens: dict[str, Any] = field(default_factory=dict)
	spacing_scale: list[int] = field(default_factory=lambda: [0, 4, 8, 12, 16, 24, 32, 48, 64])
	radius_scale: list[int] = field(default_factory=lambda: [0, 4, 6, 8, 12, 16, 9999])
	allowed_font_sizes: list[int] = field(default_factory=lambda: [12, 14, 16, 18, 20, 24, 30, 36])

	@classmethod
	def from_request(cls, request) -> LintContext:
		from ..models import ReviewRequest

		if not isinstance(request, ReviewRequest):
			return cls()
		elements = []
		for item in request.computed_styles or []:
			if isinstance(item, dict):
				elements.append(StyleSnapshot.from_dict(item))
		tokens = dict(request.design_tokens or {})
		spacing = tokens.get('spacing') or tokens.get('spacingScale')
		if isinstance(spacing, list):
			scale = [int(x) for x in spacing if str(x).isdigit()]
			if scale:
				return cls(elements=elements, design_tokens=tokens, spacing_scale=scale)
		return cls(elements=elements, design_tokens=tokens)
