"""Resource search orchestrator — full intelligence pipeline."""
from __future__ import annotations

from pathlib import Path

from navigation.resource_intelligence.adapters.ecosystem import gather_selection_context
from navigation.resource_intelligence.graph.store import ResourceGraphStore
from navigation.resource_intelligence.intent.parser import parse_intent
from navigation.resource_intelligence.license.policy import allows_use, automation_advisory
from navigation.resource_intelligence.license.resolver import build_license_summary
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceDiscoveryRequest, ResourceRecommendation
from navigation.resource_intelligence.planning.icon_family import persist_icon_family, resolve_icon_family
from navigation.resource_intelligence.planning.search_planner import ResourceSearchPlanner
from navigation.resource_intelligence.providers.manager import ResourceProviderManager
from navigation.resource_intelligence.ranking.ranker import rank_assets
from navigation.resource_intelligence.registry import ResourceProviderRegistry
from navigation.resource_intelligence.search.executor import execute_provider_searches
from navigation.resource_intelligence.selection.engine import select_best


class ResourceSearchOrchestrator:
	def __init__(
		self,
		*,
		registry: ResourceProviderRegistry | None = None,
		providers: ResourceProviderManager | None = None,
		graph: ResourceGraphStore | None = None,
	) -> None:
		self._registry = registry or ResourceProviderRegistry()
		self._providers = providers or ResourceProviderManager()
		self._planner = ResourceSearchPlanner(self._registry)
		self._graph = graph or ResourceGraphStore()

	async def search(self, request: ResourceDiscoveryRequest) -> ResourceRecommendation:
		ctx, ctx_deg = await gather_selection_context(
			repo_root=request.repo_root,
			project_id=request.project_id,
			design_sense_profile=request.design_sense_profile,
		)
		if not request.icon_family and ctx.icon_family_hint:
			request.icon_family = ctx.icon_family_hint
			ctx.reasoning.append(f'auto_icon_family:{ctx.icon_family_hint}')

		intent = parse_intent(request.query)
		categories = request.categories or [intent.category]
		search_query = intent.keywords or request.query
		degraded: list[str] = list(ctx_deg)
		license_warnings: list[str] = []

		if ResourceCategory.ICON in categories and not request.provider_preference:
			family_result = await self._search_icon_family(request, search_query, ctx)
			if family_result is not None:
				return await self._finalize(family_result, ctx, request)

		provider_ids = self._planner.resolve_provider_ids(request)
		pairs: list[tuple[str, object]] = []
		for pid in provider_ids:
			provider = self._providers.get(pid)
			if provider is not None:
				pairs.append((pid, provider))
			else:
				degraded.append(f'provider_not_implemented:{pid}')

		per_provider = max(2, request.max_results // max(1, len(pairs) or 1))
		all_assets: list[ResourceAssetRef] = []
		providers_queried: list[str] = []
		for category in categories:
			assets, pdeg, queried = await execute_provider_searches(
				pairs,
				query=search_query,
				category=category,
				max_results=per_provider,
			)
			degraded.extend(pdeg)
			providers_queried.extend(queried)
			all_assets.extend(self._gate_assets(assets, request, license_warnings, degraded))

		ranked = rank_assets(all_assets, request)
		deduped = self._dedupe(ranked, request.max_results)

		if not deduped and not providers_queried:
			degraded.append('no_live_providers_for_query')

		result = ResourceRecommendation(
			request=request,
			assets=deduped,
			providers_queried=sorted(set(providers_queried)),
			license_warnings=license_warnings,
			degraded=degraded,
			intelligence_context=ctx.to_dict(),
		)
		return await self._finalize(result, ctx, request)

	async def _search_icon_family(self, request, search_query, ctx):
		family = resolve_icon_family(request, project_root=Path(request.repo_root) if request.repo_root else None)
		if family is None:
			return None
		if request.persist_icon_family:
			persist_icon_family(family.family_id)
		provider = self._providers.get_icon_family_provider(family.family_id)
		if provider is None:
			return None
		degraded: list[str] = []
		license_warnings: list[str] = []
		try:
			assets, provider_deg = await provider.search(
				search_query,
				category=ResourceCategory.ICON,
				max_results=request.max_results,
			)
		except Exception as exc:
			degraded.append(f'{family.family_id}_search_failed:{exc}')
			assets = []
			provider_deg = []
		degraded.extend(provider_deg)
		assets = self._gate_assets(assets, request, license_warnings, degraded)
		if assets:
			return ResourceRecommendation(
				request=request,
				assets=assets[: request.max_results],
				providers_queried=[family.provider_id],
				license_warnings=license_warnings,
				degraded=degraded,
				icon_family=family.family_id,
				family_match=True,
				intelligence_context=ctx.to_dict(),
			)
		if request.icon_family_strict and not request.allow_family_fallback:
			degraded.append(f'icon_family_miss:{family.family_id}')
			return ResourceRecommendation(
				request=request,
				providers_queried=[family.provider_id],
				license_warnings=license_warnings,
				degraded=degraded,
				icon_family=family.family_id,
				family_match=False,
				intelligence_context=ctx.to_dict(),
			)
		degraded.append(f'icon_family_miss:{family.family_id}')
		provider_ids = ['iconify']
		pairs = [(pid, self._providers.get(pid)) for pid in provider_ids if self._providers.get(pid)]
		assets, pdeg, queried = await execute_provider_searches(
			pairs,  # type: ignore[arg-type]
			query=search_query,
			category=ResourceCategory.ICON,
			max_results=request.max_results,
		)
		degraded.extend(pdeg)
		assets = self._gate_assets(assets, request, license_warnings, degraded)
		for asset in assets:
			asset.metadata.setdefault('family_match', False)
			asset.metadata['delivery'] = 'vision_fallback_candidate'
		return ResourceRecommendation(
			request=request,
			assets=assets[: request.max_results],
			providers_queried=queried,
			license_warnings=license_warnings,
			degraded=degraded,
			icon_family=family.family_id,
			family_match=False,
			fallback_used=bool(assets),
			intelligence_context=ctx.to_dict(),
		)

	async def _finalize(
		self,
		result: ResourceRecommendation,
		ctx,
		request: ResourceDiscoveryRequest,
	) -> ResourceRecommendation:
		result.assets = await self._enrich_assets(result.assets, request)
		result.selection = await select_best(
			result.assets,
			ctx,
			request,
			icon_family=result.icon_family,
		)
		if result.selection:
			self._graph.record_selection(result.selection.to_dict())
		for asset in result.assets:
			self._graph.upsert_asset(asset)
		self._graph.save()
		return result

	async def _enrich_assets(
		self,
		assets: list[ResourceAssetRef],
		request: ResourceDiscoveryRequest,
	) -> list[ResourceAssetRef]:
		from navigation.resource_intelligence.import_verification.icons import verify_icon_import

		for asset in assets:
			if asset.license:
				summary = build_license_summary(asset.license, request, provider_id=asset.provider_id)
				asset.metadata['license_summary'] = summary.to_dict()
			if asset.category == ResourceCategory.ICON:
				fam = asset.metadata.get('icon_family') or request.icon_family or 'lucide'
				name = str(asset.metadata.get('icon_name') or asset.title).lower().replace(' ', '-')
				verified = await verify_icon_import(fam, name)
				if verified.get('verified') == 'true':
					asset.metadata['verified_import'] = verified.get('verified_import', '')
					asset.metadata['install_command'] = verified.get('install_command', '')
					asset.metadata['import_verified'] = True
				else:
					asset.metadata['import_verified'] = False
		return assets

	def _gate_assets(self, assets, request, license_warnings, degraded):
		out: list[ResourceAssetRef] = []
		for asset in assets:
			profile = asset.license
			if profile is None:
				provider = self._providers.get(asset.provider_id)
				profile = provider.provider_meta().license if provider else None
			if profile is None:
				continue
			ok, reason = allows_use(profile, request)
			if not ok:
				degraded.append(f'skipped:{asset.resource_id}:{reason}')
				continue
			for warning in automation_advisory(profile):
				if warning not in license_warnings:
					license_warnings.append(warning)
			out.append(asset)
		return out

	def _dedupe(self, ranked: list[ResourceAssetRef], max_results: int) -> list[ResourceAssetRef]:
		seen: set[str] = set()
		deduped: list[ResourceAssetRef] = []
		for asset in ranked:
			if asset.resource_id in seen:
				continue
			seen.add(asset.resource_id)
			deduped.append(asset)
			if len(deduped) >= max_results:
				break
		return deduped
