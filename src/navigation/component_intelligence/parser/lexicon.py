"""Extensible lexicons for component query parsing."""

from __future__ import annotations

# Visual / aesthetic style modifiers — add new entries here only.
STYLE_MODIFIERS: frozenset[str] = frozenset(
	{
		'modern',
		'minimal',
		'minimalist',
		'glassmorphism',
		'glass',
		'neumorphism',
		'brutalism',
		'brutalist',
		'enterprise',
		'clean',
		'elegant',
		'premium',
		'rounded',
		'colorful',
		'gradient',
		'flat',
		'corporate',
		'playful',
		'bold',
		'soft',
		'luxury',
		'retro',
		'futuristic',
	}
)

STYLE_ALIASES: dict[str, str] = {
	'glass': 'glassmorphism',
}

AUDIENCE_KEYWORDS: frozenset[str] = frozenset({'saas', 'startup', 'enterprise', 'premium', 'b2b', 'b2c'})

PAGE_CONTEXTS: frozenset[str] = frozenset(
	{
		'dashboard',
		'landing page',
		'auth',
		'settings',
		'marketing',
		'admin',
		'onboarding',
		'checkout',
		'profile',
		'saas',
		'startup',
		'enterprise',
		'ecommerce',
		'blog',
		'portfolio',
	}
)

# Component-level types (UI elements).
COMPONENT_TYPES: frozenset[str] = frozenset(
	{
		'button',
		'card',
		'form',
		'input',
		'navbar',
		'nav',
		'navigation',
		'sidebar',
		'hero',
		'footer',
		'header',
		'table',
		'modal',
		'dialog',
		'dropdown',
		'tabs',
		'accordion',
		'badge',
		'avatar',
		'chart',
		'calendar',
		'carousel',
		'pricing',
		'testimonial',
		'login',
		'signup',
		'register',
		'settings',
		'profile',
		'menu',
		'breadcrumb',
		'pagination',
		'tooltip',
		'toast',
		'alert',
		'skeleton',
		'loader',
		'spinner',
		'banner',
		'cta',
	}
)

# Page / block-level types.
PAGE_TYPES: frozenset[str] = frozenset(
	{
		'pricing section',
		'pricing page',
		'login form',
		'login page',
		'signup form',
		'dashboard',
		'dashboard card',
		'settings page',
		'landing page',
		'hero section',
		'auth form',
		'contact form',
		'checkout',
		'onboarding',
		'admin panel',
		'stats',
		'analytics',
		'blog',
		'portfolio',
	}
)

THEME_KEYWORDS: dict[str, str] = {
	'dark': 'dark',
	'light': 'light',
	'dark mode': 'dark',
	'light mode': 'light',
	'dark theme': 'dark',
	'light theme': 'light',
}

ANIMATION_KEYWORDS: frozenset[str] = frozenset(
	{
		'animated',
		'animation',
		'motion',
		'transition',
		'microinteraction',
		'micro-interaction',
		'hover',
		'parallax',
		'fade',
		'slide',
		'bounce',
	}
)
