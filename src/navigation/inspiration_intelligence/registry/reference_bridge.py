"""Reference Registry bridge — persist valuable captures."""
from __future__ import annotations

from navigation.inspiration_intelligence.adapters.ecosystem import to_design_snapshot_payload
from navigation.inspiration_intelligence.models import InspirationCaptureResult, InspirationIntent


def register_captures(
	captures: list[InspirationCaptureResult],
	*,
	intent: InspirationIntent,
) -> tuple[list[str], list[str]]:
	"""Register captures in design_reference_registry (scaffold)."""
	_ = intent
	degraded: list[str] = ['reference_registry_register_scaffold']
	ids: list[str] = []
	for capture in captures:
		payload = to_design_snapshot_payload(capture)
		ref_id = f'inspiration:{capture.provider_id}:{capture.candidate_id}'
		ids.append(ref_id)
		_ = payload
	return ids, degraded
