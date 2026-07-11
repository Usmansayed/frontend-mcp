"""Shared resource collection — used by MCP handlers and CLI."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from navigation.resource_intelligence.license.policy import automation_advisory
from navigation.resource_intelligence.models import ResourceDiscoveryRequest
from navigation.resource_intelligence.planning.orchestrator import ResourceSearchOrchestrator
from navigation.resource_intelligence.tools.blob_store import ResourceBlobStore
from navigation.resource_intelligence.tools.media_urls import agent_view_url


@dataclass
class ResourceHit:
	resource_id: str
	provider_id: str
	title: str
	category: str
	preview_url: str = ''
	access_url: str = ''
	agent_view_url: str = ''
	format: str = ''
	attribution_text: str = ''
	resource_blob: str = ''
	blob_session_id: str = ''
	blob_expires_at: str = ''
	blob_skipped: bool = False
	skip_blob_reason: str = ''
	license_warnings: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)
	metadata: dict[str, Any] = field(default_factory=dict)


def _asset_to_hit(asset_dict: dict[str, Any], *, license_warnings: list[str]) -> ResourceHit:
	license_data = asset_dict.get('license') or {}
	warnings = list(license_warnings)
	if license_data:
		from navigation.resource_intelligence.models import LicenseProfile

		profile = LicenseProfile(
			spdx_id=str(license_data.get('spdx_id') or 'UNKNOWN'),
			commercial_use=bool(license_data.get('commercial_use')),
			attribution_required=bool(license_data.get('attribution_required')),
			mcp_download_allowed=bool(license_data.get('mcp_download_allowed', True)),
			api_automation_allowed=bool(license_data.get('api_automation_allowed', True)),
		)
		warnings.extend(automation_advisory(profile))
	preview = str(asset_dict.get('preview_url') or '')
	access = str(asset_dict.get('access_url') or '')
	metadata = dict(asset_dict.get('metadata') or {})
	skip_blob = False
	skip_reason = ''
	if metadata.get('family_match') and metadata.get('delivery') == 'url_only':
		skip_blob = True
		skip_reason = 'icon_family_url_only'
	elif str(asset_dict.get('category') or '') == 'icon' and metadata.get('family_match'):
		skip_blob = True
		skip_reason = 'icon_family_match'
	if license_data and not license_data.get('mcp_download_allowed', True):
		skip_blob = True
		skip_reason = 'mcp_download_restricted'
	if license_data and not license_data.get('api_automation_allowed', True):
		skip_blob = True
		skip_reason = 'automation_restricted'
	category = str(asset_dict.get('category') or '')
	if category == 'font':
		skip_blob = True
		skip_reason = 'font_metadata_only'
	return ResourceHit(
		resource_id=str(asset_dict.get('resource_id') or ''),
		provider_id=str(asset_dict.get('provider_id') or ''),
		title=str(asset_dict.get('title') or ''),
		category=category,
		preview_url=preview,
		access_url=access,
		agent_view_url=agent_view_url(access_url=access, preview_url=preview),
		format=str(asset_dict.get('format') or ''),
		attribution_text=str(asset_dict.get('attribution_text') or ''),
		blob_skipped=skip_blob,
		skip_blob_reason=skip_reason,
		license_warnings=sorted(set(warnings)),
		metadata=metadata,
	)


async def collect_resource_assets(
	query: str,
	*,
	max_results: int = 12,
	categories: list[str] | None = None,
	provider_preference: str | None = None,
	icon_family: str | None = None,
	icon_family_strict: bool = True,
	allow_family_fallback: bool = True,
	persist_icon_family: bool = False,
	repo_root: str = '',
	materialize_blobs: bool | None = None,
	blob_fallback_only: bool = True,
	reference_preview_url: str = '',
	reference_image_path: str = '',
	blob_session_id: str | None = None,
	output_dir: Path | None = None,
	asset_ids: list[str] | None = None,
) -> dict[str, Any]:
	"""Search + optional ephemeral preview blobs for agent vision."""
	from navigation.resource_intelligence.models import ResourceCategory

	cat_enums: list[ResourceCategory] = []
	for raw in categories or []:
		try:
			cat_enums.append(ResourceCategory(str(raw)))
		except ValueError:
			continue

	request = ResourceDiscoveryRequest(
		query=query,
		categories=cat_enums,
		max_results=max_results,
		provider_preference=provider_preference,
		icon_family=icon_family,
		icon_family_strict=icon_family_strict,
		allow_family_fallback=allow_family_fallback,
		persist_icon_family=persist_icon_family,
		repo_root=repo_root,
	)
	orchestrator = ResourceSearchOrchestrator()
	result = await orchestrator.search(request)

	asset_dicts = [a.to_dict() for a in result.assets]
	if asset_ids:
		want = set(asset_ids)
		asset_dicts = [a for a in asset_dicts if a.get('resource_id') in want]

	hits = [_asset_to_hit(a, license_warnings=result.license_warnings) for a in asset_dicts]

	# Family miss + reference image → vision/OCR fallback blob (not for in-family icons).
	if not hits and (reference_preview_url or reference_image_path):
		ref_url = reference_preview_url.strip()
		ref_path = reference_image_path.strip()
		preview = ref_url
		if not preview and ref_path:
			preview = Path(ref_path).resolve().as_uri()
		hits.append(
			ResourceHit(
				resource_id=f'vision-fallback:{query}',
				provider_id='vision-fallback',
				title=f'Reference icon for {query}',
				category='icon',
				preview_url=preview,
				access_url=preview,
				agent_view_url=preview,
				format='reference',
				blob_skipped=False,
				skip_blob_reason='family_miss_vision_fallback',
				metadata={
					'family_match': False,
					'delivery': 'vision_fallback',
					'icon_family': result.icon_family or '',
					'advisory': 'Use perception_observe or OCR on reference; no match in icon family',
				},
			)
		)
		result.degraded.append('icon_family_vision_fallback')

	if blob_fallback_only:
		for hit in hits:
			if hit.blob_skipped:
				continue
			if hit.category == 'icon' and hit.metadata.get('family_match'):
				hit.blob_skipped = True
				hit.skip_blob_reason = 'icon_family_url_only'

	hit_dicts = [asdict(h) for h in hits]

	manifest: dict[str, Any] = {
		'query': query,
		'collected_at': datetime.now(timezone.utc).isoformat(),
		'mode': 'urls_first',
		'icon_family': result.icon_family,
		'family_match': result.family_match,
		'fallback_used': result.fallback_used,
		'providers_queried': list(result.providers_queried),
		'license_warnings': list(result.license_warnings),
		'degraded': list(result.degraded),
		'total_hits': len(hit_dicts),
		'total_with_urls': sum(1 for h in hits if h.agent_view_url),
		'hits': hit_dicts,
	}

	if output_dir is not None:
		output_dir.mkdir(parents=True, exist_ok=True)
		manifest_path = output_dir / 'manifest.json'
		manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

	if materialize_blobs is None:
		materialize_blobs = os.environ.get('RESOURCE_BLOBS', '1') != '0'

	blob_summary: dict[str, object] = {}
	if materialize_blobs and hit_dicts:
		blob_targets = [h for h in hit_dicts if not h.get('blob_skipped')]
		if blob_targets:
			store = ResourceBlobStore()
			session_id = blob_session_id or store.create_session(purpose=query)
			blob_summary = store.materialize_hits(session_id, blob_targets)
			for hit in hit_dicts:
				match = next(
					(h for h in blob_targets if h.get('resource_id') == hit.get('resource_id')),
					None,
				)
				if match:
					hit['resource_blob'] = match.get('resource_blob', '')
					hit['blob_session_id'] = match.get('blob_session_id', '')
					hit['blob_expires_at'] = match.get('blob_expires_at', '')
			manifest['hits'] = hit_dicts
			manifest['blob_session_id'] = session_id
			manifest['mode'] = 'urls_and_ephemeral_blobs'
			manifest['blob_summary'] = blob_summary
			if output_dir is not None:
				(output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

	return manifest
