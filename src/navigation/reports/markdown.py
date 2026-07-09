"""Render PerceptionReport as markdown for MCP resources."""
from __future__ import annotations

from typing import Any


def report_to_markdown(report: dict[str, Any]) -> str:
	lines = [
		'# Perception Diagnosis Report',
		'',
		f"**Mode:** {report.get('mode', 'unknown')}",
		f"**URL:** {report.get('url', '')}",
		f"**Scan ID:** {report.get('scan_id') or '—'}",
		'',
		'## Summary',
		'',
		str(report.get('summary') or ''),
		'',
	]

	blocking = report.get('blocking') or []
	lines.append('## Blocking Issues')
	lines.append('')
	if blocking:
		lines.extend(f'- {item}' for item in blocking)
	else:
		lines.append('_None_')
	lines.append('')

	warnings = report.get('warnings') or []
	lines.append('## Warnings')
	lines.append('')
	if warnings:
		lines.extend(f'- {item}' for item in warnings[:25])
	else:
		lines.append('_None_')
	lines.append('')

	_append_section(lines, 'Console', report.get('console'))
	_append_section(lines, 'Network', report.get('network'))
	_append_section(lines, 'Visual', report.get('visual'))

	audits = report.get('audits') or {}
	if audits:
		lines.append('## Audits')
		lines.append('')
		for name, audit in audits.items():
			score = audit.get('score', '?')
			lines.append(f'- **{name}:** score {score}')
		lines.append('')

	fixes = report.get('suggested_fixes') or []
	lines.append('## Suggested Fixes')
	lines.append('')
	if fixes:
		lines.extend(f'- {item}' for item in fixes)
	else:
		lines.append('_None_')
	lines.append('')

	artifacts = report.get('artifacts') or []
	if artifacts:
		lines.append('## Artifacts')
		lines.append('')
		for art in artifacts:
			uri = art.get('uri') or art.get('path') or ''
			lines.append(f"- {art.get('kind', 'artifact')}: `{uri}`")
		lines.append('')

	return '\n'.join(lines)


def _append_section(lines: list[str], title: str, block: dict[str, Any] | None) -> None:
	if not block:
		return
	lines.append(f'## {title}')
	lines.append('')
	if title == 'Console':
		lines.append(f"- Total (window): {block.get('total', 0)}")
		lines.append(f"- Session total: {block.get('session_total', 0)}")
	elif title == 'Network':
		lines.append(f"- Failed: {block.get('failed_count', 0)}")
		lines.append(f"- Slow: {block.get('slow_count', 0)}")
	elif title == 'Visual':
		blocking = block.get('blocking') or []
		lines.append(f"- Blocking signals: {len(blocking)}")
	lines.append('')
