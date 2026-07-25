"""Keyword catalog backend — no PAT, deterministic fallback."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.figma_intelligence.discovery.community_adapter.models import CommunityDiscoveryHit
from navigation.figma_intelligence.models import PlannedCommunityQuery


@dataclass(slots=True)
class CatalogEntry:
	entry_id: str
	title: str
	description: str = ''
	file_key: str = ''
	tags: list[str] = field(default_factory=list)
	keywords: list[str] = field(default_factory=list)
	author: str = ''
	preview_image: str = ''
	community_url: str = ''
	likes: int | None = None
	downloads: int | None = None
	design_system: str = ''
	extra: dict[str, Any] = field(default_factory=dict)


DEFAULT_CATALOG: list[CatalogEntry] = [
	CatalogEntry(
		entry_id='community:saas-analytics-dashboard',
		title='SaaS Analytics Dashboard UI Kit',
		description='Modern analytics dashboard with sidebar, charts, and data tables for B2B SaaS products.',
		tags=['dashboard', 'saas', 'analytics', 'admin'],
		keywords=['dashboard', 'saas', 'analytics', 'admin panel', 'control center', 'metrics'],
		author='Community',
		design_system='analytics dashboard',
		community_url='https://www.figma.com/community/file/saas-analytics-dashboard',
		likes=4200,
		downloads=18000,
	),
	CatalogEntry(
		entry_id='community:linear-minimal-saas',
		title='Linear Style Minimal SaaS UI',
		description='Clean minimal interface inspired by Linear and Vercel — bento grids and subtle borders.',
		tags=['linear', 'minimal', 'saas', 'bento'],
		keywords=['linear', 'minimal', 'saas', 'vercel', 'clean', 'bento'],
		author='Community',
		design_system='linear minimal',
		community_url='https://www.figma.com/community/file/linear-minimal-saas',
		likes=3100,
		downloads=12000,
	),
	CatalogEntry(
		entry_id='community:fintech-crm-pipeline',
		title='Fintech CRM Pipeline Dashboard',
		description='CRM pipeline board with deal cards, contact tables, and fintech-grade data density.',
		tags=['fintech', 'crm', 'pipeline', 'table'],
		keywords=['fintech', 'crm', 'pipeline', 'sales', 'table', 'dashboard'],
		author='Community',
		design_system='fintech crm',
		community_url='https://www.figma.com/community/file/fintech-crm-pipeline',
		likes=1900,
		downloads=7500,
	),
	CatalogEntry(
		entry_id='community:ecommerce-storefront',
		title='E-commerce Storefront UI Kit',
		description='Product cards, filters, cart, and checkout flows for modern e-commerce.',
		tags=['ecommerce', 'shop', 'product', 'cart'],
		keywords=['ecommerce', 'e-commerce', 'storefront', 'shop', 'product card', 'checkout'],
		author='Community',
		design_system='ecommerce kit',
		community_url='https://www.figma.com/community/file/ecommerce-storefront',
		likes=2800,
		downloads=14000,
	),
	CatalogEntry(
		entry_id='community:glass-auth-onboarding',
		title='Glassmorphism Auth & Onboarding Flow',
		description='Login, signup, and onboarding screens with glassmorphism and soft gradients.',
		tags=['auth', 'onboarding', 'glass', 'signup'],
		keywords=['auth', 'login', 'signup', 'onboarding', 'glass', 'glassmorphism'],
		author='Community',
		design_system='glass auth',
		community_url='https://www.figma.com/community/file/glass-auth-onboarding',
		likes=1500,
		downloads=6200,
	),
]


def load_catalog() -> list[CatalogEntry]:
	raw_path = os.environ.get('FIGMA_COMMUNITY_CATALOG_JSON', '').strip()
	if not raw_path:
		return list(DEFAULT_CATALOG)
	path = Path(raw_path)
	if not path.is_file():
		return list(DEFAULT_CATALOG)
	try:
		data = json.loads(path.read_text(encoding='utf-8'))
	except (OSError, json.JSONDecodeError):
		return list(DEFAULT_CATALOG)
	entries: list[CatalogEntry] = []
	for item in data if isinstance(data, list) else []:
		if not isinstance(item, dict):
			continue
		entries.append(
			CatalogEntry(
				entry_id=str(item.get('entry_id') or item.get('candidate_id', '')),
				title=str(item.get('title', '')),
				description=str(item.get('description', '')),
				file_key=str(item.get('file_key', '')),
				tags=[str(t) for t in item.get('tags', []) if t],
				keywords=[str(k) for k in item.get('keywords', []) if k],
				author=str(item.get('author', '')),
				preview_image=str(item.get('preview_image', '')),
				community_url=str(item.get('community_url', '') or item.get('url', '')),
				likes=_optional_int(item.get('likes')),
				downloads=_optional_int(item.get('downloads')),
				design_system=str(item.get('design_system', '')),
				extra=dict(item.get('extra', {})),
			)
		)
	return entries or list(DEFAULT_CATALOG)


class CatalogBackend:
	backend_id = 'catalog'

	async def search(
		self,
		query: PlannedCommunityQuery,
		*,
		max_results: int,
	) -> tuple[list[CommunityDiscoveryHit], list[str]]:
		catalog = load_catalog()
		q_tokens = _tokenize(query.text)
		scored: list[tuple[float, CatalogEntry]] = []
		for entry in catalog:
			blob = ' '.join(
				[entry.title, entry.description, ' '.join(entry.tags), ' '.join(entry.keywords), entry.design_system]
			).lower()
			overlap = sum(1 for t in q_tokens if t in blob)
			if overlap == 0:
				continue
			score = query.confidence * (0.12 * overlap)
			if entry.likes:
				score += min(0.08, entry.likes / 100_000)
			scored.append((score, entry))

		scored.sort(key=lambda x: x[0], reverse=True)
		hits = [_entry_to_hit(entry, score) for score, entry in scored[:max_results]]
		degraded = ['catalog_backend'] if hits else ['catalog_no_matches']
		return hits, degraded


def _entry_to_hit(entry: CatalogEntry, score: float) -> CommunityDiscoveryHit:
	return CommunityDiscoveryHit(
		hit_id=entry.entry_id,
		title=entry.title,
		description=entry.description,
		tags=list(entry.tags),
		author=entry.author,
		preview_image=entry.preview_image,
		community_url=entry.community_url,
		file_key=entry.file_key,
		likes=entry.likes,
		downloads=entry.downloads,
		design_system=entry.design_system,
		source_backend='catalog',
		discovery_score=min(1.0, score),
		extra=dict(entry.extra),
	)


def _tokenize(text: str) -> list[str]:
	return [t for t in re.split(r'[\s\-_]+', text.lower()) if len(t) > 2]


def _optional_int(value: Any) -> int | None:
	if value is None:
		return None
	try:
		return int(value)
	except (TypeError, ValueError):
		return None
