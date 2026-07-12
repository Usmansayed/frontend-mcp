"""Temporary localhost OAuth callback server — internal to SEO Intelligence."""
from __future__ import annotations

import asyncio
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from navigation.seo_intelligence.config.defaults import oauth_callback_host, oauth_callback_port

_SUCCESS_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>SEO Intelligence</title></head>
<body style="font-family:system-ui,sans-serif;text-align:center;padding:3rem">
<h1>Connected</h1>
<p>Authentication succeeded. You can close this window and return to your agent.</p>
</body>
</html>"""

_ERROR_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>SEO Intelligence</title></head>
<body style="font-family:system-ui,sans-serif;text-align:center;padding:3rem">
<h1>Authentication failed</h1>
<p>{message}</p>
</body>
</html>"""


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
	callback_path: str = '/'
	loop: asyncio.AbstractEventLoop | None = None
	future: asyncio.Future[str] | None = None

	def do_GET(self) -> None:
		parsed = urlparse(self.path)
		if parsed.path != self.callback_path:
			self.send_error(404)
			return
		params = parse_qs(parsed.query)
		if 'error' in params:
			error = params['error'][0]
			description = params.get('error_description', [''])[0]
			message = description or error
			self._send_html(_ERROR_HTML.format(message=message), status=400)
			self._fail(RuntimeError(f'oauth_error:{error}'))
			return
		code = str(params.get('code', [''])[0] or '').strip()
		if not code:
			self._send_html(_ERROR_HTML.format(message='Missing authorization code.'), status=400)
			self._fail(RuntimeError('oauth_missing_code'))
			return
		self._send_html(_SUCCESS_HTML)
		self._succeed(code)

	def _send_html(self, body: str, *, status: int = 200) -> None:
		payload = body.encode('utf-8')
		self.send_response(status)
		self.send_header('Content-Type', 'text/html; charset=utf-8')
		self.send_header('Content-Length', str(len(payload)))
		self.end_headers()
		self.wfile.write(payload)

	def _succeed(self, code: str) -> None:
		if self.loop is not None and self.future is not None and not self.future.done():
			self.loop.call_soon_threadsafe(self.future.set_result, code)

	def _fail(self, exc: Exception) -> None:
		if self.loop is not None and self.future is not None and not self.future.done():
			self.loop.call_soon_threadsafe(self.future.set_exception, exc)

	def log_message(self, format: str, *args: Any) -> None:
		return


def _callback_timeout_s() -> float:
	raw = os.environ.get('SEO_OAUTH_CALLBACK_TIMEOUT_S', '300').strip()
	try:
		return max(30.0, float(raw))
	except ValueError:
		return 300.0


async def await_oauth_callback(
	*,
	callback_path: str,
	port: int | None = None,
	host: str | None = None,
) -> tuple[str, str]:
	"""Block until OAuth provider redirects to callback_path. Returns (code, redirect_uri)."""
	loop = asyncio.get_running_loop()
	bind_host = host or oauth_callback_host()
	bind_port = port if port is not None else oauth_callback_port()
	future: asyncio.Future[str] = loop.create_future()
	handler_cls = type(
		'_BoundOAuthHandler',
		(_OAuthCallbackHandler,),
		{'callback_path': callback_path, 'loop': loop, 'future': future},
	)
	httpd = HTTPServer((bind_host, bind_port), handler_cls)
	redirect_uri = f'http://localhost:{bind_port}{callback_path}'

	def serve_once() -> None:
		try:
			httpd.handle_request()
		except Exception as exc:
			if not future.done():
				loop.call_soon_threadsafe(future.set_exception, exc)

	thread = threading.Thread(target=serve_once, daemon=True)
	thread.start()
	await asyncio.sleep(0.05)
	try:
		code = await asyncio.wait_for(future, timeout=_callback_timeout_s())
	except asyncio.TimeoutError as exc:
		raise RuntimeError('oauth_callback_timeout') from exc
	finally:
		thread.join(timeout=2.0)
		try:
			httpd.server_close()
		except Exception:
			pass
	return code, redirect_uri


async def run_browser_oauth(
	*,
	authorization_url: str,
	callback_path: str,
	port: int | None = None,
	open_browser: bool = True,
) -> tuple[str, str]:
	"""Open browser (optional), wait for localhost callback, return (code, redirect_uri)."""
	loop = asyncio.get_running_loop()
	wait_task = asyncio.create_task(
		await_oauth_callback(callback_path=callback_path, port=port),
	)
	await asyncio.sleep(0.1)
	if open_browser:
		await loop.run_in_executor(None, webbrowser.open, authorization_url)
	code, redirect_uri = await wait_task
	return code, redirect_uri
