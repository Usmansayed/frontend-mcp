"""Hero Patterns provider — searchable SVG background patterns (npm + preview links)."""

from __future__ import annotations

import re

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers.hero_patterns.catalog import PATTERN_CATALOG


class HeroPatternsProvider:
	provider_id = "hero-patterns"

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		_ = category
		degraded: list[str] = []
		tokens = {t for t in re.split(r"[^a-z0-9]+", query.lower()) if len(t) > 1}
		license_profile = self.provider_meta().license
		scored: list[tuple[float, dict[str, str]]] = []
		for item in PATTERN_CATALOG:
			blob = f"{item['id']} {item['title']} {item['npm_export']}".lower()
			if tokens:
				overlap = sum(1 for t in tokens if t in blob)
				if overlap == 0:
					continue
				score = float(overlap)
			else:
				score = 0.1
			# Exact / prefix boosts
			if query.strip().lower() in (item["id"], item["title"].lower(), item["npm_export"].lower()):
				score += 5.0
			scored.append((score, item))
		scored.sort(key=lambda pair: pair[0], reverse=True)
		if not scored:
			# Broad browse: return popular defaults rather than empty "provider down".
			scored = [(0.05, item) for item in PATTERN_CATALOG[:max_results]]
			degraded.append("hero_patterns_browse_fallback")

		assets: list[ResourceAssetRef] = []
		for score, item in scored[:max_results]:
			export = item["npm_export"]
			slug = item["id"]
			assets.append(
				ResourceAssetRef(
					resource_id=f"hero-patterns:{slug}",
					provider_id=self.provider_id,
					category=ResourceCategory.PATTERN,
					title=item["title"],
					preview_url=f"https://heropatterns.com/#{slug}",
					access_url="https://www.npmjs.com/package/hero-patterns",
					license=license_profile,
					tags=[slug, export, "pattern", "svg", "background", query],
					format="svg",
					score=min(1.0, 0.45 + score * 0.12),
					metadata={
						"npm_package": "hero-patterns",
						"npm_export": export,
						"install_command": "npm install hero-patterns",
						"usage_js": (
							f"import {{ {export} }} from 'hero-patterns';\n"
							f"el.style.backgroundImage = {export}('#0f172a', 0.15);"
						),
						"css_hint": "Use returned data-URI as background-image; pattern art is CC-BY-4.0 (Steve Schoger).",
						"delivery": "url_only",
						"framework_compat": ["react", "next", "vite", "any"],
					},
				)
			)
		return assets, degraded
