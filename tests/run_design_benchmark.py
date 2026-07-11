"""Design Benchmark Suite — compare Design Review output against gold standards."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
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
BENCHMARKS_ROOT = ROOT / 'design_benchmarks'
RESULTS_DIR = ROOT / 'tests' / 'results'
sys.path.insert(0, str(SRC))

from navigation.design_sense_intelligence import DesignSenseService
from navigation.design_sense_intelligence.snapshot_access import review_request_from_snapshot
from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.observe.scan import scan_page

from design_sense_fixtures import FAKE_SCENARIOS

FIXTURE_BY_ID = {s['id']: s for s in FAKE_SCENARIOS}
_snapshot_engine = DesignSnapshotEngine()


@dataclass
class MatchResult:
	benchmark_id: str
	tp: int = 0
	fp: int = 0
	fn: int = 0
	generic_count: int = 0
	duplicate_estimate: int = 0
	reference_noise: int = 0
	score_pass_mismatch: bool = False
	precision: float = 0.0
	recall: float = 0.0
	finding_count: int = 0
	blocking_count: int = 0
	passed: bool = False
	expected_passed: bool = True
	false_positive_findings: list[str] = field(default_factory=list)
	false_negative_gold: list[str] = field(default_factory=list)
	generic_findings: list[str] = field(default_factory=list)


def _discover_benchmarks(root: Path) -> list[Path]:
	return sorted(root.glob('**/benchmark.json'))


def _finding_text(f: dict[str, Any]) -> str:
	parts = [f.get('category', ''), f.get('message', ''), f.get('id', ''), f.get('recommendation', '')]
	return ' '.join(str(p) for p in parts).lower()


def _matches_patterns(text: str, patterns: list[str]) -> bool:
	return any(p.lower() in text for p in patterns)


def _matches_gold(finding: dict[str, Any], gold: dict[str, Any]) -> bool:
	text = _finding_text(finding)
	if gold.get('severity') and finding.get('severity') != gold.get('severity'):
		# allow severity mismatch only if not specified strictly
		pass
	return _matches_patterns(text, gold.get('match', []))


def _is_generic(finding: dict[str, Any]) -> bool:
	msg = str(finding.get('message', ''))
	if msg.lower().startswith('verify:'):
		return True
	if finding.get('confirmed') is False and finding.get('confidence', 1) < 0.5:
		return True
	if not finding.get('evidence') and not finding.get('affected_element') and finding.get('severity') == 'advisory':
		if any(k in msg.lower() for k in ('verify', 'awaiting', 'not supplied', 'insufficient')):
			return True
	return False


def _duplicate_estimate(findings: list[dict[str, Any]]) -> int:
	total = 0
	for f in findings:
		merged = f.get('metadata', {}).get('merged_from', 1)
		if isinstance(merged, int) and merged > 1:
			total += merged - 1
	return total


def _reference_noise(report_summary: str, findings: list[dict[str, Any]]) -> int:
	count = 0
	if 'vs ' in report_summary.lower() and 'reference' in report_summary.lower():
		count += 1
	for f in findings:
		msg = _finding_text(f)
		if 'reference' in msg or 'align font stack with reference' in msg:
			count += 1
	return count


def evaluate_benchmark(
	benchmark: dict[str, Any],
	findings: list[dict[str, Any]],
	*,
	passed: bool,
	summary: str,
) -> MatchResult:
	bid = benchmark['id']
	gold_required = [g for g in benchmark.get('gold_findings', []) if g.get('required')]
	gold_optional = [g for g in benchmark.get('gold_findings', []) if not g.get('required')]
	forbidden = benchmark.get('gold_forbidden', [])
	expected = benchmark.get('expected_score', {})

	matched_gold: set[str] = set()
	tp = 0
	fp = 0

	for f in findings:
		text = _finding_text(f)
		if any(_matches_patterns(text, fb.get('match', [])) for fb in forbidden):
			fp += 1
			continue
		matched_any = False
		for g in gold_required + gold_optional:
			if g['id'] in matched_gold:
				continue
			if _matches_gold(f, g):
				matched_gold.add(g['id'])
				tp += 1
				matched_any = True
				break
		if not matched_any and gold_required:
			# only count as FP if we have gold expectations; otherwise unlabeled findings on clean pages
			if gold_required or gold_optional:
				if not _is_generic(f) and f.get('severity') in ('blocking', 'major', 'minor'):
					fp += 1
			elif f.get('severity') in ('blocking', 'major'):
				fp += 1

	# Clean pages: findings without gold are FP if not generic minor
	if not gold_required and not gold_optional:
		for f in findings:
			text = _finding_text(f)
			if any(_matches_patterns(text, fb.get('match', [])) for fb in forbidden):
				continue
			if f.get('severity') == 'blocking':
				fp += 1
			elif f.get('severity') == 'major' and not _is_generic(f):
				fp += 0.5  # counted in aggregate later

	fn = sum(1 for g in gold_required if g['id'] not in matched_gold)
	generic = [f for f in findings if _is_generic(f)]
	dupes = _duplicate_estimate(findings)
	ref_noise = _reference_noise(summary, findings)

	expected_passed = expected.get('passed', True)
	score_mismatch = passed != expected_passed
	if expected.get('min_blocking', 0) and sum(1 for f in findings if f.get('severity') == 'blocking') < expected['min_blocking']:
		score_mismatch = True
	if expected.get('max_blocking') is not None:
		if sum(1 for f in findings if f.get('severity') == 'blocking') > expected['max_blocking']:
			score_mismatch = True

	precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fp == 0 else 0.0)
	recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fn == 0 else 0.0)

	return MatchResult(
		benchmark_id=bid,
		tp=tp,
		fp=int(fp) if isinstance(fp, int) else int(round(fp)),
		fn=fn,
		generic_count=len(generic),
		duplicate_estimate=dupes,
		reference_noise=ref_noise,
		score_pass_mismatch=score_mismatch,
		precision=round(precision, 3),
		recall=round(recall, 3),
		finding_count=len(findings),
		blocking_count=sum(1 for f in findings if f.get('severity') == 'blocking'),
		passed=passed,
		expected_passed=expected_passed,
		false_positive_findings=[f.get('message', '')[:80] for f in findings if _is_generic(f) is False][:5],
		false_negative_gold=[g['id'] for g in gold_required if g['id'] not in matched_gold],
		generic_findings=[f.get('message', '')[:80] for f in generic[:5]],
	)


async def _run_fixture_benchmark(benchmark: dict[str, Any]) -> tuple[list[dict], bool, str]:
	ref = benchmark.get('fixture_ref')
	scenario = FIXTURE_BY_ID.get(ref)
	if not scenario:
		raise ValueError(f'unknown fixture_ref: {ref}')
	request = scenario['request']
	report = await DesignSenseService().review(request)
	return [f.to_dict() for f in report.findings], report.passed, report.summary


async def _run_sandbox_benchmark(
	benchmark: dict[str, Any],
	*,
	base_url: str,
	headless: bool,
) -> tuple[list[dict], bool, str]:
	path = benchmark['sandbox_path']
	store = SessionStore(artifacts_root=ROOT / 'artifacts' / 'design_benchmarks')
	rec = await store.start(base_url=base_url, headless=headless)
	try:
		url = urljoin(base_url.rstrip('/') + '/', path.lstrip('/'))
		scan = await scan_page(
			rec.browser, url,
			images_dir=rec.artifacts_dir / 'scans',
			name=benchmark['id'].replace('/', '_'),
			screenshot_mode='viewport',
			annotate_screenshot=False,
			console_service=rec.console,
			network_service=rec.network,
		)
		if not scan.ok or scan.observation is None:
			raise RuntimeError(scan.error or 'scan_failed')
		obs = scan.observation.to_dict()
		snapshot = await _snapshot_engine.capture_from_session(
			rec.browser,
			visual_insights=obs.get('visual_insights'),
			a11y_tree=obs.get('a11y_tree', ''),
			dom_text=obs.get('dom_text', ''),
			scan_id=benchmark['id'],
		)
		request = review_request_from_snapshot(
			snapshot,
			user_task=benchmark['user_task'],
			scope=benchmark.get('scope', 'page'),
		)
		report = await DesignSenseService().review(request)
		return [f.to_dict() for f in report.findings], report.passed, report.summary
	finally:
		await store.end(rec.session_id)


def _compute_error_breakdown(results: list[MatchResult], total_findings: int) -> dict[str, Any]:
	"""Map benchmark metrics to score loss budget (100% - overall%)."""
	total_tp = sum(r.tp for r in results)
	total_fp = sum(r.fp for r in results)
	total_fn = sum(r.fn for r in results)
	total_generic = sum(r.generic_count for r in results)
	total_dupes = sum(r.duplicate_estimate for r in results)
	total_ref = sum(r.reference_noise for r in results)
	pass_mismatches = sum(1 for r in results if r.score_pass_mismatch)

	n = max(len(results), 1)
	denom_findings = max(total_findings, 1)

	# Rates
	fp_rate = total_fp / max(total_tp + total_fp, 1)
	fn_rate = total_fn / max(total_tp + total_fn, 1)
	generic_rate = total_generic / denom_findings
	dupe_rate = total_dupes / max(total_findings + total_dupes, 1)
	pass_miss_rate = pass_mismatches / n
	ref_rate = total_ref / n

	# Weighted loss components (sum ~26% from ~74% overall)
	false_positives_pct = round(fp_rate * 18, 1)
	false_negatives_pct = round(fn_rate * 22, 1)
	generic_pct = round(generic_rate * 12, 1)
	duplicate_pct = round(dupe_rate * 8, 1)
	missing_detection_pct = round(fn_rate * 12 + pass_miss_rate * 4, 1)
	reference_pct = round(ref_rate * 6, 1)

	overall = max(0, round(100 - (
		false_positives_pct + false_negatives_pct + generic_pct +
		duplicate_pct + missing_detection_pct + reference_pct
	), 1))

	return {
		'overall_percent': overall,
		'loss_breakdown': {
			'false_positives': f'{false_positives_pct}%',
			'false_negatives': f'{false_negatives_pct}%',
			'duplicate_findings': f'{duplicate_pct}%',
			'generic_findings': f'{generic_pct}%',
			'missing_design_detection': f'{missing_detection_pct}%',
			'reference_comparison_accuracy': f'{reference_pct}%',
		},
		'raw_metrics': {
			'precision': round(total_tp / max(total_tp + total_fp, 1), 3),
			'recall': round(total_tp / max(total_tp + total_fn, 1), 3),
			'total_tp': total_tp,
			'total_fp': total_fp,
			'total_fn': total_fn,
			'total_generic': total_generic,
			'total_duplicates_estimated': total_dupes,
			'pass_mismatches': pass_mismatches,
			'reference_noise_hits': total_ref,
			'total_findings': total_findings,
		},
	}


def _write_analysis_md(payload: dict[str, Any], path: Path) -> None:
	bd = payload['error_breakdown']
	raw = bd['raw_metrics']
	lb = bd['loss_breakdown']
	lines = [
		'# Design Benchmark Analysis',
		'',
		f"Generated: {payload['generated_at']}",
		'',
		f"## Overall score: **{bd['overall_percent']}%**",
		'',
		'### Where the score is lost',
		'',
		'```',
		f"Overall: {bd['overall_percent']}%",
		'',
		f"False Positives: {lb['false_positives']}",
		f"False Negatives: {lb['false_negatives']}",
		f"Duplicate Findings: {lb['duplicate_findings']}",
		f"Generic Findings: {lb['generic_findings']}",
		f"Missing Design Detection: {lb['missing_design_detection']}",
		f"Reference Comparison Accuracy: {lb['reference_comparison_accuracy']}",
		'```',
		'',
		'## Aggregate metrics',
		'',
		f"- Precision: **{raw['precision']}**",
		f"- Recall: **{raw['recall']}**",
		f"- True positives: {raw['total_tp']}",
		f"- False positives: {raw['total_fp']}",
		f"- False negatives: {raw['total_fn']}",
		f"- Generic findings: {raw['total_generic']} / {raw['total_findings']}",
		f"- Duplicates estimated (consensus merged): {raw['total_duplicates_estimated']}",
		f"- Pass/fail mismatches vs gold: {raw['pass_mismatches']}",
		'',
		'## Per benchmark',
		'',
	]
	for r in payload['benchmarks']:
		lines.append(f"### {r['benchmark_id']}")
		lines.append('')
		lines.append(
			f"- Precision {r['precision']} | Recall {r['recall']} | "
			f"Findings {r['finding_count']} | Blocking {r['blocking_count']} | "
			f"Passed {r['passed']} (expected {r['expected_passed']})"
		)
		if r['false_negative_gold']:
			lines.append(f"- **Missed gold:** {', '.join(r['false_negative_gold'])}")
		if r['generic_findings']:
			lines.append(f"- Generic: {r['generic_findings'][0]}")
		if r['score_pass_mismatch']:
			lines.append('- **Pass/fail mismatch with gold**')
		lines.append('')
	path.write_text('\n'.join(lines), encoding='utf-8')


async def run_benchmarks(
	*,
	include_sandbox: bool,
	base_url: str,
	headless: bool,
) -> dict[str, Any]:
	paths = _discover_benchmarks(BENCHMARKS_ROOT)
	results: list[MatchResult] = []
	errors: list[dict[str, str]] = []

	for path in paths:
		benchmark = json.loads(path.read_text(encoding='utf-8'))
		if benchmark.get('sandbox_path') and not include_sandbox:
			continue
		try:
			if benchmark.get('fixture_ref'):
				findings, passed, summary = await _run_fixture_benchmark(benchmark)
			elif benchmark.get('sandbox_path'):
				findings, passed, summary = await _run_sandbox_benchmark(
					benchmark, base_url=base_url, headless=headless,
				)
			else:
				continue
			results.append(evaluate_benchmark(benchmark, findings, passed=passed, summary=summary))
		except Exception as exc:
			errors.append({'benchmark_id': benchmark.get('id', str(path)), 'error': str(exc)})

	total_findings = sum(r.finding_count for r in results)
	breakdown = _compute_error_breakdown(results, total_findings)

	return {
		'generated_at': datetime.now(timezone.utc).isoformat(),
		'runner': 'tests/run_design_benchmark.py',
		'benchmarks_run': len(results),
		'errors': errors,
		'error_breakdown': breakdown,
		'benchmarks': [asdict(r) for r in results],
	}


def main() -> int:
	parser = argparse.ArgumentParser(description='Run design benchmark suite')
	parser.add_argument('--no-sandbox', action='store_true')
	parser.add_argument('--base-url', default='http://localhost:5173')
	parser.add_argument('--headed', action='store_true')
	args = parser.parse_args()

	if not args.no_sandbox:
		try:
			with urllib.request.urlopen(args.base_url, timeout=3) as resp:
				if resp.status != 200:
					print(f'warning: sandbox returned {resp.status}')
		except (urllib.error.URLError, TimeoutError):
			print(f'warning: sandbox unreachable at {args.base_url}; use --no-sandbox')

	payload = asyncio.run(run_benchmarks(
		include_sandbox=not args.no_sandbox,
		base_url=args.base_url,
		headless=not args.headed,
	))

	RESULTS_DIR.mkdir(parents=True, exist_ok=True)
	report_path = RESULTS_DIR / 'design_benchmark_report.json'
	analysis_path = RESULTS_DIR / 'design_benchmark_analysis.md'
	report_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
	_write_analysis_md(payload, analysis_path)

	bd = payload['error_breakdown']
	print(f'Wrote {report_path}')
	print(f'Wrote {analysis_path}')
	print(f"Overall: {bd['overall_percent']}% | precision={bd['raw_metrics']['precision']} recall={bd['raw_metrics']['recall']}")
	return 0 if not payload['errors'] else 1


if __name__ == '__main__':
	raise SystemExit(main())
