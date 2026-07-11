"""Ephemeral medium-quality inspiration blobs — session-scoped, auto-expire."""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from navigation.inspiration_intelligence.tools.media_urls import (
	MEDIUM_JPEG_QUALITY,
	MEDIUM_MAX_WIDTH,
	is_http_url,
	is_local_image_ref,
	normalize_image_url,
	to_medium_inspiration_url,
)


def _blob_root() -> Path:
	return Path(os.environ.get('INSPIRATION_BLOB_ROOT', '.cache/inspiration_blobs'))


def _sessions_path() -> Path:
	return Path(os.environ.get('INSPIRATION_SESSIONS_CACHE', '.cache/inspiration_sessions.json'))


def _default_ttl_s() -> float:
	hours = float(os.environ.get('INSPIRATION_BLOB_TTL_HOURS', '24'))
	return hours * 3600.0


def _slugify(text: str, *, max_len: int = 48) -> str:
	slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
	return slug[:max_len] or 'item'


@dataclass(slots=True)
class BlobRecord:
	session_id: str
	blob_path: str
	candidate_id: str
	provider_id: str
	source_url: str
	created_at: float
	expires_at: float


class InspirationBlobStore:
	"""Temporary inspiration images for agents — deleted on session end or TTL."""

	def __init__(self) -> None:
		self._root = _blob_root()
		self._sessions_file = _sessions_path()
		self._ttl_s = _default_ttl_s()

	def create_session(self, *, purpose: str = '') -> str:
		self.cleanup_expired()
		session_id = f'insp_{uuid.uuid4().hex[:12]}'
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
		page_url: str,
		provider_id: str,
		candidate_id: str,
		title: str,
		screenshot_path: str = '',
	) -> str | None:
		"""Download or copy a medium-quality JPEG into the session blob dir."""
		state = self._load_sessions()
		if session_id not in state:
			raise KeyError(f'inspiration_session_not_found:{session_id}')

		session_dir = self._root / session_id
		session_dir.mkdir(parents=True, exist_ok=True)

		medium_url = to_medium_inspiration_url(
			normalize_image_url(preview_url),
			provider_id=provider_id,
		)
		source = medium_url or normalize_image_url(preview_url) or screenshot_path
		if not source:
			return None
		if provider_id == 'land-book' and 'og-image' in source:
			return None

		stem = _slugify(f'{provider_id}-{candidate_id or title}')
		dest = session_dir / f'{stem}.jpg'

		raw: bytes | None = None
		if is_local_image_ref(source):
			path = Path(source)
			if source.startswith('file://'):
				from urllib.parse import unquote, urlparse

				path = Path(unquote(urlparse(source).path))
			if path.is_file():
				raw = path.read_bytes()
		elif is_http_url(source):
			raw = self._fetch_bytes(source, referer=page_url)

		if not raw:
			return None

		if not self._write_medium_jpeg(raw, dest):
			return None

		rel = str(dest.resolve()).replace('\\', '/')
		now = time.time()
		record = {
			'blob_path': rel,
			'candidate_id': candidate_id,
			'provider_id': provider_id,
			'source_url': source,
			'created_at': now,
		}
		state[session_id]['blobs'].append(record)
		state[session_id]['expires_at'] = now + self._ttl_s
		self._save_sessions(state)
		return rel

	def materialize_hits(self, session_id: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
		"""Materialize blobs for manifest hit dicts; mutates hits with inspiration_blob fields."""
		materialized = 0
		failed = 0
		for hit in hits:
			blob = self.materialize(
				session_id,
				preview_url=str(hit.get('preview_url') or ''),
				page_url=str(hit.get('url') or ''),
				provider_id=str(hit.get('provider_id') or ''),
				candidate_id=str(hit.get('candidate_id') or ''),
				title=str(hit.get('title') or ''),
				screenshot_path=str(hit.get('screenshot_path') or ''),
			)
			if blob:
				hit['inspiration_blob'] = blob
				hit['blob_session_id'] = session_id
				state = self._load_sessions()
				exp = state.get(session_id, {}).get('expires_at', time.time() + self._ttl_s)
				hit['blob_expires_at'] = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
				materialized += 1
			else:
				failed += 1
		return {'materialized': materialized, 'failed': failed, 'session_id': session_id}

	def materialize_manifest(self, session_id: str, manifest_path: Path) -> dict[str, Any]:
		data = json.loads(manifest_path.read_text(encoding='utf-8'))
		hits: list[dict[str, Any]] = list(data.get('hits') or [])
		summary = self.materialize_hits(session_id, hits)
		data['hits'] = hits
		data['blob_session_id'] = session_id
		data['mode'] = 'urls_and_ephemeral_blobs'
		data['blob_summary'] = summary
		manifest_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
		return summary

	def end_session(self, session_id: str) -> int:
		"""Delete all blobs for a session (call when agent work is done)."""
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
		"""Remove sessions past TTL — safety net if Cursor closes without explicit end."""
		state = self._load_sessions()
		now = time.time()
		removed = 0
		for session_id, meta in list(state.items()):
			if float(meta.get('expires_at', 0)) > now:
				continue
			self.end_session(session_id)
			removed += 1
		return removed

	def list_sessions(self) -> list[dict[str, Any]]:
		self.cleanup_expired()
		state = self._load_sessions()
		out: list[dict[str, Any]] = []
		for sid, meta in state.items():
			out.append(
				{
					'session_id': sid,
					'purpose': meta.get('purpose', ''),
					'blob_count': len(meta.get('blobs') or []),
					'expires_at': meta.get('expires_at'),
				}
			)
		return out

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
