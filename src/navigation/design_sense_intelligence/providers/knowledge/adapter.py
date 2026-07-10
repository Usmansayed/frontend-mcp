"""Knowledge provider adapter — wraps first-class design knowledge."""
from __future__ import annotations

from ...knowledge.service import KnowledgeService
from ...models import ReviewRequest


class KnowledgeProvider:
	name = 'design_knowledge'
	kind = 'knowledge'
	lane = 'subjective'

	def __init__(self, service: KnowledgeService | None = None) -> None:
		self._service = service or KnowledgeService()

	async def contribute(self, request: ReviewRequest):
		return await self._service.contribute(request)
