"""Cross-analysis — correlate evidence across providers (evidence-based only)."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoEvidenceRef


def run_cross_analysis(evidence: list[SeoEvidenceRef]) -> list[dict[str, object]]:
	"""Return analysis hypotheses with required evidence_ids — no unsupported claims."""
	by_kind: dict[str, list[SeoEvidenceRef]] = {}
	for item in evidence:
		by_kind.setdefault(item.kind.value, []).append(item)

	findings: list[dict[str, object]] = []

	index_issues = by_kind.get('index_status', []) + by_kind.get('crawl_issue', [])
	render_issues = by_kind.get('rendering_issue', [])
	cwv = by_kind.get('core_web_vital', [])
	queries = by_kind.get('search_query', [])

	if index_issues and render_issues:
		findings.append({
			'analysis_id': 'indexing_rendering_correlation',
			'title': 'Rendering may affect indexing',
			'summary': 'Both index/crawl signals and rendering issues present — investigate client-side rendering.',
			'evidence_ids': [e.evidence_id for e in index_issues[:3] + render_issues[:3]],
			'confidence': 0.6,
		})

	if cwv and render_issues:
		findings.append({
			'analysis_id': 'cwv_rendering_correlation',
			'title': 'Core Web Vitals and rendering overlap',
			'summary': 'Poor CWV alongside rendering issues — check hydration, layout shift, and JS errors.',
			'evidence_ids': [e.evidence_id for e in cwv[:3] + render_issues[:3]],
			'confidence': 0.65,
		})

	if queries and cwv:
		findings.append({
			'analysis_id': 'ctr_cwv_correlation',
			'title': 'CTR may be affected by page experience',
			'summary': 'Search query performance data plus CWV signals — correlate landing page speed with CTR drops.',
			'evidence_ids': [e.evidence_id for e in queries[:3] + cwv[:3]],
			'confidence': 0.55,
		})

	return findings
