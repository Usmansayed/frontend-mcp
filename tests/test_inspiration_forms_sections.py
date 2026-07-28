"""Scope + pattern coverage for forms, inputs, sections, and pages."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_scope_input_and_auth_queries() -> None:
	from navigation.inspiration_intelligence.query_flex import resolve_flexible_query

	inp = resolve_flexible_query("text input with label and placeholder")
	assert inp.scope == "chrome"
	assert inp.intent_class == "auth"
	assert "input" in inp.search_query.lower()

	auth = resolve_flexible_query("login signup form with email password")
	assert auth.scope == "section"
	assert auth.intent_class == "auth"

	checkout = resolve_flexible_query("checkout payment form multi step")
	assert checkout.scope == "section"
	assert checkout.intent_class == "checkout"

	drop = resolve_flexible_query("dropdown select combobox menu")
	assert drop.scope == "component"


def test_search_bar_not_stolen_by_button() -> None:
	from navigation.inspiration_intelligence.query_flex import resolve_flexible_query

	sb = resolve_flexible_query("search bar with icon and clear button")
	assert sb.scope == "component"
	assert "search" in sb.search_query.lower()


def test_daisy_slugs_for_form_controls() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import (
		load_pattern_sources,
		resolve_daisy_slugs,
	)

	load_pattern_sources.cache_clear()
	assert "input" in resolve_daisy_slugs("text input field")
	assert "textarea" in resolve_daisy_slugs("textarea multiline text field")
	cb = resolve_daisy_slugs("checkbox toggle switch")
	assert "checkbox" in cb
	assert len(cb) >= 3
	# dead form.webp remapped — form asks expand to input pack
	form = resolve_daisy_slugs("contact form section")
	assert "form" not in form
	assert "input" in form
	assert len(form) >= 3


def test_auth_checkout_specialists() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import (
		load_pattern_sources,
		select_specialist_targets,
	)

	load_pattern_sources.cache_clear()
	login_ids = {t["id"] for t in select_specialist_targets("login signup form", scope="section")}
	assert login_ids & {"saasframe_login", "saasframe_signup", "nicelydone_auth"}
	co_ids = {t["id"] for t in select_specialist_targets("checkout payment form", scope="section")}
	assert "saasframe_checkout" in co_ids


def test_region_crop_input_query_not_nav_first() -> None:
	from navigation.inspiration_intelligence.region_focus import selectors_for_scope

	sels = selectors_for_scope("chrome", "text input with label")
	assert sels
	assert sels[0] not in {"header", "nav", '[role="banner"]', '[role="navigation"]'}
	btn = selectors_for_scope("chrome", "primary button")
	assert btn[0] in {"button", "[role=\"button\"]", "[class*=\"btn\" i]", "a.button"}
