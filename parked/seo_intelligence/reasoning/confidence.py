"""Composed confidence from evidence — transparent, not hand-tuned (ADR-027)."""
from __future__ import annotations

import time
from typing import Any

from navigation.seo_intelligence.knowledge.graph.issue_class import provider_agreement_v2
from navigation.seo_intelligence.models import SeoEvidenceRef

_SEVERITY_WEIGHT = {'critical': 1.0, 'high': 0.85, 'medium': 0.6, 'info': 0.35, 'low': 0.25}


def confidence_label(score: float) -> str:
	if score >= 0.85:
		return 'high'
	if score >= 0.60:
		return 'medium'
	return 'low'


def compose_confidence(
	evidence: list[SeoEvidenceRef],
	*,
	providers_present: list[str] | None = None,
	collected_at: float | None = None,
	max_providers: int = 4,
) -> dict[str, Any]:
	"""confidence = provider_agreement × data_freshness × metric_strength × sample_size."""
	if not evidence:
		return {
			'score': 0.0,
			'label': 'low',
			'composition': {
				'provider_agreement': 0.0,
				'data_freshness': 0.0,
				'metric_strength': 0.0,
				'sample_size': 0.0,
			},
			'providers_present': [],
			'providers_absent': [],
			'explanation': 'no evidence',
		}

	present = sorted(set(providers_present or [e.provider_id for e in evidence]))
	agreement_block = provider_agreement_v2(evidence)
	provider_agreement = float(agreement_block.get('score') or 0.0)
	if provider_agreement <= 0.0:
		provider_agreement = min(1.0, len(present) / max(1, max_providers))

	data_freshness = _freshness_factor(collected_at)
	metric_strength = _metric_strength_factor(evidence)
	sample_size = _sample_size_factor(evidence)

	score = provider_agreement * data_freshness * metric_strength * sample_size
	score = round(min(1.0, max(0.0, score)), 3)

	return {
		'score': score,
		'label': confidence_label(score),
		'composition': {
			'provider_agreement': round(provider_agreement, 3),
			'data_freshness': round(data_freshness, 3),
			'metric_strength': round(metric_strength, 3),
			'sample_size': round(sample_size, 3),
		},
		'providers_present': present,
		'providers_absent': [],
		'provider_agreement_v2': agreement_block,
		'explanation': (
			f'{agreement_block.get("explanation", "")}; '
			f'freshness {data_freshness:.0%}; '
			f'metric strength {metric_strength:.0%}; sample {sample_size:.0%}'
		).strip('; '),
	}


def _freshness_factor(collected_at: float | None) -> float:
	if collected_at is None:
		return 1.0
	age_days = (time.time() - collected_at) / 86400
	if age_days <= 7:
		return 1.0
	if age_days <= 28:
		return 0.85
	if age_days <= 90:
		return 0.65
	return 0.45


def _metric_strength_factor(evidence: list[SeoEvidenceRef]) -> float:
	weights = [_SEVERITY_WEIGHT.get(e.severity, 0.4) for e in evidence]
	if not weights:
		return 0.5
	return min(1.0, sum(weights) / len(weights))


def _sample_size_factor(evidence: list[SeoEvidenceRef]) -> float:
	impressions = 0.0
	for item in evidence:
		impressions = max(impressions, float(item.metadata.get('impressions') or 0))
		if item.kind.value == 'traffic_metric' and item.metric_value:
			impressions = max(impressions, float(item.metric_value))
	if impressions >= 1000:
		return 1.0
	if impressions >= 100:
		return 0.82
	if impressions >= 20:
		return 0.65
	if impressions > 0:
		return 0.5
	return 0.35
