"""Commercial-safe icon families — same-style sets for consistent UI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IconFamily:
	family_id: str
	display_name: str
	iconify_prefix: str
	provider_id: str
	npm_package: str = ''
	import_example: str = ''
	notes: str = ''


# Curated families — one style per project; search stays inside the family by default.
ICON_FAMILIES: dict[str, IconFamily] = {
	'lucide': IconFamily(
		family_id='lucide',
		display_name='Lucide',
		iconify_prefix='lucide',
		provider_id='lucide',
		npm_package='lucide-react',
		import_example="import { Settings } from 'lucide-react'",
		notes='Stroke icons; default when lucide-react is in the stack',
	),
	'heroicons': IconFamily(
		family_id='heroicons',
		display_name='Heroicons',
		iconify_prefix='heroicons',
		provider_id='heroicons',
		npm_package='@heroicons/react',
		import_example="import { Cog6ToothIcon } from '@heroicons/react/24/outline'",
	),
	'tabler-icons': IconFamily(
		family_id='tabler-icons',
		display_name='Tabler Icons',
		iconify_prefix='tabler',
		provider_id='tabler-icons',
		npm_package='@tabler/icons-react',
		import_example="import { IconSettings } from '@tabler/icons-react'",
	),
	'phosphor-icons': IconFamily(
		family_id='phosphor-icons',
		display_name='Phosphor Icons',
		iconify_prefix='ph',
		provider_id='phosphor-icons',
		npm_package='@phosphor-icons/react',
		import_example="import { Gear } from '@phosphor-icons/react'",
	),
	'remix-icon': IconFamily(
		family_id='remix-icon',
		display_name='Remix Icon',
		iconify_prefix='ri',
		provider_id='remix-icon',
		npm_package='@remixicon/react',
		import_example="import { RiSettings3Line } from '@remixicon/react'",
	),
	'material-symbols': IconFamily(
		family_id='material-symbols',
		display_name='Material Symbols',
		iconify_prefix='material-symbols',
		provider_id='iconify',
		npm_package='',
		notes='Google Material Symbols via Iconify',
	),
}


def get_icon_family(family_id: str) -> IconFamily | None:
	key = family_id.strip().lower().replace('_', '-')
	if key in ICON_FAMILIES:
		return ICON_FAMILIES[key]
	for family in ICON_FAMILIES.values():
		if family.iconify_prefix == key or family.provider_id == key:
			return family
	return None


def list_icon_families() -> list[dict[str, str]]:
	return [
		{
			'family_id': f.family_id,
			'display_name': f.display_name,
			'iconify_prefix': f.iconify_prefix,
			'npm_package': f.npm_package,
		}
		for f in ICON_FAMILIES.values()
	]
