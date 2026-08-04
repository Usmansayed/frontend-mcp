"""Tests for inspiration sources corpus loader."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_corpus_loads_and_has_showcases() -> None:
	from navigation.inspiration_intelligence.inspiration_sources import (
		list_candidate_providers,
		load_inspiration_sources_corpus,
		select_screenshot_demos,
	)

	corpus = load_inspiration_sources_corpus()
	assert corpus.get("schema") == "inspiration_sources_corpus.v1"
	cats = corpus.get("categories") or {}
	assert "landing_gallery" in cats
	assert "component_showcase" in cats
	assert "shadcn_ui" in [s["id"] for s in cats["component_showcase"]["sources"]]

	demos = select_screenshot_demos(intent_text="saas landing with motion", max_demos=2)
	assert len(demos) >= 1
	assert demos[0]["url"].startswith("http")
	assert demos[0]["source_kind"] == "screenshot_demo"

	cands = list_candidate_providers()
	assert "landing_love" in cands
	assert "saas_interface" in cands
