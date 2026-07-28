"""Flexible inspiration queries — page / section / component / chrome."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_scope_navbar_and_button() -> None:
	from navigation.inspiration_intelligence.query_flex import (
		hit_relevance_score,
		resolve_flexible_query,
	)

	nav = resolve_flexible_query("navbar with mega menu")
	assert nav.scope == "component"
	assert nav.intent_class == "navigation"
	assert "navigation" in nav.search_query.lower() or "menu" in nav.search_query.lower()
	assert "component_showcase" in nav.prefer_categories

	btn = resolve_flexible_query("primary button hover")
	assert btn.scope == "chrome"

	page = resolve_flexible_query("saas landing page")
	assert page.scope == "page"


def test_relevance_rejects_unrelated_titles() -> None:
	from navigation.inspiration_intelligence.query_flex import hit_relevance_score, is_relevant_hit

	q = "navbar with mega menu"
	assert is_relevant_hit(q, title="Mega Menu Navigation Header", search_query=q)
	assert not is_relevant_hit(q, title="PP Neue Montreal", search_query=q)
	assert hit_relevance_score(q, title="Website Header Nav", search_query=q) > 0.18


def test_enough_relevant_not_any_three() -> None:
	from navigation.inspiration_intelligence.planning.progressive_search import (
		has_enough_relevant_refs,
	)

	junk = [
		{"preview_url": "https://cdn.example.com/1.jpg", "title": "PP Neue Montreal"},
		{"preview_url": "https://cdn.example.com/2.jpg", "title": "SimpleSketche"},
		{"preview_url": "https://cdn.example.com/3.jpg", "title": "RSquad"},
	]
	assert not has_enough_relevant_refs(
		junk, query="navbar mega menu", search_query="website navigation header menu", min_refs=2, target_refs=3
	)
	good = [
		{"preview_url": "https://cdn.example.com/1.jpg", "title": "Mega menu navigation"},
		{"preview_url": "https://cdn.example.com/2.jpg", "title": "Header nav website"},
	]
	assert has_enough_relevant_refs(
		good, query="navbar mega menu", search_query="website navigation header menu", min_refs=2, target_refs=3
	)
