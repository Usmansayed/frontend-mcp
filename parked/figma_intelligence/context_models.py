"""Normalized Figma design context — consumed by all intelligence modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FigmaTokenRef:
	token_id: str
	name: str
	value: str = ''
	collection: str = ''
	mode: str = ''
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'token_id': self.token_id,
			'name': self.name,
			'value': self.value,
			'collection': self.collection,
			'mode': self.mode,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class FigmaStyleRef:
	style_id: str
	name: str
	kind: str = ''  # color | text | effect | grid
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'style_id': self.style_id,
			'name': self.name,
			'kind': self.kind,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class FigmaVariableRef:
	variable_id: str
	name: str
	type: str = ''
	values_by_mode: dict[str, Any] = field(default_factory=dict)
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'variable_id': self.variable_id,
			'name': self.name,
			'type': self.type,
			'values_by_mode': dict(self.values_by_mode),
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class FigmaVariantRef:
	variant_id: str
	name: str
	properties: dict[str, str] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'variant_id': self.variant_id,
			'name': self.name,
			'properties': dict(self.properties),
		}


@dataclass(slots=True)
class FigmaComponentRef:
	component_id: str
	name: str
	key: str = ''
	description: str = ''
	variants: list[FigmaVariantRef] = field(default_factory=list)
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'component_id': self.component_id,
			'name': self.name,
			'key': self.key,
			'description': self.description,
			'variants': [v.to_dict() for v in self.variants],
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class FigmaFrameRef:
	frame_id: str
	name: str
	page_id: str = ''
	width: float | None = None
	height: float | None = None
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'frame_id': self.frame_id,
			'name': self.name,
			'page_id': self.page_id,
			'width': self.width,
			'height': self.height,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class FigmaPageRef:
	page_id: str
	name: str
	frames: list[FigmaFrameRef] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'page_id': self.page_id,
			'name': self.name,
			'frames': [f.to_dict() for f in self.frames],
		}


@dataclass(slots=True)
class FigmaFileRef:
	file_key: str
	name: str = ''
	url: str = ''
	last_modified: str = ''
	pages: list[FigmaPageRef] = field(default_factory=list)
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'file_key': self.file_key,
			'name': self.name,
			'url': self.url,
			'last_modified': self.last_modified,
			'pages': [p.to_dict() for p in self.pages],
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class FigmaSelectionRef:
	node_ids: list[str] = field(default_factory=list)
	nodes: list[dict[str, Any]] = field(default_factory=list)
	page_id: str = ''
	frame_id: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'node_ids': list(self.node_ids),
			'nodes': list(self.nodes),
			'page_id': self.page_id,
			'frame_id': self.frame_id,
		}


@dataclass(slots=True)
class FigmaDesignContext:
	"""Normalized design context for agent and sibling intelligence modules."""

	connected: bool
	file: FigmaFileRef | None = None
	active_page_id: str = ''
	active_frame_id: str = ''
	selection: FigmaSelectionRef = field(default_factory=FigmaSelectionRef)
	components: list[FigmaComponentRef] = field(default_factory=list)
	variables: list[FigmaVariableRef] = field(default_factory=list)
	styles: list[FigmaStyleRef] = field(default_factory=list)
	tokens: list[FigmaTokenRef] = field(default_factory=list)
	assets: list[dict[str, Any]] = field(default_factory=list)
	session: dict[str, Any] = field(default_factory=dict)
	cache: dict[str, Any] = field(default_factory=dict)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'connected': self.connected,
			'file': self.file.to_dict() if self.file else None,
			'active_page_id': self.active_page_id,
			'active_frame_id': self.active_frame_id,
			'selection': self.selection.to_dict(),
			'components': [c.to_dict() for c in self.components],
			'variables': [v.to_dict() for v in self.variables],
			'styles': [s.to_dict() for s in self.styles],
			'tokens': [t.to_dict() for t in self.tokens],
			'assets': list(self.assets),
			'session': dict(self.session),
			'cache': dict(self.cache),
			'degraded': list(self.degraded),
		}
