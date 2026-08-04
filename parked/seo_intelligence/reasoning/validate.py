"""Post-validate LLM draft recommendations against reasoning_context_v2 (Sprint 3)."""
from __future__ import annotations

import re
from typing import Any

_VALID_PRIORITIES = frozenset({'critical', 'high', 'medium', 'low'})
_NUMBER_RE = re.compile(r'\b\d{2,}(?:\.\d+)?\b')


def validate_draft_recommendations(
	drafts: list[dict[str, Any]],
	*,
	reasoning_context_v2: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
	"""Return accepted drafts and validation error messages."""
	if not drafts:
		return [], ['ai_validation:no_drafts']

	allowed_evidence = _allowed_evidence_ids(reasoning_context_v2)
	units_by_id = {
		str(u.get('unit_id') or ''): u
		for u in (reasoning_context_v2.get('reasoning_units') or [])
		if isinstance(u, dict)
	}
	allowed_metrics = _allowed_metric_tokens(reasoning_context_v2)
	verification_state = reasoning_context_v2.get('verification_state') or {}

	accepted: list[dict[str, Any]] = []
	errors: list[str] = []

	for idx, draft in enumerate(drafts):
		if not isinstance(draft, dict):
			errors.append(f'ai_validation:draft_{idx}:not_object')
			continue

		rec_id = str(draft.get('recommendation_id') or draft.get('correlation_id') or '')
		title = str(draft.get('title') or '').strip()
		root_cause = str(draft.get('root_cause') or '').strip()
		fix_guidance = str(draft.get('fix_guidance') or '').strip()
		evidence_ids = [str(e) for e in (draft.get('evidence_ids') or []) if e]
		unit_id = str(draft.get('reasoning_unit_id') or '')

		if not title:
			errors.append(f'ai_validation:draft_{idx}:missing_title')
			continue
		if not root_cause:
			errors.append(f'ai_validation:draft_{idx}:missing_root_cause')
			continue
		if not fix_guidance:
			errors.append(f'ai_validation:draft_{idx}:missing_fix_guidance')
			continue
		if not evidence_ids:
			errors.append(f'ai_validation:draft_{idx}:missing_evidence_ids')
			continue

		unknown = [eid for eid in evidence_ids if eid not in allowed_evidence]
		if unknown:
			errors.append(f'ai_validation:draft_{idx}:unknown_evidence:{",".join(unknown[:3])}')
			continue

		if unit_id:
			unit = units_by_id.get(unit_id)
			if unit is None:
				errors.append(f'ai_validation:draft_{idx}:unknown_unit:{unit_id}')
				continue
			unit_evidence = {str(e) for e in (unit.get('evidence_ids') or [])}
			if not unit_evidence.intersection(evidence_ids):
				errors.append(f'ai_validation:draft_{idx}:evidence_not_in_unit')
				continue

		priority = str(draft.get('priority') or 'medium').lower()
		if priority not in _VALID_PRIORITIES:
			errors.append(f'ai_validation:draft_{idx}:invalid_priority:{priority}')
			continue

		if rec_id and verification_state.get(rec_id, {}).get('status') == 'passed':
			errors.append(f'ai_validation:draft_{idx}:already_verified:{rec_id}')
			continue

		invented = _invented_metric_numbers(draft, allowed_metrics)
		if invented:
			errors.append(f'ai_validation:draft_{idx}:invented_metrics:{",".join(invented[:3])}')
			continue

		accepted.append(draft)

	if not accepted and drafts:
		errors.append('ai_validation:no_valid_drafts')
	return accepted, errors


def _allowed_evidence_ids(ctx: dict[str, Any]) -> set[str]:
	out: set[str] = set()
	for page in ctx.get('pages') or []:
		if not isinstance(page, dict):
			continue
		for eid in page.get('evidence_ids') or []:
			if eid:
				out.add(str(eid))
		for ev in page.get('evidence') or []:
			if isinstance(ev, dict) and ev.get('evidence_id'):
				out.add(str(ev['evidence_id']))
	return out


def _allowed_metric_tokens(ctx: dict[str, Any]) -> set[str]:
	tokens: set[str] = set()
	for page in ctx.get('pages') or []:
		if not isinstance(page, dict):
			continue
		metrics = page.get('metrics') or {}
		if isinstance(metrics, dict):
			for key, value in metrics.items():
				tokens.add(str(key))
				tokens.add(str(value))
				if isinstance(value, (int, float)):
					tokens.add(str(int(value)))
					tokens.add(f'{value:.2f}'.rstrip('0').rstrip('.'))
	for unit in ctx.get('reasoning_units') or []:
		if not isinstance(unit, dict):
			continue
		metrics = unit.get('metrics') or {}
		if isinstance(metrics, dict):
			for key, value in metrics.items():
				tokens.add(str(key))
				tokens.add(str(value))
				if isinstance(value, (int, float)):
					tokens.add(str(int(value)))
		impact = unit.get('impact') or {}
		if isinstance(impact, dict):
			for key, value in impact.items():
				if key != 'rationale':
					tokens.add(str(value))
	return {t for t in tokens if t and t not in {'None', 'null'}}


def _invented_metric_numbers(draft: dict[str, Any], allowed: set[str]) -> list[str]:
	text = ' '.join(
		str(draft.get(field) or '')
		for field in ('title', 'summary', 'root_cause', 'business_impact', 'fix_guidance')
	)
	suspect: list[str] = []
	for match in _NUMBER_RE.findall(text):
		if match in allowed:
			continue
		# Small integers (priority ranks, step counts) are allowed
		try:
			val = float(match)
		except ValueError:
			continue
		if val < 20:
			continue
		suspect.append(match)
	return suspect
