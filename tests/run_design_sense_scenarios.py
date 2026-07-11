"""Run Design Sense Intelligence across fake + sandbox scenarios; save results."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.design_sense_intelligence.snapshot_access import review_request_from_snapshot
from navigation.design_sense_intelligence import DesignSenseService, ReviewRequest
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.observe.scan import scan_page

from design_sense_fixtures import FAKE_SCENARIOS, SANDBOX_PAGES

RESULTS_DIR = ROOT / 'tests' / 'results'
DEFAULT_OUTPUT = RESULTS_DIR / 'design_sense_scenario_results.json'
DEFAULT_SUMMARY = RESULTS_DIR / 'design_sense_scenario_summary.md'

_snapshot_engine = DesignSnapshotEngine()


@dataclass
class ScenarioResult:
	scenario_id: str
	source: str
	description: str
	passed: bool
	summary: str
	finding_count: int
	blocking_count: int
	major_count: int
	objective_count: int
	subjective_count: int
	consulted_reviewers: list[str] = field(default_factory=list)
	consulted_providers: list[str] = field(default_factory=list)
	top_findings: list[dict[str, Any]] = field(default_factory=list)
	reasoning_narrative: str = ''
	degraded: list[str] = field(default_factory=list)
	error: str | None = None
	input_meta: dict[str, Any] = field(default_factory=dict)
	actionable_count: int = 0
	generic_advisory_count: int = 0
	confirmed_count: int = 0

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)


def _is_reachable(base_url: str, timeout: float = 5.0) -> tuple[bool, int | None, str | None]:
	try:
		with urllib.request.urlopen(base_url, timeout=timeout) as resp:
			return resp.status == 200, resp.status, None
	except urllib.error.HTTPError as exc:
		return False, exc.code, str(exc)
	except Exception as exc:
		return False, None, str(exc)


def _summarize_report(scenario: dict, report) -> ScenarioResult:
	blocking = sum(1 for f in report.findings if f.severity == 'blocking')
	major = sum(1 for f in report.findings if f.severity == 'major')
	top = sorted(report.findings, key=lambda f: {'blocking': 0, 'major': 1, 'minor': 2, 'advisory': 3}.get(f.severity, 9))[:5]
	req: ReviewRequest = scenario['request']
	actionable = sum(
		1 for f in report.findings
		if f.confirmed and (f.evidence or f.recommendation) and f.severity in ('blocking', 'major', 'minor')
	)
	generic = sum(1 for f in report.findings if str(f.message).startswith('Verify:'))
	confirmed = sum(1 for f in report.findings if f.confirmed)
	return ScenarioResult(
		scenario_id=scenario['id'],
		source=scenario['source'],
		description=scenario.get('description', ''),
		passed=report.passed,
		summary=report.summary,
		finding_count=len(report.findings),
		blocking_count=blocking,
		major_count=major,
		objective_count=len(report.objective_findings),
		subjective_count=len(report.subjective_findings),
		consulted_reviewers=list(report.consulted_reviewers),
		consulted_providers=list(report.consulted_providers),
		top_findings=[f.to_dict() for f in top],
		reasoning_narrative=report.reasoning.narrative if report.reasoning else '',
		degraded=list(report.degraded),
		actionable_count=actionable,
		generic_advisory_count=generic,
		confirmed_count=confirmed,
		input_meta={
			'user_task': req.user_task,
			'scope': req.scope,
			'preview_url': req.preview_url,
			'has_design_snapshot': req.design_snapshot is not None,
			'has_visual_insights': bool(req.visual_insights),
			'has_computed_styles': bool(req.computed_styles),
			'snapshot_sections': list((req.design_snapshot.to_dict().keys() if req.design_snapshot else [])),
		},
	)


async def _collect_sandbox_request(
	base_url: str,
	page: dict,
	*,
	headless: bool,
) -> tuple[ReviewRequest | None, str | None]:
	store = SessionStore(artifacts_root=ROOT / 'artifacts' / 'design_sense_scenarios')
	rec = await store.start(base_url=base_url, headless=headless)
	try:
		full_url = urljoin(base_url.rstrip('/') + '/', page['path'].lstrip('/'))
		scan = await scan_page(
			rec.browser,
			full_url,
			images_dir=rec.artifacts_dir / 'scans',
			name=page['id'],
			screenshot_mode='viewport',
			annotate_screenshot=False,
			console_service=rec.console,
			network_service=rec.network,
		)
		if not scan.ok or scan.observation is None:
			return None, scan.error or 'scan_failed'

		obs = scan.observation.to_dict()
		snapshot = await _snapshot_engine.capture_from_session(
			rec.browser,
			visual_insights=obs.get('visual_insights'),
			a11y_tree=obs.get('a11y_tree', ''),
			dom_text=obs.get('dom_text', ''),
			screenshot_ref=obs.get('screenshot_path') or obs.get('annotated_screenshot_path'),
			scan_id=page['id'],
		)

		return review_request_from_snapshot(
			snapshot,
			user_task=page['user_task'],
			scope=page.get('scope', 'page'),
		), None
	finally:
		await store.end(rec.session_id)


async def run_all(
	*,
	base_url: str,
	include_sandbox: bool,
	headless: bool,
	output_path: Path,
) -> dict[str, Any]:
	service = DesignSenseService()
	scenarios: list[dict] = [dict(s) for s in FAKE_SCENARIOS]
	sandbox_reachable, http_status, reach_error = _is_reachable(base_url)
	sandbox_skipped_reason: str | None = None

	if include_sandbox:
		if sandbox_reachable:
			for page in SANDBOX_PAGES:
				req, err = await _collect_sandbox_request(base_url, page, headless=headless)
				if req is None:
					scenarios.append({
						'id': page['id'],
						'source': 'sandbox',
						'description': f'Sandbox {page["path"]} (collection failed)',
						'request': ReviewRequest(user_task=page['user_task'], preview_url=urljoin(base_url, page['path'])),
						'collection_error': err,
					})
				else:
					scenarios.append({
						'id': page['id'],
						'source': 'sandbox',
						'description': f'Live sandbox page {page["path"]}',
						'request': req,
					})
		else:
			sandbox_skipped_reason = reach_error or f'HTTP {http_status}'

	results: list[ScenarioResult] = []
	for scenario in scenarios:
		try:
			report = await service.review(scenario['request'])
			row = _summarize_report(scenario, report)
			if scenario.get('collection_error'):
				row.degraded.append(f'sandbox_collection:{scenario["collection_error"]}')
		except Exception as exc:
			row = ScenarioResult(
				scenario_id=scenario['id'],
				source=scenario['source'],
				description=scenario.get('description', ''),
				passed=False,
				summary='',
				finding_count=0,
				blocking_count=0,
				major_count=0,
				objective_count=0,
				subjective_count=0,
				error=str(exc),
			)
		results.append(row)

	passed = sum(1 for r in results if r.error is None)
	blocking_total = sum(r.blocking_count for r in results)
	payload = {
		'generated_at': datetime.now(timezone.utc).isoformat(),
		'runner': 'tests/run_design_sense_scenarios.py',
		'sandbox': {
			'base_url': base_url,
			'reachable': sandbox_reachable,
			'http_status': http_status,
			'included': include_sandbox and sandbox_reachable,
			'skipped_reason': sandbox_skipped_reason,
		},
		'summary': {
			'total_scenarios': len(results),
			'completed_without_error': passed,
			'errors': sum(1 for r in results if r.error),
			'total_findings': sum(r.finding_count for r in results),
			'total_blocking': blocking_total,
			'total_actionable': sum(r.actionable_count for r in results),
			'total_generic_advisories': sum(r.generic_advisory_count for r in results),
			'total_confirmed': sum(r.confirmed_count for r in results),
		},
		'scenarios': [r.to_dict() for r in results],
	}

	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
	_write_summary_md(payload, DEFAULT_SUMMARY)
	return payload


def _write_summary_md(payload: dict[str, Any], path: Path) -> None:
	lines = [
		'# Design Sense Scenario Results',
		'',
		f"Generated: {payload['generated_at']}",
		'',
		'## Run summary',
		'',
	]
	s = payload['summary']
	sb = payload['sandbox']
	lines.extend([
		f"- Scenarios: **{s['total_scenarios']}**",
		f"- Completed: **{s['completed_without_error']}**",
		f"- Errors: **{s['errors']}**",
		f"- Total findings: **{s['total_findings']}**",
		f"- Total blocking: **{s['total_blocking']}**",
		f"- Sandbox: **{'live' if sb['included'] else 'skipped'}** ({sb['base_url']})",
		'',
		'## Per scenario',
		'',
	])
	for row in payload['scenarios']:
		status = 'ERROR' if row.get('error') else ('PASS' if row['passed'] else 'REVIEW')
		lines.append(f"### {row['scenario_id']} ({row['source']}) — {status}")
		lines.append('')
		lines.append(row.get('description') or '')
		lines.append('')
		if row.get('error'):
			lines.append(f"- **Error:** {row['error']}")
		else:
			lines.append(f"- Findings: {row['finding_count']} (blocking: {row['blocking_count']}, major: {row['major_count']})")
			lines.append(f"- Lanes: objective={row['objective_count']}, subjective={row['subjective_count']}")
			lines.append(f"- Reviewers: {', '.join(row['consulted_reviewers'][:5])}{'…' if len(row['consulted_reviewers']) > 5 else ''}")
			lines.append(f"- Summary: {row['summary'][:200]}{'…' if len(row['summary']) > 200 else ''}")
			if row['top_findings']:
				lines.append('- Top findings:')
				for f in row['top_findings'][:3]:
					lines.append(f"  - [{f['severity']}] {f['message'][:100]}")
		lines.append('')
	path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> int:
	parser = argparse.ArgumentParser(description='Run Design Sense scenario benchmarks')
	parser.add_argument('--base-url', default='http://localhost:5173')
	parser.add_argument('--no-sandbox', action='store_true', help='Only run fixture scenarios')
	parser.add_argument('--headed', action='store_true', help='Show browser during sandbox collection')
	parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
	args = parser.parse_args()

	payload = asyncio.run(
		run_all(
			base_url=args.base_url,
			include_sandbox=not args.no_sandbox,
			headless=not args.headed,
			output_path=args.output,
		)
	)
	print(f"Wrote {args.output}")
	print(f"Wrote {DEFAULT_SUMMARY}")
	print(
		f"scenarios={payload['summary']['total_scenarios']} "
		f"findings={payload['summary']['total_findings']} "
		f"blocking={payload['summary']['total_blocking']} "
		f"sandbox={'yes' if payload['sandbox']['included'] else 'no'}"
	)
	return 0 if payload['summary']['errors'] == 0 else 1


if __name__ == '__main__':
	raise SystemExit(main())
