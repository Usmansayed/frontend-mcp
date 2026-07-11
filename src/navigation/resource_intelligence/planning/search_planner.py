"""Search planner — route queries to providers by category."""
from __future__ import annotations

from navigation.resource_intelligence.models import ResourceCategory, ResourceDiscoveryRequest
from navigation.resource_intelligence.registry import ResourceProviderRegistry

_CATEGORY_PROVIDERS: dict[ResourceCategory, list[str]] = {
	ResourceCategory.ICON: ['lucide', 'heroicons', 'tabler-icons', 'phosphor-icons', 'remix-icon', 'material-symbols', 'iconify'],
	ResourceCategory.LOGO: ['thesvg', 'simple-icons'],
	ResourceCategory.FONT: ['fontsource'],
	ResourceCategory.PHOTO: ['pexels', 'pixabay'],
	ResourceCategory.ILLUSTRATION: ['open-doodles', 'ira-design', 'undraw', 'storyset'],
	ResourceCategory.AVATAR: ['dicebear'],
	ResourceCategory.SVG: ['svg-repo', 'simple-icons', 'iconify'],
	ResourceCategory.GRAPHIC: ['svg-repo'],
	ResourceCategory.THREE_D: ['poly-pizza', '3dicons'],
	ResourceCategory.GRADIENT: ['uigradients'],
	ResourceCategory.ANIMATION: ['rive', 'lottiefiles'],
	ResourceCategory.PATTERN: ['hero-patterns'],
}


class ResourceSearchPlanner:
	def __init__(self, registry: ResourceProviderRegistry | None = None) -> None:
		self._registry = registry or ResourceProviderRegistry()

	def resolve_provider_ids(self, request: ResourceDiscoveryRequest) -> list[str]:
		if request.provider_preference:
			return [request.provider_preference]
		categories = request.categories or []
		if not categories:
			from navigation.resource_intelligence.intent.parser import parse_intent

			categories = [parse_intent(request.query).category]
		seen: set[str] = set()
		ordered: list[str] = []
		for category in categories:
			for pid in _CATEGORY_PROVIDERS.get(category, ['iconify']):
				meta = self._registry.get(pid)
				if meta is None or meta.excluded or not meta.license.commercial_use:
					continue
				if pid in seen:
					continue
				seen.add(pid)
				ordered.append(pid)
		if not ordered:
			ordered = ['iconify']
		return sorted(ordered, key=lambda pid: self._registry.get(pid).priority_tier if self._registry.get(pid) else 9)
