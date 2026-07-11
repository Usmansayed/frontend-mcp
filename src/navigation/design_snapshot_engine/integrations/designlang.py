"""Optional integration with external design extraction tools.

Research summary (2026):
- **designlang** (npm, MIT, github.com/Manavarya09/design-extract)
  Playwright-based CLI that walks live DOM, clusters components, emits DTCG tokens,
  typography, spacing, motion, WCAG contrast, and MCP resources.

Integration strategy for this repo:
1. **Primary path** — native Python extractors in design_snapshot_engine/ (no Node dep).
2. **Augment path** — optional subprocess `npx designlang <url> --json` when Node is available.
3. **MCP path** — future: consume designlang MCP resources alongside our snapshot.

We do not bundle designlang; callers opt in via DESIGNLANG_ENABLED=1.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..models import DesignSnapshot


def designlang_available() -> bool:
	if os.environ.get('DESIGNLANG_ENABLED', '').lower() not in ('1', 'true', 'yes'):
		return False
	return shutil.which('npx') is not None


def augment_snapshot_from_designlang(
	snapshot: DesignSnapshot,
	url: str,
	*,
	output_dir: Path | None = None,
	timeout: float = 120.0,
) -> DesignSnapshot:
	"""Merge designlang CLI output into snapshot when available (best-effort)."""
	if not designlang_available():
		snapshot.degraded.append('designlang_not_enabled')
		return snapshot

	out = output_dir or Path.cwd() / 'artifacts' / 'designlang'
	out.mkdir(parents=True, exist_ok=True)
	try:
		subprocess.run(
			['npx', 'designlang', url, '--output', str(out)],
			check=False,
			timeout=timeout,
			capture_output=True,
		)
	except (subprocess.TimeoutExpired, OSError) as exc:
		snapshot.degraded.append(f'designlang_failed:{type(exc).__name__}')
		return snapshot

	token_files = list(out.glob('*design-tokens.json'))
	if token_files:
		try:
			data = json.loads(token_files[0].read_text(encoding='utf-8'))
			if isinstance(data, dict):
				snapshot.design_tokens.css_variables.update(
					{k: str(v) for k, v in data.items() if k.startswith('--')}
				)
				snapshot.provenance['designlang_tokens'] = str(token_files[0])
		except Exception:
			snapshot.degraded.append('designlang_parse_failed')
	else:
		snapshot.degraded.append('designlang_no_output')

	return snapshot
