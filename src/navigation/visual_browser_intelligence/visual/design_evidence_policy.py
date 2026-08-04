"""Smart screenshot pack + agent visual-feedback → next-actions for design/consistency.

Design and consistency checks should show the agent what the page *looks like*
(viewport / full / section), then accept the agent's judgment and turn it into
concrete next tool calls (remeasure, verify section, propose_fix, re-edit).
"""
from __future__ import annotations

from typing import Any

# Pack ladder: what to capture for a design/consistency call.
# design = viewport + full + sections (default for design intelligence / consistency)
PACK_DESIGN = 'design'
PACK_VIEWPORT = 'viewport'
PACK_FULL = 'full'
PACK_SECTION = 'section'
PACK_ELEMENT = 'element'
PACK_NONE = 'none'
PACK_AUTO = 'auto'

VALID_PACKS = frozenset(
	{PACK_DESIGN, PACK_VIEWPORT, PACK_FULL, PACK_SECTION, PACK_ELEMENT, PACK_NONE, PACK_AUTO}
)

# Tools that should always present pixels by default (user requirement).
VISUAL_DEFAULT_TOOLS = frozenset(
	{
		'perception_build_design_snapshot',
		'perception_design_review',
		'perception_consistency_review',
		'perception_consistency_audit',
	}
)


def resolve_screenshot_pack(
	tool: str,
	arguments: dict[str, Any],
	*,
	feedback: dict[str, Any] | None = None,
) -> str:
	"""Pick the smallest useful pack. Design/consistency default to ``design``."""
	if arguments.get('include_screenshots') is False:
		return PACK_NONE
	raw = str(arguments.get('screenshot_pack') or PACK_AUTO).strip().lower()
	if raw not in VALID_PACKS:
		raw = PACK_AUTO
	if raw != PACK_AUTO:
		return raw

	fb = feedback or {}
	if str(arguments.get('screenshot_selector') or fb.get('focus_selector') or '').strip():
		return PACK_ELEMENT
	focus_sections = fb.get('focus_sections') or arguments.get('focus_sections') or []
	if isinstance(focus_sections, list) and focus_sections:
		return PACK_SECTION
	# Design intelligence + consistency: always show viewport+full+sections.
	if tool in VISUAL_DEFAULT_TOOLS:
		return PACK_DESIGN
	return PACK_VIEWPORT


def normalize_visual_feedback(arguments: dict[str, Any]) -> dict[str, Any] | None:
	"""Normalize agent visual feedback from flat or nested args.

	Accepted shapes:
	- visual_feedback: {judgment, notes, focus_sections, focus_selector, issues[]}
	- flat: judgment / visual_notes / focus_sections / screenshot_selector
	"""
	raw = arguments.get('visual_feedback')
	fb: dict[str, Any] = {}
	if isinstance(raw, dict):
		fb.update(raw)
	elif isinstance(raw, str) and raw.strip():
		fb['notes'] = raw.strip()

	for key_src, key_dst in (
		('judgment', 'judgment'),
		('visual_notes', 'notes'),
		('visual_judgment', 'judgment'),
		('focus_sections', 'focus_sections'),
		('screenshot_selector', 'focus_selector'),
		('focus_selector', 'focus_selector'),
	):
		if key_src in arguments and arguments[key_src] not in (None, '', []):
			fb.setdefault(key_dst, arguments[key_src])

	if not fb:
		return None

	judgment = str(fb.get('judgment') or 'needs_work').strip().lower()
	if judgment not in ('ok', 'needs_work', 'unclear'):
		judgment = 'needs_work'
	notes = str(fb.get('notes') or '').strip()
	focus_selector = str(fb.get('focus_selector') or '').strip() or None
	focus_sections_raw = fb.get('focus_sections') or []
	if isinstance(focus_sections_raw, str):
		focus_sections = [s.strip() for s in focus_sections_raw.split(',') if s.strip()]
	elif isinstance(focus_sections_raw, list):
		focus_sections = [str(s).strip() for s in focus_sections_raw if str(s).strip()]
	else:
		focus_sections = []
	issues_raw = fb.get('issues') or []
	issues: list[dict[str, Any]] = []
	if isinstance(issues_raw, list):
		for item in issues_raw:
			if isinstance(item, dict):
				issues.append(
					{
						'section': str(item.get('section') or '').strip() or None,
						'selector': str(item.get('selector') or '').strip() or None,
						'problem': str(item.get('problem') or item.get('detail') or '').strip(),
						'wanted': str(item.get('wanted') or item.get('fix') or '').strip() or None,
					}
				)
			elif isinstance(item, str) and item.strip():
				issues.append({'section': None, 'selector': None, 'problem': item.strip(), 'wanted': None})

	# Pull section mentions out of free-text notes when focus_sections empty.
	if not focus_sections and notes:
		for token in ('header', 'nav', 'footer', 'hero', 'main', 'sidebar', 'form', 'section'):
			if token in notes.lower() and token not in focus_sections:
				focus_sections.append(token)

	return {
		'judgment': judgment,
		'notes': notes,
		'focus_sections': focus_sections,
		'focus_selector': focus_selector,
		'issues': issues,
	}


def pack_capture_kwargs(pack: str, arguments: dict[str, Any], feedback: dict[str, Any] | None) -> dict[str, Any]:
	"""Translate pack + feedback into capture_design_evidence kwargs."""
	fb = feedback or {}
	selector = str(arguments.get('screenshot_selector') or fb.get('focus_selector') or '').strip() or None
	try:
		max_sections = int(arguments.get('max_sections', 3))
	except (TypeError, ValueError):
		max_sections = 3
	prefer = list(fb.get('focus_sections') or arguments.get('focus_sections') or [])
	prefer = [str(s).strip().lower() for s in prefer if str(s).strip()]

	want_viewport = pack in (PACK_DESIGN, PACK_VIEWPORT, PACK_FULL, PACK_SECTION, PACK_ELEMENT)
	want_full = pack in (PACK_DESIGN, PACK_FULL, PACK_SECTION)  # section crops need full PNG
	want_sections = pack in (PACK_DESIGN, PACK_SECTION)
	want_element = pack == PACK_ELEMENT or bool(selector and pack in (PACK_DESIGN, PACK_ELEMENT))

	return {
		'want_viewport': want_viewport,
		'want_full': want_full,
		'want_sections': want_sections,
		'want_element': want_element,
		'selector': selector if want_element else None,
		'max_sections': max_sections if want_sections else 0,
		'prefer_sections': prefer,
	}


def build_visual_next_actions(
	*,
	tool: str,
	envelope: dict[str, Any],
	feedback: dict[str, Any],
) -> list[dict[str, Any]]:
	"""Turn agent visual judgment into concrete next tool calls."""
	actions: list[dict[str, Any]] = []
	data = envelope.get('data') if isinstance(envelope.get('data'), dict) else {}
	session_id = envelope.get('session_id') or data.get('session_id')
	scan_id = envelope.get('scan_id') or data.get('scan_id')
	snapshot_id = data.get('snapshot_id')

	judgment = feedback.get('judgment') or 'needs_work'
	notes = feedback.get('notes') or ''
	focus_selector = feedback.get('focus_selector')
	focus_sections = list(feedback.get('focus_sections') or [])
	issues = list(feedback.get('issues') or [])

	if judgment == 'ok':
		actions.append(
			{
				'action': 'continue_done_ladder',
				'why': 'Agent judged visuals OK — proceed to verify / section checklist / Ship Council as required.',
				'tool': 'perception_verify',
				'args_hint': {'session_id': session_id},
			}
		)
		return actions[:6]

	# Focused re-observe of a flagged element.
	if focus_selector:
		actions.append(
			{
				'action': 'reobserve_element',
				'why': notes or f'Agent focused selector {focus_selector}',
				'tool': 'perception_observe',
				'args_hint': {
					'session_id': session_id,
					'screenshot_mode': 'element',
					'screenshot_selector': focus_selector,
					'annotate_screenshot': True,
				},
			}
		)

	# Section checklist / verify for each flagged section.
	for section in focus_sections[:4]:
		actions.append(
			{
				'action': 'verify_section',
				'why': notes or f'Agent flagged section {section}',
				'tool': 'perception_verify',
				'args_hint': {'session_id': session_id, 'section_id': section},
			}
		)

	# Issue-level tips.
	for issue in issues[:4]:
		sel = issue.get('selector') or focus_selector
		sec = issue.get('section')
		problem = issue.get('problem') or ''
		wanted = issue.get('wanted')
		actions.append(
			{
				'action': 'edit_then_remeasure',
				'why': problem + (f' → want: {wanted}' if wanted else ''),
				'tool': 'perception_build_design_snapshot',
				'args_hint': {
					'session_id': session_id,
					'scan_id': scan_id,
					'screenshot_pack': 'section' if sec else ('element' if sel else 'design'),
					'screenshot_selector': sel,
					'focus_sections': [sec] if sec else [],
					'include_screenshots': True,
				},
				'edit_hint': {
					'section': sec,
					'selector': sel,
					'problem': problem,
					'wanted': wanted,
				},
			}
		)

	# Consistency findings → propose_fix when feedback overlaps.
	findings = list(data.get('findings') or data.get('top_findings') or data.get('blocking_findings') or [])
	notes_l = notes.lower()
	for finding in findings[:8]:
		if not isinstance(finding, dict):
			continue
		detail = ' '.join(
			str(finding.get(k) or '')
			for k in ('detail', 'summary', 'message', 'kind', 'property', 'selector', 'standard_id')
		).lower()
		standard_id = finding.get('standard_id') or (finding.get('standard') or {}).get('id')
		selector = finding.get('selector') or focus_selector
		# Prefer findings that match free-text notes, else take first few when needs_work.
		matched = bool(notes_l) and any(tok in detail for tok in notes_l.split() if len(tok) > 3)
		if not matched and not notes_l:
			matched = True
		if not matched and not focus_sections and not focus_selector:
			matched = True
		if matched and standard_id:
			actions.append(
				{
					'action': 'propose_consistency_fix',
					'why': finding.get('detail') or finding.get('summary') or 'Consistency drift vs standard',
					'tool': 'perception_consistency_propose_fix',
					'args_hint': {
						'standard_id': standard_id,
						'selector': selector or '',
						'actual': finding.get('actual') or finding.get('actual_values'),
					},
				}
			)
		elif matched and selector:
			actions.append(
				{
					'action': 'assess_element',
					'why': finding.get('detail') or 'Assess flagged element against graph',
					'tool': 'perception_consistency_assess',
					'args_hint': {
						'selector': selector,
						'actual': finding.get('actual') or finding.get('actual_values') or {},
					},
				}
			)

	# Always close the loop with a remeasure after edits when judgment is needs_work.
	if judgment == 'needs_work' and not any(a.get('action') == 'edit_then_remeasure' for a in actions):
		actions.append(
			{
				'action': 'edit_then_remeasure',
				'why': notes or 'Agent judged visuals need work — edit UI, then remeasure with screenshots.',
				'tool': tool if tool in VISUAL_DEFAULT_TOOLS else 'perception_design_review',
				'args_hint': {
					'session_id': session_id,
					'scan_id': scan_id,
					'snapshot_id': snapshot_id,
					'screenshot_pack': 'design',
					'include_screenshots': True,
					'visual_feedback': {
						'judgment': 'needs_work',
						'notes': notes,
						'focus_sections': focus_sections,
						'focus_selector': focus_selector,
					},
				},
			}
		)

	# Deduplicate by (action, tool).
	seen: set[tuple[str, str]] = set()
	out: list[dict[str, Any]] = []
	for a in actions:
		key = (str(a.get('action')), str(a.get('tool')))
		if key in seen:
			continue
		seen.add(key)
		out.append(a)
	return out[:8]


def visual_feedback_advisory(feedback: dict[str, Any], next_actions: list[dict[str, Any]]) -> list[str]:
	"""Short host-facing advisory lines."""
	lines = [
		'VISUAL FEEDBACK received — next_actions ranked from your judgment + tool findings.',
		'LOOK at attached screenshots, apply the top next_action, then re-run this tool with updated visual_feedback.',
	]
	judgment = feedback.get('judgment')
	if judgment == 'ok':
		lines.append('Judgment=ok — do not polish-loop; advance Done ladder (verify → sections → Ship).')
	elif judgment == 'needs_work':
		top = next_actions[0] if next_actions else None
		if top:
			lines.append(
				f"Top action: {top.get('action')} via {top.get('tool')} — {top.get('why') or ''}"[:220]
			)
	return lines
