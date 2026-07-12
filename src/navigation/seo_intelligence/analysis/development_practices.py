"""Development SEO best-practice signals — from Browser, Lighthouse, and LibreCrawl only."""
from __future__ import annotations

from navigation.seo_intelligence.evidence.identity import page_url_for_evidence
from navigation.seo_intelligence.models import SeoEvidenceRef

_DEV_PROVIDERS = frozenset({'browser', 'lighthouse', 'librecrawl'})


def detect_development_practices(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> list[dict[str, object]]:
	"""Best-practice findings for Development SEO mode — evidence-linked only."""
	dev_evidence = [e for e in evidence if e.provider_id in _DEV_PROVIDERS]
	if not dev_evidence:
		return []

	findings: list[dict[str, object]] = []
	by_kind: dict[str, list[SeoEvidenceRef]] = {}
	for item in dev_evidence:
		by_kind.setdefault(item.kind.value, []).append(item)

	technical = by_kind.get('technical_issue', []) + by_kind.get('schema', [])
	rendering = by_kind.get('rendering_issue', [])
	cwv = by_kind.get('core_web_vital', []) + by_kind.get('performance', [])

	meta_issues = [
		t for t in technical
		if any(k in t.title.lower() for k in ('title', 'meta', 'description', 'canonical', 'robots', 'hreflang'))
	]
	if meta_issues:
		sample = meta_issues[:3]
		findings.append(_finding(
			'dev_practice_metadata',
			sample,
			title='On-page metadata needs attention',
			summary='Title, meta description, or canonical signals are missing or inconsistent.',
			priority='high',
			base_url=base_url,
		))

	schema_issues = [t for t in technical if 'schema' in t.title.lower() or t.kind.value == 'schema']
	if schema_issues:
		sample = schema_issues[:2]
		findings.append(_finding(
			'dev_practice_schema',
			sample,
			title='Structured data opportunity',
			summary='Schema markup is missing or invalid on crawled pages.',
			priority='medium',
			base_url=base_url,
		))

	a11y_perf = [
		e for e in cwv + technical
		if e.severity in {'medium', 'high', 'critical'}
		or 'accessibility' in e.title.lower()
		or 'a11y' in e.summary.lower()
	]
	if a11y_perf:
		sample = a11y_perf[:3]
		findings.append(_finding(
			'dev_practice_accessibility_cwv',
			sample,
			title='Accessibility or Core Web Vitals gap',
			summary='Lighthouse or crawl found accessibility or performance issues to fix before launch.',
			priority='high',
			base_url=base_url,
		))

	if rendering:
		sample = rendering[:2]
		findings.append(_finding(
			'dev_practice_rendering',
			sample,
			title='Client rendering issue during development',
			summary='Browser Intelligence found hydration, layout, or console errors.',
			priority='high',
			base_url=base_url,
		))

	link_issues = [
		t for t in technical
		if 'internal link' in t.title.lower() or 'orphan' in t.summary.lower() or 'broken link' in t.title.lower()
	]
	if link_issues:
		sample = link_issues[:3]
		findings.append(_finding(
			'dev_practice_internal_links',
			sample,
			title='Internal linking structure needs work',
			summary='Crawl found weak internal links, orphans, or broken links.',
			priority='medium',
			base_url=base_url,
		))

	semantic_hints = [
		t for t in technical
		if any(k in t.title.lower() for k in ('h1', 'heading', 'semantic', 'alt text', 'alt attribute'))
	]
	if semantic_hints:
		sample = semantic_hints[:2]
		findings.append(_finding(
			'dev_practice_semantic_html',
			sample,
			title='Semantic HTML or content structure gap',
			summary='Heading hierarchy or image alt text issues detected.',
			priority='medium',
			base_url=base_url,
		))

	return findings


def _finding(
	analysis_id: str,
	sample: list[SeoEvidenceRef],
	*,
	title: str,
	summary: str,
	priority: str,
	base_url: str,
) -> dict[str, object]:
	page_url = page_url_for_evidence(sample[0], base_url=base_url) if sample else ''
	return {
		'analysis_id': analysis_id,
		'page_url': page_url,
		'scope': 'page' if page_url else 'site',
		'title': title,
		'summary': summary,
		'root_cause': summary,
		'business_impact': 'Improves launch-quality SEO and crawl understanding',
		'evidence_ids': [e.evidence_id for e in sample],
		'confidence': 0.7,
		'category': 'development_practice',
		'priority': priority,
		'providers': sorted({e.provider_id for e in sample}),
	}
