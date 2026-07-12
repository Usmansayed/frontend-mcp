"""Codebase bridge — map SEO issues to likely source files (Sprint 2)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from navigation.seo_intelligence.evidence.identity import normalize_page_url
from navigation.seo_intelligence.models import SeoEvidenceRef

_SKIP_DIRS = frozenset({
	'node_modules', '.git', 'dist', 'build', '.next', '.nuxt', 'coverage',
	'__pycache__', '.perception', 'vendor', '.turbo', '.cache', 'artifacts',
})
_PAGE_EXTENSIONS = frozenset({'.tsx', '.jsx', '.vue', '.svelte', '.html', '.mdx'})
_METADATA_MARKERS = ('metadata', 'metatags', '<title', 'meta name=', 'og:title', 'canonical')
_RENDER_MARKERS = ('use client', 'hydrate', 'createRoot', 'hydration')


def build_codebase_hints(
	evidence: list[SeoEvidenceRef],
	*,
	page_url: str,
	repo_root: str = '',
	base_url: str = '',
) -> list[dict[str, Any]]:
	"""Heuristic file hints — optional CRG search when available."""
	if not repo_root.strip():
		return []

	root = Path(repo_root)
	if not root.is_dir():
		return []

	segment = _url_path_segment(page_url, base_url=base_url)
	keywords = _keywords_from_evidence(evidence)
	hints: list[dict[str, Any]] = []
	seen: set[str] = set()

	for path in _candidate_files(root, segment):
		rel = str(path.relative_to(root)).replace('\\', '/')
		if rel in seen:
			continue
		score, reasons = _score_file(path, segment=segment, keywords=keywords, evidence=evidence)
		if score < 0.35:
			continue
		seen.add(rel)
		hints.append({
			'file': rel,
			'score': round(score, 3),
			'reasons': reasons,
			'source': 'heuristic',
		})

	hints.extend(_crg_hints(repo_root, segment, keywords))
	hints.sort(key=lambda h: -float(h.get('score') or 0))
	return hints[:8]


def _crg_hints(repo_root: str, segment: str, keywords: list[str]) -> list[dict[str, Any]]:
	query = ' '.join([segment, *keywords[:3]]).strip()
	if not query:
		return []
	try:
		from navigation.codebase_intelligence.service import CodebaseIntelligenceService

		service = CodebaseIntelligenceService(Path(repo_root))
		result = service.graph.search(query, limit=5)
	except Exception:
		return []
	if not result.ok:
		return []

	hints: list[dict[str, Any]] = []
	for node in (result.payload.get('nodes') or result.payload.get('results') or [])[:5]:
		if not isinstance(node, dict):
			continue
		path = str(node.get('path') or node.get('file') or node.get('id') or '')
		if not path:
			continue
		hints.append({
			'file': path,
			'score': 0.55,
			'reasons': ['code_review_graph semantic match'],
			'source': 'crg',
		})
	return hints


def _url_path_segment(page_url: str, *, base_url: str = '') -> str:
	url = normalize_page_url(page_url, base_url=base_url) or page_url
	parsed = urlparse(url if '://' in url else f'https://{url}')
	parts = [p for p in parsed.path.split('/') if p and p not in {'index', 'page'}]
	return parts[-1] if parts else ''


def _keywords_from_evidence(evidence: list[SeoEvidenceRef]) -> list[str]:
	words: list[str] = []
	for item in evidence:
		title = item.title.lower()
		if any(k in title for k in ('meta', 'title', 'description', 'canonical')):
			words.extend(['metadata', 'layout', 'head'])
		if item.kind.value == 'rendering_issue':
			words.extend(['component', 'page', 'layout'])
		if 'schema' in title or item.kind.value == 'schema':
			words.append('schema')
		if item.kind.value == 'core_web_vital':
			words.extend(['image', 'font', 'lazy'])
	return list(dict.fromkeys(w for w in words if w))


def _candidate_files(root: Path, segment: str) -> list[Path]:
	candidates: list[Path] = []
	if segment:
		for pattern in (
			f'**/{segment}/page.tsx',
			f'**/{segment}/page.jsx',
			f'**/{segment}.tsx',
			f'**/{segment}.jsx',
			f'**/pages/{segment}.*',
			f'**/app/**/{segment}/**',
		):
			candidates.extend(root.glob(pattern))

	for path in root.rglob('*'):
		if not path.is_file():
			continue
		if path.suffix.lower() not in _PAGE_EXTENSIONS:
			continue
		if any(part in _SKIP_DIRS for part in path.parts):
			continue
		if segment and segment.lower() in path.as_posix().lower():
			candidates.append(path)
		elif not segment and ('layout' in path.name.lower() or 'page' in path.name.lower()):
			candidates.append(path)
		if len(candidates) >= 40:
			break
	return candidates


def _score_file(
	path: Path,
	*,
	segment: str,
	keywords: list[str],
	evidence: list[SeoEvidenceRef],
) -> tuple[float, list[str]]:
	try:
		text = path.read_text(encoding='utf-8', errors='ignore').lower()
	except OSError:
		return 0.0, []

	score = 0.2
	reasons: list[str] = []
	rel = path.as_posix().lower()

	if segment and segment.lower() in rel:
		score += 0.35
		reasons.append(f'path matches /{segment}')

	for kw in keywords:
		if kw in text:
			score += 0.08
			reasons.append(f'contains {kw}')

	if any(m in text for m in _METADATA_MARKERS):
		score += 0.15
		reasons.append('metadata patterns')
	if any(m in text for m in _RENDER_MARKERS):
		score += 0.1
		reasons.append('client render patterns')

	if any(e.kind.value == 'rendering_issue' for e in evidence):
		if 'error' in text or 'console' in text:
			score += 0.05

	return min(1.0, score), reasons[:4]
