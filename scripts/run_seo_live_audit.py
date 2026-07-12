"""Run live SEO audit against a real website using stored Google OAuth."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')


async def run_audit(
	website_url: str,
	*,
	property_url: str = '',
	mode: str = 'professional',
	ai_reasoning: bool | None = False,
) -> dict:
	from navigation.seo_intelligence import SeoIntelligenceService
	from navigation.seo_intelligence.auth.google import get_valid_credentials, gsc_list_sites, google_oauth_status
	from navigation.seo_intelligence.models import SeoAuditRequest
	from navigation.seo_intelligence.planning.modes import parse_audit_mode
	from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

	print('=== OAuth ===')
	print(json.dumps(google_oauth_status(), indent=2))
	creds = get_valid_credentials()
	if creds:
		sites, _ = await gsc_list_sites(creds)
		print('GSC properties:')
		for site in sites:
			print(' ', site.get('siteUrl'), '-', site.get('permissionLevel'))

	svc = SeoIntelligenceService()
	onboarding = SeoOnboardingService()
	req = SeoAuditRequest(
		website_url=website_url,
		property_url=property_url,
		mode=parse_audit_mode(mode),
		include_recommendations=True,
		ai_reasoning=ai_reasoning,
	)
	enriched, profile, notes = onboarding.enrich_audit_request(req)
	print('\n=== Onboarding ===')
	print('website:', enriched.website_url)
	print('property_url:', enriched.property_url or property_url)
	print('ga4_property_id:', enriched.ga4_property_id)
	print('notes:', notes)

	t0 = time.time()
	print(f'\n=== Audit ({mode}) ===')
	result = await svc.audit(enriched)
	elapsed = time.time() - t0

	ctx = result.reasoning_context or {}
	units = ctx.get('reasoning_units') or []

	by_provider: dict[str, int] = {}
	for item in result.evidence:
		by_provider[item.provider_id] = by_provider.get(item.provider_id, 0) + 1

	print(f'elapsed_s: {elapsed:.1f}')
	print('audit_id:', result.audit_id)
	print('evidence:', len(result.evidence), '| recs:', len(result.recommendations), '| units:', len(units))
	print('providers_queried:', result.providers_queried)
	print('connections:', result.connections)
	print('degraded:', result.degraded)
	print('evidence_by_provider:', by_provider)

	print('\n=== GSC evidence (sample) ===')
	for item in result.evidence:
		if item.provider_id != 'search-console':
			continue
		print('-', item.kind.value, item.title[:70])
		print('  page:', item.page_url or item.url)

	print('\n=== Reasoning units ===')
	for unit in units[:8]:
		conf = unit.get('confidence') or {}
		agr = conf.get('provider_agreement_v2') or {}
		print('-', unit.get('title'))
		print('  page:', unit.get('page_url'))
		print('  impact:', (unit.get('impact') or {}).get('score'), '| confidence:', conf.get('score'))
		if agr:
			print('  agreement_v2:', agr.get('score'), '-', agr.get('explanation'))

	print('\n=== Recommendations ===')
	for rec in result.recommendations[:12]:
		print(f'[{rec.priority}] {rec.title}')
		print('  page:', (rec.metadata or {}).get('page_url'))
		print('  evidence:', rec.evidence_ids[:3])

	print('\n=== Graph queries ===')
	for query_id, params in [
		('graph.summary', {}),
		('page.issues', {'page_url': enriched.website_url.rstrip('/')}),
		('site.traffic_signals', {}),
		('audit.diff', {}),
	]:
		outcome = svc.graph_query(query_id, params)
		result_block = outcome.get('result') or {}
		print(query_id, json.dumps(result_block, indent=2)[:600])

	slug = website_url.replace('https://', '').replace('http://', '').strip('/').replace('.', '_')
	out_path = ROOT / 'artifacts' / f'seo_live_{slug}.json'
	payload = {
		'website': website_url,
		'property_url': enriched.property_url or property_url,
		'audit_id': result.audit_id,
		'elapsed_s': elapsed,
		'evidence_count': len(result.evidence),
		'evidence_by_provider': by_provider,
		'recommendation_count': len(result.recommendations),
		'recommendations': [r.to_dict() for r in result.recommendations],
		'reasoning_units': units,
		'reasoning_context_meta': {
			'sprint': ctx.get('sprint'),
			'ai_reasoning': ctx.get('ai_reasoning'),
		},
		'degraded': result.degraded,
		'connections': result.connections,
		'cross_analysis': result.cross_analysis,
	}
	out_path.parent.mkdir(parents=True, exist_ok=True)
	out_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
	print('\nWrote', out_path)
	return payload


def main() -> None:
	parser = argparse.ArgumentParser(description='Live SEO audit with stored OAuth')
	parser.add_argument('--website', default='https://strikeloop.com/', help='Website URL')
	parser.add_argument('--property-url', default='', help='GSC property override e.g. sc-domain:example.com')
	parser.add_argument('--mode', default='professional', choices=['development', 'professional'])
	parser.add_argument('--ai-reasoning', action='store_true', help='Enable Bedrock AI recommendations')
	args = parser.parse_args()

	if args.ai_reasoning:
		os.environ.pop('SEO_SKIP_AI_REASONING', None)
	else:
		os.environ['SEO_SKIP_AI_REASONING'] = '1'

	asyncio.run(
		run_audit(
			args.website,
			property_url=args.property_url,
			mode=args.mode,
			ai_reasoning=True if args.ai_reasoning else False,
		)
	)


if __name__ == '__main__':
	main()
