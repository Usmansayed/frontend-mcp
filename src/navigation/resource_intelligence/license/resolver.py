"""License Intelligence — structured licensing on every asset response."""
from __future__ import annotations

from typing import Any

from navigation.resource_intelligence.license.policy import allows_use, automation_advisory
from navigation.resource_intelligence.models import LicenseProfile, LicenseSummary, ResourceDiscoveryRequest

# Flat SPDX / common name strings agents often pass as asset.license.
_PERMISSIVE_COMMERCIAL: dict[str, dict[str, Any]] = {
	'mit': {'spdx_id': 'MIT', 'commercial_use': True, 'attribution_required': True},
	'isc': {'spdx_id': 'ISC', 'commercial_use': True, 'attribution_required': True},
	'apache-2.0': {'spdx_id': 'Apache-2.0', 'commercial_use': True, 'attribution_required': True},
	'apache 2.0': {'spdx_id': 'Apache-2.0', 'commercial_use': True, 'attribution_required': True},
	'bsd-2-clause': {'spdx_id': 'BSD-2-Clause', 'commercial_use': True, 'attribution_required': True},
	'bsd-3-clause': {'spdx_id': 'BSD-3-Clause', 'commercial_use': True, 'attribution_required': True},
	'cc0': {'spdx_id': 'CC0', 'commercial_use': True, 'attribution_required': False},
	'cc0-1.0': {'spdx_id': 'CC0-1.0', 'commercial_use': True, 'attribution_required': False},
	'ofl': {'spdx_id': 'OFL-1.1', 'commercial_use': True, 'attribution_required': True},
	'ofl-1.1': {'spdx_id': 'OFL-1.1', 'commercial_use': True, 'attribution_required': True},
	'cc-by': {'spdx_id': 'CC-BY', 'commercial_use': True, 'attribution_required': True},
	'cc-by-4.0': {'spdx_id': 'CC-BY-4.0', 'commercial_use': True, 'attribution_required': True},
}


def normalize_license_input(raw: Any) -> LicenseProfile:
	"""Accept LicenseProfile dict, {name, commercial_use}, or flat SPDX string.

	Never raise on plausible agent input shapes — Run 2 hardcore found flat
	``\"license\": \"ISC\"`` crashed with ``'str' object has no attribute 'get'``.
	"""
	if raw is None or raw == '':
		return LicenseProfile(spdx_id='UNKNOWN', notes=['license_missing'])
	if isinstance(raw, LicenseProfile):
		return raw
	if isinstance(raw, str):
		key = raw.strip().lower()
		known = _PERMISSIVE_COMMERCIAL.get(key)
		if known:
			return LicenseProfile(
				spdx_id=str(known['spdx_id']),
				commercial_use=bool(known['commercial_use']),
				attribution_required=bool(known.get('attribution_required', False)),
				redistribution_allowed=True,
				mcp_download_allowed=True,
				ai_training_allowed=True,
				dataset_use_allowed=True,
				api_automation_allowed=True,
				self_hostable=True,
				notes=['normalized_from_string_license'],
			)
		return LicenseProfile(
			spdx_id=raw.strip() or 'UNKNOWN',
			commercial_use=False,
			notes=['unrecognized_string_license', 'commercial_use_unconfirmed'],
		)
	if not isinstance(raw, dict):
		return LicenseProfile(
			spdx_id='UNKNOWN',
			notes=[f'unsupported_license_type:{type(raw).__name__}'],
		)

	spdx = str(
		raw.get('spdx_id')
		or raw.get('name')
		or raw.get('license')
		or raw.get('id')
		or 'UNKNOWN'
	).strip() or 'UNKNOWN'
	# Nested string license inside object.
	if isinstance(raw.get('license'), str) and not raw.get('spdx_id') and not raw.get('name'):
		return normalize_license_input(raw.get('license'))

	commercial = raw.get('commercial_use')
	if commercial is None and spdx.lower() in _PERMISSIVE_COMMERCIAL:
		commercial = _PERMISSIVE_COMMERCIAL[spdx.lower()]['commercial_use']
	return LicenseProfile(
		spdx_id=spdx,
		commercial_use=bool(commercial),
		attribution_required=bool(raw.get('attribution_required')),
		redistribution_allowed=bool(raw.get('redistribution_allowed', True)),
		mcp_download_allowed=bool(raw.get('mcp_download_allowed', True)),
		ai_training_allowed=bool(raw.get('ai_training_allowed', True)),
		dataset_use_allowed=bool(raw.get('dataset_use_allowed', True)),
		api_automation_allowed=bool(raw.get('api_automation_allowed', True)),
		self_hostable=bool(raw.get('self_hostable')),
		notes=list(raw.get('notes') or []),
		source_url=str(raw.get('source_url') or ''),
	)


def build_license_summary(
	profile: LicenseProfile,
	request: ResourceDiscoveryRequest,
	*,
	provider_id: str = '',
) -> LicenseSummary:
	ok, blocked_reason = allows_use(profile, request)
	warnings = automation_advisory(profile)
	if not profile.commercial_use and request.commercial_required:
		blocked_reason = blocked_reason or 'commercial_use_denied'
	return LicenseSummary(
		spdx_id=profile.spdx_id,
		commercial_use=profile.commercial_use,
		requires_attribution=profile.attribution_required,
		redistribution=profile.redistribution_allowed,
		ai_restrictions=not profile.ai_training_allowed,
		dataset_restrictions=not profile.dataset_use_allowed,
		api_automation_restricted=not profile.api_automation_allowed,
		mcp_download_allowed=profile.mcp_download_allowed,
		self_hostable=profile.self_hostable,
		api_terms_url=profile.source_url,
		blocked_reason=blocked_reason if not ok else '',
		warnings=list(warnings) + list(profile.notes),
		provider_id=provider_id,
		allowed=ok,
	)


def attach_license_to_asset_dict(asset_dict: dict, request: ResourceDiscoveryRequest) -> dict:
	profile = normalize_license_input(asset_dict.get('license'))
	summary = build_license_summary(profile, request, provider_id=str(asset_dict.get('provider_id') or ''))
	asset_dict['license_summary'] = summary.to_dict()
	return asset_dict
