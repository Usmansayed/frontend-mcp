"""Frontend quality intelligence service facade."""
from __future__ import annotations

from navigation.frontend_quality_intelligence.audits.service import run_audit
from navigation.frontend_quality_intelligence.console.service import SessionConsoleService
from navigation.frontend_quality_intelligence.network.service import SessionNetworkService
from navigation.frontend_quality_intelligence.reports.diagnosis import (
	run_audit_mode,
	run_debug_mode,
	run_full_diagnosis,
)

__all__ = [
	'FrontendQualityService',
	'SessionConsoleService',
	'SessionNetworkService',
	'run_audit',
	'run_audit_mode',
	'run_debug_mode',
	'run_full_diagnosis',
]


class FrontendQualityService:
	"""Facade for quality, debugging, and diagnosis subsystems."""

	pass
