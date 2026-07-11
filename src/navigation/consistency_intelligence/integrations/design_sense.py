"""Cross-module integration — Consistency Intelligence ↔ Design Sense."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.consistency_intelligence.service import ConsistencyIntelligenceService, _project_id_from_url


def load_project_design_knowledge(
	*,
	repo_root: str | Path | None,
	url: str | None,
	project_id: str | None = None,
) -> dict[str, Any]:
	"""Load PDG summary + key standards for Design Sense enrichment."""
	if not repo_root and not project_id:
		return {'degraded': ['no_repo_root_for_pdg']}

	pid = project_id or _project_id_from_url(url)
	service = ConsistencyIntelligenceService(repo_root=repo_root)
	summary = service.graph_summary(project_id=pid)

	standards_sample: list[dict[str, Any]] = []
	for std in summary.standards[:12]:
		standards_sample.append(std.to_dict())

	spacing = service.query('spacing.system', project_id=pid)
	typography = service.query('typography.scale', project_id=pid)

	return {
		'project_id': pid,
		'graph_version': summary.graph_version,
		'stats': summary.answer.get('stats'),
		'standards_sample': standards_sample,
		'spacing': spacing.answer.get('scales'),
		'typography': typography.answer.get('scales'),
		'overall_confidence': summary.confidence,
		'degraded': list(summary.degraded),
	}
