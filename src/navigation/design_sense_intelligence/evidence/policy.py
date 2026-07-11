"""Evidence-first policy — every surfaced finding needs proof and rationale."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ..snapshot_access import resolve_snapshot


def enforce_evidence_policy(
	findings: list[ReviewFinding],
	*,
	request: ReviewRequest | None = None,
) -> list[ReviewFinding]:
	"""Drop findings that lack evidence, affected element, and rationale."""
	has_snapshot = resolve_snapshot(request) is not None if request else False
	kept: list[ReviewFinding] = []

	for f in findings:
		if _passes_evidence_gate(f, has_snapshot=has_snapshot):
			kept.append(f)

	return kept


def _passes_evidence_gate(finding: ReviewFinding, *, has_snapshot: bool) -> bool:
	has_target = bool(
		finding.affected_element or finding.selector or finding.region
	)
	has_why = bool(
		(finding.rationale or '').strip() or (finding.recommendation or '').strip()
	)
	has_proof = bool((finding.evidence or '').strip())

	if finding.severity == 'blocking':
		return has_proof or has_target

	if finding.severity == 'major':
		if has_proof and has_why:
			return True
		if has_target and has_proof:
			return True
		return has_target and has_why and finding.confirmed

	if not has_proof and not has_target:
		return False

	if not has_why:
		return False

	if has_snapshot and not has_proof and finding.severity == 'advisory':
		return False

	return has_proof or (has_target and finding.confirmed)
