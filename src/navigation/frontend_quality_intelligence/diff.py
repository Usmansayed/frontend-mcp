"""Compare two observation snapshots by scan_id."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.visual_browser_intelligence.visual.visual_diff import VisualDiffResult, diff_screenshot_files


def _blocking_issues(obs: dict[str, Any]) -> list[str]:
	di = obs.get('dev_insights') or {}
	summary = di.get('summary') or {}
	blocking = list(summary.get('blocking_issues') or [])
	visual = obs.get('visual_insights') or {}
	blocking.extend(visual.get('blocking') or [])
	return blocking


def _visual_issues_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[str]]:
	b_vis = set((before.get('visual_insights') or {}).get('blocking') or [])
	a_vis = set((after.get('visual_insights') or {}).get('blocking') or [])
	return {
		'new_visual_blocking': sorted(a_vis - b_vis),
		'removed_visual_blocking': sorted(b_vis - a_vis),
	}


def diff_observations(
	before: dict[str, Any],
	after: dict[str, Any],
	*,
	artifacts_dir: Path | None = None,
	scan_id_before: str = '',
	scan_id_after: str = '',
) -> dict[str, Any]:
	b_block = set(_blocking_issues(before))
	a_block = set(_blocking_issues(after))
	b_dom = str(before.get('dom_text') or '')
	a_dom = str(after.get('dom_text') or '')
	excerpt_len = 500
	visual_delta = _visual_issues_delta(before, after)

	result: dict[str, Any] = {
		'url_before': before.get('url') or '',
		'url_after': after.get('url') or '',
		'url_changed': (before.get('url') or '') != (after.get('url') or ''),
		'dom_text_changed': b_dom != a_dom,
		'new_blocking_issues': sorted(a_block - b_block),
		'removed_blocking_issues': sorted(b_block - a_block),
		'dom_excerpt_before': b_dom[:excerpt_len],
		'dom_excerpt_after': a_dom[:excerpt_len],
		**visual_delta,
		'visual_diff': None,
	}

	before_shot = before.get('annotated_screenshot_path') or before.get('screenshot_path')
	after_shot = after.get('annotated_screenshot_path') or after.get('screenshot_path')
	if artifacts_dir and before_shot and after_shot:
		prefix = f'{scan_id_before}_vs_{scan_id_after}'.replace('/', '_')[:80]
		vd: VisualDiffResult = diff_screenshot_files(
			before_shot,
			after_shot,
			artifacts_dir / 'diffs',
			prefix=prefix,
		)
		result['visual_diff'] = vd.to_dict()

	return result
