"""Simple Icons — brand logos via Iconify simple-icons collection."""
from __future__ import annotations

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import LicenseProfile, ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers.iconify.provider import IconifyProvider


class SimpleIconsProvider:
	provider_id = 'simple-icons'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		iconify = IconifyProvider()
		assets, degraded = await iconify.search(
			query,
			category=ResourceCategory.LOGO,
			max_results=max_results,
			prefix_filter='simple-icons',
		)
		lic = LicenseProfile(
			spdx_id='CC0-1.0',
			commercial_use=True,
			attribution_required=False,
			redistribution_allowed=True,
			mcp_download_allowed=True,
			source_url='https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md',
			notes=['Trademark: logos are not endorsement; verify brand guidelines'],
		)
		for asset in assets:
			asset.provider_id = self.provider_id
			asset.category = ResourceCategory.LOGO
			asset.resource_id = asset.resource_id.replace('iconify:', 'simple-icons:', 1)
			asset.license = lic
			slug = asset.metadata.get('icon_name', '')
			asset.metadata.update(
				{
					'npm_package': 'simple-icons',
					'install_command': 'npm install simple-icons',
					'import_guidance': f"import {{ si{''.join(p.capitalize() for p in slug.split('-'))} }} from 'simple-icons'",
					'dark_light': 'monochrome SVG — apply currentColor for theme',
					'trademark_warning': True,
				}
			)
		return assets, degraded
