"""Opportunity detection — page-aware SEO growth signals (Sprint 2)."""
from __future__ import annotations

from navigation.seo_intelligence.evidence.identity import normalize_page_url, page_url_for_evidence
from navigation.seo_intelligence.knowledge.graph.pages import group_evidence_by_page
from navigation.seo_intelligence.models import SeoEvidenceRef


def detect_opportunities(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> list[dict[str, object]]:
	findings: list[dict[str, object]] = []
	pages = group_evidence_by_page(evidence, base_url=base_url)

	for page_key, items in pages.items():
		page_url = '' if page_key == '__site__' else page_key
		findings.extend(_page_opportunities(page_url, items))

	findings.extend(_site_opportunities(evidence, base_url=base_url))
	return findings


def _page_opportunities(page_url: str, items: list[SeoEvidenceRef]) -> list[dict[str, object]]:
	findings: list[dict[str, object]] = []
	by_kind: dict[str, list[SeoEvidenceRef]] = {}
	for item in items:
		by_kind.setdefault(item.kind.value, []).append(item)

	queries = by_kind.get('search_query', [])
	technical = by_kind.get('technical_issue', []) + by_kind.get('schema', [])
	index_issues = by_kind.get('index_status', []) + by_kind.get('crawl_issue', [])
	cwv = by_kind.get('core_web_vital', []) + by_kind.get('performance', [])

	for q in queries:
		impressions = float(q.metadata.get('impressions') or 0)
		ctr = float(q.metadata.get('ctr') or q.metric_value or 0)
		position = float(q.metadata.get('position') or q.metadata.get('average_position') or 0)

		if impressions >= 100 and 0 < ctr < 0.02:
			findings.append(_opp(
				f'opportunity_low_ctr_{q.evidence_id}',
				page_url=page_url,
				title='High impressions with low CTR',
				summary=(
					f'Query "{q.title}" has {int(impressions)} impressions but CTR {ctr:.2%} — '
					f'improve title and meta on {page_url or "landing page"}.'
				),
				evidence=[q],
				priority='medium',
			))

		if 8 <= position <= 20 and impressions >= 20:
			findings.append(_opp(
				f'opportunity_striking_distance_{q.evidence_id}',
				page_url=page_url,
				title='Striking-distance keyword (positions 8–20)',
				summary=(
					f'"{q.title}" at position {position:.1f} with {int(impressions)} impressions — '
					'incremental on-page and internal link work may reach page one.'
				),
				evidence=[q],
				priority='medium',
			))

	weak_meta = [
		t for t in technical
		if any(k in t.title.lower() for k in ('missing title', 'missing meta', 'duplicate title', 'thin content'))
	]
	if weak_meta:
		findings.append(_opp(
			'opportunity_weak_metadata',
			page_url=page_url,
			title='Weak or missing metadata',
			summary='Crawl found missing/duplicate titles or thin content on this URL.',
			evidence=weak_meta[:3],
			priority='medium',
		))

	if index_issues and queries:
		not_indexed = [
			i for i in index_issues
			if 'not indexed' in i.summary.lower() or 'excluded' in i.summary.lower() or i.metadata.get('verdict') == 'FAIL'
		]
		if not_indexed:
			findings.append(_opp(
				'opportunity_indexing',
				page_url=page_url,
				title='Indexing opportunity',
				summary='Coverage issues on a URL with search query demand.',
				evidence=not_indexed[:2] + queries[:2],
				priority='high',
			))

	if cwv:
		quick = [c for c in cwv if c.severity in {'medium', 'high', 'critical'}]
		if quick:
			findings.append(_opp(
				'opportunity_cwv_quick_win',
				page_url=page_url,
				title='Core Web Vitals quick win',
				summary='Fixable CWV issues on this page.',
				evidence=quick[:2],
				priority='medium',
			))

	link_gaps = [
		t for t in technical
		if 'internal link' in t.title.lower() or 'orphan' in t.summary.lower()
	]
	if link_gaps:
		findings.append(_opp(
			'opportunity_internal_links',
			page_url=page_url,
			title='Internal linking opportunity',
			summary='Weak internal links on this URL.',
			evidence=link_gaps[:3],
			priority='medium',
		))

	return findings


def _site_opportunities(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> list[dict[str, object]]:
	"""Cross-page opportunities when page join is unavailable."""
	findings: list[dict[str, object]] = []
	queries = [e for e in evidence if e.kind.value == 'search_query']
	cwv = [e for e in evidence if e.kind.value in {'core_web_vital', 'performance'}]

	for q in queries:
		landing = str(q.metadata.get('landingPage') or q.page_url or '')
		page = normalize_page_url(landing, base_url=base_url) if landing else ''
		if not page:
			continue
		matching_cwv = [
			c for c in cwv
			if normalize_page_url(page_url_for_evidence(c, base_url=base_url)) == page
		]
		if matching_cwv and float(q.metadata.get('impressions') or 0) >= 50:
			findings.append(_opp(
				f'opportunity_query_cwv_{q.evidence_id}',
				page_url=page,
				title='Query traffic with CWV issues on landing page',
				summary=f'High-impression query "{q.title}" lands on a page with CWV signals.',
				evidence=[q, matching_cwv[0]],
				priority='high',
			))

	return findings


def _opp(
	analysis_id: str,
	*,
	page_url: str,
	title: str,
	summary: str,
	evidence: list[SeoEvidenceRef],
	priority: str,
) -> dict[str, object]:
	return {
		'analysis_id': analysis_id,
		'page_url': page_url,
		'scope': 'page' if page_url else 'site',
		'title': title,
		'summary': summary,
		'root_cause': summary,
		'business_impact': 'Incremental organic traffic gain',
		'evidence_ids': [e.evidence_id for e in evidence],
		'confidence': 0.62,
		'category': 'opportunity',
		'priority': priority,
		'providers': sorted({e.provider_id for e in evidence}),
	}
