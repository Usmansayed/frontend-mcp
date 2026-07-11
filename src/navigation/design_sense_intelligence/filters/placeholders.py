"""Drop developer-log / placeholder findings — not user-facing critique."""
from __future__ import annotations

import re

from ..models import ReviewFinding

_PLACEHOLDER_IDS = frozenset({
	'color_awaiting_snapshot',
	'layout_awaiting_dom',
	'ms_tokens_unknown',
	'ms_compare_figma',
	'ux_task_identified',
})

_PLACEHOLDER_MSG_RE = re.compile(
	r'|'.join(
		(
			r'^verify:',
			r'awaiting\s+(design\s+)?snapshot',
			r'awaiting\s+dom',
			r'not\s+supplied',
			r'cannot\s+verify\s+token',
			r'requires\s+screenshot',
			r'implementation\s+comparison\s+requires',
			r'^primary\s+user\s+task:',
			r'color\s+review\s+awaiting',
			r'layout\s+review\s+awaiting',
		)
	),
	re.IGNORECASE,
)


def is_placeholder_finding(finding: ReviewFinding) -> bool:
	"""True when the finding is a status log, not an actionable design issue."""
	if finding.id in _PLACEHOLDER_IDS:
		return True
	msg = (finding.message or '').strip()
	if not msg:
		return True
	if _PLACEHOLDER_MSG_RE.search(msg):
		return True
	if finding.source == 'design_knowledge' and msg.lower().startswith('verify:'):
		return True
	if finding.id.startswith('principle_') and not finding.evidence:
		return True
	if finding.id.startswith('pattern_') and not finding.evidence:
		return True
	if finding.id.startswith('checklist_'):
		return True
	return False


def drop_placeholders(findings: list[ReviewFinding]) -> tuple[list[ReviewFinding], int]:
	"""Remove placeholders; return (kept, dropped_count)."""
	kept: list[ReviewFinding] = []
	dropped = 0
	for f in findings:
		if is_placeholder_finding(f):
			dropped += 1
			continue
		kept.append(f)
	return kept, dropped
