"""Run full Figma Intelligence pipeline using figma_pat from .env."""
from __future__ import annotations

import asyncio
import json
import re
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')
load_dotenv()

# figma-console-mcp expects FIGMA_ACCESS_TOKEN
_pat = os.environ.get('figma_pat', '').strip() or os.environ.get('FIGMA_PAT', '').strip()
if _pat:
	os.environ['FIGMA_ACCESS_TOKEN'] = _pat

from navigation.figma_intelligence.models import FigmaCandidate, FigmaDiscoveryRequest, FigmaRankedCandidate
from navigation.figma_intelligence.extraction.pipeline import extract_selection_plan
from navigation.figma_intelligence.providers.figma_console.client import FigmaConsoleMcpClient
from navigation.figma_intelligence.providers.manager import FigmaProviderRegistry
from navigation.figma_intelligence.registry.reference_bridge import register_extractions
from navigation.figma_intelligence.review.deep_review import deep_review_extractions
from navigation.figma_intelligence.service import FigmaIntelligenceService


_FIGMA_FILE_KEY_RE = re.compile(r'figma\.com/(?:file|design)/([A-Za-z0-9]+)')


def _file_key_from_health(health: dict) -> str:
	payload = health.get('payload')
	if not isinstance(payload, dict):
		return ''
	url = str(payload.get('monitoredPageUrl') or '').strip()
	match = _FIGMA_FILE_KEY_RE.search(url)
	return match.group(1) if match else ''


def _inject_file_key(selection_plan, file_key: str) -> None:
	"""Attach file_key to selected candidates missing one (smoke / owned-file test)."""
	if not selection_plan or not file_key:
		return
	for selected in selection_plan.selected:
		c = selected.ranked.candidate
		if c.file_key:
			continue
		selected.ranked = FigmaRankedCandidate(
			candidate=FigmaCandidate(
				candidate_id=c.candidate_id,
				title=c.title,
				source=c.source,
				provider_id='figma_console',
				file_key=file_key,
				node_id=c.node_id,
				url=c.url,
				tags=list(c.tags),
				preview_ref=c.preview_ref,
				metadata=dict(c.metadata),
				profile=c.profile,
				discovery_score=c.discovery_score,
			),
			inspiration_score=selected.ranked.inspiration_score,
			consistency_fit=selected.ranked.consistency_fit,
			component_reuse_score=selected.ranked.component_reuse_score,
			design_quality_score=selected.ranked.design_quality_score,
			framework_fit=selected.ranked.framework_fit,
			overall_score=selected.ranked.overall_score,
			rationale=selected.ranked.rationale,
			degraded=list(selected.ranked.degraded),
		)


def _redact(result: dict) -> dict:
	"""Summary safe for logs — no secrets."""
	out = json.loads(json.dumps(result, default=str))
	disc = out.get('discovery', {})
	for c in disc.get('candidates', []):
		cand = c.get('candidate', {})
		cand.pop('metadata', None)
	return out


async def main() -> int:
	query = os.environ.get('FIGMA_PIPELINE_QUERY', 'minimal saas dashboard inspiration')
	repo_root = os.environ.get('FIGMA_PIPELINE_REPO', str(ROOT))
	max_candidates = int(os.environ.get('FIGMA_PIPELINE_MAX', '5'))

	print('=== Figma Intelligence — full pipeline ===')
	print(f'query: {query}')
	print(f'pat_configured: {bool(_pat)}')
	print(f'repo_root: {repo_root}')

	svc = FigmaIntelligenceService()

	# MCP health (extraction backend)
	client = FigmaConsoleMcpClient()
	health = await client.health()
	print('\n--- Figma Console MCP health ---')
	print(json.dumps({k: v for k, v in health.items() if k != 'payload'}, indent=2))
	bridge_key = ''
	if health.get('payload'):
		print('status_payload_keys:', list(health['payload'].keys())[:10] if isinstance(health['payload'], dict) else type(health['payload']))
	bridge_key = _file_key_from_health(health)
	if bridge_key:
		print(f'desktop_bridge_file_key: {bridge_key}')

	print('\n--- Discovery (no PAT) ---')
	discovery = await svc.discover(
		FigmaDiscoveryRequest(query=query, repo_root=repo_root, max_candidates=max_candidates)
	)
	print(f'intent: {discovery.intent.kind.value}')
	print(f'community_queries: {len(discovery.community_plan.executable_queries)}')
	print(f'candidates: {len(discovery.candidates)}')
	print(f'selection_open: {len(discovery.selection_plan.selected) if discovery.selection_plan else 0}')
	for i, ranked in enumerate(discovery.candidates[:3], 1):
		c = ranked.candidate
		print(f'  {i}. {c.title!r} score={ranked.overall_score:.3f} file_key={c.file_key or "(none)"}')
	print(f'degraded: {discovery.degraded[:8]}')

	print('\n--- Full pipeline (discovery + extraction + deep review) ---')
	file_key = os.environ.get('FIGMA_PIPELINE_FILE_KEY', '').strip() or bridge_key
	if file_key:
		source = 'FIGMA_PIPELINE_FILE_KEY' if os.environ.get('FIGMA_PIPELINE_FILE_KEY', '').strip() else 'Desktop Bridge'
		print(f'file_key source: {source} — injecting into selected candidates')
		_inject_file_key(discovery.selection_plan, file_key)

	if file_key and discovery.selection_plan:
		providers = FigmaProviderRegistry()
		extractions, extract_degraded = await extract_selection_plan(
			discovery.selection_plan,
			intent=discovery.intent,
			providers=providers,
		)
		ranked_by_id = {c.candidate.candidate_id: c for c in discovery.candidates}
		deep_reviews, review_degraded = deep_review_extractions(
			extractions,
			ranked_by_id=ranked_by_id,
			intent=discovery.intent,
			repo_root=repo_root,
		)
		ref_ids, reg_degraded = register_extractions(extractions, intent=discovery.intent)
		pipeline_degraded = list(discovery.degraded) + extract_degraded + review_degraded + reg_degraded
		from navigation.figma_intelligence.models import FigmaPipelineResult, FigmaIntentKind

		pipeline = FigmaPipelineResult(
			discovery=discovery,
			extractions=extractions,
			deep_reviews=deep_reviews,
			reference_registry_ids=ref_ids,
			pdg_ingest_ready=discovery.intent.kind == FigmaIntentKind.LEARN_PATTERNS,
			degraded=pipeline_degraded,
		)
	else:
		pipeline = await svc.run_pipeline(
			FigmaDiscoveryRequest(query=query, repo_root=repo_root, max_candidates=max_candidates)
		)
	print(f'extractions: {len(pipeline.extractions)}')
	for ext in pipeline.extractions:
		print(
			f'  - {ext.candidate_id}: tokens={len(ext.tokens)} '
			f'components={len(ext.components)} variables={len(ext.variables)} '
			f'degraded={ext.degraded}'
		)
	print(f'deep_reviews: {len(pipeline.deep_reviews)}')
	for review in pipeline.deep_reviews[:3]:
		print(
			f'  - {review.candidate_id}: overall={review.overall_score:.3f} '
			f'extraction_weight={review.extraction_weight:.2f}'
		)
	print(f'reference_registry_ids: {pipeline.reference_registry_ids}')
	print(f'pdg_ingest_ready: {pipeline.pdg_ingest_ready}')
	print(f'pipeline_degraded ({len(pipeline.degraded)}): {pipeline.degraded[:12]}')

	if not file_key and any('figma_console_missing_file_key' in d for d in pipeline.degraded):
		print('\n--- Extraction blocked ---')
		print('Catalog hits have no file_key. To complete extraction, either:')
		print('  1. Set FIGMA_PIPELINE_FILE_KEY=<your-owned-figma-file-key> in .env')
		print('  2. Open Figma Desktop + Desktop Bridge plugin, then re-run')
		print('  (Plugins -> Development -> Figma Desktop Bridge)')

	return 0


if __name__ == '__main__':
	raise SystemExit(asyncio.run(main()))
