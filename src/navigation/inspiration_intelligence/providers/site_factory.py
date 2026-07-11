"""Factory for resilient gallery site providers."""
from __future__ import annotations

from navigation.inspiration_intelligence.browser.extract_scripts import (
	AWWWARDS_EXTRACT,
	GODLY_EXTRACT,
	LANDBOOK_EXTRACT,
	SITEINSPIRE_EXTRACT,
)
from navigation.inspiration_intelligence.browser.resilient_fetch import ResilientFetchConfig
from navigation.inspiration_intelligence.providers.awwwards.navigation import AWWWARDS_NAVIGATION
from navigation.inspiration_intelligence.providers.behance.navigation import BEHANCE_NAVIGATION
from navigation.inspiration_intelligence.providers.gallery_parse import (
	awwwards_search_urls,
	behance_search_urls,
	godly_search_urls,
	landbook_search_urls,
	onepagelove_search_urls,
	parse_awwwards_html,
	parse_behance_html,
	parse_godly_html,
	parse_landbook_html,
	parse_onepagelove_html,
	parse_siteinspire_html,
	siteinspire_search_urls,
)
from navigation.inspiration_intelligence.providers.gallery_provider import GallerySiteProvider
from navigation.inspiration_intelligence.providers.godly.navigation import GODLY_NAVIGATION
from navigation.inspiration_intelligence.providers.land_book.navigation import LANDBOOK_NAVIGATION
from navigation.inspiration_intelligence.providers.one_page_love.navigation import ONEPAGELOVE_NAVIGATION
from navigation.inspiration_intelligence.providers.siteinspire.navigation import SITEINSPIRE_NAVIGATION


def build_behance_provider() -> GallerySiteProvider:
	return GallerySiteProvider(
		BEHANCE_NAVIGATION,
		ResilientFetchConfig(
			provider_id='behance',
			parse_html=parse_behance_html,
			build_urls=behance_search_urls,
			link_selector='a[href*="/gallery/"]',
			id_regex=r'/gallery/(\d+)',
		),
	)


def build_awwwards_provider() -> GallerySiteProvider:
	return GallerySiteProvider(
		AWWWARDS_NAVIGATION,
		ResilientFetchConfig(
			provider_id='awwwards',
			parse_html=parse_awwwards_html,
			build_urls=awwwards_search_urls,
			extract_script=AWWWARDS_EXTRACT,
			prefer_browser=True,
			ready_timeout=25.0,
			hydration_s=6.0,
		),
	)


def build_siteinspire_provider() -> GallerySiteProvider:
	return GallerySiteProvider(
		SITEINSPIRE_NAVIGATION,
		ResilientFetchConfig(
			provider_id='siteinspire',
			parse_html=parse_siteinspire_html,
			build_urls=siteinspire_search_urls,
			extract_script=SITEINSPIRE_EXTRACT,
			prefer_browser=True,
			ready_timeout=22.0,
			hydration_s=5.0,
		),
	)


def build_godly_provider() -> GallerySiteProvider:
	return GallerySiteProvider(
		GODLY_NAVIGATION,
		ResilientFetchConfig(
			provider_id='godly',
			parse_html=parse_godly_html,
			build_urls=godly_search_urls,
			extract_script=GODLY_EXTRACT,
			prefer_browser=True,
			ready_timeout=25.0,
			hydration_s=7.0,
		),
	)


def build_landbook_provider() -> GallerySiteProvider:
	return GallerySiteProvider(
		LANDBOOK_NAVIGATION,
		ResilientFetchConfig(
			provider_id='land-book',
			parse_html=parse_landbook_html,
			build_urls=landbook_search_urls,
			extract_script=LANDBOOK_EXTRACT,
			browser_required=True,
			ready_timeout=30.0,
			hydration_s=8.0,
			max_browser_retries=3,
		),
	)


def build_onepagelove_provider() -> GallerySiteProvider:
	return GallerySiteProvider(
		ONEPAGELOVE_NAVIGATION,
		ResilientFetchConfig(
			provider_id='onepagelove',
			parse_html=parse_onepagelove_html,
			build_urls=onepagelove_search_urls,
			link_selector='a[href^="https://onepagelove.com/"]',
			id_regex=r'onepagelove\.com/([a-z0-9-]+)',
		),
	)
