"""Normalize LibreCrawl crawl results to SEO evidence."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef


def normalize_crawl_payload(
	payload: dict[str, Any],
	*,
	provider_id: str = 'librecrawl',
) -> list[SeoEvidenceRef]:
	evidence: list[SeoEvidenceRef] = []
	issues = payload.get('issues') or []
	for index, issue in enumerate(issues[:50]):
		if not isinstance(issue, dict):
			continue
		title = str(issue.get('type') or issue.get('issue_type') or issue.get('title') or 'crawl_issue')
		summary = str(issue.get('message') or issue.get('description') or issue.get('detail') or title)
		page_url = str(issue.get('url') or issue.get('page') or '')
		severity = _severity_from_issue(issue)
		kind = SeoEvidenceKind.CRAWL_ISSUE
		if 'schema' in title.lower():
			kind = SeoEvidenceKind.SCHEMA
		elif 'canonical' in title.lower() or 'redirect' in title.lower():
			kind = SeoEvidenceKind.TECHNICAL_ISSUE
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'librecrawl:issue:{index}',
				provider_id=provider_id,
				kind=kind,
				title=title,
				summary=summary,
				page_url=page_url,
				severity=severity,
				source_ref='librecrawl.crawl_status.issues',
				metadata=dict(issue),
			)
		)

	urls = payload.get('urls') or []
	for index, item in enumerate(urls[:100]):
		if not isinstance(item, dict):
			continue
		status_code = item.get('status') or item.get('status_code') or item.get('code')
		page_url = str(item.get('url') or '')
		if status_code is None and not item.get('canonical_url'):
			continue
		try:
			code = int(status_code) if status_code is not None else 0
		except (TypeError, ValueError):
			code = 0
		if code >= 400:
			evidence.append(
				SeoEvidenceRef(
					evidence_id=f'librecrawl:url:{index}',
					provider_id=provider_id,
					kind=SeoEvidenceKind.TECHNICAL_ISSUE,
					title=f'HTTP {code}: {page_url}',
					summary=f'Crawled URL returned status {code}',
					page_url=page_url,
					metric_value=float(code),
					metric_unit='status_code',
					severity='high' if code >= 500 else 'medium',
					source_ref='librecrawl.crawl_status.urls',
					metadata=dict(item),
				)
			)
		canonical = item.get('canonical_url') or item.get('canonical')
		declared = item.get('canonical') or item.get('meta_canonical')
		if canonical and declared and str(canonical) != str(declared):
			evidence.append(
				SeoEvidenceRef(
					evidence_id=f'librecrawl:canonical:{index}',
					provider_id=provider_id,
					kind=SeoEvidenceKind.TECHNICAL_ISSUE,
					title=f'Canonical mismatch: {page_url}',
					summary=f'Declared {declared} vs detected {canonical}',
					page_url=page_url,
					severity='medium',
					source_ref='librecrawl.canonical',
					metadata={'canonical': canonical, 'declared': declared},
				)
			)

	stats = payload.get('stats') or {}
	if stats:
		discovered = stats.get('discovered')
		crawled = stats.get('crawled')
		if discovered is not None:
			evidence.append(
				SeoEvidenceRef(
					evidence_id='librecrawl:stats:summary',
					provider_id=provider_id,
					kind=SeoEvidenceKind.TECHNICAL_ISSUE,
					title='Crawl summary',
					summary=f'Discovered {discovered} URLs, crawled {crawled}',
					severity='info',
					source_ref='librecrawl.stats',
					metadata=dict(stats),
				)
			)
	return evidence


def _severity_from_issue(issue: dict[str, Any]) -> str:
	severity = str(issue.get('severity') or issue.get('level') or '').lower()
	if severity in {'critical', 'error', 'high'}:
		return 'high'
	if severity in {'warning', 'medium'}:
		return 'medium'
	issue_type = str(issue.get('type') or '').lower()
	if 'broken' in issue_type or 'error' in issue_type:
		return 'high'
	return 'medium'
