"""Live resource provider registry."""
from __future__ import annotations

from navigation.resource_intelligence.graph.icon_families import ICON_FAMILIES
from navigation.resource_intelligence.providers.dicebear.provider import DiceBearProvider
from navigation.resource_intelligence.providers.fontsource.provider import FontsourceProvider
from navigation.resource_intelligence.providers.icon_family.provider import IconFamilyProvider
from navigation.resource_intelligence.providers.iconify.provider import IconifyProvider
from navigation.resource_intelligence.providers.ira_design.provider import IraDesignProvider
from navigation.resource_intelligence.providers.open_doodles.provider import OpenDoodlesProvider
from navigation.resource_intelligence.providers.pexels.provider import PexelsProvider
from navigation.resource_intelligence.providers.pixabay.provider import PixabayProvider
from navigation.resource_intelligence.providers.poly_pizza.provider import PolyPizzaProvider
from navigation.resource_intelligence.providers.protocol import ResourceProvider
from navigation.resource_intelligence.providers.rive.provider import RiveProvider
from navigation.resource_intelligence.providers.simple_icons.provider import SimpleIconsProvider
from navigation.resource_intelligence.providers.svg_repo.provider import SvgRepoProvider
from navigation.resource_intelligence.providers.thesvg.provider import TheSVGProvider
from navigation.resource_intelligence.providers.threedicons.provider import ThreeDiconsProvider
from navigation.resource_intelligence.providers.uigradients.provider import UiGradientsProvider


class ResourceProviderManager:
	def __init__(self) -> None:
		self._providers: dict[str, ResourceProvider] = {
			'iconify': IconifyProvider(),
			'dicebear': DiceBearProvider(),
			'fontsource': FontsourceProvider(),
			'pexels': PexelsProvider(),
			'simple-icons': SimpleIconsProvider(),
			'thesvg': TheSVGProvider(),
			'open-doodles': OpenDoodlesProvider(),
			'ira-design': IraDesignProvider(),
			'pixabay': PixabayProvider(),
			'svg-repo': SvgRepoProvider(),
			'poly-pizza': PolyPizzaProvider(),
			'uigradients': UiGradientsProvider(),
			'3dicons': ThreeDiconsProvider(),
			'rive': RiveProvider(),
		}
		for family in ICON_FAMILIES.values():
			if family.provider_id not in self._providers:
				self._providers[family.provider_id] = IconFamilyProvider(family)
			self._providers[family.family_id] = IconFamilyProvider(family)

	def get(self, provider_id: str) -> ResourceProvider | None:
		return self._providers.get(provider_id)

	def get_icon_family_provider(self, family_id: str) -> ResourceProvider | None:
		return self._providers.get(family_id)

	def list_live_providers(self) -> list[str]:
		seen: set[str] = set()
		out: list[str] = []
		for key in sorted(self._providers.keys()):
			provider = self._providers[key]
			pid = getattr(provider, 'provider_id', key)
			if pid in seen:
				continue
			seen.add(pid)
			out.append(pid)
		return out
