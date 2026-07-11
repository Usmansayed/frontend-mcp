"""Thin fix proposer — composes fix.recommend query only."""
from __future__ import annotations

from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.knowledge.envelope import KnowledgeResponse, Recommendation


class FixProposer:
	"""Phase 3 consumer — proposes fixes from graph standards, never owns rules."""

	def __init__(self, api: KnowledgeAPI) -> None:
		self._api = api

	def recommend(
		self,
		*,
		standard_id: str,
		selector: str = '',
		actual: dict[str, str] | None = None,
		project_id: str = 'default',
	) -> KnowledgeResponse:
		params: dict = {'standard_id': standard_id, 'selector': selector}
		if actual:
			params['actual'] = actual
		return self._api.query('fix.recommend', params, project_id=project_id)

	def recommendation(self, response: KnowledgeResponse) -> Recommendation | None:
		return response.recommendation
