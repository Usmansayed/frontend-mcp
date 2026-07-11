"""SEO provider protocol — swappable free-first data adapters."""
from __future__ import annotations

from typing import Protocol

from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta


class SeoDataProvider(Protocol):
	provider_id: str

	def provider_meta(self) -> SeoProviderMeta:
		...

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		"""Return (status, degraded). Status: not_configured | pending_auth | connected | degraded | error."""
		...

	async def collect(
		self,
		request: SeoAuditRequest,
	) -> tuple[list[SeoEvidenceRef], list[str]]:
		"""Return normalized evidence + degraded notes."""
		...
