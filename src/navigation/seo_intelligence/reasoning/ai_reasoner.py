"""AI reasoning over reasoning_units — Sprint 3 + partial validation (ADR-027)."""

from __future__ import annotations



from typing import Any



from navigation.seo_intelligence.models import SeoEvidenceRef, SeoRecommendation

from navigation.seo_intelligence.reasoning.llm_client import (

	SeoLlmClient,

	ai_reasoning_enabled,

	draft_recommendations_with_llm,

)

from navigation.seo_intelligence.reasoning.prompt import build_ai_prompt_payload

from navigation.seo_intelligence.reasoning.validate import validate_draft_recommendations



_DEFAULT_VERIFICATION = [

	'Apply fix in codebase or CMS',

	'perception_observe affected URLs (save scan_id)',

	'perception_seo_verify with recommendation_ids',

	'perception_verify UI and metadata expectations',

]





def try_ai_recommendations(

	reasoning_context_v2: dict[str, Any],

	evidence: list[SeoEvidenceRef],

	*,

	ai_reasoning: bool | None = None,

	client: SeoLlmClient | None = None,

	max_units: int = 12,

) -> tuple[list[SeoRecommendation] | None, dict[str, Any]]:

	"""

	Attempt LLM recommendations from reasoning_units.

	Returns (recommendations, ai_metadata). recommendations is None when caller should use full deterministic fallback.

	Partial validation: valid drafts are returned even when some drafts fail.

	"""

	meta: dict[str, Any] = {

		'enabled': ai_reasoning_enabled(ai_reasoning),

		'source': 'deterministic_fallback',

		'degraded': [],

		'validation_errors': [],

		'rejected_count': 0,

	}



	if not meta['enabled']:

		meta['degraded'].append('ai_reasoning_disabled')

		return None, meta



	payload = build_ai_prompt_payload(reasoning_context_v2, max_units=max_units)

	drafts, llm_degraded = draft_recommendations_with_llm(payload, client=client)

	meta['degraded'].extend(llm_degraded)

	meta['draft_count'] = len(drafts)



	if not drafts:

		meta['degraded'].append('ai_reasoning_no_drafts')

		return None, meta



	validated, errors = validate_draft_recommendations(

		drafts,

		reasoning_context_v2=reasoning_context_v2,

	)

	meta['validation_errors'] = errors

	meta['validated_count'] = len(validated)

	meta['rejected_count'] = max(0, len(drafts) - len(validated))



	if not validated:

		meta['degraded'].append('ai_reasoning_validation_failed')

		return None, meta



	units_by_id = {

		str(u.get('unit_id') or ''): u

		for u in (reasoning_context_v2.get('reasoning_units') or [])

		if isinstance(u, dict)

	}

	evidence_by_id = {e.evidence_id: e for e in evidence}



	recommendations = [

		_draft_to_recommendation(draft, units_by_id=units_by_id, evidence_by_id=evidence_by_id)

		for draft in validated

	]

	if meta['rejected_count'] > 0:

		meta['source'] = 'llm_partial'

		meta['degraded'].append(f'ai_reasoning_partial:{meta["rejected_count"]}_rejected')

	else:

		meta['source'] = 'llm'

	return recommendations, meta





def merge_ai_and_deterministic(

	ai_recs: list[SeoRecommendation],

	deterministic: list[SeoRecommendation],

) -> list[SeoRecommendation]:

	"""AI wins on duplicate recommendation_id; deterministic fills gaps."""

	by_id: dict[str, SeoRecommendation] = {r.recommendation_id: r for r in deterministic}

	for rec in ai_recs:

		by_id[rec.recommendation_id] = rec

	return list(by_id.values())





def _draft_to_recommendation(

	draft: dict[str, Any],

	*,

	units_by_id: dict[str, dict[str, Any]],

	evidence_by_id: dict[str, SeoEvidenceRef],

) -> SeoRecommendation:

	unit_id = str(draft.get('reasoning_unit_id') or '')

	unit = units_by_id.get(unit_id, {})

	correlation_id = str(

		draft.get('recommendation_id')

		or draft.get('correlation_id')

		or unit.get('correlation_id')

		or unit_id

		or 'ai_rec'

	)

	evidence_ids = [str(e) for e in (draft.get('evidence_ids') or []) if e]

	confidence_block = unit.get('confidence') or {}

	confidence = float(confidence_block.get('score') or draft.get('confidence') or 0.65)

	impact = unit.get('impact') or {}

	page_url = str(

		draft.get('page_url')

		or unit.get('page_url')

		or _page_url_from_evidence(evidence_ids, evidence_by_id)

	)

	verification = list(draft.get('verification_steps') or _DEFAULT_VERIFICATION)



	return SeoRecommendation(

		recommendation_id=correlation_id,

		title=str(draft.get('title') or unit.get('title') or 'SEO recommendation'),

		summary=str(draft.get('summary') or unit.get('summary') or ''),

		root_cause=str(draft.get('root_cause') or unit.get('root_cause') or ''),

		business_impact=str(draft.get('business_impact') or unit.get('business_impact') or ''),

		priority=str(draft.get('priority') or 'medium'),

		category=str(draft.get('category') or unit.get('kind') or 'ai_reasoning'),

		evidence_ids=evidence_ids,

		confidence=confidence,

		fix_guidance=str(draft.get('fix_guidance') or ''),

		verification_steps=verification,

		metadata={

			'page_url': page_url,

			'confidence_composition': confidence_block.get('composition'),

			'impact': impact,

			'reasoning_unit_id': unit_id,

			'codebase_hints': unit.get('codebase_hints') or [],

			'source': 'llm',

		},

	)





def _page_url_from_evidence(

	evidence_ids: list[str],

	evidence_by_id: dict[str, SeoEvidenceRef],

) -> str:

	for eid in evidence_ids:

		item = evidence_by_id.get(eid)

		if item and (item.page_url or item.url):

			return item.page_url or item.url

	return ''


