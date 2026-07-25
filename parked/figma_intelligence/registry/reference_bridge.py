"""Reference Registry bridge — persist valuable extractions."""
from __future__ import annotations

from navigation.figma_intelligence.adapters.ecosystem import to_design_snapshot_payload
from navigation.figma_intelligence.models import FigmaExtractionResult, FigmaIntent


def register_extractions(
	extractions: list[FigmaExtractionResult],
	*,
	intent: FigmaIntent,
) -> tuple[list[str], list[str]]:
	"""Register extractions in design_reference_registry (scaffold)."""
	_ = intent
	degraded: list[str] = ['reference_registry_register_scaffold']
	ids: list[str] = []
	for extraction in extractions:
		payload = to_design_snapshot_payload(extraction)
		ref_id = f'figma:{extraction.provider_id}:{extraction.candidate_id}'
		ids.append(ref_id)
		_ = payload  # wire to design_reference_registry when execution phase starts
	return ids, degraded
