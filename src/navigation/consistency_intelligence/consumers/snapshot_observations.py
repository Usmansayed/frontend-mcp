"""Extract assessable observations from a DesignSnapshot for batch audit."""
from __future__ import annotations

from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot

_STYLE_MAP = {
	'padding': 'padding',
	'fontSize': 'font-size',
	'borderRadius': 'border-radius',
	'color': 'color',
	'backgroundColor': 'background-color',
	'gap': 'gap',
	'margin': 'margin',
}


def observations_from_snapshot(snapshot: DesignSnapshot | dict[str, Any]) -> list[dict[str, Any]]:
	"""Yield {selector, context, actual} dicts for consistency assessment."""
	if isinstance(snapshot, dict):
		snapshot = DesignSnapshot.from_dict(snapshot)

	out: list[dict[str, Any]] = []
	seen: set[str] = set()

	for node in snapshot.components.nodes:
		selector = str(node.get('selector') or node.get('tag') or '')
		if not selector or selector in seen:
			continue
		seen.add(selector)
		tag = str(node.get('tag') or '').lower()
		actual = _style_actuals(node.get('style') or {})
		if not actual:
			continue
		out.append({
			'selector': selector,
			'context': tag or 'element',
			'actual': actual,
		})

	for row in snapshot.spacing.matrix[:30]:
		selector = str(row.get('selector') or row.get('tag') or '')
		if not selector or selector in seen:
			continue
		actual: dict[str, str] = {}
		if row.get('gap_px') is not None:
			actual['gap'] = f"{row['gap_px']}px"
		pad = row.get('padding_px') or []
		if pad:
			actual['padding'] = f"{pad[0]}px" if len(pad) == 1 else str(pad)
		if actual:
			seen.add(selector)
			out.append({
				'selector': selector,
				'context': str(row.get('tag') or 'element').lower(),
				'actual': actual,
			})

	return out


def _style_actuals(style: dict[str, Any]) -> dict[str, str]:
	actual: dict[str, str] = {}
	for style_key, prop in _STYLE_MAP.items():
		val = style.get(style_key)
		if val is not None and str(val).strip():
			actual[prop] = str(val).strip()
	return actual
