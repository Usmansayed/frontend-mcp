"""Per-website SEO profile — auto-discovered IDs, no user configuration."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.seo_intelligence.config.defaults import default_seo_cache_dir
from navigation.seo_intelligence.setup.discovery import domain_from_website, normalize_website_url


@dataclass(slots=True)
class SeoSiteProfile:
	website_url: str
	domain: str
	gsc_property_url: str = ''
	ga4_property_id: str = ''
	bing_site_url: str = ''
	google_connected: bool = False
	bing_connected: bool = False
	auto_configured: bool = False
	discovery_notes: list[str] = field(default_factory=list)
	advanced_overrides: dict[str, str] = field(default_factory=dict)
	updated_at: float = 0.0

	def to_dict(self) -> dict[str, Any]:
		return {
			'website_url': self.website_url,
			'domain': self.domain,
			'gsc_property_url': self.gsc_property_url,
			'ga4_property_id': self.ga4_property_id,
			'bing_site_url': self.bing_site_url,
			'google_connected': self.google_connected,
			'bing_connected': self.bing_connected,
			'auto_configured': self.auto_configured,
			'discovery_notes': list(self.discovery_notes),
			'advanced_overrides': dict(self.advanced_overrides),
			'updated_at': self.updated_at,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> SeoSiteProfile:
		return cls(
			website_url=str(data.get('website_url') or ''),
			domain=str(data.get('domain') or ''),
			gsc_property_url=str(data.get('gsc_property_url') or ''),
			ga4_property_id=str(data.get('ga4_property_id') or ''),
			bing_site_url=str(data.get('bing_site_url') or ''),
			google_connected=bool(data.get('google_connected')),
			bing_connected=bool(data.get('bing_connected')),
			auto_configured=bool(data.get('auto_configured')),
			discovery_notes=list(data.get('discovery_notes') or []),
			advanced_overrides={str(k): str(v) for k, v in (data.get('advanced_overrides') or {}).items()},
			updated_at=float(data.get('updated_at') or 0.0),
		)


class SeoSiteStore:
	def __init__(self, *, path: Path | None = None) -> None:
		cache = default_seo_cache_dir()
		cache.mkdir(parents=True, exist_ok=True)
		self._path = path or cache / 'seo_sites.json'
		self._data: dict[str, Any] | None = None

	def _load(self) -> dict[str, Any]:
		if self._data is not None:
			return self._data
		if self._path.is_file():
			try:
				self._data = json.loads(self._path.read_text(encoding='utf-8'))
				return self._data
			except json.JSONDecodeError:
				pass
		self._data = {'version': 1, 'sites': {}}
		return self._data

	def _key(self, website_url: str) -> str:
		return domain_from_website(website_url)

	def get(self, website_url: str) -> SeoSiteProfile | None:
		data = self._load()
		sites: dict[str, Any] = data.get('sites') or {}
		raw = sites.get(self._key(website_url))
		if not isinstance(raw, dict):
			return None
		return SeoSiteProfile.from_dict(raw)

	def save(self, profile: SeoSiteProfile) -> None:
		data = self._load()
		sites: dict[str, Any] = data.setdefault('sites', {})
		profile.updated_at = time.time()
		sites[self._key(profile.website_url)] = profile.to_dict()
		self._path.parent.mkdir(parents=True, exist_ok=True)
		self._path.write_text(json.dumps(data, indent=2), encoding='utf-8')

	def ensure(self, website_url: str) -> SeoSiteProfile:
		existing = self.get(website_url)
		if existing is not None:
			return existing
		normalized = normalize_website_url(website_url)
		profile = SeoSiteProfile(
			website_url=normalized,
			domain=domain_from_website(normalized),
		)
		self.save(profile)
		return profile
