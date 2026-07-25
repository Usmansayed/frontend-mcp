"""Stable contract for cross-module SEO orchestration."""
from __future__ import annotations

from typing import Any, Protocol

from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult


class SeoIntelligencePort(Protocol):
	async def audit(self, request: SeoAuditRequest) -> SeoAuditResult:
		...

	def status(self) -> dict[str, Any]:
		...


class SeoIntelligenceAdapter:
	"""Thin adapter — other modules depend on this, not provider internals."""

	def __init__(self, service: SeoIntelligencePort | None = None) -> None:
		from navigation.seo_intelligence.service import SeoIntelligenceService

		self._service = service or SeoIntelligenceService()

	async def audit(self, request: SeoAuditRequest) -> SeoAuditResult:
		return await self._service.audit(request)

	def status(self) -> dict[str, Any]:
		return self._service.status()
