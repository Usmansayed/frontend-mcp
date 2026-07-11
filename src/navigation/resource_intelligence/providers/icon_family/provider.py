"""Generic icon family provider — one consistent style set per family."""
from __future__ import annotations

from navigation.resource_intelligence.graph.icon_families import IconFamily
from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers.iconify.provider import IconifyProvider


class IconFamilyProvider:
	def __init__(self, family: IconFamily) -> None:
		self._family = family
		self._iconify = IconifyProvider()

	@property
	def provider_id(self) -> str:
		return self._family.provider_id

	def provider_meta(self) -> ResourceProviderMeta:
		meta = SEED_PROVIDERS.get(self._family.provider_id)
		if meta is not None:
			return meta
		return SEED_PROVIDERS['iconify']

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		assets, degraded = await self._iconify.search(
			query,
			category=category,
			max_results=max_results,
			prefix_filter=self._family.iconify_prefix,
		)
		for asset in assets:
			asset.provider_id = self._family.provider_id
			asset.resource_id = asset.resource_id.replace('iconify:', f'{self._family.family_id}:', 1)
			asset.score = min(1.0, asset.score + 0.25)
			icon_name = str(asset.metadata.get('icon_name') or '')
			from navigation.resource_intelligence.import_verification.icons import verify_icon_import

			verified = await verify_icon_import(self._family.family_id, icon_name)
			asset.metadata.update(
				{
					'icon_family': self._family.family_id,
					'iconify_prefix': self._family.iconify_prefix,
					'family_match': True,
					'delivery': 'url_only',
					'npm_package': self._family.npm_package,
					'import_verified': verified.get('verified') == 'true',
					'verified_import': verified.get('verified_import', ''),
					'install_command': verified.get('install_command', ''),
					'usage': verified.get('usage', ''),
				}
			)
		return assets, degraded
