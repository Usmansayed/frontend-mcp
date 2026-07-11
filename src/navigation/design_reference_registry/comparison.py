"""Structural snapshot comparison — not image-based."""
from __future__ import annotations

from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot

from .models import SnapshotComparison


def _jaccard(a: set[str], b: set[str]) -> float:
	if not a and not b:
		return 1.0
	if not a or not b:
		return 0.0
	return len(a & b) / len(a | b)


def _snapshot_features(snapshot: DesignSnapshot | dict[str, Any]) -> dict[str, set[str]]:
	if isinstance(snapshot, DesignSnapshot):
		data = snapshot.to_dict()
	else:
		data = snapshot

	typo = data.get('typography') or {}
	colors = data.get('colors') or {}
	spacing = data.get('spacing') or {}
	components = data.get('components') or {}

	return {
		'font_families': set(typo.get('font_families') or []),
		'font_sizes': {str(s) for s in (typo.get('font_sizes_px') or [])},
		'palette': {p.get('value', '') for p in (colors.get('palette') or []) if p.get('value')},
		'spacing': {str(s) for s in (spacing.get('padding_values_px') or [])},
		'patterns': {p.get('name', '') for p in (components.get('patterns') or [])},
	}


def compare_snapshots(
	current: DesignSnapshot,
	reference: DesignSnapshot,
	*,
	reference_id: str = '',
	reference_name: str = '',
) -> SnapshotComparison:
	"""Compare two snapshots structurally."""
	cur = _snapshot_features(current)
	ref = _snapshot_features(reference)
	dimensions: dict[str, float] = {}
	for key in cur:
		dimensions[key] = round(_jaccard(cur[key], ref[key]), 3)

	overall = round(sum(dimensions.values()) / max(len(dimensions), 1), 3)
	gaps: list[str] = []
	recs: list[str] = []

	if dimensions.get('font_families', 0) < 0.5:
		gaps.append('Typography families differ from reference')
		recs.append('Align font stack with reference product typography')
	if dimensions.get('palette', 0) < 0.4:
		gaps.append('Color palette diverges from reference')
		recs.append('Review semantic color roles against reference palette')
	if dimensions.get('spacing', 0) < 0.5:
		gaps.append('Spacing scale differs')
		recs.append('Normalize spacing to reference 4pt/8pt scale')

	return SnapshotComparison(
		reference_id=reference_id,
		reference_name=reference_name,
		similarity_score=overall,
		dimension_scores=dimensions,
		recommendations=recs,
		gaps=gaps,
	)


_MIN_REFERENCE_SIMILARITY = 0.45
_MIN_LAYOUT_SIMILARITY = 0.35

_PAGE_TYPE_ALIASES: dict[str, set[str]] = {
	'auth': {'auth', 'login', 'signin'},
	'checkout': {'checkout', 'storefront', 'ecommerce', 'cart'},
	'dashboard': {'dashboard', 'admin', 'analytics'},
	'landing': {'landing', 'marketing', 'home'},
	'forms': {'forms', 'validation', 'wizard'},
	'editor': {'editor', 'document'},
	'product': {'product', 'detail', 'listing'},
}


def infer_page_type(snapshot: DesignSnapshot, *, user_task: str = '') -> str:
	"""Infer page type from URL, task, and component patterns."""
	task = (user_task or '').lower()
	url = (snapshot.url or '').lower()
	patterns = {
		str(p.get('name', '')).lower()
		for p in (snapshot.components.patterns or [])
	}

	if any(k in task for k in ('checkout', 'cart', 'shipping', 'payment')):
		return 'checkout'
	if any(k in task for k in ('sign in', 'login', 'auth', 'register')):
		return 'auth'
	if any(k in task for k in ('dashboard', 'analytics', 'admin')):
		return 'dashboard'
	if 'form' in task or 'validation' in task:
		return 'forms'
	if any(k in url for k in ('login', 'signin', 'auth')):
		return 'auth'
	if any(k in url for k in ('checkout', 'cart')):
		return 'checkout'
	if 'form' in patterns or 'input' in patterns:
		return 'forms'
	if 'nav' in patterns or 'sidebar' in patterns:
		return 'dashboard'
	return 'landing'


def _page_types_compatible(current: str, reference: str) -> bool:
	if not current or not reference:
		return True
	cur = _PAGE_TYPE_ALIASES.get(current, {current})
	ref = _PAGE_TYPE_ALIASES.get(reference, {reference})
	return bool(cur & ref) or current == reference


def _reference_page_type(entry) -> str:
	from .models import ReferenceEntry

	if not isinstance(entry, ReferenceEntry):
		return ''
	meta = (entry.snapshot or {}).get('provenance', {}).get('reference_meta', {})
	return str(meta.get('page_type', '') or '')


def should_compare_reference(
	current: DesignSnapshot,
	entry,
	cmp: SnapshotComparison,
	*,
	current_page_type: str = '',
) -> bool:
	"""Gate reference comparison — same page type, similar layout, high confidence."""
	from .models import ReferenceEntry

	if not isinstance(entry, ReferenceEntry):
		return False
	if cmp.similarity_score < _MIN_REFERENCE_SIMILARITY:
		return False

	ref_type = _reference_page_type(entry)
	if current_page_type and ref_type and not _page_types_compatible(current_page_type, ref_type):
		return False

	layout_sim = cmp.dimension_scores.get('patterns', cmp.similarity_score)
	if layout_sim < _MIN_LAYOUT_SIMILARITY and cmp.similarity_score < 0.55:
		return False

	return True


def find_similar_references(
	current: DesignSnapshot,
	entries: list,
	*,
	limit: int = 5,
	user_task: str = '',
) -> list[SnapshotComparison]:
	from .models import ReferenceEntry

	current_type = infer_page_type(current, user_task=user_task)
	results: list[SnapshotComparison] = []
	for entry in entries:
		if not isinstance(entry, ReferenceEntry):
			continue
		ref_snap = DesignSnapshot.from_dict(entry.snapshot)
		cmp = compare_snapshots(current, ref_snap, reference_id=entry.id, reference_name=entry.name)
		if should_compare_reference(current, entry, cmp, current_page_type=current_type):
			results.append(cmp)
	results.sort(key=lambda c: -c.similarity_score)
	return results[:limit]
