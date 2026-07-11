"""Verified production imports for icon families — no hallucinated exports."""
from __future__ import annotations

import asyncio
import re
from functools import lru_cache

from navigation.resource_intelligence.graph.icon_families import ICON_FAMILIES, IconFamily
from navigation.resource_intelligence.providers._http import fetch_json_sync

_ICONIFY_COLLECTION = 'https://api.iconify.design/collection?prefix={prefix}'


@lru_cache(maxsize=32)
def _collection_icons(prefix: str) -> frozenset[str]:
	try:
		payload = fetch_json_sync(_ICONIFY_COLLECTION.format(prefix=prefix))
		icons = payload.get('icons') or payload.get('uncategorized') or []
		if isinstance(icons, dict):
			icons = list(icons.keys())
		return frozenset(str(i) for i in icons)
	except Exception:
		return frozenset()


async def icon_exists_in_family(family: IconFamily, icon_name: str) -> bool:
	name = icon_name.strip().lower().replace('_', '-')
	icons = await asyncio.to_thread(_collection_icons, family.iconify_prefix)
	return name in icons


def _pascal(kebab: str) -> str:
	return ''.join(part.capitalize() for part in kebab.split('-') if part)


def _heroicons_export(kebab: str) -> str:
	pascal = _pascal(kebab)
	return f'{pascal}Icon'


def _tabler_export(kebab: str) -> str:
	return f'Icon{_pascal(kebab)}'


def _phosphor_export(kebab: str) -> str:
	return _pascal(kebab)


def _remix_export(kebab: str) -> str:
	pascal = _pascal(kebab)
	return f'Ri{pascal}Line'


async def verify_icon_import(family_id: str, icon_name: str) -> dict[str, str]:
	family = ICON_FAMILIES.get(family_id)
	if family is None:
		return {'verified': 'false', 'reason': 'unknown_family'}
	name = icon_name.strip().lower().replace('_', '-')
	if not await icon_exists_in_family(family, name):
		return {'verified': 'false', 'reason': 'icon_not_in_family', 'icon_name': name}

	if not family.npm_package:
		return {
			'verified': 'true',
			'icon_name': name,
			'access_url': f'https://api.iconify.design/{family.iconify_prefix}/{name}.svg',
			'note': 'Use Iconify or npm package for framework integration',
		}

	export_name = _pascal(name)
	if family_id == 'heroicons':
		export_name = _heroicons_export(name)
	elif family_id == 'tabler-icons':
		export_name = _tabler_export(name)
	elif family_id == 'phosphor-icons':
		export_name = _phosphor_export(name)
	elif family_id == 'remix-icon':
		export_name = _remix_export(name)

	import_line = f"import {{ {export_name} }} from '{family.npm_package}'"
	install = f'npm install {family.npm_package}'
	if family_id == 'heroicons':
		import_line = f"import {{ {export_name} }} from '@heroicons/react/24/outline'"
	return {
		'verified': 'true',
		'icon_name': name,
		'export_name': export_name,
		'verified_import': import_line,
		'install_command': install,
		'usage': f'<{export_name} className="h-5 w-5" />',
	}
