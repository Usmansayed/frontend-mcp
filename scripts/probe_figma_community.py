"""Probe Figma Community search — research script."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

SEARCH_URL = 'https://www.figma.com/community/search'


def fetch_search_html(query: str) -> str:
	params = urllib.parse.urlencode(
		{'query': query, 'sort_by': 'relevancy', 'file_type': 'ui', 'page': '1'}
	)
	url = f'{SEARCH_URL}?{params}'
	req = urllib.request.Request(
		url,
		headers={
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
			'Accept': 'text/html,application/json',
		},
	)
	with urllib.request.urlopen(req, timeout=30) as r:
		return r.read().decode('utf-8', 'replace')


def extract_json_blobs(html: str) -> list[dict]:
	blobs: list[dict] = []
	for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S):
		try:
			blobs.append(json.loads(m.group(1)))
		except json.JSONDecodeError:
			continue
	return blobs


if __name__ == '__main__':
	html = fetch_search_html('dashboard')
	print('html_len', len(html))
	blobs = extract_json_blobs(html)
	print('json_blobs', len(blobs))
	for i, blob in enumerate(blobs[:5]):
		print('blob', i, type(blob), str(blob)[:200] if not isinstance(blob, dict) else list(blob.keys())[:15])


