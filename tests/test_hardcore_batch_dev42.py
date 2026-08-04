"""Failure-retest leftovers — pattern provider + SPA settle wait."""

from __future__ import annotations

import asyncio

import pytest

from navigation.resource_intelligence.models import ResourceCategory
from navigation.resource_intelligence.providers.hero_patterns.provider import HeroPatternsProvider
from navigation.resource_intelligence.providers.manager import ResourceProviderManager
from navigation.visual_browser_intelligence.observe.preflight import wait_for_spa_navigation_settle


@pytest.mark.unit
def test_hero_patterns_provider_is_live() -> None:
	mgr = ResourceProviderManager()
	assert "hero-patterns" in mgr.list_live_providers()
	assert mgr.get("hero-patterns") is not None


@pytest.mark.unit
def test_hero_patterns_search_returns_assets() -> None:
	provider = HeroPatternsProvider()
	assets, degraded = asyncio.run(
		provider.search("circuit", category=ResourceCategory.PATTERN, max_results=6)
	)
	assert assets
	assert any("circuit" in a.title.lower() or "circuit" in a.resource_id for a in assets)
	assert all(a.provider_id == "hero-patterns" for a in assets)
	assert "no_live_providers_for_query" not in degraded


@pytest.mark.unit
def test_spa_settle_waits_for_url_change() -> None:
	from navigation.visual_browser_intelligence.observe import preflight as pf

	calls = {"n": 0}
	seq = [
		{"url": "http://127.0.0.1:3001/about", "title": "About", "ready": "complete"},
		{"url": "http://127.0.0.1:3001/work", "title": "About", "ready": "complete"},
		{"url": "http://127.0.0.1:3001/work", "title": "Projects", "ready": "complete"},
		{"url": "http://127.0.0.1:3001/work", "title": "Projects", "ready": "complete"},
		{"url": "http://127.0.0.1:3001/work", "title": "Projects", "ready": "complete"},
	]

	async def fake_eval(session, expr):  # noqa: ANN001
		_ = session, expr
		i = min(calls["n"], len(seq) - 1)
		calls["n"] += 1
		return seq[i]

	orig = pf.evaluate_js
	pf.evaluate_js = fake_eval  # type: ignore[assignment]
	try:
		out = asyncio.run(
			wait_for_spa_navigation_settle(
				object(),
				url_before="http://127.0.0.1:3001/about",
				timeout=2.0,
				poll=0.01,
				stable_polls=2,
			)
		)
	finally:
		pf.evaluate_js = orig  # type: ignore[assignment]
	assert out["changed"] is True
	assert out["url"].endswith("/work")
	assert out["title"] == "Projects"
	assert out.get("ok") is True
