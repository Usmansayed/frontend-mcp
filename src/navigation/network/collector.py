"""CDP Network event collector."""
from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

from navigation.perception.cdp_hub import (
	CDP_LOADING_FAILED,
	CDP_LOADING_FINISHED,
	CDP_REQUEST,
	CDP_RESPONSE,
	DevInsightsHub,
)

from .buffer import NetworkRingBuffer, finalize_entry_metadata
from .cdp_parse import cdp_get, headers_to_dict, timing_duration_ms, truncate_body
from .models import NetworkEntry

logger = logging.getLogger(__name__)

DEFAULT_MAX_BODY_BYTES = 65536


class NetworkCollector:
	def __init__(
		self,
		buffer: NetworkRingBuffer,
		*,
		max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
	) -> None:
		self._buffer = buffer
		self._max_body_bytes = max_body_bytes
		self._pending: dict[str, NetworkEntry] = {}
		self._hub: DevInsightsHub | None = None
		self._client: Any = None
		self._session_id: str | None = None
		self._started = False

	async def start(self, session: Any) -> None:
		if self._started:
			return
		cdp_session = await session.get_or_create_cdp_session(target_id=None, focus=True)
		self._client = cdp_session.cdp_client
		self._session_id = cdp_session.session_id
		self._hub = await DevInsightsHub.for_session(session)
		await self._hub.ensure_domains()
		self._hub.attach(self)
		self._started = True

	def stop(self) -> None:
		if self._started and self._hub is not None:
			self._hub.detach(self)
		self._started = False
		self._hub = None
		self._client = None
		self._session_id = None
		self._pending.clear()

	async def await_pending(self, timeout: float = 5.0) -> None:
		"""Wait for in-flight requests to receive loadingFinished/loadingFailed."""
		deadline = time.monotonic() + timeout
		while self._pending and time.monotonic() < deadline:
			await asyncio.sleep(0.05)

	def _handle_cdp(self, method: str, params: Any, session_id: str | None = None) -> None:
		if method == CDP_REQUEST:
			self._on_request(params)
		elif method == CDP_RESPONSE:
			self._on_response(params)
		elif method == CDP_LOADING_FINISHED:
			self._on_loading_finished(params)
		elif method == CDP_LOADING_FAILED:
			self._on_loading_failed(params)

	def _on_request(self, params: Any) -> None:
		request_id = str(cdp_get(params, 'requestId') or '')
		if not request_id:
			return
		req = cdp_get(params, 'request') or {}
		url = str(cdp_get(req, 'url') or '')
		method = str(cdp_get(req, 'method') or 'GET')
		post_data = cdp_get(req, 'postData')
		headers = headers_to_dict(cdp_get(req, 'headers'))
		redirect = cdp_get(params, 'redirectResponse') or {}
		redirect_urls: list[str] = []
		if redirect:
			red_url = str(cdp_get(redirect, 'url') or '')
			if red_url:
				redirect_urls.append(red_url)
		entry = NetworkEntry(
			request_id=request_id,
			url=url,
			method=method,
			started_at=time.time(),
			request_headers=headers,
			request_body=str(post_data) if post_data else None,
			redirect_urls=redirect_urls,
			resource_type=str(cdp_get(params, 'type') or ''),
		)
		if entry.request_body:
			entry.request_body, entry.request_body_truncated = truncate_body(
				entry.request_body,
				self._max_body_bytes,
			)
		self._pending[request_id] = entry

	def _on_response(self, params: Any) -> None:
		request_id = str(cdp_get(params, 'requestId') or '')
		entry = self._pending.get(request_id)
		if entry is None:
			return
		response = cdp_get(params, 'response') or {}
		status = cdp_get(response, 'status')
		entry.status = int(status) if status is not None else None
		entry.status_text = str(cdp_get(response, 'statusText') or '')
		entry.mime_type = str(cdp_get(response, 'mimeType') or '')
		entry.response_headers = headers_to_dict(cdp_get(response, 'headers'))
		resp_url = str(cdp_get(response, 'url') or '')
		if resp_url:
			entry.url = resp_url
		timing = timing_duration_ms(cdp_get(response, 'timing'))
		if timing is not None:
			entry.duration_ms = timing

	def _finalize(self, request_id: str, *, failed: bool = False, error_text: str = '', canceled: bool = False) -> None:
		entry = self._pending.pop(request_id, None)
		if entry is None:
			return
		entry.ended_at = time.time()
		if entry.duration_ms is None and entry.started_at:
			entry.duration_ms = max(0.0, (entry.ended_at - entry.started_at) * 1000.0)
		entry.failed = failed
		entry.canceled = canceled
		entry.error_text = error_text
		finalize_entry_metadata(entry)
		self._buffer.add(entry)

	def _on_loading_finished(self, params: Any) -> None:
		request_id = str(cdp_get(params, 'requestId') or '')
		self._finalize(request_id)

	def _on_loading_failed(self, params: Any) -> None:
		request_id = str(cdp_get(params, 'requestId') or '')
		canceled = bool(cdp_get(params, 'canceled'))
		if canceled:
			self._finalize(request_id, canceled=True)
			return
		error_text = str(cdp_get(params, 'errorText') or 'loading failed')
		self._finalize(request_id, failed=True, error_text=error_text)

	async def enrich_bodies(self, entries: list[NetworkEntry]) -> None:
		if not self._client or not self._session_id:
			return
		for entry in entries:
			if entry.response_body is not None:
				continue
			if entry.failed and entry.status is None:
				continue
			try:
				result = await self._client.send.Network.getResponseBody(
					params={'requestId': entry.request_id},
					session_id=self._session_id,
				)
				body = str(cdp_get(result, 'body') or '')
				if bool(cdp_get(result, 'base64Encoded')):
					body = base64.b64decode(body).decode('utf-8', errors='replace')
				entry.response_body, entry.response_body_truncated = truncate_body(body, self._max_body_bytes)
			except Exception:
				logger.debug('getResponseBody failed for %s', entry.request_id, exc_info=True)
			if entry.request_body is None:
				try:
					post = await self._client.send.Network.getRequestPostData(
						params={'requestId': entry.request_id},
						session_id=self._session_id,
					)
					text = str(cdp_get(post, 'postData') or '')
					if text:
						entry.request_body, entry.request_body_truncated = truncate_body(
							text,
							self._max_body_bytes,
						)
				except Exception:
					pass
			finalize_entry_metadata(entry)
