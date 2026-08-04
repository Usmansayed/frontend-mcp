"""Run Lighthouse CLI and load LHR JSON."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from .models import AuditCategory

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 120
LH_CATEGORIES: dict[AuditCategory, str] = {
	AuditCategory.ACCESSIBILITY: 'accessibility',
	AuditCategory.PERFORMANCE: 'performance',
	AuditCategory.SEO: 'seo',
	AuditCategory.BEST_PRACTICES: 'best-practices',
}

# Keep Chrome launch isolated from the MCP-owned Playwright browser and from
# leftover locks after a prior kill. Without these flags, chrome-launcher can
# hang under a live perception session (hardcore retest: empty logs, exact
# timeout_s, then MCP process death on a longer retry).
_CHROME_FLAGS = (
	'--headless=new --no-first-run --no-default-browser-check '
	'--disable-gpu --disable-extensions --disable-background-networking '
	'--disable-dev-shm-usage --mute-audio'
)


class LighthouseNotAvailableError(RuntimeError):
	"""Node.js or Lighthouse CLI is not available."""


class LighthouseRunError(RuntimeError):
	"""Lighthouse failed without producing a valid report."""


def lighthouse_available() -> bool:
	return bool(shutil.which('npx') or shutil.which('npx.cmd') or shutil.which('lighthouse'))


def _find_chrome_path() -> str | None:
	"""Prefer an explicit Chrome/Chromium binary so chrome-launcher does not search."""
	for key in ('CHROME_PATH', 'LIGHTHOUSE_CHROMIUM_PATH', 'PUPPETEER_EXECUTABLE_PATH'):
		raw = (os.environ.get(key) or '').strip()
		if raw and Path(raw).is_file():
			return raw
	candidates: list[Path] = []
	if sys.platform == 'win32':
		pf = os.environ.get('PROGRAMFILES', r'C:\Program Files')
		pf86 = os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')
		local = os.environ.get('LOCALAPPDATA', '')
		candidates.extend(
			[
				Path(pf) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
				Path(pf86) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
				Path(local) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
				Path(pf) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
			]
		)
	else:
		candidates.extend(
			[
				Path('/usr/bin/google-chrome'),
				Path('/usr/bin/google-chrome-stable'),
				Path('/usr/bin/chromium'),
				Path('/usr/bin/chromium-browser'),
				Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
			]
		)
	# Playwright's bundled Chromium (often present next to MCP browser runtime).
	try:
		from playwright.sync_api import sync_playwright

		with sync_playwright() as p:
			exe = Path(p.chromium.executable_path)
			if exe.is_file():
				candidates.insert(0, exe)
	except Exception:
		pass
	for path in candidates:
		if path.is_file():
			return str(path)
	return None


def _lighthouse_base_cmd() -> list[str]:
	# Prefer a real .exe / binary over npx.CMD — batch shims under CREATE_NO_WINDOW
	# and MCP stdio hosts are fragile on Windows.
	lh = shutil.which('lighthouse')
	if lh and not lh.lower().endswith(('.cmd', '.bat')):
		return [lh]
	node = shutil.which('node') or shutil.which('node.exe')
	if node:
		# Resolve lighthouse CLI from the npx cache without going through npx.CMD.
		npx_root = Path.home() / 'AppData' / 'Local' / 'npm-cache' / '_npx'
		if npx_root.is_dir():
			matches = sorted(
				npx_root.glob('*/node_modules/lighthouse/cli/index.js'),
				key=lambda p: p.stat().st_mtime,
				reverse=True,
			)
			if matches:
				return [node, str(matches[0])]
		# Global install fallback.
		for base in (
			Path(os.environ.get('APPDATA', '')) / 'npm' / 'node_modules',
			Path('/usr/local/lib/node_modules'),
			Path('/usr/lib/node_modules'),
		):
			cli = base / 'lighthouse' / 'cli' / 'index.js'
			if cli.is_file():
				return [node, str(cli)]
	npx = shutil.which('npx') or shutil.which('npx.cmd')
	if not npx:
		raise LighthouseNotAvailableError(
			'Lighthouse requires Node.js (npx). Install Node.js or run: npm install -g lighthouse'
		)
	# Last resort: npx (may be .CMD on Windows).
	return [npx, '--yes', 'lighthouse@12']


def _category_flag(category: AuditCategory) -> str:
	return LH_CATEGORIES[category]


def _kill_process_tree(pid: int) -> None:
	"""Kill a process and all descendants.

	Killing only the direct child (cmd.exe shim for npx.CMD) leaves node/Chrome
	grandchildren alive — they hold the output pipes past the timeout and leak
	zombie node processes that can pin dev-server ports.

	Never escalate to killing our own process / parent.
	"""
	try:
		if pid <= 0 or pid == os.getpid():
			return
		if sys.platform == 'win32':
			# CREATE_NEW_PROCESS_GROUP isolates the tree; /T reaps descendants only.
			subprocess.run(
				['taskkill', '/T', '/F', '/PID', str(pid)],
				capture_output=True,
				timeout=15,
				check=False,
			)
		else:
			import signal

			os.killpg(os.getpgid(pid), signal.SIGKILL)
	except Exception:
		logger.warning('kill_process_tree failed for pid=%s', pid, exc_info=True)


def _tail(path: Path, limit: int = 800) -> str:
	try:
		text = path.read_text(encoding='utf-8', errors='replace').strip()
		return text[-limit:]
	except OSError:
		return ''


def _load_report(output_path: Path) -> dict[str, Any]:
	try:
		return json.loads(output_path.read_text(encoding='utf-8'))
	except json.JSONDecodeError as exc:
		raise LighthouseRunError(f'Invalid Lighthouse JSON at {output_path}') from exc


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

	# Fresh per-run chrome profile dir — avoids leftover locks after a kill.
	run_tag = uuid.uuid4().hex[:10]
	profile_parent = Path(tmp_dir) if tmp_dir is not None else output_path.parent / 'lighthouse-tmp'
	profile_parent.mkdir(parents=True, exist_ok=True)
	user_data_dir = profile_parent / f'chrome-profile-{run_tag}'
	user_data_dir.mkdir(parents=True, exist_ok=True)

	chrome_flags = f'{_CHROME_FLAGS} --user-data-dir={user_data_dir}'
	cmd = [
		*_lighthouse_base_cmd(),
		url,
		f'--only-categories={_category_flag(category)}',
		'--output=json',
		f'--output-path={output_path}',
		'--preset=desktop',
		'--quiet',
		'--no-enable-error-reporting',
		f'--chrome-flags={chrome_flags}',
		# Bound page-load wait so a hung Next.js request cannot eat the whole budget.
		'--max-wait-for-load=20000',
	]
	chrome = _find_chrome_path()
	if chrome:
		cmd.append(f'--chrome-path={chrome}')

	env = os.environ.copy()
	# Per-run TEMP — never reuse a shared locked TEMP from a prior killed audit.
	run_tmp = profile_parent / f'tmp-{run_tag}'
	run_tmp.mkdir(parents=True, exist_ok=True)
	env['TEMP'] = str(run_tmp)
	env['TMP'] = str(run_tmp)

	# Redirect to files, never pipes: on Windows, killing the cmd.exe shim on
	# timeout leaves node/Chrome holding inherited pipes, so pipe reads block
	# past the timeout (observed as wall-timeout at timeout_s+5 in hardcore runs).
	stdout_path = output_path.with_suffix('.stdout.log')
	stderr_path = output_path.with_suffix('.stderr.log')

	creationflags = 0
	preexec_fn = None
	if sys.platform == 'win32':
		# NEW_PROCESS_GROUP so taskkill /T cannot walk into the MCP parent tree.
		creationflags = (
			subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
		)
	else:
		preexec_fn = os.setsid

	logger.debug('Running lighthouse: %s', ' '.join(cmd))
	try:
		with open(stdout_path, 'wb') as so, open(stderr_path, 'wb') as se:
			proc = subprocess.Popen(
				cmd,
				stdout=so,
				stderr=se,
				# Never inherit MCP stdio — the JSON-RPC pipe must not leak to npm/node.
				stdin=subprocess.DEVNULL,
				env=env,
				shell=False,
				creationflags=creationflags,
				preexec_fn=preexec_fn,
			)
			try:
				proc.wait(timeout=timeout_s)
			except subprocess.TimeoutExpired:
				_kill_process_tree(proc.pid)
				try:
					proc.wait(timeout=10)
				except Exception:
					pass
				# Report is often written before the (slow) chrome cleanup phase.
				if output_path.is_file():
					logger.warning('Lighthouse timed out after report write — salvaging report')
					return _load_report(output_path)
				detail = _tail(stderr_path) or _tail(stdout_path)
				raise LighthouseRunError(
					f'Lighthouse timed out after {timeout_s}s'
					+ (f' — stderr tail: {detail}' if detail else '')
				) from None
	except FileNotFoundError as exc:
		raise LighthouseNotAvailableError(str(exc)) from exc

	if output_path.is_file():
		# chrome-launcher temp cleanup can EPERM on Windows and flip the exit
		# code after a fully successful audit — trust the written report.
		return _load_report(output_path)

	detail = _tail(stderr_path) or _tail(stdout_path) or f'exit code {proc.returncode}'
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
