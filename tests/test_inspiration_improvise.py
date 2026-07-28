"""Inspiration layer improvisations — disk cache, chrome sources, crop, VF."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_disk_affinity_survives_clear_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setenv("INSPIRATION_CACHE_DIR", str(tmp_path))
	# Re-import modules so they pick up cache dir — use functions after clearing
	from navigation.inspiration_intelligence import source_affinity as sa

	sa.clear_affinity()
	key = sa.affinity_key(scope="chrome", intent_class="", query="primary button")
	sa.record_winners(key, ["aceternity_buttons", "daisyui"])
	assert sa.prefer_providers(key)[0] == "aceternity_buttons"
	# Simulate process restart: wipe memory, reload from disk
	sa._WINS.clear()
	sa._LOADED = False
	assert sa.prefer_providers(key)[0] == "aceternity_buttons"
	sa.clear_affinity()


def test_disk_serp_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setenv("INSPIRATION_CACHE_DIR", str(tmp_path))
	from navigation.inspiration_intelligence import serp_cache as sc

	sc.clear_serp_cache()
	fp = sc.serp_fingerprint("modal ui", limit=4)
	sc.put_serp(fp, {"engine": "test", "hits": [{"title": "A", "url": "https://a.test", "host": "a.test"}], "degraded": []})
	sc._CACHE.clear()
	sc._LOADED = False
	cached = sc.get_serp(fp)
	assert cached and cached["hits"]
	sc.clear_serp_cache()


def test_chrome_specialists_include_button_sources() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import (
		load_pattern_sources,
		select_specialist_targets,
	)

	load_pattern_sources.cache_clear()
	targets = select_specialist_targets("primary button hover states", scope="chrome")
	ids = {str(t.get("id")) for t in targets}
	assert ids & {"aceternity_buttons", "ibelick_buttons", "shadcnblocks"}


def test_query_aware_region_crop_button_before_nav() -> None:
	from navigation.inspiration_intelligence.region_focus import selectors_for_scope

	sels = selectors_for_scope("chrome", "primary button hover")
	assert sels[0] in {"button", "[role=\"button\"]", "[class*=\"btn\" i]", "a.button"}
	nav = selectors_for_scope("chrome", "navbar mega menu")
	assert nav[0] in {"nav", "header", "[role=\"navigation\"]", "[role=\"banner\"]"}


def test_design_vf_vs_inspiration_when_locked() -> None:
	from navigation.visual_browser_intelligence.visual.visual_feedback_policy import (
		PURPOSE_DESIGN,
		build_purpose_next_actions,
	)

	actions = build_purpose_next_actions(
		purpose=PURPOSE_DESIGN,
		tool="perception_visual_feedback",
		envelope={"ok": True, "data": {}},
		feedback={
			"judgment": "needs_work",
			"look_lock": {"density": "tight"},
			"primary_ref_ids": ["ref_1"],
		},
	)
	kinds = [a.get("action") for a in actions]
	assert "revise_vs_inspiration" in kinds

	plain = build_purpose_next_actions(
		purpose=PURPOSE_DESIGN,
		tool="perception_visual_feedback",
		envelope={"ok": True, "data": {}},
		feedback={"judgment": "needs_work", "notes": "no lock"},
	)
	assert "revise_vs_inspiration" not in [a.get("action") for a in plain]


def test_affinity_maps_new_chrome_providers() -> None:
	from navigation.inspiration_intelligence.source_affinity import prefer_categories_from_providers

	cats = prefer_categories_from_providers(["aceternity_buttons", "navbar_gallery"])
	assert "component_showcase" in cats
	assert "navigation" in cats
