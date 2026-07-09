"""CDP parameter parsing for console events."""
from __future__ import annotations

from typing import Any


def cdp_get(params: Any, key: str, default: Any = None) -> Any:
	if params is None:
		return default
	if isinstance(params, dict):
		return params.get(key, default)
	return getattr(params, key, default)


def remote_object_text(obj: Any) -> str:
	if obj is None:
		return ''
	if isinstance(obj, dict):
		if obj.get('value') is not None:
			return str(obj['value'])
		if obj.get('description'):
			return str(obj['description'])
		if obj.get('unserializableValue'):
			return str(obj['unserializableValue'])
	return str(obj)


def format_console_message(params: Any) -> str:
	args = cdp_get(params, 'args') or []
	parts = [remote_object_text(a) for a in args]
	return ' '.join(p for p in parts if p).strip()


def format_stack_trace(stack: Any) -> str:
	if not stack:
		return ''
	frames = cdp_get(stack, 'callFrames') or []
	lines: list[str] = []
	for fr in frames[:12]:
		if isinstance(fr, dict):
			fn = fr.get('functionName') or '<anonymous>'
			url = fr.get('url') or ''
			line = fr.get('lineNumber')
			lines.append(f'  at {fn} ({url}:{line})')
	return '\n'.join(lines)


def normalize_level(level: str) -> str:
	raw = (level or 'log').strip().lower()
	if raw == 'warning':
		return 'warn'
	if raw in {'log', 'info', 'debug', 'warn', 'error', 'exception', 'assert'}:
		return raw
	return raw or 'log'


def exception_message(details: Any) -> str:
	text = str(cdp_get(details, 'text') or '')
	exc = cdp_get(details, 'exception') or {}
	desc = str(cdp_get(exc, 'description') or '')
	if desc:
		return desc
	if text and text != 'Uncaught':
		return text
	stack = format_stack_trace(cdp_get(details, 'stackTrace'))
	if 'Error:' in stack:
		for line in stack.splitlines():
			if 'Error:' in line:
				return line.strip()
	return text or 'exception'
