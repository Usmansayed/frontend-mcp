"""Seed reference catalog — metadata + fixture snapshots for structural comparison."""
from __future__ import annotations

from pathlib import Path

from navigation.design_reference_registry import DesignReferenceRegistry
from navigation.design_snapshot_engine.engine import DesignSnapshotEngine

# Reference products to capture (URLs for future live capture)
REFERENCE_CATALOG = [
	{
		'id': 'stripe_checkout',
		'name': 'Stripe Checkout',
		'tags': ['fintech', 'checkout', 'saas'],
		'industry': 'fintech',
		'page_type': 'checkout',
		'source_url': 'https://stripe.com',
	},
	{
		'id': 'linear_dashboard',
		'name': 'Linear Dashboard',
		'tags': ['saas', 'dashboard', 'productivity'],
		'industry': 'saas',
		'page_type': 'dashboard',
		'source_url': 'https://linear.app',
	},
	{
		'id': 'notion_editor',
		'name': 'Notion Editor',
		'tags': ['saas', 'editor', 'productivity'],
		'industry': 'saas',
		'page_type': 'editor',
		'source_url': 'https://notion.so',
	},
	{
		'id': 'vercel_landing',
		'name': 'Vercel Landing',
		'tags': ['developer', 'landing', 'saas'],
		'industry': 'developer-tools',
		'page_type': 'landing',
		'source_url': 'https://vercel.com',
	},
	{
		'id': 'github_repo',
		'name': 'GitHub Repository',
		'tags': ['developer', 'code', 'navigation'],
		'industry': 'developer-tools',
		'page_type': 'detail',
		'source_url': 'https://github.com',
	},
	{
		'id': 'shopify_storefront',
		'name': 'Shopify Storefront',
		'tags': ['ecommerce', 'retail'],
		'industry': 'ecommerce',
		'page_type': 'storefront',
		'source_url': 'https://shopify.com',
	},
	{
		'id': 'apple_product',
		'name': 'Apple Product Page',
		'tags': ['consumer', 'product', 'minimal'],
		'industry': 'consumer',
		'page_type': 'product',
		'source_url': 'https://apple.com',
	},
	{
		'id': 'airbnb_listing',
		'name': 'Airbnb Listing',
		'tags': ['marketplace', 'travel', 'booking'],
		'industry': 'travel',
		'page_type': 'listing',
		'source_url': 'https://airbnb.com',
	},
]

# Fixture snapshots representing "good" reference patterns (expand via live capture)
_REFERENCE_FIXTURES: dict[str, dict] = {
	'stripe_checkout': {
		'url': 'https://stripe.com/checkout',
		'elements': [
			{'tag': 'button', 'selector': 'button', 'text': 'Pay', 'classes': ['primary'],
			 'style': {'fontSize': '16px', 'color': 'var(--foreground)', 'backgroundColor': 'var(--primary)',
			           'padding': '16px', 'borderRadius': '8px'}},
			{'tag': 'h1', 'selector': 'h1', 'text': 'Checkout', 'classes': [],
			 'style': {'fontSize': '24px', 'fontFamily': 'Inter, sans-serif', 'color': 'rgb(17, 24, 39)'}},
		],
		'css_variables': {'--primary': '#635bff', '--foreground': '#ffffff', '--spacing-4': '16px'},
	},
	'linear_dashboard': {
		'url': 'https://linear.app/dashboard',
		'elements': [
			{'tag': 'nav', 'selector': 'nav', 'text': 'Issues', 'classes': ['sidebar'],
			 'style': {'fontSize': '14px', 'padding': '8px', 'color': 'rgb(55, 65, 81)'}},
			{'tag': 'h2', 'selector': 'h2', 'text': 'Active issues', 'classes': [],
			 'style': {'fontSize': '20px', 'fontFamily': 'Inter, sans-serif'}},
		],
		'css_variables': {'--primary': '#5e6ad2', '--spacing-4': '16px'},
	},
	'sandbox_login': {
		'url': 'http://localhost:5173/login',
		'elements': [
			{'tag': 'h1', 'selector': 'h1', 'text': 'Sign in', 'classes': [],
			 'style': {'fontSize': '22px', 'fontFamily': 'system-ui', 'color': 'rgb(17, 24, 39)'}},
			{'tag': 'button', 'selector': 'button.primary', 'text': 'Continue', 'classes': ['primary'],
			 'style': {'fontSize': '16px', 'padding': '16px', 'borderRadius': '8px'}},
		],
		'css_variables': {},
	},
}


def default_reference_registry(
	*,
	storage_path: Path | None = None,
) -> DesignReferenceRegistry:
	"""Registry pre-loaded with seed reference snapshots."""
	reg = DesignReferenceRegistry(storage_path=storage_path)
	engine = DesignSnapshotEngine()
	for meta in REFERENCE_CATALOG:
		fixture = _REFERENCE_FIXTURES.get(meta['id'])
		if fixture is None:
			continue
		snapshot = engine.capture_from_fixture(fixture)
		snapshot.provenance['reference_meta'] = {
			'industry': meta['industry'],
			'page_type': meta['page_type'],
			'tags': meta['tags'],
		}
		reg.register(
			meta['id'],
			meta['name'],
			snapshot,
			tags=meta['tags'],
			source_url=meta['source_url'],
			notes=f"{meta['industry']} / {meta['page_type']}",
		)
	return reg
