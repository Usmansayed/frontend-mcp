"""Ephemeral medium-quality resource preview blobs — session-scoped, auto-expire."""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from navigation.resource_intelligence.tools.media_urls import (
	MEDIUM_JPEG_QUALITY,
	MEDIUM_MAX_WIDTH,
	is_http_url,
	is_local_image_ref,
	normalize_asset_url,
	to_medium_preview_url,
)


def _blob_root() -> Path:
	return Path(os.environ.get('RESOURCE_BLOB_ROOT', '.cache/resource_blobs'))


def _sessions_path() -> Path:
	return Path(os.environ.get('RESOURCE_SESSIONS_CACHE', '.cache/resource_sessions.json'))


def _default_ttl_s() -> float:
	hours = float(os.environ.get('RESOURCE_BLOB_TTL_HOURS', os.environ.get('INSPIRATION_BLOB_TTL_HOURS', '24')))
	return hours * 3600.0


def _slugify(text: str, *, max_len: int = 48) -> str:
	slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
	return slug[:max_len] or 'asset'


class ResourceBlobStore:
	"""Temporary resource previews for agents — deleted on session end or TTL."""

	def __init__(self) -> None:
		self._root = _blob_root()
		self._sessions_file = _sessions_path()
		self._ttl_s = _default_ttl_s()

	def create_session(self, *, purpose: str = '') -> str:
		self.cleanup_expired()
		session_id = f'res_{uuid.uuid4().hex[:12]}'
		session_dir = self._root / session_id
		session_dir.mkdir(parents=True, exist_ok=True)
		now = time.time()
		state = self._load_sessions()
		state[session_id] = {
			'purpose': purpose,
			'created_at': now,
			'expires_at': now + self._ttl_s,
			'blobs': [],
		}
		self._save_sessions(state)
		return session_id

	def materialize(
		self,
		session_id: str,
		*,
		preview_url: str,
		access_url: str,
		provider_id: str,
		resource_id: str,
		title: str,
		format_hint: str = '',
	) -> str | None:
		state = self._load_sessions()
		if session_id not in state:
			raise KeyError(f'resource_session_not_found:{session_id}')

		session_dir = self._root / session_id
		session_dir.mkdir(parents=True, exist_ok=True)

		medium_url = to_medium_preview_url(
			normalize_asset_url(preview_url) or normalize_asset_url(access_url),
			provider_id=provider_id,
			format_hint=format_hint,
		)
		if not medium_url:
			return None

		stem = _slugify(f'{provider_id}-{resource_id or title}')
		dest = session_dir / f'{stem}.jpg'

		raw: bytes | None = None
		if is_local_image_ref(medium_url):
			path = Path(medium_url)
			if medium_url.startswith('file://'):
				from urllib.parse import unquote, urlparse

				path = Path(unquote(urlparse(medium_url).path))
			if path.is_file():
				raw = path.read_bytes()
		elif is_http_url(medium_url):
			raw = self._fetch_bytes(medium_url, referer=access_url)

		if not raw:
			return None

		blob_path = self._write_blob(raw, dest)
		if not blob_path:
			return None

		rel = str(blob_path.resolve()).replace('\\', '/')
		now = time.time()
		state[session_id]['blobs'].append(
			{
				'blob_path': rel,
				'resource_id': resource_id,
				'provider_id': provider_id,
				'source_url': medium_url,
				'created_at': now,
			}
		)
		state[session_id]['expires_at'] = now + self._ttl_s
		self._save_sessions(state)
		return rel

	def materialize_hits(self, session_id: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
		materialized = 0
		skipped = 0
		failed = 0
		for hit in hits:
			if hit.get('blob_skipped'):
				skipped += 1
				continue
			blob = self.materialize(
				session_id,
				preview_url=str(hit.get('preview_url') or ''),
				access_url=str(hit.get('access_url') or ''),
				provider_id=str(hit.get('provider_id') or ''),
				resource_id=str(hit.get('resource_id') or ''),
				title=str(hit.get('title') or ''),
				format_hint=str(hit.get('format') or ''),
			)
			if blob:
				hit['resource_blob'] = blob
				hit['blob_session_id'] = session_id
				state = self._load_sessions()
				exp = state.get(session_id, {}).get('expires_at', time.time() + self._ttl_s)
				hit['blob_expires_at'] = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
				materialized += 1
			else:
				failed += 1
		return {
			'materialized': materialized,
			'skipped': skipped,
			'failed': failed,
			'session_id': session_id,
		}

	def end_session(self, session_id: str) -> int:
		state = self._load_sessions()
		removed = 0
		session_dir = self._root / session_id
		if session_dir.is_dir():
			shutil.rmtree(session_dir, ignore_errors=True)
			removed = 1
		if session_id in state:
			del state[session_id]
			self._save_sessions(state)
		return removed

	def cleanup_expired(self) -> int:
		state = self._load_sessions()
		now = time.time()
		removed = 0
		for session_id, meta in list(state.items()):
			if float(meta.get('expires_at', 0)) > now:
				continue
			self.end_session(session_id)
			removed += 1
		return removed

	def _fetch_bytes(self, url: str, *, referer: str) -> bytes | None:
		try:
			headers = {'User-Agent': 'Mozilla/5.0'}
			if referer:
				headers['Referer'] = referer
			req = urllib.request.Request(url, headers=headers)
			with urllib.request.urlopen(req, timeout=45) as resp:
				return resp.read()
		except Exception:
			return None

	def _write_blob(self, raw: bytes, dest: Path) -> Path | None:
		head = raw[:256].lstrip()
		if head.startswith(b'<svg') or head.startswith(b'<?xml'):
			svg_dest = dest.with_suffix('.svg')
			svg_dest.parent.mkdir(parents=True, exist_ok=True)
			svg_dest.write_bytes(raw)
			return svg_dest if svg_dest.stat().st_size > 0 else None
		if self._write_medium_jpeg(raw, dest):
			return dest
		return None

	def _write_medium_jpeg(self, raw: bytes, dest: Path) -> bool:
		try:
			from PIL import Image

			img = Image.open(BytesIO(raw))
			if img.mode not in ('RGB', 'L'):
				img = img.convert('RGB')
			w, h = img.size
			if w > MEDIUM_MAX_WIDTH:
				new_h = max(1, int(h * (MEDIUM_MAX_WIDTH / w)))
				img = img.resize((MEDIUM_MAX_WIDTH, new_h), Image.Resampling.LANCZOS)
			dest.parent.mkdir(parents=True, exist_ok=True)
			img.save(dest, format='JPEG', quality=MEDIUM_JPEG_QUALITY, optimize=True)
			return dest.stat().st_size > 0
		except Exception:
			return False

	def _load_sessions(self) -> dict[str, Any]:
		path = self._sessions_file
		if not path.exists():
			return {}
		try:
			data = json.loads(path.read_text(encoding='utf-8'))
			return data if isinstance(data, dict) else {}
		except json.JSONDecodeError:
			return {}

	def _save_sessions(self, state: dict[str, Any]) -> None:
		self._sessions_file.parent.mkdir(parents=True, exist_ok=True)
		self._sessions_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
