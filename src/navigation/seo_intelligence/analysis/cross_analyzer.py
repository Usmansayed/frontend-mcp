"""Cross-analysis — correlate live evidence across providers (evidence-based only)."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoEvidenceRef


def run_cross_analysis(evidence: list[SeoEvidenceRef]) -> list[dict[str, object]]:
	"""Return analysis hypotheses with required evidence_ids — no unsupported claims."""
	by_kind: dict[str, list[SeoEvidenceRef]] = {}
	by_provider: dict[str, list[SeoEvidenceRef]] = {}
	for item in evidence:
		by_kind.setdefault(item.kind.value, []).append(item)
		by_provider.setdefault(item.provider_id, []).append(item)

	findings: list[dict[str, object]] = []

	index_issues = by_kind.get('index_status', []) + by_kind.get('crawl_issue', [])
	render_issues = by_kind.get('rendering_issue', [])
	cwv = by_kind.get('core_web_vital', []) + by_kind.get('performance', [])
	queries = by_kind.get('search_query', [])
	technical = by_kind.get('technical_issue', []) + by_kind.get('schema', [])
	traffic = by_kind.get('traffic_metric', [])

	if index_issues and render_issues:
		findings.append({
			'analysis_id': 'indexing_rendering_correlation',
			'title': 'Rendering may affect indexing',
			'summary': 'Both index/crawl signals and rendering issues present — investigate client-side rendering.',
			'evidence_ids': [e.evidence_id for e in index_issues[:3] + render_issues[:3]],
			'confidence': 0.72,
			'providers': sorted({e.provider_id for e in index_issues[:3] + render_issues[:3]}),
		})

	if cwv and render_issues:
		findings.append({
			'analysis_id': 'cwv_rendering_correlation',
			'title': 'Core Web Vitals and rendering overlap',
			'summary': 'Poor CWV alongside rendering issues — check hydration, layout shift, and JS errors.',
			'evidence_ids': [e.evidence_id for e in cwv[:3] + render_issues[:3]],
			'confidence': 0.68,
			'providers': sorted({e.provider_id for e in cwv[:3] + render_issues[:3]}),
		})

	if queries and cwv:
		high_impression = [q for q in queries if (q.metadata.get('impressions') or 0) >= 50 or q.metric_value]
		sample_q = high_impression[:3] or queries[:3]
		findings.append({
			'analysis_id': 'ctr_cwv_correlation',
			'title': 'CTR may be affected by page experience',
			'summary': 'Search query performance data plus CWV signals — correlate landing page speed with CTR drops.',
			'evidence_ids': [e.evidence_id for e in sample_q + cwv[:3]],
			'confidence': 0.58,
			'providers': sorted({e.provider_id for e in sample_q + cwv[:3]}),
		})

	if technical and index_issues:
		findings.append({
			'analysis_id': 'technical_index_correlation',
			'title': 'Technical crawl issues may block indexing',
			'summary': 'LibreCrawl/Lighthouse technical issues coincide with index coverage problems.',
			'evidence_ids': [e.evidence_id for e in technical[:3] + index_issues[:3]],
			'confidence': 0.64,
			'providers': sorted({e.provider_id for e in technical[:3] + index_issues[:3]}),
		})

	if technical and queries:
		broken = [t for t in technical if t.severity in {'high', 'critical'} or 'HTTP 4' in t.title or 'HTTP 5' in t.title]
		if broken:
			findings.append({
				'analysis_id': 'broken_pages_with_search_visibility',
				'title': 'Broken or error pages may still receive impressions',
				'summary': 'Technical HTTP errors overlap with search query data — fix crawl errors on ranking URLs.',
				'evidence_ids': [e.evidence_id for e in broken[:3] + queries[:3]],
				'confidence': 0.7,
				'providers': sorted({e.provider_id for e in broken[:3] + queries[:3]}),
			})

	if traffic and queries:
		findings.append({
			'analysis_id': 'traffic_query_landing_alignment',
			'title': 'Align GA4 landing pages with GSC queries',
			'summary': 'Traffic and search query evidence both present — compare landing page sessions to query landing URLs.',
			'evidence_ids': [e.evidence_id for e in traffic[:3] + queries[:3]],
			'confidence': 0.52,
			'providers': sorted({e.provider_id for e in traffic[:3] + queries[:3]}),
		})

	if len(by_provider) >= 3 and findings:
		findings.append({
			'analysis_id': 'multi_provider_coverage',
			'title': 'Multi-source SEO evidence collected',
			'summary': (
				f'Evidence from {len(by_provider)} providers enables cross-source validation — '
				'prioritize fixes cited by multiple sources.'
			),
			'evidence_ids': [e.evidence_id for e in evidence[:6]],
			'confidence': 0.45,
			'providers': sorted(by_provider.keys()),
		})

	return findings
