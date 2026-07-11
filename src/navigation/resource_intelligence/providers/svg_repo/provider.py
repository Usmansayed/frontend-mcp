"""SVG Repo provider — svgapi.com search with per-asset NC filter."""
from __future__ import annotations

import os
import re
import urllib.parse

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import LicenseProfile, ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_API_BASE = 'https://api.svgapi.com/v1'
_NC_PATTERN = re.compile(r'nc|non[- ]?commercial|by-nc', re.I)


def _api_key() -> str:
	return (
		os.environ.get('SVG_REPO_API_KEY', '').strip()
		or os.environ.get('SVGAPI_DOMAIN_KEY', '').strip()
	)


def _is_non_commercial_license(license_text: str) -> bool:
	return bool(_NC_PATTERN.search(license_text or ''))


def _license_from_asset(raw: str) -> LicenseProfile:
	text = (raw or '').strip()
	if _is_non_commercial_license(text):
		return LicenseProfile(
			spdx_id='CC-BY-NC',
			commercial_use=False,
			attribution_required=True,
			mcp_download_allowed=False,
			source_url='https://www.svgrepo.com/page/licensing',
			notes=['Non-commercial asset — skipped in commercial_only mode'],
		)
	attribution = 'by' in text.lower() or 'attribution' in text.lower()
	return LicenseProfile(
		spdx_id=text or 'PD/CC',
		commercial_use=True,
		attribution_required=attribution,
		mcp_download_allowed=True,
		source_url='https://www.svgrepo.com/page/licensing',
		notes=['Commercial OK; verify license on SVG Repo page if attribution required'],
	)


class SvgRepoProvider:
	provider_id = 'svg-repo'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		key = _api_key()
		if not key:
			return [], ['svg_repo_api_key_missing:set_SVG_REPO_API_KEY_or_SVGAPI_DOMAIN_KEY']
		degraded: list[str] = []
		q = urllib.parse.quote(query.strip())
		limit = max(1, min(max_results, 20))
		commercial_only = os.environ.get('SVG_REPO_COMMERCIAL_ONLY', '1').strip().lower() not in ('0', 'false', 'no')
		nc_param = '&nc=true' if commercial_only else ''
		try:
			payload = await fetch_json(
				f'{_API_BASE}/{urllib.parse.quote(key)}/list/?search={q}&limit={limit}{nc_param}',
			)
		except Exception as exc:
			return [], [f'svg_repo_search_failed:{exc}']

		items = payload if isinstance(payload, list) else list(payload.get('icons') or payload.get('results') or payload.get('data') or [])
		if not items and isinstance(payload, dict):
			items = [payload]
		assets: list[ResourceAssetRef] = []
		skipped_nc = 0
		for item in items:
			if not isinstance(item, dict):
				continue
			icon_id = str(item.get('id') or item.get('slug') or item.get('hash') or '')
			title = str(item.get('title') or item.get('name') or icon_id or 'SVG')
			license_raw = str(item.get('license') or item.get('license_type') or item.get('licence') or '')
			profile = _license_from_asset(license_raw)
			if commercial_only and not profile.commercial_use:
				skipped_nc += 1
				continue
			svg_url = str(
				item.get('svg_url')
				or item.get('svg')
				or item.get('url')
				or item.get('download')
				or ''
			)
			page_url = str(item.get('page_url') or item.get('link') or item.get('permalink') or '')
			if not page_url and icon_id.isdigit():
				slug = re.sub(r'[^a-z0-9-]+', '-', title.lower()).strip('-')
				page_url = f'https://www.svgrepo.com/svg/{icon_id}/{slug}' if slug else f'https://www.svgrepo.com/svg/{icon_id}'
			if not svg_url and page_url:
				svg_url = page_url.replace('/svg/', '/show/') if '/svg/' in page_url else page_url
			rid = f'svg-repo:{icon_id or title}'
			assets.append(
				ResourceAssetRef(
					resource_id=rid,
					provider_id=self.provider_id,
					category=ResourceCategory.SVG if category != ResourceCategory.GRAPHIC else ResourceCategory.GRAPHIC,
					title=title,
					preview_url=svg_url or page_url,
					access_url=svg_url or page_url,
					license=profile,
					tags=[query, title, 'svg'],
					format='svg',
					score=0.72,
					attribution_text=f'Attribution required — see {page_url}' if profile.attribution_required else '',
					metadata={
						'svg_repo_url': page_url,
						'license_raw': license_raw,
						'nc_filtered': commercial_only,
					},
				)
			)
		if skipped_nc:
			degraded.append(f'svg_repo_skipped_nc:{skipped_nc}')
		if not assets and items:
			degraded.append('svg_repo_all_results_filtered_or_unparsed')
		return assets[:max_results], degraded
