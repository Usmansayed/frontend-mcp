"""Design Snapshot Engine — observe, extract, normalize, measure. Never critiques."""
from __future__ import annotations

from typing import Any

from .extractors import default_extractors
from .models import DesignSnapshot
from .protocol import DesignExtractor, merge_sections
from .raw_context import RawBrowserContext


class DesignSnapshotEngine:
	"""Convert live browser state into a unified DesignSnapshot."""

	def __init__(self, *, extractors: list[DesignExtractor] | None = None) -> None:
		self._extractors = extractors or default_extractors()

	async def capture_from_session(
		self,
		session: Any,
		*,
		visual_insights: dict[str, Any] | None = None,
		a11y_tree: str = '',
		dom_text: str = '',
		screenshot_ref: str | None = None,
		scan_id: str | None = None,
	) -> DesignSnapshot:
		"""Build snapshot from an active browser session."""
		if visual_insights is None:
			try:
				from navigation.design_sense_intelligence.heuristics.visual_insights import collect_visual_insights

				insights = await collect_visual_insights(session)
				visual_insights = insights.to_dict()
			except Exception:
				visual_insights = None

		context = await RawBrowserContext.from_session(
			session,
			visual_insights=visual_insights,
			a11y_tree=a11y_tree,
			dom_text=dom_text,
			screenshot_ref=screenshot_ref,
			scan_id=scan_id,
		)
		return self.capture_from_context(context)

	def capture_from_context(self, context: RawBrowserContext) -> DesignSnapshot:
		"""Run all extractors on pre-built raw context."""
		snapshot = DesignSnapshot(
			url=context.url,
			scan_id=context.scan_id,
			provenance={
				'element_count': len(context.elements),
				'extractors': [e.name for e in self._extractors],
				'elements': context.elements[:48],
			},
			degraded=list(context.degraded),
		)
		sections = [ext.extract(context) for ext in self._extractors]
		snapshot = merge_sections(snapshot, sections)
		if context.screenshot_ref:
			snapshot.provenance['screenshot_ref'] = context.screenshot_ref
		return snapshot

	def capture_from_fixture(self, data: dict[str, Any]) -> DesignSnapshot:
		"""Test/helper path without a browser."""
		context = RawBrowserContext.from_fixture(data)
		return self.capture_from_context(context)
