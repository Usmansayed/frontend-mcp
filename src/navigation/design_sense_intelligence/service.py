"""Design sense intelligence service facade."""
from __future__ import annotations

from navigation.design_sense_intelligence.heuristics.quality_hints import build_suggested_fixes
from navigation.design_sense_intelligence.models import DesignReviewReport, ReviewRequest
from navigation.design_sense_intelligence.reviewers.coordinator import ReviewCoordinator
from navigation.design_sense_intelligence.snapshot_access import enrich_request


class DesignSenseService:
	"""Facade for design review, critique, and UX reasoning — does not generate UI or extract DOM."""

	def __init__(self, *, coordinator: ReviewCoordinator | None = None) -> None:
		self._coordinator = coordinator or ReviewCoordinator()

	async def review(
		self,
		request: ReviewRequest,
		*,
		compare_references: bool = True,
	) -> DesignReviewReport:
		"""Run full specialist + provider orchestration over structured snapshot inputs."""
		enriched = enrich_request(request)
		return await self._coordinator.run(enriched, compare_references=compare_references)

	@staticmethod
	async def collect_visual_insights_from_page(page) -> dict:
		"""Deprecated — use DesignSnapshotService.capture() instead."""
		from navigation.design_sense_intelligence.heuristics.visual_insights import collect_visual_insights

		insights = await collect_visual_insights(page)
		return insights.to_dict() if hasattr(insights, 'to_dict') else dict(insights)

	collect_visual_insights = staticmethod(collect_visual_insights_from_page)
	build_suggested_fixes = staticmethod(build_suggested_fixes)

	def list_providers(self) -> list[dict[str, str]]:
		return self._coordinator._providers.list_providers()

	def list_reviewers(self) -> list[str]:
		return [r.name for r in self._coordinator._reviewers]
