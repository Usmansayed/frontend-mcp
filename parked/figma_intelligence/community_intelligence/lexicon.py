"""Community search lexicon — synonyms, styles, industries, component expansions."""
from __future__ import annotations

# Page / layout synonyms (query expansion).
PAGE_SYNONYMS: dict[str, list[str]] = {
	'dashboard': ['admin panel', 'analytics', 'control center', 'overview', 'metrics hub'],
	'landing': ['marketing page', 'homepage', 'hero page', 'product page'],
	'auth': ['login', 'sign in', 'signup', 'registration', 'onboarding auth'],
	'settings': ['preferences', 'account settings', 'profile settings'],
	'checkout': ['payment', 'cart', 'order summary'],
	'pricing': ['plans', 'subscription', 'tiers'],
	'profile': ['user profile', 'account page'],
	'onboarding': ['welcome flow', 'getting started', 'setup wizard'],
}

# Brand / design-language references (style expansion).
DESIGN_LANGUAGES: dict[str, list[str]] = {
	'linear': ['linear app', 'minimal saas', 'dark ui'],
	'vercel': ['vercel style', 'geist', 'developer saas'],
	'stripe': ['stripe dashboard', 'fintech clean'],
	'notion': ['notion ui', 'workspace'],
	'apple': ['apple hig', 'ios style'],
	'shadcn': ['shadcn ui', 'new york', 'radix'],
}

STYLE_MODIFIERS: frozenset[str] = frozenset(
	{
		'minimal',
		'minimalist',
		'glassmorphism',
		'glass',
		'bento',
		'neumorphism',
		'brutalist',
		'corporate',
		'premium',
		'clean',
		'elegant',
		'gradient',
		'flat',
		'rounded',
		'dark',
		'light',
	}
)

STYLE_ALIASES: dict[str, str] = {
	'glass': 'glassmorphism',
}

# Industry / vertical expansion.
INDUSTRIES: dict[str, list[str]] = {
	'saas': ['b2b saas', 'startup', 'subscription software', 'product led'],
	'fintech': ['finance', 'banking', 'payments', 'trading'],
	'crm': ['sales crm', 'pipeline', 'customer management'],
	'ecommerce': ['e-commerce', 'shop', 'retail', 'storefront'],
	'healthcare': ['medical', 'clinic', 'patient portal'],
	'education': ['edtech', 'learning platform', 'course'],
	'crypto': ['web3', 'defi', 'wallet'],
}

# When user needs a page type, also search component-level templates.
PAGE_COMPONENT_EXPANSION: dict[str, list[str]] = {
	'dashboard': ['sidebar', 'table', 'chart', 'card', 'stats', 'navigation', 'header'],
	'landing': ['hero', 'feature grid', 'pricing', 'testimonial', 'cta', 'footer'],
	'auth': ['login form', 'signup form', 'oauth buttons'],
	'ecommerce': ['product card', 'cart', 'checkout form', 'filter'],
	'crm': ['pipeline board', 'contact table', 'deal card'],
	'saas': ['pricing table', 'feature section', 'navbar'],
}

# Component synonym rings.
COMPONENT_SYNONYMS: dict[str, list[str]] = {
	'navbar': ['navigation', 'header', 'top bar', 'menubar'],
	'sidebar': ['side nav', 'drawer', 'navigation rail'],
	'table': ['data table', 'grid', 'datagrid'],
	'chart': ['graph', 'analytics chart', 'visualization'],
	'card': ['tile', 'panel', 'widget'],
}

# Minimum confidence to send a query to providers.
EXECUTION_CONFIDENCE_THRESHOLD = 0.55
