"""Issue class normalization for provider agreement v2."""
from __future__ import annotations

from navigation.seo_intelligence.evidence.identity import normalize_page_url, page_url_for_evidence
from navigation.seo_intelligence.models import SeoEvidenceRef

_APPLICABLE_PROVIDERS: dict[str, frozenset[str]] = {
	'indexing': frozenset({'search-console', 'librecrawl', 'browser'}),
	'rendering': frozenset({'browser', 'librecrawl', 'lighthouse'}),
	'cwv': frozenset({'lighthouse', 'browser'}),
	'metadata': frozenset({'librecrawl', 'lighthouse', 'browser'}),
	'technical': frozenset({'librecrawl', 'lighthouse', 'browser'}),
	'traffic': frozenset({'analytics-ga4', 'search-console'}),
	'query': frozenset({'search-console', 'bing-webmaster'}),
}


def issue_class_for_evidence(item: SeoEvidenceRef) -> str:
	kind = item.kind.value
	title = item.title.lower()

	if kind == 'index_status':
		return 'indexing'
	if kind == 'rendering_issue':
		return 'rendering'
	if kind in {'core_web_vital', 'performance'}:
		return 'cwv'
	if kind == 'traffic_metric':
		return 'traffic'
	if kind == 'search_query':
		return 'query'
	if kind == 'crawl_issue':
		return 'technical'
	if kind == 'technical_issue':
		if any(k in title for k in ('meta', 'title', 'description')):
			return 'metadata'
		if any(k in title for k in ('canonical', 'redirect', 'robots')):
			return 'indexing'
		return 'technical'
	if kind == 'schema':
		return 'metadata'
	return kind


def applicable_providers(issue_class: str) -> frozenset[str]:
	return _APPLICABLE_PROVIDERS.get(issue_class, frozenset())


def provider_agreement_v2(
	evidence: list[SeoEvidenceRef],
	*,
	page_url: str = '',
	base_url: str = '',
) -> dict[str, object]:
	"""
	Score whether independent providers agree on the same issue class for the same URL.
	Returns score in [0, 1] plus breakdown.
	"""
	target = normalize_page_url(page_url) if page_url else ''
	by_class: dict[str, set[str]] = {}

	for item in evidence:
		item_page = normalize_page_url(page_url_for_evidence(item, base_url=base_url))
		if target and item_page != target:
			continue
		cls = issue_class_for_evidence(item)
		by_class.setdefault(cls, set()).add(item.provider_id)

	if not by_class:
		present = sorted({e.provider_id for e in evidence})
		return {
			'score': min(1.0, len(present) / 4) if present else 0.0,
			'issue_classes': [],
			'providers_by_class': {},
			'explanation': 'no_issue_class_match_for_page',
		}

	best_score = 0.0
	best_class = ''
	providers_by_class: dict[str, list[str]] = {}

	for cls, providers in by_class.items():
		applicable = applicable_providers(cls) or providers
		overlap = providers & applicable
		score = len(overlap) / max(1, len(applicable))
		providers_by_class[cls] = sorted(providers)
		if score > best_score:
			best_score = score
			best_class = cls

	return {
		'score': round(min(1.0, best_score), 3),
		'primary_issue_class': best_class,
		'issue_classes': sorted(by_class.keys()),
		'providers_by_class': providers_by_class,
		'explanation': (
			f'{len(by_class.get(best_class, set()))} provider(s) on '
			f'"{best_class}" for {target or "site"}'
		),
	}
