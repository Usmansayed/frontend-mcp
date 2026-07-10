"""Component search provider orchestration."""
from __future__ import annotations

import asyncio
from typing import Any

from ..models import ComponentCandidate, ComponentDetail, SearchContext, SearchPlan
from .component import ComponentProvider, ComponentProviderError
from .external import build_external_providers
from .shadcn_ecosystem import ShadcnEcosystemProvider


class ProviderManager:
	"""Runs enabled providers in parallel for each search pass."""

	def __init__(self, providers: list[ComponentProvider] | None = None) -> None:
		self._providers = providers or self.default_providers()

	@staticmethod
	def default_providers() -> list[ComponentProvider]:
		return [ShadcnEcosystemProvider(), *build_external_providers()]

	def list_providers(self) -> list[dict[str, Any]]:
		return [
			{
				'name': provider.name,
				'group': provider.group,
				'enabled': provider.enabled,
			}
			for provider in self._providers
		]

	async def search_pass(self, context: SearchContext) -> dict[str, dict[str, Any]]:
		active = [p for p in self._providers if getattr(p, 'enabled', True)]
		names = [p.name for p in active]
		results = await asyncio.gather(
			*[self._safe_search(provider, context) for provider in active],
			return_exceptions=False,
		)
		return dict(zip(names, results, strict=True))

	async def get_component(self, component_id: str) -> ComponentDetail:
		provider_name = component_id.split(':', 1)[0]
		for provider in self._providers:
			if provider.name == provider_name:
				return await provider.get_component(component_id)
		raise ComponentProviderError(f'provider_not_found:{provider_name}')

	async def install(self, component_id: str) -> dict[str, object]:
		provider_name = component_id.split(':', 1)[0]
		for provider in self._providers:
			if provider.name == provider_name:
				return await provider.install(component_id)
		raise ComponentProviderError(f'provider_not_found:{provider_name}')

	@staticmethod
	async def _safe_search(provider: ComponentProvider, context: SearchContext) -> dict[str, Any]:
		try:
			items = await provider.search(context)
			return {'candidates': items, 'error': None}
		except ComponentProviderError as exc:
			return {'candidates': [], 'error': str(exc)}
		except Exception as exc:
			return {'candidates': [], 'error': f'unexpected:{exc}'}
