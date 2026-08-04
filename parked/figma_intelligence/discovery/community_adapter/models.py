"""Community discovery hit — normalized public metadata (no PAT)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CommunityDiscoveryHit:
	"""One public Community template — provider-independent."""

	hit_id: str
	title: str
	description: str = ''
	tags: list[str] = field(default_factory=list)
	author: str = ''
	preview_image: str = ''
	community_url: str = ''
	file_key: str = ''
	likes: int | None = None
	downloads: int | None = None
	design_system: str = ''
	source_backend: str = ''
	discovery_score: float = 0.0
	extra: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'hit_id': self.hit_id,
			'title': self.title,
			'description': self.description,
			'tags': list(self.tags),
			'author': self.author,
			'preview_image': self.preview_image,
			'community_url': self.community_url,
			'file_key': self.file_key,
			'likes': self.likes,
			'downloads': self.downloads,
			'design_system': self.design_system,
			'source_backend': self.source_backend,
			'discovery_score': self.discovery_score,
			'extra': dict(self.extra),
		}
