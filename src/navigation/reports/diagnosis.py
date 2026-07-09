"""Diagnosis orchestration — observe, console, network, audits, report assembly."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from navigation.audits.models import AuditCategory
from navigation.audits.runner import LighthouseNotAvailableError
from navigation.audits.service import run_audit
from navigation.perception.budget import OutputBudget
from navigation.perception.observation import collect_observation
from navigation.perception.scan import scan_page
from navigation.perception.verification import read_current_url

from .hints import build_suggested_fixes
from .markdown import report_to_markdown
from .models import ArtifactRef, DiagnosisOptions, PerceptionReport


class DiagnosisError(Exception):
	pass


def _resolve_url(base: str, url: str) -> str:
	if url.startswith('http://') or url.startswith('https://'):
		return url
	return urljoin(base.rstrip('/') + '/', url.lstrip('/'))


def _audit_categories_for_mode(options: DiagnosisOptions) -> tuple[AuditCategory, ...]:
	if options.audit_categories:
		out: list[AuditCategory] = []
		for name in options.audit_categories:
			out.append(AuditCategory.from_tool_name(str(name)))
		return tuple(out)
	if options.mode == 'audit':
		return (
			AuditCategory.ACCESSIBILITY,
			AuditCategory.PERFORMANCE,
			AuditCategory.SEO,
			AuditCategory.BEST_PRACTICES,
		)
	if options.mode == 'full' and options.include_audits:
		return (AuditCategory.ACCESSIBILITY, AuditCategory.PERFORMANCE)
	return ()


async def _observe(
	rec: Any,
	scans: Any,
	session_id: str,
	options: DiagnosisOptions,
) -> tuple[dict[str, Any], Any, list[str]]:
	degraded: list[str] = []
	images_dir = rec.artifacts_dir / 'images' if options.include_screenshot else None
	name = f'diagnosis-{options.mode}-{rec.run_counter}'

	if options.url:
		target = _resolve_url(rec.base_url, options.url)
		result = await scan_page(
			rec.browser,
			target,
			images_dir=images_dir,
			name=name,
			budget=OutputBudget(),
			screenshot_mode='viewport',
			annotate_screenshot=True,
			console_service=rec.console,
			network_service=rec.network,
			har_dir=rec.artifacts_dir / 'network',
		)
		degraded.extend(result.degraded)
		if not result.ok:
			raise DiagnosisError(result.error or 'navigation failed')
		obs_dict = result.observation.to_dict() if result.observation else {}
		page_url = result.url
	else:
		obs = await collect_observation(
			rec.browser,
			images_dir=images_dir,
			name=name,
			screenshot_mode='viewport',
			annotate_screenshot=True,
			console_service=rec.console,
			network_service=rec.network,
			har_dir=rec.artifacts_dir / 'network',
		)
		obs_dict = obs.to_dict()
		page_url = obs.url

	scan_rec = scans.register(
		session_id=session_id,
		run_id=rec.current_run_id,
		url=page_url,
		observation=obs_dict,
	)
	return obs_dict, scan_rec, degraded


async def _run_audits(
	rec: Any,
	categories: tuple[AuditCategory, ...],
	*,
	url: str,
	timeout_s: int,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
	audits: dict[str, dict[str, Any]] = {}
	blocking: list[str] = []
	warnings: list[str] = []
	degraded: list[str] = []

	for category in categories:
		key = category.value
		try:
			report = await run_audit(
				rec.browser,
				category=category,
				base_url=rec.base_url,
				artifacts_dir=rec.artifacts_dir,
				url=url,
				timeout_s=timeout_s,
			)
			audit_dict = report.to_dict()
			audits[key] = audit_dict
			for item in report.blocking:
				if item not in blocking:
					blocking.append(item)
			for item in report.warnings[:10]:
				title = str(item.get('title') or item.get('id') or '')
				if title and title not in warnings:
					warnings.append(title)
			degraded.extend(report.degraded)
		except LighthouseNotAvailableError:
			degraded.append('lighthouse_unavailable')
			break
		except Exception as exc:
			degraded.append(f'lighthouse_failed_{key}')
			warnings.append(f'Audit {key} failed: {exc}')

	return audits, blocking, degraded


def _verification_from_observation(obs_dict: dict[str, Any]) -> dict[str, Any]:
	di = obs_dict.get('dev_insights') or {}
	summary = di.get('summary') or {}
	dom_text = str(obs_dict.get('dom_text') or '').strip()
	return {
		'page_loaded': bool(obs_dict.get('url')),
		'dom_nonempty': len(dom_text) > 0,
		'blocking_count': len(summary.get('blocking_issues') or []),
		'ok': bool(obs_dict.get('url')) and len(dom_text) > 0,
	}


def _build_summary(
	*,
	url: str,
	blocking_count: int,
	warning_count: int,
	console: dict[str, Any] | None,
	network: dict[str, Any] | None,
	audits: dict[str, dict[str, Any]],
	mode: str,
) -> str:
	parts = [f'{mode} diagnosis at {url or "current page"}']
	parts.append(f'{blocking_count} blocking, {warning_count} warnings')
	if console:
		errors = (console.get('by_level') or {}).get('error', 0)
		if errors:
			parts.append(f'{errors} console errors')
	if network:
		failed = network.get('failed_count', 0)
		if failed:
			parts.append(f'{failed} network failures')
	for key, audit in audits.items():
		score = audit.get('score')
		if score is not None:
			parts.append(f'{key} score {score:.0f}')
	return '; '.join(parts)


def _collect_artifacts(
	obs_dict: dict[str, Any],
	audits: dict[str, dict[str, Any]],
	diagnosis_dir: Path,
	scan_id: str,
) -> list[dict[str, Any]]:
	artifacts: list[dict[str, Any]] = []

	def add(kind: str, path: str | None) -> None:
		if not path:
			return
		p = Path(path)
		if not p.is_file():
			return
		uri = None
		if kind == 'diagnosis_json':
			uri = f'perception://scan/{scan_id}/diagnosis.json'
		elif kind == 'diagnosis_md':
			uri = f'perception://scan/{scan_id}/diagnosis.md'
		elif kind == 'network_har':
			uri = f'perception://scan/{scan_id}/network.har'
		artifacts.append(ArtifactRef(kind=kind, path=str(p), uri=uri).to_dict())

	add('screenshot', obs_dict.get('screenshot_path'))
	add('screenshot_annotated', obs_dict.get('annotated_screenshot_path'))
	net = obs_dict.get('network') or {}
	add('network_har', net.get('har_path'))
	add('diagnosis_json', str(diagnosis_dir / 'diagnosis.json'))
	add('diagnosis_md', str(diagnosis_dir / 'diagnosis.md'))
	for audit in audits.values():
		add(f"lighthouse_{audit.get('category', 'audit')}", audit.get('artifacts', {}).get('lighthouse_json'))
	return artifacts


def _assemble_report(
	*,
	obs_dict: dict[str, Any],
	scan_id: str,
	mode: str,
	audits: dict[str, dict[str, Any]],
	degraded: list[str],
	extra_blocking: list[str] | None = None,
) -> PerceptionReport:
	from navigation.mcp.envelope import agent_summary_from_observation

	agent_summary = agent_summary_from_observation(obs_dict)
	blocking = list(agent_summary.get('blocking') or [])
	warnings = list(agent_summary.get('advisory') or [])
	for item in extra_blocking or []:
		if item not in blocking:
			blocking.append(item)
	for audit in audits.values():
		for item in audit.get('blocking') or []:
			if item not in blocking:
				blocking.append(item)
		for item in audit.get('warnings') or []:
			title = str(item.get('title') or item.get('id') or '')
			if title and title not in warnings:
				warnings.append(title)

	console = obs_dict.get('console')
	network = obs_dict.get('network')
	visual = obs_dict.get('visual_insights')
	verification = _verification_from_observation(obs_dict)
	suggested = build_suggested_fixes(
		blocking=blocking,
		warnings=warnings,
		console=console,
		network=network,
		visual=visual,
		audits=audits,
	)
	summary = _build_summary(
		url=str(obs_dict.get('url') or ''),
		blocking_count=len(blocking),
		warning_count=len(warnings),
		console=console,
		network=network,
		audits=audits,
		mode=mode,
	)
	return PerceptionReport(
		summary=summary,
		blocking=blocking,
		warnings=warnings,
		console=console,
		network=network,
		visual=visual,
		audits=audits,
		verification=verification,
		suggested_fixes=suggested,
		scan_id=scan_id,
		url=str(obs_dict.get('url') or ''),
		mode=mode,
		degraded=list(dict.fromkeys(degraded + list(agent_summary.get('degraded') or []))),
	)


def _persist_report(
	report: PerceptionReport,
	scan_rec: Any,
	obs_dict: dict[str, Any],
	artifacts_dir: Path,
) -> list[dict[str, Any]]:
	diagnosis_dir = artifacts_dir / 'diagnosis'
	diagnosis_dir.mkdir(parents=True, exist_ok=True)
	json_path = diagnosis_dir / 'diagnosis.json'
	md_path = diagnosis_dir / 'diagnosis.md'

	preliminary = report.to_dict()
	json_path.write_text(json.dumps(preliminary, indent=2, default=str), encoding='utf-8')
	md_path.write_text(report_to_markdown(preliminary), encoding='utf-8')

	artifacts = _collect_artifacts(obs_dict, report.audits, diagnosis_dir, scan_rec.scan_id)
	report.artifacts = artifacts
	final_dict = report.to_dict()
	json_path.write_text(json.dumps(final_dict, indent=2, default=str), encoding='utf-8')
	md_path.write_text(report_to_markdown(final_dict), encoding='utf-8')

	obs_dict['perception_report'] = final_dict
	scan_rec.observation = obs_dict
	return artifacts


async def run_debug_mode(
	rec: Any,
	scans: Any,
	session_id: str,
	options: DiagnosisOptions,
) -> PerceptionReport:
	options = DiagnosisOptions(
		url=options.url,
		include_screenshot=options.include_screenshot,
		include_audits=False,
		mode='debug',
	)
	obs_dict, scan_rec, degraded = await _observe(rec, scans, session_id, options)
	report = _assemble_report(
		obs_dict=obs_dict,
		scan_id=scan_rec.scan_id,
		mode='debug',
		audits={},
		degraded=degraded,
	)
	_persist_report(report, scan_rec, obs_dict, rec.artifacts_dir)
	return report


async def run_full_diagnosis(
	rec: Any,
	scans: Any,
	session_id: str,
	options: DiagnosisOptions,
) -> PerceptionReport:
	options = DiagnosisOptions(
		url=options.url,
		include_screenshot=options.include_screenshot,
		include_audits=options.include_audits,
		audit_categories=options.audit_categories,
		audit_timeout_s=options.audit_timeout_s,
		mode='full',
	)
	obs_dict, scan_rec, degraded = await _observe(rec, scans, session_id, options)
	page_url = str(obs_dict.get('url') or '')
	audits: dict[str, dict[str, Any]] = {}
	extra_blocking: list[str] = []
	categories = _audit_categories_for_mode(options)
	if categories:
		audit_results, audit_blocking, audit_degraded = await _run_audits(
			rec,
			categories,
			url=page_url,
			timeout_s=options.audit_timeout_s,
		)
		audits = audit_results
		extra_blocking = audit_blocking
		degraded.extend(audit_degraded)

	report = _assemble_report(
		obs_dict=obs_dict,
		scan_id=scan_rec.scan_id,
		mode='full',
		audits=audits,
		degraded=degraded,
		extra_blocking=extra_blocking,
	)
	_persist_report(report, scan_rec, obs_dict, rec.artifacts_dir)
	return report


async def run_audit_mode(
	rec: Any,
	scans: Any,
	session_id: str,
	options: DiagnosisOptions,
) -> PerceptionReport:
	"""Run all Lighthouse categories; light observe when url omitted uses current page."""
	options = DiagnosisOptions(
		url=options.url,
		include_screenshot=False,
		include_audits=True,
		audit_timeout_s=options.audit_timeout_s,
		mode='audit',
	)
	degraded: list[str] = []
	obs_dict: dict[str, Any]
	scan_rec: Any

	if options.url:
		obs_dict, scan_rec, observe_degraded = await _observe(rec, scans, session_id, options)
		degraded.extend(observe_degraded)
		page_url = str(obs_dict.get('url') or '')
	else:
		page_url = await read_current_url(rec.browser)
		if not page_url.startswith('http'):
			page_url = _resolve_url(rec.base_url, page_url)
		obs_dict = {'url': page_url}
		scan_rec = scans.register(
			session_id=session_id,
			run_id=rec.current_run_id,
			url=page_url,
			observation=obs_dict,
		)

	categories = _audit_categories_for_mode(options)
	audits, extra_blocking, audit_degraded = await _run_audits(
		rec,
		categories,
		url=page_url,
		timeout_s=options.audit_timeout_s,
	)
	degraded.extend(audit_degraded)

	report = _assemble_report(
		obs_dict=obs_dict,
		scan_id=scan_rec.scan_id,
		mode='audit',
		audits=audits,
		degraded=degraded,
		extra_blocking=extra_blocking,
	)
	_persist_report(report, scan_rec, obs_dict, rec.artifacts_dir)
	return report
