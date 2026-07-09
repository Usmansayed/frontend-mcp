"""Run Lighthouse CLI and load LHR JSON."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

from .models import AuditCategory

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 120
LH_CATEGORIES: dict[AuditCategory, str] = {
	AuditCategory.ACCESSIBILITY: 'accessibility',
	AuditCategory.PERFORMANCE: 'performance',
	AuditCategory.SEO: 'seo',
	AuditCategory.BEST_PRACTICES: 'best-practices',
}


class LighthouseNotAvailableError(RuntimeError):
	"""Node.js or Lighthouse CLI is not available."""


class LighthouseRunError(RuntimeError):
	"""Lighthouse failed without producing a valid report."""


def lighthouse_available() -> bool:
	return bool(shutil.which('npx') or shutil.which('npx.cmd') or shutil.which('lighthouse'))


def _lighthouse_base_cmd() -> list[str]:
	if shutil.which('lighthouse'):
		return ['lighthouse']
	npx = shutil.which('npx') or shutil.which('npx.cmd')
	if not npx:
		raise LighthouseNotAvailableError(
			'Lighthouse requires Node.js (npx). Install Node.js or run: npm install -g lighthouse'
		)
	return [npx, '--yes', 'lighthouse@12']


def _category_flag(category: AuditCategory) -> str:
	return LH_CATEGORIES[category]


def run_lighthouse_sync(
	url: str,
	category: AuditCategory,
	output_path: Path,
	*,
	tmp_dir: Path | None = None,
	timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
	assert url and url != 'about:blank', 'Cannot audit empty or about:blank URL'

	output_path.parent.mkdir(parents=True, exist_ok=True)
	if output_path.exists():
		output_path.unlink()

	cmd = [
		*_lighthouse_base_cmd(),
		url,
		f'--only-categories={_category_flag(category)}',
		'--output=json',
		f'--output-path={output_path}',
		'--preset=desktop',
		'--quiet',
		'--no-enable-error-reporting',
	]

	env = os.environ.copy()
	if tmp_dir is not None:
		tmp_dir.mkdir(parents=True, exist_ok=True)
		env['TEMP'] = str(tmp_dir)
		env['TMP'] = str(tmp_dir)

	logger.debug('Running lighthouse: %s', ' '.join(cmd))
	try:
		result = subprocess.run(
			cmd,
			capture_output=True,
			text=True,
			timeout=timeout_s,
			env=env,
			shell=False,
		)
	except subprocess.TimeoutExpired as exc:
		raise LighthouseRunError(f'Lighthouse timed out after {timeout_s}s') from exc
	except FileNotFoundError as exc:
		raise LighthouseNotAvailableError(str(exc)) from exc

	if output_path.is_file():
		try:
			return json.loads(output_path.read_text(encoding='utf-8'))
		except json.JSONDecodeError as exc:
			raise LighthouseRunError(f'Invalid Lighthouse JSON at {output_path}') from exc

	stderr = (result.stderr or '').strip()
	stdout = (result.stdout or '').strip()
	detail = stderr or stdout or f'exit code {result.returncode}'
	raise LighthouseRunError(f'Lighthouse failed: {detail}')


async def run_lighthouse(
	url: str,
	category: AuditCategory,
	output_path: Path,
	*,
	tmp_dir: Path | None = None,
	timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
	"""Run Lighthouse in a worker thread (subprocess)."""
	return await asyncio.to_thread(
		run_lighthouse_sync,
		url,
		category,
		output_path,
		tmp_dir=tmp_dir,
		timeout_s=timeout_s,
	)
