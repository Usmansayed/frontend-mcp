"""Shadcn registry catalog helpers."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

REGISTRIES_INDEX_URL = 'https://ui.shadcn.com/r/registries.json'
DEFAULT_STYLE = 'new-york'
_INDEX_TTL_S = 3600

_index_cache: tuple[float, list[dict[str, Any]]] | None = None


@dataclass(frozen=True, slots=True)
class RegistryEntry:
	namespace: str
	item_url_template: str
	homepage: str | None
	catalog_url: str


# Core shadcn/ui registry — not listed in registries.json but required for primitives.
DEFAULT_SHADCN_UI_ENTRY = RegistryEntry(
	namespace='@shadcn',
	item_url_template='https://ui.shadcn.com/r/styles/{style}/{name}.json',
	homepage='https://ui.shadcn.com',
	catalog_url=f'https://ui.shadcn.com/r/styles/{DEFAULT_STYLE}/registry.json',
)


def registry_lookup(index: list[dict[str, Any]]) -> dict[str, RegistryEntry]:
	by_ns: dict[str, RegistryEntry] = {}
	for raw in index:
		entry = to_registry_entry(raw)
		if entry:
			by_ns[entry.namespace.lower()] = entry
	if '@shadcn' not in by_ns:
		by_ns['@shadcn'] = DEFAULT_SHADCN_UI_ENTRY
	return by_ns


def fetch_registries_index(*, force_refresh: bool = False) -> list[dict[str, Any]]:
	global _index_cache
	now = time.time()
	if not force_refresh and _index_cache and now - _index_cache[0] < _INDEX_TTL_S:
		return _index_cache[1]
	with urllib.request.urlopen(REGISTRIES_INDEX_URL, timeout=30) as resp:
		payload = json.loads(resp.read().decode('utf-8'))
	if not isinstance(payload, list):
		raise ValueError('invalid registries index payload')
	_index_cache = (now, payload)
	return payload


def catalog_url_from_template(template: str) -> str:
	if '{style}' in template:
		return template.replace('{style}', DEFAULT_STYLE).replace('{name}.json', 'registry.json')
	if '{name}' in template:
		return template.replace('{name}.json', 'registry.json').replace('/{name}', '/registry.json')
	return template.rstrip('/') + '/registry.json'


def to_registry_entry(raw: dict[str, Any]) -> RegistryEntry | None:
	namespace = str(raw.get('name') or '').strip()
	template = str(raw.get('url') or '').strip()
	if not namespace or not template:
		return None
	return RegistryEntry(
		namespace=namespace,
		item_url_template=template,
		homepage=str(raw.get('homepage') or '').strip() or None,
		catalog_url=catalog_url_from_template(template),
	)


def fetch_registry_catalog(catalog_url: str) -> list[dict[str, Any]]:
	try:
		with urllib.request.urlopen(catalog_url, timeout=20) as resp:
			payload = json.loads(resp.read().decode('utf-8'))
	except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
		return []
	items = payload.get('items') if isinstance(payload, dict) else None
	return list(items) if isinstance(items, list) else []


# Priority namespaces for Group A — always considered for shadcn-ecosystem search.
PRIORITY_NAMESPACES: tuple[str, ...] = (
	'@shadcn',
	'@magicui',
	'@origin-ui',
	'@kibo-ui',
	'@diceui',
	'@fancycomponents',
	'@motion-primitives',
	'@tailark',
	'@kokonutui',
	'@cult-ui',
	'@ai-elements',
	'@blocks',
	'@shadcn-space',
	'@abui',
	'@pureui',
	'@doras-ui',
	'@8bitcn',
	'@aceternity',
)


def select_registries_for_plan(
	index: list[dict[str, Any]],
	suggested_registries: list[str],
	parsed_text: str,
	*,
	max_registries: int = 25,
) -> list[RegistryEntry]:
	by_ns = registry_lookup(index)
	selected: list[RegistryEntry] = []
	seen: set[str] = set()

	for ns in suggested_registries:
		entry = by_ns.get(ns.lower())
		if entry and entry.namespace not in seen:
			selected.append(entry)
			seen.add(entry.namespace)

	for ns in PRIORITY_NAMESPACES:
		if len(selected) >= max_registries:
			break
		entry = by_ns.get(ns.lower())
		if entry and entry.namespace not in seen:
			selected.append(entry)
			seen.add(entry.namespace)

	if len(selected) < max_registries:
		for entry in select_registries(index, parsed_text, max_registries=max_registries):
			if entry.namespace not in seen:
				selected.append(entry)
				seen.add(entry.namespace)

	return selected[:max_registries]


def select_registries(
	index: list[dict[str, Any]],
	parsed_text: str,
	*,
	max_registries: int = 25,
) -> list[RegistryEntry]:
	by_ns = registry_lookup(index)

	selected: list[RegistryEntry] = []
	seen: set[str] = set()

	for ns in PRIORITY_NAMESPACES:
		entry = by_ns.get(ns.lower())
		if entry and entry.namespace not in seen:
			selected.append(entry)
			seen.add(entry.namespace)

	needle = parsed_text.lower()
	for raw in index:
		entry = to_registry_entry(raw)
		if entry is None or entry.namespace in seen:
			continue
		hay = f'{entry.namespace} {entry.homepage or ""}'.lower()
		if any(tok in hay for tok in re.findall(r'[a-z0-9]+', needle) if len(tok) > 3):
			selected.append(entry)
			seen.add(entry.namespace)
		if len(selected) >= max_registries:
			break

	return selected[:max_registries]
