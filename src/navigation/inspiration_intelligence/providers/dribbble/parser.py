"""Parse Dribbble search HTML into inspiration hits."""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin

_SHOT_HREF = re.compile(r'href="(https?://dribbble\.com/shots/(\d+)[^"]*|/shots/(\d+)[^"]*)"', re.IGNORECASE)
_ARIA_TITLE = re.compile(r'aria-label="View\s+([^"]+)"', re.IGNORECASE)
_IMG_SRC = re.compile(r'<img[^>]+src="([^"]+cdn\.dribbble\.com[^"]+)"', re.IGNORECASE)


@dataclass(slots=True)
class DribbbleHit:
	shot_id: str
	title: str
	url: str
	preview_url: str = ''


def query_to_slug(text: str) -> str:
	slug = text.strip().lower()
	slug = re.sub(r'[^a-z0-9\s-]', '', slug)
	slug = re.sub(r'\s+', '-', slug)
	return slug or 'design'


def parse_search_html(html: str, *, base_url: str = 'https://dribbble.com') -> list[DribbbleHit]:
	"""Extract shot cards from search page HTML (navigation knowledge only)."""
	seen: set[str] = set()
	hits: list[DribbbleHit] = []

	for match in _SHOT_HREF.finditer(html):
		groups = match.groups()
		shot_id = groups[1] or groups[2]
		path = groups[0]
		if not shot_id:
			continue
		if shot_id in seen:
			continue
		seen.add(shot_id)

		window_start = max(0, match.start() - 400)
		window_end = min(len(html), match.end() + 400)
		window = html[window_start:window_end]

		title = _extract_title(window) or _title_from_path(path) or f'Shot {shot_id}'
		preview = _extract_preview(window)
		url = urljoin(base_url, path.split('"')[0] if '"' in path else path)

		hits.append(
			DribbbleHit(
				shot_id=shot_id,
				title=unescape(title),
				url=url,
				preview_url=preview,
			)
		)

	return hits


def _title_from_path(path: str) -> str:
	# /shots/25447833-AI-Content-Generator-SaaS-Dashboard
	slug = path.split('/shots/', 1)[-1].split('"')[0].split('?')[0]
	slug = re.sub(r'^\d+-?', '', slug)
	return unescape(slug.replace('-', ' ').strip())


def _extract_title(fragment: str) -> str:
	aria = _ARIA_TITLE.search(fragment)
	if aria:
		return aria.group(1).strip()
	return ''


def _extract_preview(fragment: str) -> str:
	img = _IMG_SRC.search(fragment)
	return unescape(img.group(1)) if img else ''
