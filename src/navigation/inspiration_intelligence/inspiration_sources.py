"""Load curated inspiration source registry (galleries + demo screenshot targets)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_CORPUS_PATH = Path(__file__).resolve().parent / 'data' / 'inspiration_sources_corpus.json'


@lru_cache(maxsize=1)
def load_inspiration_sources_corpus() -> dict[str, Any]:
	if not _CORPUS_PATH.is_file():
		return {'schema': 'inspiration_sources_corpus.v1', 'categories': {}, 'planner_defaults': {}}
	return json.loads(_CORPUS_PATH.read_text(encoding='utf-8'))


def select_screenshot_demos(
	*,
	intent_text: str = '',
	categories: list[str] | None = None,
	max_demos: int = 2,
) -> list[dict[str, str]]:
	"""Pick showcase/demo URLs for exclusive-browser viewport capture."""
	corpus = load_inspiration_sources_corpus()
	cats = corpus.get('categories') or {}
	want = categories or ['component_showcase', 'motion_showcase', 'landing_gallery']
	text = (intent_text or '').lower()
	picked: list[dict[str, str]] = []
	seen: set[str] = set()

	for cat in want:
		bucket = cats.get(cat) or {}
		for src in bucket.get('sources') or []:
			tier = str(src.get('tier') or '')
			if tier not in {'screenshot_demo', 'browser_gallery'} and cat not in {
				'component_showcase',
				'motion_showcase',
			}:
				continue
			if tier == 'research_only':
				continue
			hints = [str(h).lower() for h in (bucket.get('intent_hints') or [])]
			if text and hints and not any(h in text for h in hints):
				# Soft filter — still allow if no strong mismatch and we need fillers
				if cat in {'component_showcase', 'motion_showcase'} and any(
					k in text for k in ('component', 'animation', 'motion', 'ui', 'landing', 'saas')
				):
					pass
				elif cat not in {'component_showcase', 'motion_showcase'}:
					continue
			demos = list(src.get('demo_urls') or [])
			if not demos:
				demos = [str(src.get('url') or '')]
			for demo in demos[:1]:
				if not demo or demo in seen:
					continue
				seen.add(demo)
				picked.append(
					{
						'id': str(src.get('id') or ''),
						'url': demo,
						'title': str(src.get('title') or src.get('id') or ''),
						'category': cat,
						'source_kind': 'screenshot_demo',
						'tier': tier or 'screenshot_demo',
					}
				)
				if len(picked) >= max_demos:
					return picked
	return picked


def list_candidate_providers() -> list[str]:
	corpus = load_inspiration_sources_corpus()
	return list(corpus.get('next_provider_candidates') or [])
