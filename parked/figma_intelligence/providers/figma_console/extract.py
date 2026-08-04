"""Map Figma Console MCP payloads to FigmaExtractionResult."""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.models import FigmaCandidate, FigmaExtractionResult


def normalize_kit_payload(
	candidate: FigmaCandidate,
	payload: dict[str, Any] | None,
	*,
	degraded: list[str],
) -> FigmaExtractionResult:
	if not payload:
		return FigmaExtractionResult(
			candidate_id=candidate.candidate_id,
			provider_id='figma_console',
			degraded=degraded + ['figma_console_kit_empty'],
		)

	tokens = _as_list(payload.get('tokens') or payload.get('variables') or [])
	components = _as_list(payload.get('components') or payload.get('componentSets') or [])
	variables = _as_list(payload.get('variables') or payload.get('variableCollections') or [])
	patterns = _as_list(payload.get('patterns') or payload.get('styles') or [])

	return FigmaExtractionResult(
		candidate_id=candidate.candidate_id,
		provider_id='figma_console',
		raw_payload=payload,
		tokens=tokens,
		components=components,
		variables=variables,
		patterns=patterns,
		screenshot_refs=_screenshot_refs(payload),
		degraded=list(degraded),
	)


def _as_list(value: Any) -> list[dict[str, Any]]:
	if isinstance(value, list):
		return [item for item in value if isinstance(item, dict)]
	if isinstance(value, dict):
		return [{'id': k, **v} if isinstance(v, dict) else {'id': k, 'value': v} for k, v in value.items()]
	return []


def _screenshot_refs(payload: dict[str, Any]) -> list[str]:
	refs: list[str] = []
	for key in ('screenshot', 'screenshotPath', 'imageUrl', 'preview'):
		val = payload.get(key)
		if isinstance(val, str) and val.strip():
			refs.append(val.strip())
	return refs
