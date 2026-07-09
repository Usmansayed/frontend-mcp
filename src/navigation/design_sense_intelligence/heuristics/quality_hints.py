"""Rule-based suggested fixes (no LLM)."""
from __future__ import annotations

from typing import Any


def build_suggested_fixes(
	*,
	blocking: list[str],
	warnings: list[str],
	console: dict[str, Any] | None,
	network: dict[str, Any] | None,
	visual: dict[str, Any] | None,
	audits: dict[str, dict[str, Any]],
) -> list[str]:
	hints: list[str] = []

	if console and (console.get('by_level', {}).get('error') or console.get('blocking')):
		hints.append('Console errors detected — use perception_console_get for filtered history.')
	if network and network.get('failed_count', 0) > 0:
		hints.append('Network failures detected — inspect data.network.failures and HAR artifact.')
	if network and network.get('slow_count', 0) > 0:
		hints.append('Slow requests detected — review data.network.slow_requests thresholds.')

	a11y = audits.get('accessibility') or {}
	if a11y and float(a11y.get('score') or 100) < 90:
		hints.append('Accessibility score below 90 — fix warnings in audits.accessibility.')
	perf = audits.get('performance') or {}
	if perf and float(perf.get('score') or 100) < 80:
		hints.append('Performance score below 80 — review audits.performance.metrics.')

	if visual:
		for item in visual.get('blocking') or []:
			if 'overflow' in str(item).lower():
				hints.append('Layout overflow — check CSS width/height and container constraints.')
				break
		for item in visual.get('blocking') or []:
			if 'overlap' in str(item).lower():
				hints.append('Overlapping elements — adjust z-index or layout spacing.')
				break

	if blocking and not hints:
		hints.append('Blocking issues present — address data.blocking before claiming UI work is done.')
	if warnings and len(hints) < 5:
		hints.append('Review data.warnings and re-run perception_verify after fixes.')

	seen: set[str] = set()
	out: list[str] = []
	for hint in hints:
		if hint not in seen:
			seen.add(hint)
			out.append(hint)
	return out[:12]
