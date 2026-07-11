"""Shared extractor utilities."""
from __future__ import annotations

import math
import re
from typing import Any


def parse_px(value: str | None) -> float | None:
	if not value:
		return None
	val = str(value).strip().lower()
	if val.endswith('px'):
		try:
			return float(val[:-2])
		except ValueError:
			return None
	if val.endswith('rem'):
		try:
			return float(val[:-3]) * 16.0
		except ValueError:
			return None
	return None


def parse_sides(value: str | None) -> list[float]:
	if not value:
		return []
	parts = [p for p in str(value).split() if p]
	out: list[float] = []
	for p in parts:
		px = parse_px(p)
		if px is not None:
			out.append(px)
	return out


def is_css_var(value: str | None) -> bool:
	return bool(value and 'var(--' in value)


def rgb_to_luminance(rgb: str) -> float | None:
	m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', rgb)
	if not m:
		return None
	r, g, b = (int(m.group(i)) / 255.0 for i in range(1, 4))

	def lin(c: float) -> float:
		return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

	r, g, b = lin(r), lin(g), lin(b)
	return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float | None:
	l1 = rgb_to_luminance(fg)
	l2 = rgb_to_luminance(bg)
	if l1 is None or l2 is None:
		return None
	light = max(l1, l2)
	dark = min(l1, l2)
	return (light + 0.05) / (dark + 0.05)


def infer_base_unit(values: list[float], candidates: tuple[int, ...] = (4, 8)) -> int | None:
	if not values:
		return None
	for unit in candidates:
		if all(abs(v % unit) < 0.01 or v == 0 for v in values if v > 0):
			return unit
	return None


def unique_sorted(values: list[float], *, limit: int = 24) -> list[float]:
	seen: set[float] = set()
	out: list[float] = []
	for v in sorted(values):
		rounded = round(v, 2)
		if rounded in seen:
			continue
		seen.add(rounded)
		out.append(rounded)
		if len(out) >= limit:
			break
	return out


def element_style(el: dict[str, Any]) -> dict[str, Any]:
	return el.get('style') if isinstance(el.get('style'), dict) else {}
