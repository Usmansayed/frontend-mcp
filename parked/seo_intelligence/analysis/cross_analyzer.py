"""Cross-analysis — URL-joined evidence correlation (ADR-027)."""
from __future__ import annotations

from navigation.seo_intelligence.evidence.identity import normalize_page_url, page_url_for_evidence
from navigation.seo_intelligence.knowledge.graph.pages import group_evidence_by_page
from navigation.seo_intelligence.models import SeoEvidenceRef

_INDEX_KINDS = frozenset({'index_status', 'crawl_issue'})
_RENDER_KINDS = frozenset({'rendering_issue'})
_CWV_KINDS = frozenset({'core_web_vital', 'performance'})
_TECH_KINDS = frozenset({'technical_issue', 'schema'})
_QUERY_KINDS = frozenset({'search_query'})
_TRAFFIC_KINDS = frozenset({'traffic_metric'})


def run_cross_analysis(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> list[dict[str, object]]:
	"""Return URL-joined hypotheses — same page required for page-level correlations."""
	findings: list[dict[str, object]] = []
	pages = group_evidence_by_page(evidence, base_url=base_url)

	for page_key, items in pages.items():
		page_url = '' if page_key == '__site__' else page_key
		findings.extend(_page_correlations(page_url, items))

	findings.extend(_site_level_correlations(evidence, base_url=base_url))
	return findings


def _page_correlations(page_url: str, items: list[SeoEvidenceRef]) -> list[dict[str, object]]:
	findings: list[dict[str, object]] = []
	by_kind: dict[str, list[SeoEvidenceRef]] = {}
	for item in items:
		by_kind.setdefault(item.kind.value, []).append(item)

	index_issues = [e for k in _INDEX_KINDS for e in by_kind.get(k, [])]
	render_issues = [e for k in _RENDER_KINDS for e in by_kind.get(k, [])]
	cwv = [e for k in _CWV_KINDS for e in by_kind.get(k, [])]
	technical = [e for k in _TECH_KINDS for e in by_kind.get(k, [])]

	if index_issues and render_issues:
		sample = index_issues[:2] + render_issues[:2]
		findings.append(_finding(
			'indexing_rendering_correlation',
			page_url=page_url,
			title='Rendering may affect indexing on this page',
			summary='Index/crawl signals and rendering issues on the same URL — investigate client-side rendering.',
			root_cause='Client-side rendering or hydration failures may prevent indexing for this URL',
			evidence=sample,
			confidence=0.82,
		))

	if cwv and render_issues:
		sample = cwv[:2] + render_issues[:2]
		findings.append(_finding(
			'cwv_rendering_correlation',
			page_url=page_url,
			title='Core Web Vitals and rendering overlap on this page',
			summary='Poor CWV alongside rendering issues on the same URL.',
			root_cause='JavaScript errors or hydration mismatch degrading page experience on this URL',
			evidence=sample,
			confidence=0.75,
		))

	if technical and index_issues:
		sample = technical[:2] + index_issues[:2]
		findings.append(_finding(
			'technical_index_correlation',
			page_url=page_url,
			title='Technical issues may block indexing on this page',
			summary='Technical crawl issues coincide with index problems on the same URL.',
			root_cause='Canonical, redirect, or robots issues blocking indexation for this URL',
			evidence=sample,
			confidence=0.78,
		))

	broken = [
		t for t in technical
		if t.severity in {'high', 'critical'} or 'HTTP 4' in t.title or 'HTTP 5' in t.title
	]
	queries = by_kind.get('search_query', [])
	if broken and queries and page_url:
		findings.append(_finding(
			'broken_pages_with_search_visibility',
			page_url=page_url,
			title='Broken page may still receive search visibility',
			summary='HTTP errors on a URL with search query evidence.',
			root_cause='HTTP errors on a URL that receives search impressions',
			evidence=broken[:2] + queries[:2],
			confidence=0.8,
		))

	return findings


def _site_level_correlations(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> list[dict[str, object]]:
	findings: list[dict[str, object]] = []
	by_kind: dict[str, list[SeoEvidenceRef]] = {}
	by_provider: dict[str, list[SeoEvidenceRef]] = {}
	for item in evidence:
		by_kind.setdefault(item.kind.value, []).append(item)
		by_provider.setdefault(item.provider_id, []).append(item)

	queries = by_kind.get('search_query', [])
	cwv = [e for k in _CWV_KINDS for e in by_kind.get(k, [])]
	traffic = by_kind.get('traffic_metric', [])

	if queries and cwv:
		joined = _join_query_cwv_on_page(queries, cwv, base_url=base_url)
		if joined:
			q, c, page_url = joined
			findings.append(_finding(
				'ctr_cwv_correlation',
				page_url=page_url,
				title='CTR may be affected by page experience',
				summary='Search query and CWV evidence share a landing URL.',
				root_cause='Slow or unstable page may reduce CTR from SERPs',
				evidence=[q, c],
				confidence=0.68,
			))
		else:
			sample_q = [q for q in queries if (q.metadata.get('impressions') or 0) >= 50][:2]
			if sample_q and cwv:
				findings.append(_finding(
					'ctr_cwv_correlation',
					page_url='',
					scope='site',
					title='CTR may be affected by page experience (site-level)',
					summary='Query and CWV data present — URL join unavailable; verify landing page manually.',
					root_cause='Possible page experience impact on high-impression queries',
					evidence=sample_q + cwv[:2],
					confidence=0.52,
				))

	if traffic and queries:
		findings.append(_finding(
			'traffic_query_landing_alignment',
			page_url='',
			scope='site',
			title='Align GA4 landing pages with GSC queries',
			summary='Traffic and search query evidence collected — compare landing pages to query intent.',
			root_cause='Landing page traffic may not align with top GSC queries',
			evidence=traffic[:3] + queries[:3],
			confidence=0.55,
		))

	return findings


def _join_query_cwv_on_page(
	queries: list[SeoEvidenceRef],
	cwv: list[SeoEvidenceRef],
	*,
	base_url: str,
) -> tuple[SeoEvidenceRef, SeoEvidenceRef, str] | None:
	cwv_by_page = {normalize_page_url(page_url_for_evidence(c, base_url=base_url)): c for c in cwv}
	for q in queries:
		landing = str(q.metadata.get('landingPage') or q.metadata.get('page') or '').strip()
		page = normalize_page_url(landing, base_url=base_url) if landing else ''
		if page and page in cwv_by_page:
			return q, cwv_by_page[page], page
	return None


def _finding(
	analysis_id: str,
	*,
	page_url: str = '',
	scope: str = 'page',
	title: str,
	summary: str,
	root_cause: str,
	evidence: list[SeoEvidenceRef],
	confidence: float,
	business_impact: str = '',
) -> dict[str, object]:
	return {
		'analysis_id': analysis_id,
		'page_url': page_url,
		'scope': scope,
		'title': title,
		'summary': summary,
		'root_cause': root_cause,
		'business_impact': business_impact or 'Improves organic visibility for affected URLs',
		'evidence_ids': [e.evidence_id for e in evidence],
		'confidence': confidence,
		'category': 'cross_analysis',
		'providers': sorted({e.provider_id for e in evidence}),
	}
