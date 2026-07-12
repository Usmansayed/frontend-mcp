"""Build LLM prompt payload from reasoning_context_v2 — Sprint 3 (ADR-027)."""
from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are an SEO engineer. You receive structured reasoning_units from an evidence-first audit.

Rules (non-negotiable):
- Output JSON only, matching the response schema.
- Every recommendation MUST include evidence_ids from evidence_catalog only.
- Never invent metrics, traffic numbers, or URLs not present in the input.
- Each recommendation should map to one reasoning_unit_id when possible.
- fix_guidance must be actionable for a frontend engineer.
- verification_steps must mention perception_observe and perception_seo_verify.
"""


def build_ai_prompt_payload(
	reasoning_context_v2: dict[str, Any],
	*,
	max_units: int = 12,
) -> dict[str, Any]:
	"""Compact payload for host LLM — reasoning_units + evidence catalog only."""
	units = list(reasoning_context_v2.get('reasoning_units') or [])[:max_units]
	evidence_index = _evidence_catalog(reasoning_context_v2, units)

	return {
		'schema_version': reasoning_context_v2.get('schema_version'),
		'website_url': (reasoning_context_v2.get('meta') or {}).get('website_url'),
		'constraints': reasoning_context_v2.get('constraints'),
		'reasoning_units': units,
		'evidence_catalog': evidence_index,
	}


def build_ai_user_message(payload: dict[str, Any]) -> str:
	schema = {
		'recommendations': [
			{
				'reasoning_unit_id': 'ru:...',
				'recommendation_id': 'correlation_id or stable id',
				'title': 'string',
				'summary': 'string',
				'root_cause': 'string',
				'business_impact': 'string',
				'fix_guidance': 'string',
				'priority': 'high|medium|low',
				'evidence_ids': ['ev:provider:kind:fingerprint'],
				'verification_steps': ['string'],
			}
		]
	}
	return (
		'Generate SEO recommendations from this reasoning_context_v2 excerpt.\n\n'
		f'INPUT:\n{json.dumps(payload, indent=2, default=str)}\n\n'
		f'RESPONSE_SCHEMA:\n{json.dumps(schema, indent=2)}'
	)


def _evidence_catalog(
	ctx: dict[str, Any],
	units: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
	needed: set[str] = set()
	for unit in units:
		for eid in unit.get('evidence_ids') or []:
			if eid:
				needed.add(str(eid))

	catalog: dict[str, dict[str, Any]] = {}
	for page in ctx.get('pages') or []:
		if not isinstance(page, dict):
			continue
		page_url = str(page.get('url') or '')
		for ev in page.get('evidence') or []:
			if not isinstance(ev, dict):
				continue
			eid = str(ev.get('evidence_id') or '')
			if not eid or (needed and eid not in needed):
				continue
			catalog[eid] = {
				'title': ev.get('title'),
				'summary': ev.get('summary'),
				'kind': ev.get('kind'),
				'page_url': page_url or ev.get('page_url'),
				'severity': ev.get('severity'),
				'metric_value': ev.get('metric_value'),
				'metric_unit': ev.get('metric_unit'),
			}
	return catalog
