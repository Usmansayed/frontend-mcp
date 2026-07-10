"""Synonym and terminology expansion for search planning."""

from __future__ import annotations

# Component type -> alternative search terms (pass 2+).
COMPONENT_SYNONYMS: dict[str, tuple[str, ...]] = {
	'navbar': (
		'navigation menu',
		'header',
		'top navigation',
		'nav bar',
		'menubar',
		'site header',
		'sticky navbar',
		'animated navigation',
	),
	'nav': ('navigation menu', 'navbar', 'header'),
	'navigation': ('navbar', 'navigation menu', 'header', 'menubar'),
	'header': ('navbar', 'top navigation', 'site header', 'navigation menu'),
	'sidebar': ('side navigation', 'side menu', 'drawer navigation', 'app sidebar'),
	'pricing': ('pricing section', 'pricing table', 'plans', 'pricing cards', 'subscription'),
	'login': ('sign in', 'auth form', 'login form', 'authentication'),
	'signup': ('register', 'sign up', 'registration form'),
	'hero': ('hero section', 'landing hero', 'banner'),
	'footer': ('site footer', 'page footer'),
	'button': ('cta', 'action button'),
	'card': ('panel', 'tile'),
	'dashboard': ('dashboard layout', 'admin dashboard', 'analytics dashboard'),
	'form': ('input form', 'contact form'),
	'menu': ('dropdown menu', 'context menu', 'navigation menu'),
}

# Broader concepts when results are weak (pass 3).
BROAD_CONCEPTS: dict[str, tuple[str, ...]] = {
	'navbar': ('layout', 'shell', 'navigation', 'app bar'),
	'pricing': ('marketing', 'landing', 'conversion'),
	'login': ('auth', 'account', 'onboarding'),
	'dashboard': ('admin', 'analytics', 'overview'),
	'hero': ('marketing', 'landing page'),
	'button': ('interactive', 'ui'),
	'card': ('content', 'layout'),
}
