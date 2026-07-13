"""Standard MCP tool response envelope (contract v1.0)."""
from __future__ import annotations

import json
from typing import Any

from navigation.mcp.agent_guidance import attach_guidance

CONTRACT_VERSION = "1.0"


def make_envelope(
    tool: str,
    *,
    ok: bool = True,
    session_id: str | None = None,
    run_id: str | None = None,
    scan_id: str | None = None,
    url: str = "",
    error: str | None = None,
    degraded: list[str] | None = None,
    data: dict[str, Any] | None = None,
    agent_guidance: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    env: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "tool": tool,
        "ok": ok,
        "session_id": session_id,
        "run_id": run_id,
        "scan_id": scan_id,
        "url": url,
        "error": error,
        "degraded": list(degraded or []),
        "data": data or {},
    }
    if agent_guidance:
        env["agent_guidance"] = list(agent_guidance)
    return attach_guidance(env)


def envelope_json(**kwargs: Any) -> str:
    return json.dumps(make_envelope(**kwargs), indent=2, default=str)


def agent_summary_from_observation(obs_dict: dict[str, Any]) -> dict[str, Any]:
	"""Compact summary for host agent reasoning (no planning hints)."""
	di = obs_dict.get('dev_insights') or {}
	summary = di.get('summary') or {}
	page_meta = di.get('page_meta')
	blocking = list(summary.get('blocking_issues') or [])
	advisory = list(summary.get('advisory_issues') or [])
	console_block = obs_dict.get('console') or {}
	for item in console_block.get('blocking') or []:
		if item not in blocking:
			blocking.append(item)
	network_block = obs_dict.get('network') or {}
	for item in network_block.get('blocking') or []:
		if item not in blocking:
			blocking.append(item)
	for item in network_block.get('slow_requests') or []:
		url = item.get('url') or ''
		duration = item.get('duration_ms')
		msg = f'Slow request ({duration:.0f}ms): {url}' if duration is not None else f'Slow request: {url}'
		if msg not in advisory:
			advisory.append(msg)
	visual = obs_dict.get('visual_insights') or {}
	for item in visual.get('blocking') or []:
		if item not in blocking:
			blocking.append(item)
	for item in visual.get('advisory') or []:
		if item not in advisory:
			advisory.append(item)
	console_summary = None
	if console_block:
		console_summary = {
			'total': console_block.get('total', 0),
			'session_total': console_block.get('session_total', 0),
			'by_level': console_block.get('by_level') or {},
			'blocking': list(console_block.get('blocking') or []),
		}
	out: dict[str, Any] = {
		'blocking': blocking,
		'advisory': advisory,
		'page_meta': page_meta,
		'degraded': list(obs_dict.get('degraded') or []) + list(di.get('degraded') or []),
	}
	if console_summary is not None:
		out['console'] = console_summary
	network_summary = None
	if network_block:
		network_summary = {
			'total': network_block.get('total', 0),
			'session_total': network_block.get('session_total', 0),
			'failed_count': network_block.get('failed_count', 0),
			'slow_count': network_block.get('slow_count', 0),
			'duplicate_count': network_block.get('duplicate_count', 0),
			'by_api_group': network_block.get('by_api_group') or {},
			'blocking': list(network_block.get('blocking') or []),
			'har_path': network_block.get('har_path'),
		}
	if network_summary is not None:
		out['network'] = network_summary
	return out


def agent_summary_from_report(report_dict: dict[str, Any]) -> dict[str, Any]:
	"""Compact summary from a PerceptionReport dict."""
	out: dict[str, Any] = {
		'blocking': list(report_dict.get('blocking') or []),
		'advisory': list(report_dict.get('warnings') or []),
		'degraded': list(report_dict.get('degraded') or []),
		'diagnosis': {
			'mode': report_dict.get('mode'),
			'summary': report_dict.get('summary'),
			'scan_id': report_dict.get('scan_id'),
			'verification_ok': (report_dict.get('verification') or {}).get('ok'),
		},
	}
	console = report_dict.get('console')
	if console:
		out['console'] = {
			'total': console.get('total', 0),
			'session_total': console.get('session_total', 0),
			'by_level': console.get('by_level') or {},
			'blocking': list(console.get('blocking') or []),
		}
	network = report_dict.get('network')
	if network:
		out['network'] = {
			'total': network.get('total', 0),
			'failed_count': network.get('failed_count', 0),
			'slow_count': network.get('slow_count', 0),
			'har_path': network.get('har_path'),
		}
	audits = report_dict.get('audits') or {}
	if audits:
		out['audits'] = {
			name: {'score': audit.get('score'), 'category': audit.get('category')}
			for name, audit in audits.items()
		}
	return out
