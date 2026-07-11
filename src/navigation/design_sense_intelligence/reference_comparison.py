"""Reference comparison for Design Sense reviews — gated by page type and similarity."""
from __future__ import annotations

from navigation.design_reference_registry.comparison import infer_page_type
from navigation.design_snapshot_engine.models import DesignSnapshot


def compare_with_references(
	snapshot: DesignSnapshot,
	*,
	registry=None,
	limit: int = 3,
	user_task: str = '',
) -> tuple[list[dict], list[str]]:
	"""Return comparison dicts and recommendation notes for consensus (gated)."""
	if registry is None:
		from navigation.design_reference_registry.seeds import default_reference_registry

		reg = default_reference_registry()
	else:
		reg = registry

	page_type = infer_page_type(snapshot, user_task=user_task)
	comparisons = reg.find_similar(snapshot, limit=limit, user_task=user_task)
	notes: list[str] = []
	for cmp in comparisons:
		if cmp.similarity_score < 0.45:
			continue
		if cmp.gaps:
			notes.append(f'vs {cmp.reference_name}: {cmp.gaps[0]}')
		if cmp.recommendations and cmp.similarity_score >= 0.5:
			notes.append(cmp.recommendations[0])

	return [c.to_dict() for c in comparisons], notes
