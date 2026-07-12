#!/usr/bin/env python3
"""Dev CLI for SEO Intelligence — browser OAuth connect + audit."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.core.env import load_project_env


def _print(data: object) -> None:
	print(json.dumps(data, indent=2, default=str))


async def _cmd_status() -> None:
	from navigation.seo_intelligence import SeoIntelligenceService
	from navigation.seo_intelligence.setup.companion_services import ensure_companions_ready

	load_project_env()
	service = SeoIntelligenceService()
	payload = service.status()
	companions, notes = await ensure_companions_ready()
	payload['companions_live'] = {sid: st.to_dict() for sid, st in companions.items()}
	payload['companions_notes'] = notes
	_print(payload)


async def _cmd_companions_up() -> None:
	from navigation.seo_intelligence.setup.companion_services import ensure_companions_ready

	load_project_env()
	companions, notes = await ensure_companions_ready()
	_print({'companions': {sid: st.to_dict() for sid, st in companions.items()}, 'notes': notes})


async def _cmd_companions_status() -> None:
	from navigation.seo_intelligence.setup.companion_services import probe_librecrawl

	load_project_env()
	librecrawl = await probe_librecrawl()
	_print({'librecrawl': librecrawl.to_dict()})


async def _cmd_setup(website_url: str) -> None:
	from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

	load_project_env()
	result = await SeoOnboardingService().register_website(website_url)
	_print(result)


async def _cmd_connect_google(website_url: str) -> None:
	from navigation.seo_intelligence.auth.connect import connect_google
	from navigation.seo_intelligence.auth.google import google_oauth_configured

	load_project_env()
	if not google_oauth_configured():
		raise SystemExit(
			'Google OAuth not configured. Set GOOGLE_OAUTH_CLIENT_ID and '
			'GOOGLE_OAUTH_CLIENT_SECRET in .env (redirect: http://localhost:5000/api/auth/google/callback)'
		)
	print(f'Opening browser for Google OAuth — website: {website_url}')
	print('Sign in when prompted. Waiting for localhost callback...')
	result = await connect_google(website_url)
	_print(result)


async def _cmd_connect_bing(website_url: str) -> None:
	from navigation.seo_intelligence.auth import bing as bing_api
	from navigation.seo_intelligence.auth.connect import connect_bing
	from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

	load_project_env()
	if bing_api.bing_oauth_configured():
		print(f'Opening browser for Bing OAuth — website: {website_url}')
		print('Sign in with Microsoft. Waiting for localhost callback...')
		result = await connect_bing(website_url)
		_print(result)
		return
	api_key = bing_api._load_token_data()  # noqa: SLF001 — dev fallback check only
	if api_key and str(api_key.get('api_key') or '').strip():
		onboarding = SeoOnboardingService()
		result = await onboarding.complete_bing_api_key(website_url, str(api_key['api_key']))
		_print(result)
		return
	raise SystemExit(
		'Bing OAuth not configured. Set BING_WEBMASTER_OAUTH_CLIENT_ID and '
		'BING_WEBMASTER_OAUTH_CLIENT_SECRET in .env (redirect: http://localhost:8787/bing/callback)'
	)


async def _cmd_gsc_debug(website_url: str) -> None:
	from navigation.seo_intelligence.auth.google import (
		get_valid_credentials,
		google_oauth_status,
		gsc_list_sites,
	)
	from navigation.seo_intelligence.setup.discovery import pick_gsc_property
	from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

	load_project_env()
	oauth = google_oauth_status()
	creds = get_valid_credentials()
	sites: list = []
	notes: list[str] = []
	if creds is not None:
		sites, notes = await gsc_list_sites(creds)
	selected, pick_notes = pick_gsc_property(website_url, sites)
	profile = await SeoOnboardingService().refresh_discovery(website_url, provider='google')
	_print(
		{
			'oauth': oauth,
			'gsc_api': {'sites': sites, 'notes': notes},
			'property_match': {'selected': selected, 'notes': pick_notes},
			'profile': profile.to_dict(),
		}
	)


async def _cmd_audit(website_url: str) -> None:
	from navigation.seo_intelligence import SeoAuditRequest, SeoIntelligenceService
	from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

	load_project_env()
	request = SeoAuditRequest(website_url=website_url)
	enriched, profile, notes = SeoOnboardingService().enrich_audit_request(request)
	service = SeoIntelligenceService()
	result = await service.audit(enriched)
	payload = result.to_dict()
	payload['onboarding_notes'] = notes
	if profile is not None:
		payload['site_profile'] = profile.to_dict()
	_print(payload)


def main() -> None:
	parser = argparse.ArgumentParser(description='SEO Intelligence dev CLI')
	sub = parser.add_subparsers(dest='command', required=True)

	sub.add_parser('status', help='Module status + OAuth readiness + companion health')

	sub.add_parser('companions-up', help='Start/wait for LibreCrawl')
	sub.add_parser('companions-status', help='Probe LibreCrawl health')

	p_s = sub.add_parser('setup', help='Register website URL only (no OAuth)')
	p_s.add_argument('website_url', help='e.g. https://strikeloop.com')

	p_g = sub.add_parser('connect-google', help='On-demand Google OAuth (GSC + GA4)')
	p_g.add_argument('website_url', help='e.g. https://strikeloop.com')

	p_b = sub.add_parser('connect-bing', help='Browser OAuth for Bing Webmaster')
	p_b.add_argument('website_url', help='e.g. https://strikeloop.com')

	p_a = sub.add_parser('audit', help='Run full SEO audit')
	p_a.add_argument('website_url', help='e.g. https://strikeloop.com')

	p_d = sub.add_parser('gsc-debug', help='Diagnose GSC OAuth scopes, sites.list, property match')
	p_d.add_argument('website_url', help='e.g. https://scubiee.com')

	args = parser.parse_args()
	if args.command == 'status':
		asyncio.run(_cmd_status())
	elif args.command == 'companions-up':
		asyncio.run(_cmd_companions_up())
	elif args.command == 'companions-status':
		asyncio.run(_cmd_companions_status())
	elif args.command == 'setup':
		asyncio.run(_cmd_setup(args.website_url))
	elif args.command == 'connect-google':
		asyncio.run(_cmd_connect_google(args.website_url))
	elif args.command == 'connect-bing':
		asyncio.run(_cmd_connect_bing(args.website_url))
	elif args.command == 'audit':
		asyncio.run(_cmd_audit(args.website_url))
	elif args.command == 'gsc-debug':
		asyncio.run(_cmd_gsc_debug(args.website_url))


if __name__ == '__main__':
	main()
