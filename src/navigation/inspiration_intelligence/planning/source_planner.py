"""Intent → source planner taxonomy (galleries + famous-site categories + modes).

Research deliverable R1 — deterministic routing for Inspiration Intelligence.
Modes:
  fast  — HTTP/CDN galleries only; optional 0–2 famous sites
  broad — HTTP + limited browser galleries + more famous sites
  deep  — full cascade including WAF galleries
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from navigation.inspiration_intelligence.planning.progressive_search import (
	FAST_HTTP_PROVIDER_ORDER,
)
from navigation.inspiration_intelligence.planning.search_planner import DEFAULT_PROVIDER_PRIORITY


class InspirationMode(str, Enum):
	FAST = 'fast'
	BROAD = 'broad'
	DEEP = 'deep'


# Intent class → gallery query hints + famous-site category keys.
INTENT_SOURCE_TAXONOMY: dict[str, dict[str, Any]] = {
	'landing': {
		'gallery_queries': ['saas landing page', 'marketing landing ui', 'hero landing design'],
		'famous_categories': ['marketing'],
		'prefer_providers': ['onepagelove', 'lapa', 'behance', 'httpster'],
	},
	'marketing': {
		'gallery_queries': ['saas marketing site', 'product landing page'],
		'famous_categories': ['marketing'],
		'prefer_providers': ['onepagelove', 'lapa', 'behance'],
	},
	'dashboard': {
		'gallery_queries': ['admin dashboard ui', 'analytics dashboard', 'saas dashboard'],
		'famous_categories': ['dashboard'],
		'prefer_providers': ['behance', 'lapa', 'onepagelove', 'httpster'],
	},
	'admin': {
		'gallery_queries': ['admin panel ui', 'crm dashboard'],
		'famous_categories': ['dashboard'],
		'prefer_providers': ['behance', 'lapa', 'onepagelove'],
	},
	'ecommerce': {
		'gallery_queries': ['ecommerce storefront', 'product page ui', 'checkout form'],
		'famous_categories': ['ecommerce'],
		'prefer_providers': ['behance', 'onepagelove', 'lapa', 'httpster'],
	},
	'checkout': {
		'gallery_queries': ['checkout form ui', 'payment form design'],
		'famous_categories': ['ecommerce', 'auth'],
		'prefer_providers': ['behance', 'onepagelove', 'lapa'],
	},
	'docs': {
		'gallery_queries': ['documentation site design', 'developer docs ui'],
		'famous_categories': ['docs'],
		'prefer_providers': ['onepagelove', 'lapa', 'httpster'],
	},
	'auth': {
		'gallery_queries': ['login page ui', 'signup form interface'],
		'famous_categories': ['auth'],
		'prefer_providers': ['behance', 'onepagelove', 'lapa'],
	},
	'onboarding': {
		'gallery_queries': ['onboarding ui', 'product tour interface'],
		'famous_categories': ['auth', 'marketing'],
		'prefer_providers': ['behance', 'onepagelove', 'lapa'],
	},
	'mobile': {
		'gallery_queries': ['mobile app ui', 'mobile interface design'],
		'famous_categories': ['marketing'],
		'prefer_providers': ['behance', 'onepagelove', 'lapa'],
	},
	'saas': {
		'gallery_queries': ['saas landing page', 'saas product ui'],
		'famous_categories': ['marketing', 'dashboard'],
		'prefer_providers': ['onepagelove', 'lapa', 'behance'],
	},
	'navigation': {
		'gallery_queries': [
			'website navigation header menu',
			'mega menu navbar ui',
			'site header navigation design',
		],
		'famous_categories': ['marketing'],
		'prefer_providers': ['behance', 'lapa', 'onepagelove', 'httpster'],
	},
	'default': {
		'gallery_queries': [],
		'famous_categories': ['marketing'],
		'prefer_providers': list(FAST_HTTP_PROVIDER_ORDER),
	},
}

# Mode → provider sets and budgets (stop rules applied by collect).
MODE_POLICY: dict[InspirationMode, dict[str, Any]] = {
	InspirationMode.FAST: {
		'providers': list(FAST_HTTP_PROVIDER_ORDER),
		'include_browser_galleries': False,
		'max_famous_sites': 2,
		'max_queries': 2,
		'target_refs': 5,
		'min_refs': 3,
		'http_concurrency': 5,
		'browser_concurrency': 0,
		'budget_note': 'discover <3s p50; collect usable pack <15s p50',
	},
	InspirationMode.BROAD: {
		# Breadth comes from multi-scout corpus, not WAF Chromium galleries.
		'providers': list(FAST_HTTP_PROVIDER_ORDER) + ['siteinspire'],
		'include_browser_galleries': False,
		'max_famous_sites': 2,
		'max_queries': 3,
		'target_refs': 5,
		'min_refs': 3,
		'http_concurrency': 5,
		'browser_concurrency': 0,
		'budget_note': 'HTTP + siteinspire; corpus multi-scout for breadth; no WAF browsers',
	},
	InspirationMode.DEEP: {
		'providers': list(DEFAULT_PROVIDER_PRIORITY),
		'include_browser_galleries': True,
		'max_famous_sites': 4,
		'max_queries': 5,
		'target_refs': 5,
		'min_refs': 3,
		'http_concurrency': 5,
		'browser_concurrency': 1,
		'budget_note': 'explicit research; at most one browser gallery at a time; hard timeouts',
	},
}


@dataclass
class SourcePlan:
	"""Planner output — which channels / providers / famous sites to fire."""

	mode: InspirationMode
	intent_class: str
	gallery_queries: list[str] = field(default_factory=list)
	provider_ids: list[str] = field(default_factory=list)
	famous_categories: list[str] = field(default_factory=list)
	max_famous_sites: int = 0
	http_concurrency: int = 5
	browser_concurrency: int = 0
	target_refs: int = 5
	min_refs: int = 3
	max_queries: int = 3
	channels: list[str] = field(default_factory=list)
	stop_rules: dict[str, Any] = field(default_factory=dict)
	notes: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'mode': self.mode.value,
			'intent_class': self.intent_class,
			'gallery_queries': list(self.gallery_queries),
			'provider_ids': list(self.provider_ids),
			'famous_categories': list(self.famous_categories),
			'max_famous_sites': self.max_famous_sites,
			'http_concurrency': self.http_concurrency,
			'browser_concurrency': self.browser_concurrency,
			'target_refs': self.target_refs,
			'min_refs': self.min_refs,
			'max_queries': self.max_queries,
			'channels': list(self.channels),
			'stop_rules': dict(self.stop_rules),
			'notes': list(self.notes),
		}


def classify_intent_class(query: str, target_styles: list[str] | None = None) -> str:
	"""Map free-text / style tags to a taxonomy key."""
	text = (query or '').strip().lower()
	styles = [s.lower() for s in (target_styles or [])]

	# Prefer explicit style tags from intent parser.
	priority = [
		'checkout',
		'docs',
		'auth',
		'onboarding',
		'ecommerce',
		'dashboard',
		'admin',
		'landing',
		'marketing',
		'mobile',
		'saas',
		'navigation',
	]
	for key in priority:
		if key in styles:
			return key

	# Keyword fallbacks (checkout before ecommerce; docs/auth before generic).
	checks: list[tuple[str, tuple[str, ...]]] = [
		('checkout', ('checkout', 'cart', 'payment form')),
		('docs', ('documentation', ' docs', 'api reference', 'developer docs')),
		('auth', ('login', 'sign in', 'signup', 'sign up', 'auth')),
		('onboarding', ('onboarding', 'product tour', 'getting started ui')),
		('ecommerce', ('ecommerce', 'e-commerce', 'shop', 'storefront')),
		('navigation', ('navbar', 'nav bar', 'mega menu', 'navigation bar', 'header nav', 'sidebar nav')),
		('dashboard', ('dashboard', 'analytics', 'crm', 'console')),
		('admin', ('admin panel', 'admin ui')),
		('landing', ('landing', 'homepage', 'hero')),
		('marketing', ('marketing', 'marketing site')),
		('mobile', ('mobile app', 'mobile ui', 'ios', 'android')),
		('saas', ('saas',)),
	]
	for key, needles in checks:
		if any(n in text for n in needles):
			return key
	return 'default'


def resolve_mode(mode: str | InspirationMode | None = None) -> InspirationMode:
	if isinstance(mode, InspirationMode):
		return mode
	raw = (mode or '').strip().lower()
	if raw in {'broad', 'breadth'}:
		return InspirationMode.BROAD
	if raw in {'deep', 'research', 'full'}:
		return InspirationMode.DEEP
	if raw in {'fast', 'scout', 'default', ''}:
		# Empty → honor INSPIRATION_FAST env via caller; default fast for planner.
		return InspirationMode.FAST
	return InspirationMode.FAST


def build_source_plan(
	query: str,
	*,
	mode: str | InspirationMode | None = None,
	target_styles: list[str] | None = None,
	provider_ids: list[str] | None = None,
	intent_class_override: str | None = None,
) -> SourcePlan:
	"""Decide galleries + famous-site categories for an intent."""
	resolved_mode = resolve_mode(mode)
	intent_class = (intent_class_override or '').strip() or classify_intent_class(
		query, target_styles
	)
	if intent_class not in INTENT_SOURCE_TAXONOMY:
		intent_class = classify_intent_class(query, target_styles)
	tax = INTENT_SOURCE_TAXONOMY.get(intent_class) or INTENT_SOURCE_TAXONOMY['default']
	policy = MODE_POLICY[resolved_mode]

	providers = list(provider_ids) if provider_ids else list(policy['providers'])
	# Soft preference: move taxonomy prefer_providers earlier without dropping others.
	# Always keep WAF/browser galleries AFTER HTTP so fast path never peels dribbble first.
	from navigation.inspiration_intelligence.concurrent import BROWSER_HEAVY_PROVIDERS

	prefer = [p for p in tax.get('prefer_providers', []) if p in providers]
	if prefer and not provider_ids:
		prefer_http = [p for p in prefer if p not in BROWSER_HEAVY_PROVIDERS]
		prefer_browser = [p for p in prefer if p in BROWSER_HEAVY_PROVIDERS]
		rest = [p for p in providers if p not in prefer]
		rest_http = [p for p in rest if p not in BROWSER_HEAVY_PROVIDERS]
		rest_browser = [p for p in rest if p in BROWSER_HEAVY_PROVIDERS]
		providers = prefer_http + rest_http + prefer_browser + rest_browser

	if not policy.get('include_browser_galleries'):
		providers = [p for p in providers if p not in BROWSER_HEAVY_PROVIDERS]
	else:
		# Deep: at most one browser-heavy gallery unless explicitly pinned
		if not provider_ids:
			http_part = [p for p in providers if p not in BROWSER_HEAVY_PROVIDERS]
			browser_part = [p for p in providers if p in BROWSER_HEAVY_PROVIDERS][:1]
			providers = http_part + browser_part

	gallery_queries = list(tax.get('gallery_queries') or [])
	if query.strip() and query.strip() not in gallery_queries:
		gallery_queries = [query.strip(), *gallery_queries]

	channels = ['gallery_image']
	max_famous = int(policy.get('max_famous_sites') or 0)
	famous_cats = list(tax.get('famous_categories') or [])
	if max_famous > 0 and famous_cats:
		channels.append('live_site')

	notes = [
		str(policy.get('budget_note') or ''),
		f'intent_class={intent_class}',
		f'mode={resolved_mode.value}',
	]
	if not policy.get('include_browser_galleries'):
		notes.append('browser/WAF galleries excluded')
	elif not provider_ids:
		notes.append('browser galleries capped to 1 (time-box)')

	return SourcePlan(
		mode=resolved_mode,
		intent_class=intent_class,
		gallery_queries=gallery_queries[: int(policy.get('max_queries') or 5)],
		provider_ids=providers,
		famous_categories=famous_cats,
		max_famous_sites=max_famous,
		http_concurrency=int(policy.get('http_concurrency') or 5),
		browser_concurrency=int(policy.get('browser_concurrency') or 0),
		target_refs=int(policy.get('target_refs') or 5),
		min_refs=int(policy.get('min_refs') or 3),
		max_queries=int(policy.get('max_queries') or 3),
		channels=channels,
		stop_rules={
			'usable_refs': int(policy.get('min_refs') or 3),
			'target_refs': int(policy.get('target_refs') or 5),
			'diversity': 'dedupe_preview_url_and_candidate_id',
			'early_cancel': 'cancel_pending_http_when_enough_image_refs',
		},
		notes=[n for n in notes if n],
	)
