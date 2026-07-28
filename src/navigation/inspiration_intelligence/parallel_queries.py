"""Parallel diverse inspiration queries — different angles, not suffix expansion.

`progressive_queries` widens one seed ("login ui", "login interface").
This module emits **distinct** hunt strings to run concurrently (web SERP,
multi-scout, provider waves) for speed + variety.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from navigation.inspiration_intelligence.query_flex import FlexibleQuery

_TOKEN = re.compile(r'[a-z0-9]{2,}')

# Intent-specific angles — semantically different, not "X ui" / "X interface".
_INTENT_ANGLES: dict[str, tuple[str, ...]] = {
	'auth': (
		'login form email password ui',
		'sign in page design examples',
		'signup registration form interface',
		'authentication modal card design',
	),
	'checkout': (
		'checkout payment form ui design',
		'multi step cart checkout interface',
		'ecommerce order summary checkout',
		'shipping billing form checkout',
	),
	'navigation': (
		'website navigation header menu design',
		'navbar mega menu ui examples',
		'top navigation bar interface',
	),
	'dashboard': (
		'admin dashboard analytics ui',
		'saas analytics dashboard interface',
		'crm data panel dashboard design',
	),
	'landing': (
		'saas landing page design examples',
		'b2b marketing homepage ui',
		'product marketing landing page',
	),
	'mobile': (
		'mobile app ui design examples',
		'ios android app interface design',
	),
	'default': (
		'ui design examples showcase',
		'interface design inspiration gallery',
	),
}

_SCOPE_ANGLES: dict[str, tuple[str, ...]] = {
	'chrome': (
		'ui form control component design',
		'interactive affordance chrome ui',
	),
	'component': (
		'reusable ui component design system',
		'component library ui examples',
	),
	'section': (
		'website section block design',
		'landing page section ui examples',
	),
	'page': (
		'full page website design inspiration',
		'web app page layout ui',
	),
}

# Token-triggered angles — checked against raw query before intent (more specific).
_TOKEN_ANGLES: dict[str, tuple[str, ...]] = {
	'input': (
		'text input field label placeholder ui',
		'form input control design',
		'accessible text field component',
	),
	'textarea': (
		'textarea multiline input ui',
		'message field form design',
		'comment box textarea component',
	),
	'search': (
		'search bar input with icon ui',
		'site search field design',
		'search input autocomplete ui',
	),
	'select': (
		'dropdown select combobox ui',
		'select menu form control',
		'custom select picker design',
	),
	'checkbox': (
		'checkbox toggle switch ui',
		'form checkbox control design',
		'toggle switch component states',
	),
	'button': (
		'primary button hover states ui',
		'cta button component design',
		'button group toolbar ui',
	),
	'modal': (
		'modal dialog confirmation ui',
		'overlay dialog interface design',
		'alert dialog component ui',
	),
	'pricing': (
		'saas pricing section cards ui',
		'pricing table plans design',
		'subscription tier pricing block',
	),
	'hero': (
		'landing hero section above fold ui',
		'marketing hero banner design',
		'hero headline cta section',
	),
	'footer': (
		'website footer links design',
		'site footer section ui',
		'marketing footer sitemap layout',
	),
	'login': (
		'login form ui design',
		'sign in authentication page',
		'email password login card',
	),
	'checkout': (
		'checkout form payment ui',
		'cart checkout flow design',
		'payment step checkout wizard',
	),
	'contact': (
		'contact form section ui',
		'inquiry form page design',
		'lead capture contact block',
	),
	'settings': (
		'user settings profile form ui',
		'account preferences page design',
		'profile settings form layout',
	),
	'navbar': (
		'navbar mega menu ui',
		'website header navigation design',
		'top nav bar component',
	),
	'sidebar': (
		'dashboard sidebar navigation ui',
		'app sidenav drawer design',
		'vertical nav rail component',
	),
}


def _norm(q: str) -> str:
	return re.sub(r'\s+', ' ', (q or '').strip().lower())


def _tokens(text: str) -> set[str]:
	stop = {'the', 'and', 'for', 'with', 'from', 'ui', 'ux', 'design', 'page', 'section'}
	return {t for t in _TOKEN.findall((text or '').lower()) if t not in stop}


def is_suffix_expansion(a: str, b: str) -> bool:
	"""True when b is only a trivial suffix variant of a (ui/interface/design)."""
	la, lb = _norm(a), _norm(b)
	if la == lb:
		return True
	for suffix in (' ui', ' interface', ' design', ' ui design', ' section'):
		if lb == la + suffix or la == lb + suffix:
			return True
	return False


def _pool_candidates(flex: FlexibleQuery) -> list[str]:
	"""Ordered pool: token-specific → intent → scope → user anchors."""
	seen: set[str] = set()
	pool: list[str] = []

	def push(q: str) -> None:
		k = _norm(q)
		if k and k not in seen:
			seen.add(k)
			pool.append(q.strip())

	raw_low = (flex.raw or flex.search_query or '').lower()
	toks = _tokens(raw_low)

	for tok, angles in _TOKEN_ANGLES.items():
		if tok in raw_low or tok in toks:
			for a in angles:
				push(a)

	intent = (flex.intent_class or 'default').strip().lower()
	for a in _INTENT_ANGLES.get(intent, _INTENT_ANGLES['default']):
		push(a)

	for a in _SCOPE_ANGLES.get(flex.scope, ()):
		push(a)

	push(flex.search_query)
	if flex.raw:
		push(flex.raw)
	for alias in flex.search_aliases:
		push(alias)

	return pool


def build_diverse_queries(flex: FlexibleQuery, *, max_queries: int = 3) -> list[str]:
	"""Return distinct queries to fan out in parallel (not progressive suffix variants).

	For ``standard`` (cap=3): three semantically different hunts — intent/token angles
	first; rewritten seed only if slots remain.
	"""
	cap = max(1, int(max_queries))
	pool = _pool_candidates(flex)
	if not pool:
		return [(flex.search_query or flex.raw or 'ui design').strip()]

	out: list[str] = []
	out_seen: set[str] = set()

	def take(q: str) -> bool:
		k = _norm(q)
		if not k or k in out_seen or len(out) >= cap:
			return False
		out_seen.add(k)
		out.append(q.strip())
		return True

	# Pass 1 — skip suffix-only duplicates vs already chosen
	for q in pool:
		if len(out) >= cap:
			break
		if any(is_suffix_expansion(existing, q) for existing in out):
			continue
		take(q)

	# Pass 2 — fill any remaining slots
	if len(out) < cap:
		for q in pool:
			if len(out) >= cap:
				break
			take(q)

	return out[:cap]
