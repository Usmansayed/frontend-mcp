"""Lightweight intent parsing for resource queries."""
from __future__ import annotations

from dataclasses import dataclass

from navigation.resource_intelligence.models import ResourceCategory

_CATEGORY_HINTS: dict[ResourceCategory, tuple[str, ...]] = {
	ResourceCategory.ICON: ('icon', 'icons', 'glyph', 'symbol', 'favicon'),
	ResourceCategory.FONT: ('font', 'fonts', 'typeface', 'typography'),
	ResourceCategory.PHOTO: ('photo', 'photos', 'image', 'stock', 'picture'),
	ResourceCategory.AVATAR: ('avatar', 'avatars', 'profile picture', 'user pic'),
	ResourceCategory.LOGO: ('logo', 'logos', 'brand mark'),
	ResourceCategory.ILLUSTRATION: ('illustration', 'illustrations', 'doodle', 'drawing'),
	ResourceCategory.SVG: ('svg', 'vector'),
	ResourceCategory.ANIMATION: ('animation', 'lottie', 'motion'),
	ResourceCategory.PATTERN: ('pattern', 'patterns', 'background pattern'),
	ResourceCategory.GRADIENT: ('gradient', 'gradients'),
	ResourceCategory.THREE_D: ('3d', 'three-d', 'three d'),
}


@dataclass(slots=True)
class ResourceIntent:
	raw_query: str
	category: ResourceCategory
	keywords: str


def parse_intent(query: str) -> ResourceIntent:
	text = ' '.join(query.strip().split())
	lower = text.lower()
	category = ResourceCategory.ICON
	for cat, hints in _CATEGORY_HINTS.items():
		if any(h in lower for h in hints):
			category = cat
			break
	keywords = text
	for hints in _CATEGORY_HINTS.values():
		for hint in hints:
			keywords = keywords.replace(hint, ' ')
			keywords = keywords.replace(hint.title(), ' ')
	keywords = ' '.join(keywords.split()) or text
	return ResourceIntent(raw_query=text, category=category, keywords=keywords)
