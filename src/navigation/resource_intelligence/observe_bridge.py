"""Observe bridge — connect perception_observe scans to Resource Intelligence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.resource_intelligence.collect import collect_resource_assets
from navigation.resource_intelligence.models import ResourceCategory, ResourceDiscoveryRequest
from navigation.resource_intelligence.planning.orchestrator import ResourceSearchOrchestrator
from navigation.resource_intelligence.planning.icon_family import resolve_icon_family


async def resolve_from_observe(
	*,
	scan_id: str,
	query: str,
	scans: Any,
	repo_root: str = '',
	icon_family: str | None = None,
	max_results: int = 5,
) -> dict[str, Any]:
	"""Auto-bridge: scan screenshot → family search → vision fallback on miss."""
	degraded: list[str] = []
	rec = scans.get(scan_id) if scans is not None else None
	if rec is None:
		return {'ok': False, 'degraded': ['scan_not_found'], 'hits': []}

	obs = getattr(rec, 'observation', {}) or {}
	screenshot_path = str(obs.get('screenshot_path') or '')
	preview_url = ''
	if screenshot_path and Path(screenshot_path).is_file():
		preview_url = Path(screenshot_path).resolve().as_uri()

	request = ResourceDiscoveryRequest(
		query=query,
		categories=[ResourceCategory.ICON],
		max_results=max_results,
		icon_family=icon_family,
		repo_root=repo_root,
		scan_id=scan_id,
		auto_observe_bridge=True,
	)
	family = resolve_icon_family(request, project_root=Path(repo_root) if repo_root else None)
	if family and not request.icon_family:
		request.icon_family = family.family_id

	orchestrator = ResourceSearchOrchestrator()
	result = await orchestrator.search(request)

	if result.assets:
		return {
			'ok': True,
			'bridge': 'family_match',
			'icon_family': result.icon_family,
			'family_match': result.family_match,
			'selection': result.selection.to_dict() if result.selection else None,
			'assets': [a.to_dict() for a in result.assets],
			'reference_scan_id': scan_id,
			'degraded': result.degraded,
		}

	if not preview_url:
		degraded.append('no_screenshot_for_vision_fallback')
		return {
			'ok': False,
			'bridge': 'family_miss_no_screenshot',
			'icon_family': result.icon_family,
			'degraded': result.degraded + degraded,
			'advisory': 'Run perception_observe with screenshot for vision fallback',
		}

	manifest = await collect_resource_assets(
		query,
		max_results=max_results,
		icon_family=request.icon_family,
		reference_preview_url=preview_url,
		materialize_blobs=True,
		blob_fallback_only=True,
		repo_root=repo_root,
	)
	return {
		'ok': bool(manifest.get('hits')),
		'bridge': 'vision_fallback',
		'icon_family': manifest.get('icon_family'),
		'manifest': manifest,
		'reference_scan_id': scan_id,
		'degraded': list(manifest.get('degraded') or []) + degraded,
	}
