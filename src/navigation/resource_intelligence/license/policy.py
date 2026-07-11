"""License policy gates for Resource Intelligence."""
from __future__ import annotations

from navigation.resource_intelligence.models import LicenseProfile, ResourceDiscoveryRequest


def allows_use(profile: LicenseProfile, request: ResourceDiscoveryRequest) -> tuple[bool, str]:
	"""Gate assets by commercial use and attribution — not automation bans."""
	if request.commercial_required and not profile.commercial_use:
		return False, 'commercial_use_denied'
	if profile.attribution_required and not request.attribution_ok:
		return False, 'attribution_required'
	return True, ''


def automation_advisory(profile: LicenseProfile) -> list[str]:
	"""Non-blocking warnings for adapters (catalog inclusion is unchanged)."""
	out: list[str] = []
	if not profile.api_automation_allowed:
		out.append('automation_prohibited_by_provider')
	if not profile.ai_training_allowed and profile.commercial_use:
		out.append('ai_training_prohibited')
	if not profile.mcp_download_allowed:
		out.append('mcp_download_restricted')
	return out
