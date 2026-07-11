"""License Intelligence — structured licensing on every asset response."""
from __future__ import annotations

from navigation.resource_intelligence.license.policy import allows_use, automation_advisory
from navigation.resource_intelligence.models import LicenseProfile, LicenseSummary, ResourceDiscoveryRequest


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
	lic_data = asset_dict.get('license') or {}
	profile = LicenseProfile(
		spdx_id=str(lic_data.get('spdx_id') or 'UNKNOWN'),
		commercial_use=bool(lic_data.get('commercial_use')),
		attribution_required=bool(lic_data.get('attribution_required')),
		redistribution_allowed=bool(lic_data.get('redistribution_allowed', True)),
		mcp_download_allowed=bool(lic_data.get('mcp_download_allowed', True)),
		ai_training_allowed=bool(lic_data.get('ai_training_allowed', True)),
		dataset_use_allowed=bool(lic_data.get('dataset_use_allowed', True)),
		api_automation_allowed=bool(lic_data.get('api_automation_allowed', True)),
		self_hostable=bool(lic_data.get('self_hostable')),
		notes=list(lic_data.get('notes') or []),
		source_url=str(lic_data.get('source_url') or ''),
	)
	summary = build_license_summary(profile, request, provider_id=str(asset_dict.get('provider_id') or ''))
	asset_dict['license_summary'] = summary.to_dict()
	return asset_dict
