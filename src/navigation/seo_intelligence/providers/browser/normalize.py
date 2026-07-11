"""Normalize Browser Intelligence observations into SEO evidence."""
from __future__ import annotations

from typing import Any

from navigation.core.envelope import agent_summary_from_observation
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef


def normalize_browser_observation(
	observation: dict[str, Any],
	*,
	scan_id: str,
	provider_id: str = 'browser',
) -> list[SeoEvidenceRef]:
	evidence: list[SeoEvidenceRef] = []
	page_url = str(observation.get('url') or '')
	summary = agent_summary_from_observation(observation)

	for index, message in enumerate(summary.get('blocking') or []):
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'browser:blocking:{index}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.RENDERING_ISSUE,
				title='Blocking browser issue',
				summary=str(message),
				page_url=page_url,
				severity='high',
				source_ref=f'scan:{scan_id}',
				metadata={'scan_id': scan_id, 'level': 'blocking'},
			)
		)

	dev_insights = observation.get('dev_insights') or {}
	for index, issue in enumerate((dev_insights.get('issues') or [])[:20]):
		if not isinstance(issue, dict):
			continue
		kind_name = str(issue.get('kind') or issue.get('type') or 'rendering')
		severity = 'high' if issue.get('tier') == 'blocking' or issue.get('severity') in {'high', 'critical'} else 'medium'
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'browser:dev:{index}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.RENDERING_ISSUE,
				title=str(issue.get('title') or issue.get('message') or kind_name),
				summary=str(issue.get('message') or issue.get('detail') or kind_name),
				page_url=page_url,
				severity=severity,
				source_ref=f'scan:{scan_id}',
				metadata={'scan_id': scan_id, **issue},
			)
		)

	console = observation.get('console') or {}
	for index, message in enumerate((console.get('blocking') or [])[:10]):
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'browser:console:{index}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.RENDERING_ISSUE,
				title='Console error',
				summary=str(message),
				page_url=page_url,
				severity='high',
				source_ref=f'scan:{scan_id}',
				metadata={'scan_id': scan_id},
			)
		)

	visual = observation.get('visual_insights') or {}
	for index, message in enumerate((visual.get('blocking') or [])[:10]):
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'browser:visual:{index}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.RENDERING_ISSUE,
				title='Visual insight (blocking)',
				summary=str(message),
				page_url=page_url,
				severity='high',
				source_ref=f'scan:{scan_id}',
				metadata={'scan_id': scan_id},
			)
		)

	for index, message in enumerate((summary.get('advisory') or [])[:5]):
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'browser:advisory:{index}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.RENDERING_ISSUE,
				title='Browser advisory',
				summary=str(message),
				page_url=page_url,
				severity='medium',
				source_ref=f'scan:{scan_id}',
				metadata={'scan_id': scan_id, 'level': 'advisory'},
			)
		)

	if observation.get('degraded'):
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'browser:degraded:{scan_id}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.RENDERING_ISSUE,
				title='Observation degraded signals',
				summary='; '.join(str(d) for d in observation.get('degraded')[:5]),
				page_url=page_url,
				severity='medium',
				source_ref=f'scan:{scan_id}',
				metadata={'degraded': observation.get('degraded')},
			)
		)
	return evidence
