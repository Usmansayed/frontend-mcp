from navigation.inspiration_intelligence.browser.fetch import enrich_preview_from_detail, extract_og_image, http_get
from navigation.inspiration_intelligence.browser.perception_runtime import PerceptionBrowserRuntime
from navigation.inspiration_intelligence.browser.policy import (
	ProviderFetchPolicy,
	RateLimitTracker,
	detect_block_signal,
	load_global_policy,
)
from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession

__all__ = [
	'InspirationBrowserSession',
	'PerceptionBrowserRuntime',
	'ProviderFetchPolicy',
	'RateLimitTracker',
	'detect_block_signal',
	'enrich_preview_from_detail',
	'extract_og_image',
	'http_get',
	'load_global_policy',
	'recovery_status',
]

def __getattr__(name: str):
	if name == 'recovery_status':
		from navigation.inspiration_intelligence.browser.scrapling_route import recovery_status

		return recovery_status
	raise AttributeError(name)
