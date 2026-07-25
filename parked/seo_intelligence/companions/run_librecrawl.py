"""LibreCrawl native launcher — serves on LIBRECRAWL_PORT (default 5001)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_stdio() -> None:
	"""Windows cp1252 consoles crash on LibreCrawl's unicode log lines."""
	os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
	os.environ.setdefault('PYTHONUTF8', '1')
	for stream in (sys.stdout, sys.stderr):
		reconfigure = getattr(stream, 'reconfigure', None)
		if callable(reconfigure):
			try:
				reconfigure(encoding='utf-8', errors='replace')
			except Exception:
				pass


def main() -> None:
	_configure_stdio()
	port = int(os.environ.get('LIBRECRAWL_PORT', '5001'))
	root = Path(os.environ.get('LIBRECRAWL_ROOT', '.')).resolve()
	sys.path.insert(0, str(root))
	os.chdir(root)

	# Import after cwd is set so LibreCrawl relative paths resolve.
	import main as librecrawl_main  # noqa: PLC0415
	from waitress import serve  # noqa: PLC0415

	librecrawl_main.recover_crashed_crawls()
	librecrawl_main.start_cleanup_thread()
	serve(librecrawl_main.app, host='127.0.0.1', port=port, threads=8)


if __name__ == '__main__':
	main()