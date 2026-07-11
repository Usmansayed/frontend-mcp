"""Resource Intelligence data models — stable contracts (research phase)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResourceCategory(str, Enum):
	ICON = 'icon'
	ILLUSTRATION = 'illustration'
	GRAPHIC = 'graphic'
	SVG = 'svg'
	LOGO = 'logo'
	AVATAR = 'avatar'
	THREE_D = '3d'
	MOCKUP = 'mockup'
	ANIMATION = 'animation'
	FONT = 'font'
	GRADIENT = 'gradient'
	PATTERN = 'pattern'
	PHOTO = 'photo'


class LicenseClass(str, Enum):
	MIT = 'MIT'
	ISC = 'ISC'
	APACHE_2 = 'Apache-2.0'
	CC0 = 'CC0'
	CC_BY = 'CC-BY'
	CC_BY_NC = 'CC-BY-NC'
	OFL = 'OFL-1.1'
	CUSTOM = 'Custom'
	PROPRIETARY = 'Proprietary'
	EDITORIAL = 'Editorial'
	UNKNOWN = 'Unknown'


@dataclass(slots=True)
class LicenseProfile:
	"""Structured licensing — every provider adapter must populate this."""

	spdx_id: str = 'UNKNOWN'
	commercial_use: bool = False
	attribution_required: bool = False
	redistribution_allowed: bool = False
	mcp_download_allowed: bool = False
	ai_training_allowed: bool = False
	dataset_use_allowed: bool = False
	api_automation_allowed: bool = True
	self_hostable: bool = False
	notes: list[str] = field(default_factory=list)
	source_url: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'spdx_id': self.spdx_id,
			'commercial_use': self.commercial_use,
			'attribution_required': self.attribution_required,
			'redistribution_allowed': self.redistribution_allowed,
			'mcp_download_allowed': self.mcp_download_allowed,
			'ai_training_allowed': self.ai_training_allowed,
			'dataset_use_allowed': self.dataset_use_allowed,
			'api_automation_allowed': self.api_automation_allowed,
			'self_hostable': self.self_hostable,
			'notes': list(self.notes),
			'source_url': self.source_url,
		}


@dataclass(slots=True)
class ResourceProviderMeta:
	"""Provider knowledge node in the Resource Graph."""

	provider_id: str
	display_name: str
	categories: list[ResourceCategory]
	license: LicenseProfile
	api_available: bool = False
	auth_required: bool = False
	self_hostable: bool = False
	rate_limit_notes: str = ''
	maintenance_status: str = 'active'
	priority_tier: int = 2
	excluded: bool = False
	exclusion_reason: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'provider_id': self.provider_id,
			'display_name': self.display_name,
			'categories': [c.value for c in self.categories],
			'license': self.license.to_dict(),
			'api_available': self.api_available,
			'auth_required': self.auth_required,
			'self_hostable': self.self_hostable,
			'rate_limit_notes': self.rate_limit_notes,
			'maintenance_status': self.maintenance_status,
			'priority_tier': self.priority_tier,
			'excluded': self.excluded,
			'exclusion_reason': self.exclusion_reason,
		}


@dataclass(slots=True)
class LicenseSummary:
	"""Structured license block on every asset — never guess."""

	spdx_id: str = 'UNKNOWN'
	commercial_use: bool = False
	requires_attribution: bool = False
	redistribution: bool = False
	ai_restrictions: bool = False
	dataset_restrictions: bool = False
	api_automation_restricted: bool = False
	mcp_download_allowed: bool = True
	self_hostable: bool = False
	api_terms_url: str = ''
	blocked_reason: str = ''
	warnings: list[str] = field(default_factory=list)
	provider_id: str = ''
	allowed: bool = True

	def to_dict(self) -> dict[str, Any]:
		return {
			'spdx_id': self.spdx_id,
			'commercial_use': self.commercial_use,
			'requires_attribution': self.requires_attribution,
			'redistribution': self.redistribution,
			'ai_restrictions': self.ai_restrictions,
			'dataset_restrictions': self.dataset_restrictions,
			'api_automation_restricted': self.api_automation_restricted,
			'mcp_download_allowed': self.mcp_download_allowed,
			'self_hostable': self.self_hostable,
			'api_terms_url': self.api_terms_url,
			'blocked_reason': self.blocked_reason,
			'warnings': list(self.warnings),
			'provider_id': self.provider_id,
			'allowed': self.allowed,
		}


@dataclass(slots=True)
class ResourceSelection:
	"""Selection Intelligence output — best asset + alternatives."""

	chosen_resource_id: str
	provider_id: str
	category: str
	confidence: float
	icon_family: str | None = None
	alternatives: list[str] = field(default_factory=list)
	reasoning: list[str] = field(default_factory=list)
	verified_import: str = ''
	install_command: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'chosen_resource_id': self.chosen_resource_id,
			'provider_id': self.provider_id,
			'category': self.category,
			'confidence': self.confidence,
			'icon_family': self.icon_family,
			'alternatives': list(self.alternatives),
			'reasoning': list(self.reasoning),
			'verified_import': self.verified_import,
			'install_command': self.install_command,
		}


@dataclass(slots=True)
class ResourceAssetRef:
	"""A recommended asset — metadata + access URL, not hosted file."""

	resource_id: str
	provider_id: str
	category: ResourceCategory
	title: str
	preview_url: str = ''
	access_url: str = ''
	license: LicenseProfile | None = None
	tags: list[str] = field(default_factory=list)
	style: list[str] = field(default_factory=list)
	format: str = ''
	attribution_text: str = ''
	score: float = 0.0
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'resource_id': self.resource_id,
			'provider_id': self.provider_id,
			'category': self.category.value,
			'title': self.title,
			'preview_url': self.preview_url,
			'access_url': self.access_url,
			'license': self.license.to_dict() if self.license else None,
			'tags': list(self.tags),
			'style': list(self.style),
			'format': self.format,
			'attribution_text': self.attribution_text,
			'score': self.score,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class ResourceDiscoveryRequest:
	query: str
	categories: list[ResourceCategory] = field(default_factory=list)
	commercial_required: bool = True
	attribution_ok: bool = True
	prefer_svg: bool = True
	prefer_self_hosted: bool = False
	max_results: int = 12
	provider_preference: str | None = None
	icon_family: str | None = None
	icon_family_strict: bool = True
	allow_family_fallback: bool = True
	persist_icon_family: bool = False
	repo_root: str = ''
	project_id: str = 'default'
	scan_id: str | None = None
	design_sense_profile: str | None = None
	auto_observe_bridge: bool = False

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query,
			'categories': [c.value for c in self.categories],
			'commercial_required': self.commercial_required,
			'attribution_ok': self.attribution_ok,
			'prefer_svg': self.prefer_svg,
			'prefer_self_hosted': self.prefer_self_hosted,
			'max_results': self.max_results,
			'provider_preference': self.provider_preference,
			'icon_family': self.icon_family,
			'icon_family_strict': self.icon_family_strict,
			'allow_family_fallback': self.allow_family_fallback,
			'persist_icon_family': self.persist_icon_family,
			'repo_root': self.repo_root,
			'project_id': self.project_id,
			'scan_id': self.scan_id,
			'design_sense_profile': self.design_sense_profile,
			'auto_observe_bridge': self.auto_observe_bridge,
		}


@dataclass(slots=True)
class ResourceRecommendation:
	request: ResourceDiscoveryRequest
	assets: list[ResourceAssetRef] = field(default_factory=list)
	providers_queried: list[str] = field(default_factory=list)
	license_warnings: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)
	icon_family: str | None = None
	family_match: bool = False
	fallback_used: bool = False
	selection: ResourceSelection | None = None
	intelligence_context: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'request': self.request.to_dict(),
			'assets': [a.to_dict() for a in self.assets],
			'providers_queried': list(self.providers_queried),
			'license_warnings': list(self.license_warnings),
			'degraded': list(self.degraded),
			'icon_family': self.icon_family,
			'family_match': self.family_match,
			'fallback_used': self.fallback_used,
			'selection': self.selection.to_dict() if self.selection else None,
			'intelligence_context': dict(self.intelligence_context),
		}
