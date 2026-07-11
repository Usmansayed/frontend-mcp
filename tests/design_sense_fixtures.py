"""Fake ReviewRequest payloads for Design Sense scenario testing."""
from __future__ import annotations

from navigation.design_sense_intelligence.models import ReviewRequest, ReviewScope

# Intentionally bad styles — should trigger design_lint findings
BAD_TYPOGRAPHY_STYLES = [
	{
		'selector': 'button.cta',
		'tag': 'button',
		'style': {
			'color': '#ff0000',
			'backgroundColor': '#00ff00',
			'fontSize': '13px',
			'padding': '11px',
			'borderRadius': '5px',
		},
		'classes': [],
	},
	{
		'selector': 'p.body',
		'tag': 'p',
		'style': {
			'color': '#333333',
			'fontSize': '15px',
			'fontFamily': 'Comic Sans MS',
		},
		'classes': [],
	},
]

# Clean token-based styles — lint should be quieter
GOOD_TOKEN_STYLES = [
	{
		'selector': 'button.primary',
		'tag': 'button',
		'style': {
			'color': 'var(--foreground)',
			'backgroundColor': 'var(--primary)',
			'fontSize': '16px',
			'padding': '16px',
			'borderRadius': '8px',
		},
		'classes': ['text-base', 'rounded-lg'],
	},
]

OVERFLOW_INSIGHTS = {
	'issues': [
		{'kind': 'horizontal_overflow', 'severity': 'blocking', 'detail': 'scrollWidth=2400 viewport=1280'},
		{'kind': 'truncated_text', 'severity': 'advisory', 'detail': 'Checkout summary'},
	],
	'blocking': ['horizontal_overflow'],
	'boxes': [
		{'x': 40, 'y': 120, 'width': 320, 'height': 48, 'label': 'Continue', 'role': 'button', 'interactive': True},
	],
}

LOGIN_INSIGHTS = {
	'issues': [],
	'blocking': [],
	'boxes': [
		{'x': 200, 'y': 180, 'width': 280, 'height': 40, 'label': 'Username', 'role': 'input', 'interactive': True},
		{'x': 200, 'y': 240, 'width': 280, 'height': 40, 'label': 'Password', 'role': 'input', 'interactive': True},
		{'x': 200, 'y': 300, 'width': 280, 'height': 44, 'label': 'Continue', 'role': 'button', 'interactive': True},
	],
}

FAKE_SCENARIOS: list[dict] = [
	{
		'id': 'fake_checkout_overflow',
		'source': 'fixture',
		'description': 'Ecommerce checkout with blocking horizontal overflow',
		'request': ReviewRequest(
			user_task='Complete checkout and pay for cart items',
			scope=ReviewScope.FLOW.value,
			preview_url='http://localhost:5173/shop/checkout/shipping',
			visual_insights=OVERFLOW_INSIGHTS,
			computed_styles=BAD_TYPOGRAPHY_STYLES,
		),
	},
	{
		'id': 'fake_login_form',
		'source': 'fixture',
		'description': 'Sign-in flow with clean layout signals',
		'request': ReviewRequest(
			user_task='Sign in to dashboard as admin',
			scope=ReviewScope.PAGE.value,
			preview_url='http://localhost:5173/login',
			visual_insights=LOGIN_INSIGHTS,
			computed_styles=GOOD_TOKEN_STYLES,
		),
	},
	{
		'id': 'fake_dashboard_analytics',
		'source': 'fixture',
		'description': 'Dashboard analytics page — layout and hierarchy review',
		'request': ReviewRequest(
			user_task='Review dashboard analytics charts and navigation',
			scope=ReviewScope.FEATURE.value,
			preview_url='http://localhost:5173/dashboard/analytics',
			visual_insights={
				'issues': [{'kind': 'tall_page', 'severity': 'advisory', 'detail': 'scrollHeight=4200'}],
				'blocking': [],
			},
			computed_styles=GOOD_TOKEN_STYLES,
			design_tokens={'spacing': [4, 8, 16, 24, 32]},
		),
	},
	{
		'id': 'fake_validation_form',
		'source': 'fixture',
		'description': 'Form with interaction and error-prevention checks',
		'request': ReviewRequest(
			user_task='Fill validation form and submit with invalid data first',
			scope=ReviewScope.FLOW.value,
			preview_url='http://localhost:5173/forms/validation',
			visual_insights={
				'issues': [{'kind': 'zero_size_clickable', 'severity': 'blocking', 'detail': 'Submit'}],
				'blocking': ['zero_size_clickable'],
			},
			computed_styles=BAD_TYPOGRAPHY_STYLES,
		),
	},
	{
		'id': 'fake_minimal_task',
		'source': 'fixture',
		'description': 'Task-only request — tests knowledge graph and providers without DOM',
		'request': ReviewRequest(
			user_task='Improve mobile navigation for SaaS onboarding',
			scope=ReviewScope.PAGE.value,
		),
	},
	{
		'id': 'fake_lint_only',
		'source': 'fixture',
		'description': 'Computed styles only — objective design_lint lane',
		'request': ReviewRequest(
			user_task='Audit button and text styles',
			scope=ReviewScope.COMPONENT.value,
			computed_styles=BAD_TYPOGRAPHY_STYLES,
		),
	},
]

SANDBOX_PAGES: list[dict] = [
	{
		'id': 'sandbox_login',
		'path': '/login',
		'user_task': 'Sign in to access protected dashboard',
		'scope': ReviewScope.PAGE.value,
	},
	{
		'id': 'sandbox_checkout_shipping',
		'path': '/shop/checkout/shipping',
		'user_task': 'Complete checkout shipping step',
		'scope': ReviewScope.FLOW.value,
	},
	{
		'id': 'sandbox_validation_form',
		'path': '/forms/validation',
		'user_task': 'Submit validation form with required fields',
		'scope': ReviewScope.FLOW.value,
	},
	{
		'id': 'sandbox_home',
		'path': '/',
		'user_task': 'Navigate home page and evaluate layout hierarchy',
		'scope': ReviewScope.PAGE.value,
	},
]
