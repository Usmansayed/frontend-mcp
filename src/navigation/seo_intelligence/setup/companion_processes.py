"""Native OS process management for LibreCrawl (no Docker)."""

from __future__ import annotations



import asyncio

import atexit

import logging

import os

import shutil

import signal

import subprocess

import sys

import threading

import time

from pathlib import Path

from typing import Any



from navigation.seo_intelligence.config.defaults import (

	bundled_librecrawl_base_url,

	default_seo_cache_dir,

)



logger = logging.getLogger(__name__)



_LIBRECRAWL_REPO = 'https://github.com/PhialsBasement/LibreCrawl.git'

_MONITOR_INTERVAL_S = 15.0



_manager: NativeCompanionManager | None = None

_monitor_task: asyncio.Task[None] | None = None

_shutdown_registered = False





def companions_cache_dir() -> Path:

	raw = os.environ.get('SEO_COMPANIONS_CACHE_DIR', '').strip()

	if raw:

		return Path(raw)

	return default_seo_cache_dir() / 'companions'





def librecrawl_root() -> Path:

	override = os.environ.get('LIBRECRAWL_ROOT', '').strip()

	if override:

		return Path(override)

	return companions_cache_dir() / 'LibreCrawl'





def companion_venv() -> Path:
	return companions_cache_dir() / 'venv'


def venv_python_path(venv: Path | None = None) -> Path:
	root = (venv or companion_venv()).resolve()
	name = 'python.exe' if sys.platform == 'win32' else 'python'
	scripts = 'Scripts' if sys.platform == 'win32' else 'bin'
	return root / scripts / name





def logs_dir() -> Path:

	return companions_cache_dir() / 'logs'





def pids_dir() -> Path:

	return companions_cache_dir() / 'pids'





def librecrawl_port() -> int:

	raw = os.environ.get('LIBRECRAWL_PORT', '').strip()

	if raw:

		try:

			return int(raw)

		except ValueError:

			pass

	parsed = bundled_librecrawl_base_url().rsplit(':', 1)

	if len(parsed) == 2 and parsed[1].isdigit():

		return int(parsed[1].rstrip('/'))

	return 5001





def _run_librecrawl_launcher() -> Path:

	return Path(__file__).resolve().parents[1] / 'companions' / 'run_librecrawl.py'





class NativeCompanionManager:

	def __init__(self) -> None:

		self._processes: dict[str, subprocess.Popen[Any]] = {}

		self._lock = threading.Lock()



	def pid_file(self, service_id: str) -> Path:

		return pids_dir() / f'{service_id}.pid'



	def log_file(self, service_id: str) -> Path:

		return logs_dir() / f'{service_id}.log'



	def is_managed_running(self, service_id: str) -> bool:

		with self._lock:

			proc = self._processes.get(service_id)

			if proc is None:

				return False

			if proc.poll() is not None:

				self._processes.pop(service_id, None)

				return False

			return True



	def _popen(self, cmd: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> subprocess.Popen[Any]:

		log_path.parent.mkdir(parents=True, exist_ok=True)

		log_handle = log_path.open('a', encoding='utf-8')

		kwargs: dict[str, Any] = {

			'cwd': str(cwd),

			'env': env,

			'stdout': log_handle,

			'stderr': subprocess.STDOUT,

		}

		if sys.platform == 'win32':

			kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

		else:

			kwargs['start_new_session'] = True

		return subprocess.Popen(cmd, **kwargs)



	def _record_pid(self, service_id: str, proc: subprocess.Popen[Any]) -> None:

		with self._lock:

			self._processes[service_id] = proc

		self.pid_file(service_id).parent.mkdir(parents=True, exist_ok=True)

		self.pid_file(service_id).write_text(str(proc.pid), encoding='utf-8')



	def stop(self, service_id: str) -> None:

		with self._lock:

			proc = self._processes.pop(service_id, None)

		if proc is None:

			return

		if proc.poll() is None:

			try:

				if sys.platform == 'win32':

					proc.terminate()

				else:

					os.killpg(proc.pid, signal.SIGTERM)

			except Exception:

				proc.kill()

			try:

				proc.wait(timeout=10)

			except Exception:

				proc.kill()

		self.pid_file(service_id).unlink(missing_ok=True)



	def stop_all(self) -> None:

		for service_id in list(self._processes.keys()):

			self.stop(service_id)





def get_manager() -> NativeCompanionManager:

	global _manager

	if _manager is None:

		_manager = NativeCompanionManager()

	return _manager





def _git_clone(repo: str, dest: Path) -> tuple[bool, str]:

	if dest.exists() and any(dest.iterdir()):

		return True, ''

	dest.parent.mkdir(parents=True, exist_ok=True)

	if shutil.which('git') is None:

		return False, 'git_not_found:install_git_for_companion_setup'

	try:

		subprocess.run(

			['git', 'clone', '--depth', '1', repo, str(dest)],

			check=True,

			capture_output=True,

			text=True,

			timeout=300,

		)

		return True, ''

	except subprocess.CalledProcessError as exc:

		msg = (exc.stderr or exc.stdout or str(exc)).strip()[:240]

		return False, f'git_clone_failed:{msg}'

	except Exception as exc:

		return False, f'git_clone_failed:{type(exc).__name__}'





def _run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None, timeout: int = 900) -> tuple[int, str]:

	merged = os.environ.copy()

	if env:

		merged.update(env)

	try:

		result = subprocess.run(

			cmd,

			cwd=str(cwd),

			env=merged,

			capture_output=True,

			text=True,

			timeout=timeout,

		)

		out = ((result.stdout or '') + (result.stderr or '')).strip()[:500]

		return result.returncode, out

	except subprocess.TimeoutExpired:

		return 124, 'command_timeout'

	except Exception as exc:

		return 1, f'command_error:{type(exc).__name__}:{exc}'





def ensure_librecrawl_installed() -> tuple[bool, list[str]]:

	notes: list[str] = []

	ok, err = _git_clone(_LIBRECRAWL_REPO, librecrawl_root())

	if not ok:

		return False, [err]



	marker = companions_cache_dir() / '.librecrawl-installed'

	venv = companion_venv().resolve()
	cache_dir = companions_cache_dir().resolve()
	crawl_root = librecrawl_root().resolve()
	python = Path(sys.executable).resolve()



	if not marker.is_file():

		if not venv_python_path(venv).is_file():

			code, out = _run_cmd([str(python), '-m', 'venv', str(venv)], cwd=cache_dir)

			if code != 0:

				return False, [f'librecrawl_venv_failed:exit_{code}', out]

			if not venv_python_path(venv).is_file():

				return False, [f'librecrawl_venv_failed:python_missing:{venv_python_path(venv)}']



		venv_python = venv_python_path(venv)

		req = crawl_root / 'requirements.txt'

		code, out = _run_cmd(

			[str(venv_python), '-m', 'pip', 'install', '-r', str(req.resolve())],

			cwd=crawl_root,

			timeout=600,

		)

		if code != 0:

			return False, [f'librecrawl_pip_failed:exit_{code}', out]



		code, out = _run_cmd(

			[str(venv_python), '-m', 'playwright', 'install', 'chromium'],

			cwd=crawl_root,

			timeout=600,

		)

		if code != 0:

			notes.append(f'librecrawl_playwright_warning:exit_{code}')



		marker.write_text('ok', encoding='utf-8')

		notes.append('librecrawl_installed')



	return True, notes





def start_librecrawl_process() -> tuple[bool, list[str]]:

	notes: list[str] = []

	manager = get_manager()

	if manager.is_managed_running('librecrawl'):

		notes.append('librecrawl_already_running')

		return True, notes



	installed, install_notes = ensure_librecrawl_installed()

	notes.extend(install_notes)

	if not installed:

		return False, notes



	venv_python = venv_python_path(companion_venv().resolve())

	port = librecrawl_port()

	env = os.environ.copy()

	env.update(

		{

			'LIBRECRAWL_ROOT': str(librecrawl_root().resolve()),

			'LIBRECRAWL_PORT': str(port),

			'LOCAL_MODE': '1',

			'PYTHONIOENCODING': 'utf-8',

			'PYTHONUTF8': '1',

		}

	)

	cmd = [str(venv_python), str(_run_librecrawl_launcher().resolve())]

	try:

		proc = manager._popen(cmd, cwd=librecrawl_root().resolve(), env=env, log_path=manager.log_file('librecrawl'))

		manager._record_pid('librecrawl', proc)

	except Exception as exc:

		return False, notes + [f'librecrawl_start_failed:{type(exc).__name__}:{exc}']



	notes.append(f'librecrawl_started:pid_{proc.pid}')

	return True, notes





def start_companion_process(service_id: str) -> tuple[bool, list[str]]:

	if service_id == 'librecrawl':

		return start_librecrawl_process()

	return False, [f'unknown_companion:{service_id}']





def shutdown_companions() -> None:

	global _monitor_task

	if _monitor_task is not None and not _monitor_task.done():

		_monitor_task.cancel()

	get_manager().stop_all()





def register_companion_shutdown() -> None:

	global _shutdown_registered

	if _shutdown_registered:

		return

	_shutdown_registered = True

	atexit.register(shutdown_companions)





async def _monitor_loop() -> None:

	from navigation.seo_intelligence.setup.companion_services import (

		auto_start_enabled,

		probe_librecrawl,

	)



	manager = get_manager()

	while True:

		try:

			await asyncio.sleep(_MONITOR_INTERVAL_S)

			if not auto_start_enabled():

				continue

			status = await probe_librecrawl()

			if status.healthy:

				continue

			if manager.is_managed_running('librecrawl'):

				manager.stop('librecrawl')

			await asyncio.to_thread(start_companion_process, 'librecrawl')

		except asyncio.CancelledError:

			break

		except Exception as exc:

			logger.warning('companion_monitor_error:%s', exc)





def ensure_monitor_started() -> None:

	global _monitor_task

	register_companion_shutdown()

	try:

		loop = asyncio.get_running_loop()

	except RuntimeError:

		return

	if _monitor_task is not None and not _monitor_task.done():

		return

	_monitor_task = loop.create_task(_monitor_loop())


