"""Normalize LibreCrawl crawl results to SEO evidence."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.evidence.identity import stable_evidence_id
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef


def normalize_crawl_payload(
	payload: dict[str, Any],
	*,
	provider_id: str = 'librecrawl',
	base_url: str = '',
) -> list[SeoEvidenceRef]:
	evidence: list[SeoEvidenceRef] = []
	issues = payload.get('issues') or []
	for issue in issues[:50]:
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
				evidence_id=stable_evidence_id(
					provider_id,
					kind.value,
					page_url=page_url,
					title=title,
					source_ref='librecrawl.crawl_status.issues',
					base_url=base_url,
				),
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
	for item in urls[:100]:
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
					evidence_id=stable_evidence_id(
						provider_id,
						SeoEvidenceKind.TECHNICAL_ISSUE.value,
						page_url=page_url,
						title=f'HTTP {code}',
						source_ref='librecrawl.crawl_status.urls',
						metric_key=str(code),
						base_url=base_url,
					),
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
					evidence_id=stable_evidence_id(
						provider_id,
						SeoEvidenceKind.TECHNICAL_ISSUE.value,
						page_url=page_url,
						title='canonical mismatch',
						source_ref='librecrawl.canonical',
						base_url=base_url,
					),
					provider_id=provider_id,
					kind=SeoEvidenceKind.TECHNICAL_ISSUE,
					title=f'Canonical mismatch: {page_url}',
					summary=f'Declared {declared} vs detected {canonical}',
					page_url=page_url,
					severity='medium',
					source_ref='librecrawl.canonical',
					metadata=dict(item),
				)
			)
	return evidence


def _severity_from_issue(issue: dict[str, Any]) -> str:
	raw = str(issue.get('severity') or issue.get('level') or 'medium').lower()
	if raw in {'critical', 'high', 'medium', 'low', 'info'}:
		return raw
	return 'medium'
