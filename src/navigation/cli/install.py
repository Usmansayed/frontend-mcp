"""Quiet install wrapper with a simple progress indicator."""

from __future__ import annotations

import argparse
import itertools
import platform
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path

PACKAGE_NAME = 'frontend-perception-engine'
_SPINNER_FRAMES = '|/-\\'


class _Spinner:
	def __init__(self, message: str) -> None:
		self._message = message
		self._stop = threading.Event()
		self._thread: threading.Thread | None = None

	def __enter__(self) -> _Spinner:
		self._thread = threading.Thread(target=self._run, daemon=True)
		self._thread.start()
		return self

	def __exit__(self, *_args: object) -> None:
		self._stop.set()
		if self._thread is not None:
			self._thread.join()
		width = len(self._message) + 6
		sys.stdout.write('\r' + (' ' * width) + '\r')
		sys.stdout.flush()

	def _run(self) -> None:
		for frame in itertools.cycle(_SPINNER_FRAMES):
			if self._stop.is_set():
				break
			sys.stdout.write(f'\r  {frame} {self._message}')
			sys.stdout.flush()
			time.sleep(0.1)


def _pip_available() -> bool:
	result = subprocess.run(
		[sys.executable, '-m', 'pip', '--version'],
		capture_output=True,
	)
	return result.returncode == 0


def _build_install_command(*, upgrade: bool, editable: str | None) -> list[str]:
	target: list[str]
	if editable is not None:
		target = ['-e', editable]
	else:
		target = [PACKAGE_NAME]

	if _pip_available():
		cmd = [
			sys.executable,
			'-m',
			'pip',
			'install',
			'-q',
			'--disable-pip-version-check',
		]
		if upgrade:
			cmd.append('--upgrade')
		cmd.extend(target)
		return cmd

	uv = shutil.which('uv')
	if uv is not None:
		cmd = [uv, 'pip', 'install', '-q']
		if upgrade:
			cmd.append('--upgrade')
		cmd.extend(target)
		return cmd

	raise SystemExit(
		'No installer available. Install pip or uv, or use:\n'
		'  uvx --from frontend-perception-engine frontend-perception-mcp\n',
	)


def _build_browser_install_command() -> list[str]:
	cmd = ['uvx', 'playwright', 'install', 'chromium']
	if platform.system() == 'Linux':
		cmd.append('--with-deps')
	cmd.append('--no-shell')
	return cmd


def _run_quiet(cmd: Sequence[str], *, label: str) -> None:
	with _Spinner(label):
		result = subprocess.run(
			list(cmd),
			capture_output=True,
			text=True,
		)
	if result.returncode != 0:
		sys.stderr.write(f'\nInstallation failed ({label}).\n')
		if result.stderr.strip():
			sys.stderr.write(result.stderr.strip() + '\n')
		raise SystemExit(result.returncode or 1)


def _installed_version() -> str | None:
	try:
		from importlib.metadata import version

		return version(PACKAGE_NAME)
	except Exception:
		return None


def _print_success(*, with_browser: bool) -> None:
	version = _installed_version()
	version_suffix = f' ({version})' if version else ''
	sys.stdout.write(f'\n  OK  Successfully installed {PACKAGE_NAME}{version_suffix}\n\n')
	sys.stdout.write('  Run MCP server:\n')
	sys.stdout.write('    frontend-perception-mcp\n\n')
	sys.stdout.write('  Or with uvx (no global install):\n')
	sys.stdout.write('    uvx --from frontend-perception-engine frontend-perception-mcp\n\n')
	sys.stdout.write('  Or shorter PyPI name:\n')
	sys.stdout.write('    uvx --from frontend-mcp frontend-mcp\n\n')
	sys.stdout.write('  Cursor MCP config (either name):\n')
	sys.stdout.write('    {\n')
	sys.stdout.write('      "mcpServers": {\n')
	sys.stdout.write('        "frontend-perception": {\n')
	sys.stdout.write('          "command": "uvx",\n')
	sys.stdout.write('          "args": ["--from", "frontend-perception-engine", "frontend-perception-mcp"]\n')
	sys.stdout.write('        }\n')
	sys.stdout.write('      }\n')
	sys.stdout.write('    }\n')
	sys.stdout.write('\n  Alias package: pip install frontend-mcp  →  frontend-mcp / frontend-mcp-install\n')
	if with_browser:
		sys.stdout.write('\n  Chromium is ready for Browser Use.\n')
	sys.stdout.flush()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		prog='frontend-perception-install',
		description='Install frontend-perception-engine with minimal output.',
	)
	parser.add_argument(
		'-U',
		'--upgrade',
		action='store_true',
		help='Upgrade an existing installation.',
	)
	parser.add_argument(
		'-e',
		'--editable',
		metavar='PATH',
		help='Install from a local checkout (pip install -e PATH).',
	)
	parser.add_argument(
		'--with-browser',
		action='store_true',
		help='Also install Chromium for Browser Use (via playwright).',
	)
	return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> None:
	args = _parse_args(argv)

	if args.editable is not None:
		editable_path = str(Path(args.editable).expanduser().resolve())
		label = 'Installing frontend-perception-engine (editable)'
	else:
		editable_path = None
		label = 'Installing frontend-perception-engine'

	if (
		not args.upgrade
		and editable_path is None
		and _installed_version() is not None
		and not _pip_available()
	):
		_print_success(with_browser=False)
		return

	_run_quiet(_build_install_command(upgrade=args.upgrade, editable=editable_path), label=label)

	if args.with_browser:
		browser_cmd = _build_browser_install_command()
		if shutil.which(browser_cmd[0]) is None:
			sys.stderr.write(
				'\nSkipped browser setup: uvx not found on PATH.\n'
				'Install uv (https://docs.astral.sh/uv/) or run: uvx playwright install chromium\n',
			)
		else:
			_run_quiet(browser_cmd, label='Setting up Chromium')

	_print_success(with_browser=args.with_browser)


if __name__ == '__main__':
	main()
