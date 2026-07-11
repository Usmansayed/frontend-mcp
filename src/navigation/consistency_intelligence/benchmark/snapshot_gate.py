"""Design Snapshot quality gate — separates extraction vs knowledge readiness."""
from __future__ import annotations

from typing import Any


def snapshot_extraction_gate(snapshot: Any) -> dict[str, Any]:
	"""Check whether snapshot has enough signal for Discovery Pipeline."""
	issues: list[str] = []
	degraded: list[str] = []

	typography = getattr(snapshot, 'typography', None)
	spacing = getattr(snapshot, 'spacing', None)
	components = getattr(snapshot, 'components', None)
	tokens = getattr(snapshot, 'design_tokens', None)

	if typography and not typography.font_families and not typography.font_sizes_px:
		issues.append('typography_empty')
	if spacing and not spacing.padding_values_px and not spacing.margin_values_px:
		issues.append('spacing_empty')
	if components and not components.nodes and components.interactive_count == 0:
		issues.append('components_empty')
	if tokens and not tokens.css_variables and not tokens.color_tokens:
		degraded.append('tokens_sparse')

	snapshot_degraded = list(getattr(snapshot, 'degraded', []) or [])
	extraction_ok = len(issues) == 0

	return {
		'extraction_ok': extraction_ok,
		'knowledge_ready': extraction_ok and len(issues) + len(snapshot_degraded) < 3,
		'issues': issues,
		'degraded': degraded + snapshot_degraded,
		'failure_class': None if extraction_ok else 'extraction',
	}
