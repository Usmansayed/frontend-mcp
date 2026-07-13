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

DEFAULT_PACKAGE_NAME = 'frontend-perception-engine'
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


def _resolve_install_package() -> str:
	"""Match PyPI package to the install entry point (frontend-mcp vs engine)."""
	prog = Path(sys.argv[0]).name.lower()
	if prog.startswith('frontend-mcp'):
		return 'frontend-mcp'
	return DEFAULT_PACKAGE_NAME


def _pip_available() -> bool:
	result = subprocess.run(
		[sys.executable, '-m', 'pip', '--version'],
		capture_output=True,
	)
	return result.returncode == 0


def _build_install_command(
	*,
	package: str,
	upgrade: bool,
	editable: str | None,
	force_reinstall: bool = False,
) -> list[str]:
	target: list[str]
	if editable is not None:
		target = ['-e', editable]
	else:
		target = [package]

	if _pip_available():
		cmd = [
			sys.executable,
			'-m',
			'pip',
			'install',
			'-q',
			'--disable-pip-version-check',
		]
		if force_reinstall:
			cmd.append('--force-reinstall')
		elif upgrade:
			cmd.append('--upgrade')
		cmd.extend(target)
		return cmd

	uv = shutil.which('uv')
	if uv is not None:
		cmd = [uv, 'pip', 'install', '-q']
		if force_reinstall:
			cmd.append('--reinstall')
		elif upgrade:
			cmd.append('--upgrade')
		cmd.extend(target)
		return cmd

	raise SystemExit(
		'No installer available. Install pip or uv, or use:\n'
		'  uvx --from frontend-mcp frontend-mcp\n',
	)


def _build_browser_install_command() -> list[str]:
	cmd = ['uvx', 'playwright', 'install', 'chromium']
	if platform.system() == 'Linux':
		cmd.append('--with-deps')
	cmd.append('--no-shell')
	return cmd


def _run_quiet(cmd: Sequence[str], *, label: str) -> subprocess.CompletedProcess[str]:
	with _Spinner(label):
		return subprocess.run(
			list(cmd),
			capture_output=True,
			text=True,
		)


def _installed_version(package: str) -> str | None:
	try:
		from importlib.metadata import version

		return version(package)
	except Exception:
		return None


def _print_success(*, package: str, with_browser: bool) -> None:
	engine_version = _installed_version(DEFAULT_PACKAGE_NAME)
	alias_version = _installed_version('frontend-mcp')
	version_bits: list[str] = []
	if package == 'frontend-mcp' and alias_version:
		version_bits.append(f'frontend-mcp {alias_version}')
	if engine_version:
		version_bits.append(f'frontend-perception-engine {engine_version}')
	version_suffix = f' ({", ".join(version_bits)})' if version_bits else ''
	sys.stdout.write(f'\n  OK  Successfully installed {package}{version_suffix}\n\n')
	sys.stdout.write('  Run MCP server:\n')
	sys.stdout.write('    frontend-mcp\n')
	sys.stdout.write('    # or: frontend-perception-mcp\n\n')
	sys.stdout.write('  Or with uvx (always latest from PyPI):\n')
	sys.stdout.write('    uvx --from frontend-mcp frontend-mcp\n\n')
	sys.stdout.write('  Cursor MCP config:\n')
	sys.stdout.write('    {\n')
	sys.stdout.write('      "mcpServers": {\n')
	sys.stdout.write('        "frontend-perception": {\n')
	sys.stdout.write('          "command": "uvx",\n')
	sys.stdout.write('          "args": ["--from", "frontend-mcp", "frontend-mcp"]\n')
	sys.stdout.write('        }\n')
	sys.stdout.write('      }\n')
	sys.stdout.write('    }\n')
	if with_browser:
		sys.stdout.write('\n  Chromium is ready for Browser Use.\n')
	sys.stdout.flush()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		prog=_resolve_install_package() + '-install',
		description='Install the latest Frontend Perception MCP from PyPI.',
	)
	parser.add_argument(
		'--no-upgrade',
		action='store_true',
		help='Skip upgrading to latest PyPI (only install if missing).',
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


def _install_package(
	*,
	package: str,
	upgrade: bool,
	editable: str | None,
	label: str,
) -> None:
	cmd = _build_install_command(package=package, upgrade=upgrade, editable=editable)
	result = _run_quiet(cmd, label=label)
	if result.returncode == 0:
		return

	stderr = result.stderr or ''
	if editable is None and 'uninstall-no-record-file' in stderr:
		sys.stderr.write(
			'\nDetected a broken prior install (editable leftover). Retrying with --force-reinstall...\n',
		)
		retry = _build_install_command(
			package=package,
			upgrade=False,
			editable=None,
			force_reinstall=True,
		)
		result = _run_quiet(retry, label=f'Reinstalling {package}')
		if result.returncode == 0:
			return
		stderr = result.stderr or stderr

	sys.stderr.write(f'\nInstallation failed ({label}).\n')
	if stderr.strip():
		sys.stderr.write(stderr.strip() + '\n')
	if 'uninstall-no-record-file' in stderr:
		sys.stderr.write(
			'\nManual fix: remove orphan folders in site-packages matching '
			'frontend_perception_engine-*.dist-info that lack a RECORD file, then rerun install.\n',
		)
	raise SystemExit(result.returncode or 1)


def main(argv: Sequence[str] | None = None) -> None:
	args = _parse_args(argv)
	package = _resolve_install_package()
	upgrade = not args.no_upgrade

	if args.editable is not None:
		editable_path = str(Path(args.editable).expanduser().resolve())
		label = f'Installing {DEFAULT_PACKAGE_NAME} (editable)'
	else:
		editable_path = None
		label = f'Installing latest {package} from PyPI'

	if (
		not upgrade
		and editable_path is None
		and _installed_version(package if package == 'frontend-mcp' else DEFAULT_PACKAGE_NAME) is not None
		and not _pip_available()
	):
		_print_success(package=package, with_browser=False)
		return

	_install_package(package=package, upgrade=upgrade, editable=editable_path, label=label)

	if args.with_browser:
		browser_cmd = _build_browser_install_command()
		if shutil.which(browser_cmd[0]) is None:
			sys.stderr.write(
				'\nSkipped browser setup: uvx not found on PATH.\n'
				'Install uv (https://docs.astral.sh/uv/) or run: uvx playwright install chromium\n',
			)
		else:
			result = _run_quiet(browser_cmd, label='Setting up Chromium')
			if result.returncode != 0:
				sys.stderr.write('\nBrowser setup failed.\n')
				if result.stderr.strip():
					sys.stderr.write(result.stderr.strip() + '\n')
				raise SystemExit(result.returncode or 1)

	_print_success(package=package, with_browser=args.with_browser)


if __name__ == '__main__':
	main()
