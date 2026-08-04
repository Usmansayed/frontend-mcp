"""Post-process reasoning_context_v2 — Sprint 2 intelligence layer."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.evidence.identity import normalize_page_url, page_url_for_evidence
from navigation.seo_intelligence.models import SeoEvidenceRef
from navigation.seo_intelligence.reasoning.codebase_bridge import build_codebase_hints
from navigation.seo_intelligence.reasoning.impact import impact_sort_key, score_impact
from navigation.seo_intelligence.recommendations.dedupe import dedupe_correlations, dedupe_reasoning_units


def enrich_reasoning_context_v2(
	ctx: dict[str, Any],
	*,
	evidence: list[SeoEvidenceRef],
	repo_root: str = '',
	scan_id: str = '',
	base_url: str = '',
	include_crg: bool = True,
	fast_codebase: bool = False,
) -> dict[str, Any]:
	"""Codebase hints, browser↔code links, impact ranking — still v2 schema."""
	website = str((ctx.get('meta') or {}).get('website_url') or base_url)
	evidence_by_page = _group_by_page(evidence, base_url=website)

	for page in ctx.get('pages') or []:
		if not isinstance(page, dict):
			continue
		url = str(page.get('url') or '')
		page_evidence = evidence_by_page.get(normalize_page_url(url) or '__site__', [])
		hints = build_codebase_hints(
			page_evidence,
			page_url=url,
			repo_root=repo_root,
			base_url=website,
			include_crg=include_crg,
			fast=fast_codebase,
		)
		page['codebase_hints'] = hints
		page['browser_code_links'] = _browser_code_links(page_evidence, hints, scan_id=scan_id)
		page['impact'] = score_impact(page_evidence, page_url=url)

	site_correlations = dedupe_correlations(list(ctx.get('site_correlations') or []))
	ctx['site_correlations'] = site_correlations

	units = dedupe_reasoning_units(list(ctx.get('reasoning_units') or []))
	for unit in units:
		page_url = str(unit.get('page_url') or '')
		unit_evidence = [
			e for e in evidence
			if e.evidence_id in (unit.get('evidence_ids') or [])
		]
		unit['impact'] = score_impact(unit_evidence, page_url=page_url)
		unit['codebase_hints'] = _hints_for_page(ctx, page_url)

	units.sort(key=lambda u: (-impact_sort_key(u.get('impact') or {}), -float((u.get('confidence') or {}).get('score', 0))))
	ctx['reasoning_units'] = units
	ctx['sprint'] = 'intelligence_v2'
	return ctx


def _group_by_page(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str,
) -> dict[str, list[SeoEvidenceRef]]:
	out: dict[str, list[SeoEvidenceRef]] = {}
	for item in evidence:
		key = normalize_page_url(page_url_for_evidence(item, base_url=base_url)) or '__site__'
		out.setdefault(key, []).append(item)
	return out


def _browser_code_links(
	evidence: list[SeoEvidenceRef],
	hints: list[dict[str, Any]],
	*,
	scan_id: str,
) -> list[dict[str, Any]]:
	browser = [e for e in evidence if e.provider_id == 'browser']
	if not browser or not hints:
		return []
	scan_ids = list(dict.fromkeys(
		str(e.metadata.get('scan_id') or scan_id)
		for e in browser
		if e.metadata.get('scan_id') or scan_id
	))
	return [
		{
			'scan_id': sid,
			'page_url': browser[0].page_url or browser[0].url,
			'rendering_evidence_ids': [e.evidence_id for e in browser],
			'likely_files': [h['file'] for h in hints[:3]],
			'rationale': 'Browser rendering issues on URL with heuristic code matches',
		}
		for sid in scan_ids[:2]
	]


def _hints_for_page(ctx: dict[str, Any], page_url: str) -> list[dict[str, Any]]:
	target = normalize_page_url(page_url)
	for page in ctx.get('pages') or []:
		if normalize_page_url(str(page.get('url') or '')) == target:
			return list(page.get('codebase_hints') or [])
	if not target:
		for page in ctx.get('pages') or []:
			if page.get('page_key') == '__site__':
				return list(page.get('codebase_hints') or [])
	return []
