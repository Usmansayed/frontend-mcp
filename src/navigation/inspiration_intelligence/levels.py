"""Inspiration effort levels — agent picks one; MCP executes search budgets.

Levels choose **how hard to hunt** (concurrency, sources, timeouts) — not a hard
cap on how many refs the agent may keep. Soft-stop is only an early-exit hint for
latency; pass target_refs / keep looking if you want a bigger pack.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


# Agent-facing ids (keep short).
INSPIRATION_LEVELS = ('light', 'standard', 'wide', 'max')


@dataclass(frozen=True)
class InspirationLevelPlan:
	"""Executable search budgets for one collect/discover episode.

	Not a ref quota. soft_stop_refs = “enough to stop hunting for speed”;
	the agent may request more or keep more of what arrived.
	"""

	level: str
	use_registered_providers: bool
	max_queries: int
	http_concurrency: int
	provider_timeout_s: float
	use_multi_scout: bool
	max_sources: int
	scout_concurrency: int
	scout_timeout_s: float
	top_n: int
	# Soft early-exit hint only (not a hard max on returned hits).
	soft_stop_refs: int
	# How many visuals multi-scout should try to acquire when it runs.
	scout_acquire: int
	allow_screenshots: bool
	include_live_sites: bool
	include_browser_galleries: bool
	# Channel C — DuckDuckGo search → OG thumbs → optional live screenshots
	include_web_search: bool
	max_web_search: int
	max_web_og: int
	max_web_screenshots: int
	budget_s: float
	overlap_scout: bool
	think: str

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)

	@property
	def hard_deadline_s(self) -> float:
		"""Fail-closed wall clock so MCP never hangs on WAF Chromium."""
		return max(self.budget_s * 1.25, self.budget_s + 2.0)

	# Back-compat alias used by older call sites / tests.
	@property
	def max_visuals(self) -> int:
		return self.scout_acquire


# How to think (also mirrored in the short guide).
LEVEL_THINK: dict[str, str] = {
	'light': (
		'Look already clear, or need a quick pulse. '
		'HTTP galleries / pattern CDN — small hunt. Empty packs still get a web rescue.'
	),
	'standard': (
		'Normal new UI / landing / dashboard. Default effort. '
		'Pattern CDN + DuckDuckGo search/OG thumbs; corpus scout if thin. '
		'Soft-stop when a usable pack exists — not a ref ceiling.'
	),
	'wide': (
		'Unsure which gallery fits; want variety. '
		'Broader scout + web search + a few live page screenshots. Refs are not capped.'
	),
	'max': (
		'Research / motion / demos / deep hunt. '
		'Widest scout + web search screenshots + famous live sites + browser galleries.'
	),
}

_LEVEL_PLANS: dict[str, InspirationLevelPlan] = {
	'light': InspirationLevelPlan(
		level='light',
		use_registered_providers=True,
		max_queries=1,
		http_concurrency=4,
		provider_timeout_s=5.0,
		use_multi_scout=False,
		max_sources=0,
		scout_concurrency=0,
		scout_timeout_s=0.0,
		top_n=0,
		soft_stop_refs=4,
		scout_acquire=4,
		allow_screenshots=False,
		include_live_sites=False,
		include_browser_galleries=False,
		include_web_search=False,
		max_web_search=4,
		max_web_og=3,
		max_web_screenshots=0,
		budget_s=5.0,
		overlap_scout=False,
		think=LEVEL_THINK['light'],
	),
	'standard': InspirationLevelPlan(
		level='standard',
		use_registered_providers=True,
		max_queries=3,
		http_concurrency=5,
		provider_timeout_s=6.0,
		use_multi_scout=True,
		max_sources=8,
		scout_concurrency=8,
		scout_timeout_s=0.9,
		top_n=3,
		soft_stop_refs=8,
		scout_acquire=8,
		allow_screenshots=False,
		include_live_sites=False,
		include_browser_galleries=False,
		include_web_search=True,
		max_web_search=8,
		max_web_og=6,
		max_web_screenshots=0,
		budget_s=10.0,
		overlap_scout=True,
		think=LEVEL_THINK['standard'],
	),
	'wide': InspirationLevelPlan(
		level='wide',
		use_registered_providers=True,
		max_queries=4,
		http_concurrency=5,
		provider_timeout_s=6.0,
		use_multi_scout=True,
		max_sources=14,
		scout_concurrency=12,
		scout_timeout_s=1.0,
		top_n=4,
		soft_stop_refs=12,
		scout_acquire=12,
		allow_screenshots=True,
		include_live_sites=False,
		include_browser_galleries=False,
		include_web_search=True,
		max_web_search=10,
		max_web_og=8,
		# Wide: OG thumbs only — Chromium SS reserved for max (or allow_browser_screenshot)
		max_web_screenshots=0,
		budget_s=16.0,
		overlap_scout=True,
		think=LEVEL_THINK['wide'],
	),
	'max': InspirationLevelPlan(
		level='max',
		use_registered_providers=True,
		max_queries=5,
		http_concurrency=5,
		provider_timeout_s=8.0,
		use_multi_scout=True,
		max_sources=20,
		scout_concurrency=14,
		scout_timeout_s=1.5,
		top_n=5,
		soft_stop_refs=16,
		scout_acquire=16,
		allow_screenshots=True,
		include_live_sites=True,
		include_browser_galleries=True,
		include_web_search=True,
		max_web_search=12,
		max_web_og=8,
		# Cap SS count — cooldown + deadline do the rest
		max_web_screenshots=2,
		budget_s=28.0,
		overlap_scout=True,
		think=LEVEL_THINK['max'],
	),
}


def resolve_inspiration_level(
	level: str | None = None,
	*,
	mode: str | None = None,
) -> InspirationLevelPlan:
	"""Map inspiration_level (preferred) or legacy mode → plan.

	Legacy: fast→standard, broad→wide, deep→max.
	"""
	raw = (level or '').strip().lower()
	if raw in _LEVEL_PLANS:
		return _LEVEL_PLANS[raw]
	aliases = {
		'l1': 'light',
		'spark': 'light',
		'fast': 'light',
		'l2': 'standard',
		'default': 'standard',
		'l3': 'wide',
		'sweep': 'wide',
		'broad': 'wide',
		'l4': 'max',
		'deep': 'max',
		'research': 'max',
	}
	if raw in aliases:
		return _LEVEL_PLANS[aliases[raw]]
	mode_l = (mode or '').strip().lower()
	if mode_l in {'fast', ''}:
		return _LEVEL_PLANS['standard']
	if mode_l == 'broad':
		return _LEVEL_PLANS['wide']
	if mode_l == 'deep':
		return _LEVEL_PLANS['max']
	return _LEVEL_PLANS['standard']


def next_inspiration_level(level: str | None) -> str:
	"""Bump one step: light→standard→wide→max (max stays max)."""
	cur = resolve_inspiration_level(level).level
	idx = INSPIRATION_LEVELS.index(cur) if cur in INSPIRATION_LEVELS else 1
	return INSPIRATION_LEVELS[min(idx + 1, len(INSPIRATION_LEVELS) - 1)]


def levels_card() -> dict[str, Any]:
	"""Compact chooser for agent_summary / guide."""
	return {
		'resource': 'perception://guide/inspiration',
		'rule': (
			'Look at the task. Pick ONE inspiration_level (search effort). '
			'Levels are not a hard ref quota — soft-stop only ends the hunt early for speed. '
			'You decide what to borrow.'
		),
		'levels': [
			{
				'id': lid,
				'budget_s': _LEVEL_PLANS[lid].budget_s,
				'think': LEVEL_THINK[lid],
				'scout_sources': _LEVEL_PLANS[lid].max_sources,
				'concurrency': _LEVEL_PLANS[lid].scout_concurrency
				or _LEVEL_PLANS[lid].http_concurrency,
				'soft_stop_refs': _LEVEL_PLANS[lid].soft_stop_refs,
				'browser_galleries': _LEVEL_PLANS[lid].include_browser_galleries,
			}
			for lid in INSPIRATION_LEVELS
		],
	}
