"""P1/P2: auth relevance, soft-floor, region crop, specialist force."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_sign_in_page_relevance() -> None:
	from navigation.inspiration_intelligence.query_flex import hit_relevance_score, is_relevant_hit

	q = "login signup form with email password"
	assert is_relevant_hit(q, title="Sign in page", search_query="login signup form ui design")
	assert hit_relevance_score(q, title="Sign-in authentication", search_query=q) >= 0.18
	assert hit_relevance_score(q, title="Dark Mode Design #1", search_query=q) < 0.18


def test_force_specialists_for_auth_intent() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import (
		force_specialists_for_intent,
		load_pattern_sources,
	)

	load_pattern_sources.cache_clear()
	ids = {g["id"] for g in force_specialists_for_intent("auth")}
	assert ids >= {"saasframe_login", "saasframe_signup", "nicelydone_auth"}
	assert force_specialists_for_intent("checkout")[0]["id"] == "saasframe_checkout"


def test_search_bar_skips_button_only_specialists() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import (
		load_pattern_sources,
		select_specialist_targets,
	)

	load_pattern_sources.cache_clear()
	ids = {t["id"] for t in select_specialist_targets("search bar with icon and clear button")}
	assert "aceternity_buttons" not in ids
	assert "ibelick_buttons" not in ids


def test_region_crop_input_before_nav() -> None:
	from navigation.inspiration_intelligence.region_focus import selectors_for_scope

	sels = selectors_for_scope("chrome", "text input with label")
	assert sels
	assert sels[0] in {
		"textarea",
		'input:not([type="hidden"])',
		'[role="textbox"]',
		'[class*="input" i]',
		"form",
		"label",
	}
	search = selectors_for_scope("component", "search bar with icon")
	assert search[0] in {
		'input[type="search"]',
		'[role="search"]',
		'[class*="search" i]',
		"input",
		"form",
	}
	form = selectors_for_scope("section", "login signup form")
	assert form[0] in {"form", '[class*="form" i]', '[class*="login" i]', '[class*="auth" i]'}


def test_daisy_live_slugs_exist_in_map() -> None:
	"""Unit map check — no network. Ensures dead form.webp is not primary."""
	from navigation.inspiration_intelligence.pattern_acquire import (
		load_pattern_sources,
		resolve_daisy_slugs,
	)

	load_pattern_sources.cache_clear()
	cfg = load_pattern_sources()
	block = next(b for b in cfg["component_docs_cdn"] if b["id"] == "daisyui_components")
	mapping = block["map"]
	assert mapping.get("textarea") == "textarea"
	assert mapping.get("form") == "input"  # dead form.webp remapped
	assert "textarea" in resolve_daisy_slugs("textarea multiline")
	assert "form" not in resolve_daisy_slugs("contact form")
