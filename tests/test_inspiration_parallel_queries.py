"""Parallel diverse query fan-out — not suffix expansion."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_diverse_queries_auth_standard_three_distinct() -> None:
	from navigation.inspiration_intelligence.parallel_queries import (
		build_diverse_queries,
		is_suffix_expansion,
	)
	from navigation.inspiration_intelligence.query_flex import resolve_flexible_query

	flex = resolve_flexible_query("login signup form with email password")
	qs = build_diverse_queries(flex, max_queries=3)
	assert len(qs) == 3
	# Three semantic angles — not rewritten seed + raw + one suffix
	assert not any(
		is_suffix_expansion(qs[0], q) for q in qs[1:]
	)
	joined = " ".join(qs).lower()
	assert "sign in" in joined or "signup" in joined or "registration" in joined
	assert "login" in joined


def test_diverse_queries_input_standard_three_distinct() -> None:
	from navigation.inspiration_intelligence.parallel_queries import build_diverse_queries
	from navigation.inspiration_intelligence.query_flex import resolve_flexible_query

	flex = resolve_flexible_query("text input with label and placeholder")
	qs = build_diverse_queries(flex, max_queries=3)
	assert len(qs) == 3
	joined = " ".join(qs).lower()
	assert joined.count("input") >= 2
	assert "placeholder" in joined or "label" in joined or "field" in joined


def test_diverse_queries_auth_are_distinct() -> None:
	from navigation.inspiration_intelligence.parallel_queries import (
		build_diverse_queries,
		is_suffix_expansion,
	)
	from navigation.inspiration_intelligence.query_flex import resolve_flexible_query

	flex = resolve_flexible_query("login signup form with email password")
	qs = build_diverse_queries(flex, max_queries=4)
	assert len(qs) >= 3
	pairs = [(qs[0], q) for q in qs[1:]]
	assert not all(is_suffix_expansion(a, b) for a, b in pairs)


def test_parallel_web_merges_hosts(monkeypatch) -> None:
	import asyncio

	from navigation.inspiration_intelligence.web_inspire import acquire_web_inspiration
	from navigation.inspiration_intelligence.web_search import WebSearchHit, WebSearchResult

	def fake_search(query: str, **kwargs):
		host = "a.test" if "login" in query.lower() else "b.test"
		return WebSearchResult(
			query=query,
			engine="fake",
			elapsed_ms=1.0,
			hits=[
				WebSearchHit(
					title=f"Hit for {query[:20]}",
					url=f"https://{host}/page",
					host=host,
					rank=0,
					score=10.0,
				)
			],
		)

	import navigation.inspiration_intelligence.web_inspire as wi

	monkeypatch.setattr(wi, "search_web", fake_search)

	async def _run():
		return await acquire_web_inspiration(
			"login form",
			scope="section",
			max_search=4,
			max_og=2,
			max_screenshots=0,
			parallel_queries=[
				"login form email password ui",
				"sign in page design examples",
			],
		)

	res = asyncio.run(_run())
	assert res.search_hits >= 2
	assert "parallel_web_queries" in " ".join(res.degraded)
