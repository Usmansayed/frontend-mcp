"""Grounded Docs CLI client — thin wrapper around upstream binary (no custom logic)."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .runtime import (
	MIN_NODE_MAJOR,
	ensure_store_dir,
	parse_node_major_version,
	resolve_executable,
)

PINNED_VERSION = '2.4.2'


class GroundedDocsCliError(Exception):
	pass


class GroundedDocsCli:
	"""Invoke pinned @arabold/docs-mcp-server CLI via npx or a local fork binary."""

	def __init__(
		self,
		*,
		cli_path: str | None = None,
		store_path: Path | None = None,
		scrape_timeout_s: int = 300,
		search_timeout_s: int = 60,
	) -> None:
		self._cli_path = cli_path or os.environ.get('GROUNDED_DOCS_CLI', '').strip() or None
		self._store_path = store_path
		if self._store_path is None:
			raw = os.environ.get('GROUNDED_DOCS_STORE_PATH', '').strip()
			if raw:
				self._store_path = Path(raw)
		self._scrape_timeout_s = int(
			os.environ.get('GROUNDED_DOCS_SCRAPE_TIMEOUT_S', scrape_timeout_s)
		)
		self._search_timeout_s = search_timeout_s
		self._availability_cache: bool | None = None
		self._node_major_cache: int | None = None

	def available(self) -> bool:
		if self._availability_cache is not None:
			return self._availability_cache
		ok = self._check_available()
		self._availability_cache = ok
		return ok

	def _check_available(self) -> bool:
		if self._cli_path:
			path = Path(self._cli_path).expanduser()
			if path.is_file():
				return True
			resolved = resolve_executable(self._cli_path)
			if resolved:
				self._cli_path = resolved
				return True
			return False
		npx = resolve_executable('npx')
		if not npx:
			return False
		major = self._read_node_major_version()
		return major is not None and major >= MIN_NODE_MAJOR

	def _read_node_major_version(self) -> int | None:
		if self._node_major_cache is not None:
			return self._node_major_cache
		node = resolve_executable('node')
		if not node:
			return None
		try:
			proc = subprocess.run(
				[node, '--version'],
				capture_output=True,
				text=True,
				encoding='utf-8',
				errors='replace',
				timeout=10,
				check=False,
			)
		except (FileNotFoundError, subprocess.TimeoutExpired):
			return None
		major = parse_node_major_version(proc.stdout or proc.stderr or '')
		self._node_major_cache = major
		return major

	def _resolved_store_path(self) -> Path | None:
		if self._store_path is None:
			return None
		return ensure_store_dir(self._store_path)

	def _base_cmd(self) -> list[str]:
		if self._cli_path:
			return [str(Path(self._cli_path).expanduser())]
		npx = resolve_executable('npx')
		if npx:
			return [npx, '-y', f'@arabold/docs-mcp-server@{PINNED_VERSION}']
		return ['npx', '-y', f'@arabold/docs-mcp-server@{PINNED_VERSION}']

	def _with_store(self, cmd: list[str]) -> list[str]:
		store = self._resolved_store_path()
		if store is None:
			return cmd
		return [*cmd, '--store-path', str(store)]

	async def search(
		self,
		library: str,
		query: str,
		*,
		version: str | None = None,
	) -> Any:
		cmd = [
			*self._with_store(
				[
					*self._base_cmd(),
					'search',
					library,
					query,
					'--output',
					'json',
					'--quiet',
				]
			),
		]
		if version:
			cmd.extend(['--version', version])
		return await asyncio.to_thread(self._run_json, cmd, timeout_s=self._search_timeout_s)

	async def scrape(
		self,
		library: str,
		url: str,
		*,
		version: str | None = None,
	) -> Any:
		cmd = [
			*self._with_store([*self._base_cmd(), 'scrape', library, url, '--output', 'json', '--quiet']),
		]
		if version:
			cmd.extend(['--version', version])
		return await asyncio.to_thread(self._run_json, cmd, timeout_s=self._scrape_timeout_s)

	def _run_json(self, cmd: list[str], *, timeout_s: int) -> Any:
		try:
			proc = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				encoding='utf-8',
				errors='replace',
				timeout=timeout_s,
				check=False,
			)
		except FileNotFoundError as exc:
			raise GroundedDocsCliError('grounded_docs_cli_unavailable:CLI not found') from exc
		except subprocess.TimeoutExpired as exc:
			raise GroundedDocsCliError(f'grounded_docs_timeout:{timeout_s}s') from exc

		stdout = (proc.stdout or '').strip()
		stderr = (proc.stderr or '').strip()

		if proc.returncode != 0:
			raise GroundedDocsCliError(self._format_cli_error(proc.returncode, stdout, stderr))

		if not stdout:
			return {}
		try:
			return json.loads(stdout)
		except json.JSONDecodeError:
			return {'text': stdout}

	@staticmethod
	def _format_cli_error(code: int, stdout: str, stderr: str) -> str:
		msg = stderr or stdout or f'exit code {code}'
		if 'LibraryNotFoundInStoreError' in msg or 'Library' in msg and 'not found' in msg:
			return f'library_not_indexed:{msg[:400]}'
		return msg[:500]
