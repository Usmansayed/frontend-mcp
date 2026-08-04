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

# Filler tokens that hurt literal provider search (Iconify, etc.).
_STOPWORDS = frozenset({
	'a', 'an', 'the', 'for', 'with', 'and', 'or', 'of', 'to', 'in', 'on', 'at',
	'dark', 'light', 'mode', 'theme', 'style', 'ui', 'app', 'button', 'outline',
	'filled', 'solid', 'line', 'modern', 'minimal', 'simple', 'nice', 'good',
	'best', 'new', 'small', 'large', 'big', 'tiny',
})


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
	tokens = [t for t in keywords.lower().split() if t and t not in _STOPWORDS]
	# Prefer concrete nouns: shortest non-stopword often matches provider catalogs better
	# ("moon dark mode icon" → "moon").
	if tokens:
		keywords = ' '.join(tokens)
		# For icons, lead with the shortest content token (usually the symbol name).
		if category == ResourceCategory.ICON:
			primary = sorted(tokens, key=len)[0]
			keywords = primary if primary else keywords
	else:
		keywords = text
	keywords = ' '.join(keywords.split()) or text
	return ResourceIntent(raw_query=text, category=category, keywords=keywords)
