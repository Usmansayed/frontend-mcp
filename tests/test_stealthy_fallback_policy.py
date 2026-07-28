"""Unit tests for Scrapling recovery routing (no live network)."""
from __future__ import annotations

from navigation.inspiration_intelligence.browser import scrapling_route as route
from navigation.inspiration_intelligence.browser import stealthy_fallback as sf


def setup_function() -> None:
	sf.reset_stealthy_budget_for_tests()


def test_important_hosts():
	assert route.is_important_waf_host('https://dribbble.com/search/login')
	assert route.is_important_waf_host('https://www.lapa.ninja/?s=saas')
	assert route.is_important_waf_host('https://land-book.com/')
	assert route.is_important_waf_host('https://www.behance.net/search/projects?search=x')
	assert not route.is_important_waf_host('https://www.saasframe.io/categories/login')
	assert not route.is_important_waf_host('https://img.daisyui.com/images/components/input.webp')


def test_http_looks_blocked():
	assert route.http_looks_blocked(403, '<html>no</html>', None)
	assert route.http_looks_blocked(202, 'x', None)
	assert route.http_looks_blocked(None, '', 'timeout')
	assert not route.http_looks_blocked(200, '<html>' + ('a' * 5000) + 'og:image</html>', None)


def test_stealthy_allowed_on_important_even_in_fast(monkeypatch):
	monkeypatch.setenv('INSPIRATION_SCRAPLING_RECOVERY', '1')
	monkeypatch.delenv('INSPIRATION_STEALTHY_SKIP_IN_FAST', raising=False)
	monkeypatch.setenv('INSPIRATION_STEALTHY_BUDGET', '2')
	sf.reset_stealthy_budget_for_tests()

	# Important + blocked + fast → still eligible (recovery)
	assert route.should_try_stealthy(
		'https://dribbble.com/search/x',
		blocked=True,
		fast_mode=True,
		chromium_failed_or_skipped=True,
	)
	# Friendly CDN never
	assert not route.should_try_stealthy(
		'https://www.saasframe.io/',
		blocked=True,
		fast_mode=False,
		chromium_failed_or_skipped=True,
	)
	# Not blocked → no
	assert not route.should_try_stealthy(
		'https://dribbble.com/search/x',
		blocked=False,
		fast_mode=False,
		chromium_failed_or_skipped=True,
	)


def test_stealthy_skip_in_fast_opt_out(monkeypatch):
	monkeypatch.setenv('INSPIRATION_SCRAPLING_RECOVERY', '1')
	monkeypatch.setenv('INSPIRATION_STEALTHY_SKIP_IN_FAST', '1')
	monkeypatch.setenv('INSPIRATION_STEALTHY_BUDGET', '2')
	sf.reset_stealthy_budget_for_tests()
	assert not route.should_try_stealthy(
		'https://dribbble.com/search/x',
		blocked=True,
		fast_mode=True,
		chromium_failed_or_skipped=True,
	)


def test_stealthy_budget_exhaustion(monkeypatch):
	monkeypatch.setenv('INSPIRATION_STEALTHY_BUDGET', '1')
	sf.reset_stealthy_budget_for_tests()
	assert sf.stealthy_budget_remaining() == 1
	assert sf._consume_budget() is True
	assert sf.stealthy_budget_remaining() == 0
	assert not route.should_try_stealthy(
		'https://dribbble.com/search/x',
		blocked=True,
		fast_mode=False,
		chromium_failed_or_skipped=True,
	)


def test_recovery_status_shape():
	st = route.recovery_status()
	assert 'tls_available' in st
	assert 'stealthy_available' in st
	assert 'important_hosts' in st
	assert 'dribbble.com' in st['important_hosts']
