"""Flexible inspiration queries — any UI grain: page, section, component, chrome.

Levels choose hunt effort. This module chooses *what* to ask galleries for so
navbar / modal / pricing / full landing all work through the same collect path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# page = full viewport / marketing surface
# section = major page block (pricing, hero, footer)
# component = reusable UI piece (navbar, card, modal, tabs)
# chrome = micro affordance (button, input, badge, hover)
QueryScope = str  # 'page' | 'section' | 'component' | 'chrome'


@dataclass(frozen=True)
class FlexibleQuery:
	"""Resolved query for inspiration acquisition."""

	raw: str
	scope: QueryScope
	intent_class: str
	# What we actually send to galleries / multi-scout
	search_query: str
	# Extra ladder terms (progressive)
	search_aliases: tuple[str, ...]
	# Corpus categories to prefer in multi-scout
	prefer_categories: tuple[str, ...]
	# Soft guidance for agents (not ceremony)
	think: str

	def to_dict(self) -> dict[str, Any]:
		return {
			'raw': self.raw,
			'scope': self.scope,
			'intent_class': self.intent_class,
			'search_query': self.search_query,
			'search_aliases': list(self.search_aliases),
			'prefer_categories': list(self.prefer_categories),
			'think': self.think,
		}


_TOKEN = re.compile(r'[a-z0-9]{2,}')

# (scope, intent_class, prefer_categories, rewrite template or None, think)
_SCOPE_RULES: list[tuple[tuple[str, ...], QueryScope, str, tuple[str, ...], str | None, str]] = [
	(
		('mega menu', 'navbar', 'nav bar', 'navigation bar', 'header nav', 'top nav', 'site header'),
		'component',
		'navigation',
		('ui_gallery', 'component_showcase', 'landing_gallery'),
		'website navigation header menu ui design',
		'Component-scale: nav/header patterns — galleries + showcases.',
	),
	(
		('sidebar', 'side nav', 'sidenav', 'app shell'),
		'component',
		'dashboard',
		('dashboard_gallery', 'component_showcase', 'ui_gallery'),
		'dashboard sidebar navigation ui',
		'Component-scale: sidebar / app shell.',
	),
	(
		('footer',),
		'section',
		'landing',
		('landing_gallery', 'ui_gallery'),
		'website footer links design',
		'Section-scale: footer block.',
	),
	(
		('pricing', 'price table', 'pricing cards', 'pricing section'),
		'section',
		'landing',
		('landing_gallery', 'component_showcase', 'ui_gallery'),
		'saas pricing section cards ui',
		'Section-scale: pricing block.',
	),
	(
		('hero', 'above the fold', 'first viewport'),
		'section',
		'landing',
		('landing_gallery', 'ui_gallery'),
		'landing page hero section ui',
		'Section-scale: hero / first viewport.',
	),
	(
		('cta', 'call to action', 'signup banner'),
		'section',
		'landing',
		('landing_gallery', 'ui_gallery'),
		'landing page call to action section',
		'Section-scale: CTA band.',
	),
	(
		('modal', 'dialog', 'popup', 'drawer overlay', 'confirm dialog'),
		'component',
		'default',
		('component_showcase', 'ui_gallery', 'dashboard_gallery'),
		'ui modal dialog confirmation design',
		'Component-scale: modal / dialog.',
	),
	(
		('dropdown', 'select menu', 'combobox', 'popover'),
		'component',
		'default',
		('component_showcase', 'ui_gallery'),
		'ui dropdown menu select design',
		'Component-scale: dropdown / select.',
	),
	(
		('tabs', 'tab bar', 'segmented control'),
		'component',
		'default',
		('component_showcase', 'ui_gallery', 'dashboard_gallery'),
		'ui tabs navigation design',
		'Component-scale: tabs.',
	),
	(
		('bottom tab', 'tabbar', 'mobile nav'),
		'component',
		'mobile',
		('flow_library', 'component_showcase', 'ui_gallery'),
		'mobile bottom tab bar ui',
		'Component-scale: mobile tab bar.',
	),
	# Before button — "...clear button" must not steal search-bar asks
	(
		('search bar', 'search field', 'search input', 'search box', 'site search'),
		'component',
		'default',
		('component_showcase', 'ui_gallery'),
		'ui search bar input design',
		'Component-scale: search field.',
	),
	(
		('textarea', 'text area', 'multiline text', 'multiline field'),
		'chrome',
		'auth',
		('component_showcase', 'ui_gallery'),
		'ui textarea multiline field design',
		'Chrome-scale: textarea.',
	),
	(
		('button', 'btn', 'hover state', 'primary button'),
		'chrome',
		'default',
		('component_showcase', 'ui_gallery'),
		'ui primary button states design',
		'Chrome-scale: button / control affordance.',
	),
	(
		('input', 'text field', 'form field', 'checkbox', 'toggle', 'switch'),
		'chrome',
		'auth',
		('component_showcase', 'ui_gallery'),
		'ui form input field design',
		'Chrome-scale: form control.',
	),
	(
		('card', 'tile', 'list item', 'table row'),
		'component',
		'dashboard',
		('dashboard_gallery', 'component_showcase', 'ui_gallery'),
		'ui card component design',
		'Component-scale: card / list row.',
	),
	(
		('toast', 'snackbar', 'notification', 'badge', 'chip'),
		'chrome',
		'default',
		('component_showcase', 'ui_gallery'),
		'ui toast notification badge design',
		'Chrome-scale: feedback chrome.',
	),
	(
		('checkout', 'cart', 'payment form'),
		'section',
		'checkout',
		('landing_gallery', 'flow_library', 'ui_gallery'),
		'ecommerce checkout form ui',
		'Section-scale: checkout.',
	),
	(
		('login', 'sign in', 'signup', 'sign up', 'auth'),
		'section',
		'auth',
		('landing_gallery', 'flow_library', 'ui_gallery'),
		'login signup form ui design',
		'Section-scale: auth.',
	),
	(
		('dashboard', 'analytics', 'admin panel', 'crm'),
		'page',
		'dashboard',
		('dashboard_gallery', 'ui_gallery'),
		None,
		'Page-scale: dashboard / admin.',
	),
	(
		('landing', 'homepage', 'marketing site', 'saas landing'),
		'page',
		'landing',
		('landing_gallery', 'ui_gallery'),
		None,
		'Page-scale: marketing / landing.',
	),
	(
		('mobile app', 'ios', 'android'),
		'page',
		'mobile',
		('flow_library', 'ui_gallery'),
		None,
		'Page-scale: mobile app.',
	),
]


def classify_query_scope(query: str) -> QueryScope:
	text = (query or '').strip().lower()
	for needles, scope, _ic, _cats, _rw, _think in _SCOPE_RULES:
		if any(n in text for n in needles):
			return scope
	# Heuristic: short UI nouns → component
	if re.search(r'\b(nav|menu|modal|dialog|button|card|tab|sidebar|footer|header)\b', text):
		return 'component'
	if re.search(r'\b(section|block|band|strip)\b', text):
		return 'section'
	return 'page'


def resolve_flexible_query(query: str) -> FlexibleQuery:
	raw = (query or '').strip()
	text = raw.lower()
	scope: QueryScope = 'page'
	intent_class = 'default'
	prefer: tuple[str, ...] = ('landing_gallery', 'ui_gallery')
	rewrite: str | None = None
	think = 'Page-scale default: full composition refs.'

	for needles, sc, ic, cats, rw, th in _SCOPE_RULES:
		if any(n in text for n in needles):
			scope, intent_class, prefer, rewrite, think = sc, ic, cats, rw, th
			break
	else:
		scope = classify_query_scope(raw)
		if scope == 'component':
			prefer = ('component_showcase', 'ui_gallery', 'landing_gallery')
			think = 'Component-scale: prefer showcases + UI galleries.'
		elif scope == 'section':
			prefer = ('landing_gallery', 'ui_gallery', 'component_showcase')
			think = 'Section-scale: page blocks from landings + galleries.'
		elif scope == 'chrome':
			prefer = ('component_showcase', 'ui_gallery')
			think = 'Chrome-scale: control-level visuals from showcases.'

	search = (rewrite or raw).strip()
	aliases: list[str] = []
	if search.lower() != text:
		aliases.append(raw)
	# Scope-flavored aliases help HTTP galleries that ignore exact phrases
	if scope == 'component' and 'ui' not in search.lower():
		aliases.append(f'{search} ui')
	if scope in {'component', 'chrome'} and 'design' not in search.lower():
		aliases.append(f'{search} design')
	if scope == 'section' and 'section' not in search.lower():
		aliases.append(f'{search} section')

	# Dedupe aliases
	seen = {search.lower()}
	uniq: list[str] = []
	for a in aliases:
		k = a.strip().lower()
		if k and k not in seen:
			seen.add(k)
			uniq.append(a.strip())

	return FlexibleQuery(
		raw=raw,
		scope=scope,
		intent_class=intent_class,
		search_query=search,
		search_aliases=tuple(uniq[:4]),
		prefer_categories=prefer,
		think=think,
	)


def query_tokens(text: str) -> set[str]:
	"""Tokenize with hyphen/space normalization so 'sign-in' matches 'sign in' / 'signin'."""
	stop = {
		'the', 'and', 'for', 'with', 'from', 'into', 'that', 'this', 'your', 'our',
		'ui', 'ux', 'design', 'page', 'website', 'web', 'app', 'interface',
	}
	raw = (text or '').lower()
	# Hyphen/underscore → space; keep a compacted copy for signin/signup compounds
	spaced = re.sub(r'[-_]+', ' ', raw)
	compact = re.sub(r'[^a-z0-9]+', '', spaced)
	tokens = {t for t in _TOKEN.findall(spaced) if t not in stop and len(t) > 2}
	# Phrase → compact token (sign in → signin)
	for phrase, joined in (
		('sign in', 'signin'),
		('sign up', 'signup'),
		('log in', 'login'),
		('log out', 'logout'),
	):
		if phrase in spaced:
			tokens.add(joined)
	if compact and len(compact) > 3:
		# Only add meaningful compact forms that look like known compounds
		for known in ('signin', 'signup', 'login', 'checkout', 'navbar', 'textarea'):
			if known in compact:
				tokens.add(known)
	return tokens


_SYNONYMS: dict[str, set[str]] = {
	'navbar': {'nav', 'navigation', 'header', 'menu', 'menubar'},
	'nav': {'navbar', 'navigation', 'header', 'menu'},
	'menu': {'navbar', 'nav', 'navigation', 'mega'},
	'mega': {'menu', 'dropdown', 'navigation'},
	'modal': {'dialog', 'popup', 'overlay'},
	'dialog': {'modal', 'popup', 'confirm'},
	'pricing': {'price', 'plans', 'tiers'},
	'sidebar': {'sidenav', 'drawer', 'rail'},
	'button': {'btn', 'cta'},
	'checkout': {'cart', 'payment', 'billing', 'order'},
	'login': {'signin', 'sign', 'auth', 'signup', 'registration', 'onboarding', 'authentication'},
	'signin': {'login', 'auth', 'sign', 'authentication'},
	'signup': {'register', 'registration', 'signin', 'login', 'onboarding'},
	'authentication': {'login', 'signin', 'auth', 'signup'},
	'auth': {'login', 'signin', 'authentication', 'signup'},
	'input': {'field', 'textbox', 'textarea', 'search'},
	'textarea': {'multiline', 'input', 'field'},
	'search': {'input', 'find', 'query'},
	'form': {'input', 'field', 'login', 'checkout'},
}


def hit_relevance_score(
	query: str,
	*,
	title: str = '',
	url: str = '',
	search_query: str = '',
) -> float:
	"""0..1 how well a gallery hit matches the inspiration ask.

	Used so soft-stop cannot fire on unrelated 'first three OPL cards'.
	"""
	q = query_tokens(search_query or query)
	if not q:
		return 0.5  # empty query — neutral
	blob_raw = f'{title} {url}'.lower()
	if not blob_raw.strip():
		return 0.0
	# Normalize hyphens so "Sign-in page" matches login/signin tokens
	blob = re.sub(r'[-_]+', ' ', blob_raw)
	for phrase, joined in (
		('sign in', 'signin'),
		('sign up', 'signup'),
		('log in', 'login'),
	):
		if phrase in blob:
			blob = f'{blob} {joined}'
	present = 0.0
	for t in q:
		if t in blob or t in blob_raw:
			present += 1
			continue
		alts = _SYNONYMS.get(t) or set()
		if any(a in blob or a in blob_raw for a in alts):
			present += 0.65
	cov = present / max(1, len(q))
	strong = {
		'nav', 'navbar', 'menu', 'modal', 'dialog', 'pricing', 'hero', 'sidebar',
		'dashboard', 'button', 'checkout', 'login', 'footer', 'card', 'tab',
		'navigation', 'header', 'signup', 'signin', 'authentication', 'input',
		'form', 'search',
	}
	ask = (search_query or query).lower()
	if any(s in blob for s in strong if s in q or s in ask):
		cov = min(1.0, cov + 0.15)
	return round(min(1.0, float(cov)), 3)


def is_relevant_hit(
	query: str,
	*,
	title: str = '',
	url: str = '',
	search_query: str = '',
	min_score: float = 0.18,
) -> bool:
	return hit_relevance_score(query, title=title, url=url, search_query=search_query) >= min_score
