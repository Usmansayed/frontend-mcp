"""Purpose-shaped visual feedback: one common LOOK → judge → act contract.

Every intelligence (design, consistency, component, inspiration, hotfix, forms)
needs a look at rendered pixels before structural edits. This module shapes ONE
shared contract per *purpose*: which screenshot pack to capture, which guide to
read, what feedback JSON the agent should fill, and which advisory next actions
to rank from that feedback. Core normalize/pack/action logic stays in
``design_evidence_policy`` — this layer only adds purpose routing on top, so
there is a single capture/feedback code path for the whole MCP.
"""
from __future__ import annotations

from typing import Any

from .design_evidence_policy import (
	PACK_AUTO,
	PACK_DESIGN,
	PACK_ELEMENT,
	PACK_FULL,
	PACK_NONE,
	PACK_SECTION,
	PACK_VIEWPORT,
	VALID_PACKS,
	build_visual_next_actions,
	normalize_visual_feedback,
	pack_capture_kwargs,
	resolve_screenshot_pack,
)

PURPOSE_DESIGN = 'design'
PURPOSE_CONSISTENCY = 'consistency'
PURPOSE_COMPONENT = 'component'
PURPOSE_INSPIRATION = 'inspiration'
PURPOSE_HOTFIX = 'hotfix'
PURPOSE_FORMS = 'forms'
PURPOSE_GENERAL = 'general'

VALID_PURPOSES = frozenset(
	{
		PURPOSE_DESIGN,
		PURPOSE_CONSISTENCY,
		PURPOSE_COMPONENT,
		PURPOSE_INSPIRATION,
		PURPOSE_HOTFIX,
		PURPOSE_FORMS,
		PURPOSE_GENERAL,
	}
)

# Extra feedback keys the agent may fill per purpose (preserved by normalization).
_COMMON_SCHEMA_FIELDS: dict[str, str] = {
	'judgment': "ok | needs_work | unclear — your call after LOOKING at the images",
	'notes': 'Free-text observations (what you actually see, not what the code says)',
	'focus_sections': "Semantic blocks to zoom next, e.g. ['header', 'hero']",
	'focus_selector': 'CSS selector to crop next (optional)',
	'issues': "[{section?, selector?, problem, wanted?}] — concrete visual problems",
}

PURPOSES: dict[str, dict[str, Any]] = {
	PURPOSE_DESIGN: {
		'pack': PACK_DESIGN,
		'recommended_resource': 'perception://design-workflow',
		'focus': (
			'Judge visual hierarchy, first-viewport impact, density/spacing rhythm, '
			'brand feel, and whether structure matches intent. If look_lock / primary_ref_ids '
			'are bound from inspiration, compare the draft against those refs — do not invent '
			'a third aesthetic.'
		),
		'extra_keys': ('hierarchy_issues', 'look_lock', 'primary_ref_ids', 'vs_inspiration'),
		'extra_schema': {
			'hierarchy_issues': "['hero has no focal point', 'CTAs compete'] — hierarchy-specific problems",
			'look_lock': 'Optional borrow lock carried from purpose=inspiration',
			'primary_ref_ids': 'Inspiration ref ids this draft should track',
			'vs_inspiration': "['matches hero density', 'CTA weight drifted'] — compare draft to locked refs",
		},
	},
	PURPOSE_CONSISTENCY: {
		'pack': PACK_DESIGN,
		'recommended_resource': 'perception://frontend-methodology',
		'focus': (
			'Judge consistency against the project design graph: token drift (colors, '
			'radii, spacing steps), rhythm breaks between sections, component variants '
			'that do not match siblings.'
		),
		'extra_keys': ('standard_hints',),
		'extra_schema': {
			'standard_hints': "['std.nav.gap', 'color.primary'] — standard ids you suspect drifted",
		},
	},
	PURPOSE_COMPONENT: {
		'pack': PACK_VIEWPORT,
		'recommended_resource': 'perception://agent-guide',
		'focus': (
			'Judge how a component candidate would sit in THIS page: visual match with '
			'surrounding UI (density, radius, tone), whether the slot needs a variant, '
			'and what the integration must preserve.'
		),
		'extra_keys': ('slot_notes',),
		'extra_schema': {
			'slot_notes': 'Where the component goes and what around it constrains the choice',
		},
	},
	PURPOSE_INSPIRATION: {
		'pack': PACK_FULL,
		'recommended_resource': 'perception://guide/inspiration',
		'focus': (
			'Extract what to BORROW vs IGNORE from what you see: layout skeleton, type '
			'scale, color mood, motion. Lock a look_lock so collect alone is not direction. '
			'Never copy wholesale; name the transferable idea.'
		),
		'extra_keys': ('borrow', 'ignore', 'look_lock', 'primary_ref_ids'),
		'extra_schema': {
			'borrow': "['split hero with product screenshot', 'oversized serif display'] — ideas to adopt",
			'ignore': "['their pricing table', 'dark theme'] — explicitly not transferable",
			'look_lock': (
				"{composition, hierarchy, density, type_mood, chrome, motion} — "
				"machine-usable direction after LOOK"
			),
			'primary_ref_ids': "['hit_0', 'hit_2'] — which collected refs anchor the look",
		},
	},
	PURPOSE_HOTFIX: {
		'pack': PACK_VIEWPORT,
		'recommended_resource': 'perception://bugfix-workflow',
		'focus': (
			'Judge the smallest visual blast radius: is the defect visible, what exactly '
			'looks wrong, what must NOT change around it. Before/after thinking.'
		),
		'extra_keys': ('regression_watch',),
		'extra_schema': {
			'regression_watch': "['sticky header', 'sidebar width'] — nearby things that must not regress",
		},
	},
	PURPOSE_FORMS: {
		'pack': PACK_SECTION,
		'recommended_resource': 'perception://verification-guide',
		'focus': (
			'Judge form usability from pixels: label/field association, error message '
			'placement and tone, disabled/enabled affordances, tap target size, '
			'guard messaging.'
		),
		'extra_keys': ('field_issues',),
		'extra_schema': {
			'field_issues': "[{field, problem, wanted?}] — per-field visual problems",
		},
	},
	PURPOSE_GENERAL: {
		'pack': PACK_VIEWPORT,
		'recommended_resource': 'perception://frontend-methodology',
		'focus': 'General look: note anything that contradicts the current task intent.',
		'extra_keys': (),
		'extra_schema': {},
	},
}


def resolve_purpose(arguments: dict[str, Any]) -> str:
	raw = str(arguments.get('purpose') or PURPOSE_GENERAL).strip().lower()
	return raw if raw in VALID_PURPOSES else PURPOSE_GENERAL


def purpose_for_tool(tool: str) -> str:
	"""Map legacy design/consistency alias tools onto purposes."""
	if 'consistency' in tool:
		return PURPOSE_CONSISTENCY
	return PURPOSE_DESIGN


def purpose_screenshot_pack(
	purpose: str,
	arguments: dict[str, Any],
	*,
	feedback: dict[str, Any] | None = None,
) -> str:
	"""Resolve pack with the purpose default instead of the tool-based default."""
	if arguments.get('include_screenshots') is False:
		return PACK_NONE
	raw = str(arguments.get('screenshot_pack') or PACK_AUTO).strip().lower()
	if raw in VALID_PACKS and raw != PACK_AUTO:
		return raw
	fb = feedback or {}
	if str(arguments.get('screenshot_selector') or fb.get('focus_selector') or '').strip():
		return PACK_ELEMENT
	focus_sections = fb.get('focus_sections') or arguments.get('focus_sections') or []
	if isinstance(focus_sections, list) and focus_sections:
		return PACK_SECTION
	spec = PURPOSES.get(purpose) or PURPOSES[PURPOSE_GENERAL]
	return str(spec['pack'])


def normalize_purpose_feedback(
	arguments: dict[str, Any],
	purpose: str,
) -> dict[str, Any] | None:
	"""Core feedback normalization plus purpose-specific extras."""
	fb = normalize_visual_feedback(arguments)
	if fb is None:
		return None
	fb['purpose'] = purpose
	raw = arguments.get('visual_feedback')
	raw = raw if isinstance(raw, dict) else {}
	spec = PURPOSES.get(purpose) or PURPOSES[PURPOSE_GENERAL]
	for key in spec.get('extra_keys') or ():
		value = raw.get(key, arguments.get(key))
		if value in (None, '', []):
			continue
		if isinstance(value, str):
			fb[key] = [value.strip()] if key != 'slot_notes' else value.strip()
		else:
			fb[key] = value
	return fb


def purpose_feedback_schema(purpose: str) -> dict[str, str]:
	spec = PURPOSES.get(purpose) or PURPOSES[PURPOSE_GENERAL]
	schema = dict(_COMMON_SCHEMA_FIELDS)
	schema.update(spec.get('extra_schema') or {})
	return schema


def purpose_feedback_prompt(purpose: str) -> str:
	spec = PURPOSES.get(purpose) or PURPOSES[PURPOSE_GENERAL]
	return (
		f'LOOK at the attached screenshots (purpose={purpose}). {spec["focus"]} '
		'Then call perception_visual_feedback again with the same purpose and a '
		'visual_feedback JSON matching feedback_schema. judgment=ok only if you '
		'would ship this view as-is.'
	)


def purpose_recommended_resource(purpose: str) -> str:
	spec = PURPOSES.get(purpose) or PURPOSES[PURPOSE_GENERAL]
	return str(spec['recommended_resource'])


def build_purpose_next_actions(
	*,
	purpose: str,
	tool: str,
	envelope: dict[str, Any],
	feedback: dict[str, Any],
) -> list[dict[str, Any]]:
	"""Base actions from the shared policy, then purpose-specific routing."""
	actions = build_visual_next_actions(tool=tool, envelope=envelope, feedback=feedback)
	if feedback.get('judgment') == 'ok':
		return actions

	data = envelope.get('data') if isinstance(envelope.get('data'), dict) else {}
	session_id = envelope.get('session_id') or data.get('session_id')
	scan_id = envelope.get('scan_id') or data.get('scan_id')
	extra: list[dict[str, Any]] = []

	if purpose == PURPOSE_INSPIRATION:
		borrow = list(feedback.get('borrow') or [])
		look_lock = feedback.get('look_lock')
		has_lock = bool(borrow) or (
			isinstance(look_lock, dict) and any(look_lock.values())
		) or (isinstance(look_lock, str) and look_lock.strip())
		if has_lock:
			extra.append(
				{
					'action': 'implement_from_borrow',
					'why': (
						'Look locked (borrow/look_lock) — implement from those ideas; '
						'do not invent a third aesthetic or re-collect by default.'
					),
					'tool': None,
					'args_hint': {
						'borrow': borrow[:5],
						'look_lock': look_lock,
						'primary_ref_ids': list(feedback.get('primary_ref_ids') or [])[:6],
					},
				}
			)
		else:
			extra.append(
				{
					'action': 'collect_inspiration',
					'why': 'No borrow/look_lock yet — collect measured refs, then LOOK again.',
					'tool': 'perception_inspiration_collect',
					'args_hint': {'inspiration_level': 'standard'},
				}
			)
	elif purpose == PURPOSE_COMPONENT:
		extra.append(
			{
				'action': 'select_component_foundation',
				'why': feedback.get('slot_notes') or 'Pick a foundation that visually matches the slot.',
				'tool': 'perception_select_component_foundation',
				'args_hint': {'session_id': session_id},
			}
		)
	elif purpose == PURPOSE_FORMS:
		extra.append(
			{
				'action': 'probe_form',
				'why': 'Confirm field/guard behavior matches what the pixels promise.',
				'tool': 'perception_probe_form',
				'args_hint': {'session_id': session_id},
			}
		)
	elif purpose == PURPOSE_HOTFIX:
		extra.append(
			{
				'action': 'diff_after_fix',
				'why': 'Hotfix: verify then diff against this scan to prove no visual regression.',
				'tool': 'perception_diff',
				'args_hint': {'session_id': session_id, 'baseline_scan_id': scan_id},
			}
		)
	elif purpose == PURPOSE_DESIGN:
		look_lock = feedback.get('look_lock')
		primary_refs = list(feedback.get('primary_ref_ids') or [])
		has_lock = bool(
			(isinstance(look_lock, dict) and any(look_lock.values()))
			or (isinstance(look_lock, str) and look_lock.strip())
			or primary_refs
		)
		if has_lock:
			extra.append(
				{
					'action': 'revise_vs_inspiration',
					'why': (
						'Design draft has a look_lock / primary_ref_ids — revise toward those '
						'borrowed refs; fill vs_inspiration notes; do not invent a third look.'
					),
					'tool': None,
					'args_hint': {
						'look_lock': look_lock,
						'primary_ref_ids': primary_refs[:6],
						'vs_inspiration': list(feedback.get('vs_inspiration') or [])[:6],
					},
				}
			)
	elif purpose == PURPOSE_CONSISTENCY:
		hints = list(feedback.get('standard_hints') or [])
		for standard_id in hints[:3]:
			extra.append(
				{
					'action': 'propose_consistency_fix',
					'why': f'Agent suspects drift vs {standard_id}',
					'tool': 'perception_consistency_propose_fix',
					'args_hint': {'standard_id': standard_id},
				}
			)

	seen = {(str(a.get('action')), str(a.get('tool'))) for a in actions}
	for a in extra:
		key = (str(a.get('action')), str(a.get('tool')))
		if key not in seen:
			seen.add(key)
			actions.append(a)
	return actions[:8]


def purpose_pack_capture_kwargs(
	pack: str,
	arguments: dict[str, Any],
	feedback: dict[str, Any] | None,
) -> dict[str, Any]:
	"""Same capture kwargs as the core policy (kept for one obvious import site)."""
	return pack_capture_kwargs(pack, arguments, feedback)
