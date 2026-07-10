"""Design sense intelligence service facade."""
from __future__ import annotations

from navigation.design_sense_intelligence.heuristics.visual_insights import collect_visual_insights
from navigation.design_sense_intelligence.heuristics.quality_hints import build_suggested_fixes
from navigation.design_sense_intelligence.models import DesignReviewReport, ReviewRequest
from navigation.design_sense_intelligence.reviewers.coordinator import ReviewCoordinator


class DesignSenseService:
	"""Facade for design review, critique, and UX reasoning — does not generate UI."""

	def __init__(self, *, coordinator: ReviewCoordinator | None = None) -> None:
		self._coordinator = coordinator or ReviewCoordinator()

	async def review(self, request: ReviewRequest) -> DesignReviewReport:
		"""Run full specialist + provider orchestration review."""
		enriched = await self._enrich_request(request)
		return await self._coordinator.run(enriched)

	async def _enrich_request(self, request: ReviewRequest) -> ReviewRequest:
		"""Attach visual insights when preview_url present and insights missing."""
		if request.visual_insights or not request.preview_url:
			return request
		# Future: wire perception_observe scan_id → visual_insights
		return request

	@staticmethod
	async def collect_visual_insights_from_page(page) -> dict:
		insights = await collect_visual_insights(page)
		return insights.to_dict() if hasattr(insights, 'to_dict') else dict(insights)

	collect_visual_insights = staticmethod(collect_visual_insights)
	build_suggested_fixes = staticmethod(build_suggested_fixes)

	def list_providers(self) -> list[dict[str, str]]:
		return self._coordinator._providers.list_providers()

	def list_reviewers(self) -> list[str]:
		return [r.name for r in self._coordinator._reviewers]
