"""On-demand inspiration asset downloader — agents use URLs first, download when needed."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from navigation.inspiration_intelligence.tools.media_urls import (
	image_extension,
	is_http_url,
	normalize_image_url,
	to_medium_inspiration_url,
)


def slugify(text: str, *, max_len: int = 60) -> str:
	slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
	return slug[:max_len] or 'untitled'


def download_url(
	url: str,
	dest: Path,
	*,
	referer: str = '',
	root: Path | None = None,
) -> bool:
	"""Download http(s) image or copy local perception screenshot to dest."""
	url = normalize_image_url(url)
	if not url:
		return False
	dest.parent.mkdir(parents=True, exist_ok=True)
	if dest.exists() and dest.stat().st_size > 0:
		return True

	# Local perception screenshot
	for candidate in (Path(url), *( [root / url] if root else [] )):
		if candidate.is_file() and candidate.stat().st_size > 0:
			dest.write_bytes(candidate.read_bytes())
			return True

	if not is_http_url(url):
		return False

	try:
		headers = {'User-Agent': 'Mozilla/5.0'}
		if referer:
			headers['Referer'] = referer
		req = urllib.request.Request(url, headers=headers)
		with urllib.request.urlopen(req, timeout=45) as resp:
			data = resp.read()
		if not data:
			return False
		dest.write_bytes(data)
		return True
	except Exception:
		return False


def download_manifest(
	manifest_path: Path,
	output_dir: Path | None = None,
	*,
	only_missing: bool = True,
	medium: bool = False,
) -> dict[str, Any]:
	"""Download preview images referenced in a collection manifest."""
	manifest_path = manifest_path.resolve()
	data = json.loads(manifest_path.read_text(encoding='utf-8'))
	base = output_dir or manifest_path.parent
	hits: list[dict[str, Any]] = list(data.get('hits') or [])
	downloaded = 0
	failed = 0

	for hit in hits:
		provider = str(hit.get('provider_id') or 'unknown')
		preview = normalize_image_url(str(hit.get('preview_url') or ''))
		if medium:
			preview = to_medium_inspiration_url(preview, provider_id=provider) or preview
		page_url = str(hit.get('url') or '')
		if not preview and not hit.get('local_image'):
			failed += 1
			continue

		title = str(hit.get('title') or hit.get('external_id') or 'item')
		provider_dir = base / provider
		provider_dir.mkdir(exist_ok=True)

		local_rel = str(hit.get('local_image') or '')
		dest = base / local_rel if local_rel else None
		if dest is None:
			existing = list(provider_dir.glob(f'*-{slugify(title)}.*'))
			if existing and only_missing:
				hit['local_image'] = str(existing[0].relative_to(base)).replace('\\', '/')
				continue
			ext = image_extension(preview)
			idx = hit.get('candidate_id', title).split(':')[-1][:8]
			dest = provider_dir / f'{slugify(title)}{ext}'

		if only_missing and dest.exists() and dest.stat().st_size > 0:
			hit['local_image'] = str(dest.relative_to(base)).replace('\\', '/')
			continue

		ok = download_url(preview, dest, referer=page_url, root=base)
		if ok:
			hit['local_image'] = str(dest.relative_to(base)).replace('\\', '/')
			downloaded += 1
		else:
			failed += 1

	data['hits'] = hits
	data['total_images'] = sum(1 for h in hits if h.get('local_image'))
	data['download_summary'] = {'downloaded': downloaded, 'failed': failed}
	manifest_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
	return data['download_summary']
