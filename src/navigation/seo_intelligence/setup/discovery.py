"""Auto-discover GSC / GA4 resources from a website URL."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def normalize_website_url(url: str) -> str:
	raw = url.strip()
	if not raw:
		return ''
	if not raw.startswith(('http://', 'https://')):
		raw = f'https://{raw}'
	parsed = urlparse(raw)
	if not parsed.netloc:
		return raw
	scheme = parsed.scheme or 'https'
	return f'{scheme}://{parsed.netloc}/'


def registrable_domain(host: str) -> str:
	host = host.lower().strip().rstrip('.')
	if host.startswith('www.'):
		host = host[4:]
	return host


def domain_from_website(url: str) -> str:
	parsed = urlparse(normalize_website_url(url))
	return registrable_domain(parsed.netloc or '')


def _score_gsc_property(website_url: str, site_entry: dict[str, Any]) -> int:
	domain = domain_from_website(website_url)
	site_url = str(site_entry.get('siteUrl') or '')
	if not site_url or not domain:
		return 0
	lower = site_url.lower()
	if lower == f'sc-domain:{domain}':
		return 100
	normalized = normalize_website_url(website_url).lower().rstrip('/')
	if lower.rstrip('/') == normalized.rstrip('/'):
		return 95
	if lower.rstrip('/') == f'https://{domain}/'.rstrip('/'):
		return 90
	if lower.rstrip('/') == f'https://www.{domain}/'.rstrip('/'):
		return 85
	if domain in lower:
		return 50
	return 0


def pick_gsc_property(website_url: str, sites: list[dict[str, Any]]) -> tuple[str, list[str]]:
	degraded: list[str] = []
	if not sites:
		return '', ['gsc_discovery:no_properties']
	scored = sorted(
		((_score_gsc_property(website_url, entry), str(entry.get('siteUrl') or '')) for entry in sites),
		key=lambda item: item[0],
		reverse=True,
	)
	best_score, best_url = scored[0]
	if best_score <= 0 or not best_url:
		fallback = normalize_website_url(website_url)
		degraded.append('gsc_discovery:no_exact_match:using_website_url')
		return fallback, degraded
	if best_score < 85 and len(scored) > 1 and scored[1][0] == best_score:
		degraded.append('gsc_discovery:ambiguous_property:picked_best_match')
	return best_url, degraded


def _score_ga4_property(website_url: str, prop: dict[str, Any]) -> int:
	domain = domain_from_website(website_url)
	name = str(prop.get('displayName') or '').lower()
	uri = str(prop.get('defaultUri') or prop.get('websiteUrl') or '').lower()
	score = 0
	if domain and domain in uri:
		score += 80
	if domain and domain in name:
		score += 40
	if uri.rstrip('/') == normalize_website_url(website_url).lower().rstrip('/'):
		score += 20
	return score


def pick_ga4_property(website_url: str, properties: list[dict[str, Any]]) -> tuple[str, list[str]]:
	degraded: list[str] = []
	if not properties:
		return '', ['ga4_discovery:no_properties']
	scored = sorted(
		((_score_ga4_property(website_url, prop), str(prop.get('name') or prop.get('property_id') or '')) for prop in properties),
		key=lambda item: item[0],
		reverse=True,
	)
	best_score, best_name = scored[0]
	if best_score <= 0 or not best_name:
		return '', ['ga4_discovery:no_match_for_domain']
	if best_score < 60:
		degraded.append('ga4_discovery:weak_match')
	return best_name if best_name.startswith('properties/') else f'properties/{best_name.split("/")[-1]}', degraded


def _score_bing_site(website_url: str, site: dict[str, Any]) -> int:
	domain = domain_from_website(website_url)
	site_url = str(site.get('Url') or site.get('url') or site.get('siteUrl') or '')
	if not site_url or not domain:
		return 0
	lower = site_url.lower().rstrip('/')
	normalized = normalize_website_url(website_url).lower().rstrip('/')
	score = 0
	if lower.rstrip('/') == normalized.rstrip('/'):
		score += 100
	if lower.rstrip('/') == f'https://{domain}'.rstrip('/'):
		score += 95
	if lower.rstrip('/') == f'https://www.{domain}'.rstrip('/'):
		score += 90
	if lower.rstrip('/') == f'http://{domain}'.rstrip('/'):
		score += 85
	if domain in lower:
		score += 50
	if site.get('IsVerified') is True:
		score += 10
	return score


def pick_bing_site(website_url: str, sites: list[dict[str, Any]]) -> tuple[str, list[str]]:
	degraded: list[str] = []
	if not sites:
		return '', ['bing_discovery:no_sites']
	scored = sorted(
		((_score_bing_site(website_url, site), str(site.get('Url') or site.get('url') or '')) for site in sites),
		key=lambda item: item[0],
		reverse=True,
	)
	best_score, best_url = scored[0]
	if best_score <= 0 or not best_url:
		return '', ['bing_discovery:no_match_for_domain']
	if best_score < 85 and len(scored) > 1 and scored[1][0] == best_score:
		degraded.append('bing_discovery:ambiguous_site:picked_best_match')
	if best_score < 60:
		degraded.append('bing_discovery:weak_match')
	return best_url, degraded
