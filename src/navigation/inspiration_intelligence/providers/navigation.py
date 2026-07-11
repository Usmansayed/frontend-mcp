"""Provider navigation knowledge — selectors, flows, timing (no copyrighted content)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ProviderNavigationKnowledge:
	"""Stable navigation contract for one inspiration site."""

	provider_id: str
	display_name: str
	base_url: str
	search_url_pattern: str  # e.g. https://dribbble.com/search/{query_slug}
	detail_url_pattern: str  # e.g. https://dribbble.com/shots/{shot_id}
	result_card_selector: str
	result_link_selector: str
	title_selector: str
	preview_image_selector: str
	pagination_kind: str  # infinite_scroll | numbered | load_more | none
	hydration_wait_ms: int = 8000
	headless_reliable: bool = False
	anti_bot_notes: list[str] = field(default_factory=list)
	navigation_flow: list[str] = field(default_factory=list)
	stable_anchors: list[str] = field(default_factory=list)

	def search_url(self, query_slug: str) -> str:
		return self.search_url_pattern.format(query_slug=query_slug)

	def detail_url(self, external_id: str) -> str:
		return self.detail_url_pattern.format(external_id=external_id)
