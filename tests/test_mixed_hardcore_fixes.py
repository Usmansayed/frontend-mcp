"""Unit coverage for Run-5 MIXED improvemements (diff, graph root, forms, fonts, icons, docs)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.mark.unit
def test_session_capture_names_are_unique() -> None:
	from navigation.visual_browser_intelligence.browser.session_store import SessionRecord

	rec = SessionRecord(
		session_id="s1",
		base_url="http://127.0.0.1:3001",
		browser=None,
		artifacts_dir=Path("."),
	)
	a = rec.next_capture_name("observe")
	b = rec.next_capture_name("observe")
	assert a != b
	assert a.startswith("observe-")
	assert b.startswith("observe-")


@pytest.mark.unit
def test_diff_same_file_degrades_instead_of_zero_ratio(tmp_path: Path) -> None:
	from navigation.frontend_quality_intelligence.diff import diff_observations

	shot = tmp_path / "same.png"
	shot.write_bytes(b"not-a-real-png")
	path = str(shot)
	before = {"url": "http://x/about", "dom_text": "About", "screenshot_path": path}
	after = {"url": "http://x/essays", "dom_text": "Essays", "screenshot_path": path}
	out = diff_observations(before, after, artifacts_dir=tmp_path, scan_id_before="a", scan_id_after="b")
	vd = out.get("visual_diff") or {}
	assert "before_and_after_screenshot_same_file" in (vd.get("degraded") or [])


@pytest.mark.unit
def test_icon_intent_strips_filler_tokens() -> None:
	from navigation.resource_intelligence.intent.parser import parse_intent

	intent = parse_intent("moon dark mode icon")
	assert intent.keywords == "moon"


@pytest.mark.unit
def test_font_style_hint_expansion() -> None:
	from navigation.resource_intelligence.providers.fontsource.provider import _expand_font_query

	category, hints, leftover = _expand_font_query("geometric sans serif heading font")
	assert category == "sans-serif"
	assert "inter" in hints
	assert "space-grotesk" in hints


@pytest.mark.unit
def test_framework_docs_fail_fast_without_network() -> None:
	from navigation.mcp.handlers import handle_framework_docs

	out = asyncio.run(handle_framework_docs({"topic": "metadata API"}))
	assert out["ok"] is False
	assert "framework_docs_deprecated" in (out.get("degraded") or [])
	assert "use_host_context7" in (out.get("degraded") or [])
	assert "Context7" in (out.get("error") or "")


@pytest.mark.unit
def test_graph_root_remembered_across_refresh_summary(tmp_path: Path) -> None:
	from navigation.consistency_intelligence.graph.model import ComponentNode, empty_graph
	from navigation.consistency_intelligence.graph.persistence import (
		clear_process_graph_stores,
		find_populated_graph_root,
		get_graph_store,
		last_graph_root,
		remember_graph_root,
	)

	clear_process_graph_stores()
	store = get_graph_store(tmp_path)
	graph = empty_graph(project_id="default")
	graph.components["Button"] = ComponentNode(name="Button")
	store.save(graph)
	remember_graph_root("default", tmp_path)
	assert last_graph_root("default") == str(tmp_path.resolve())
	assert find_populated_graph_root("default") == str(tmp_path.resolve())
	clear_process_graph_stores()


@pytest.mark.unit
def test_probe_form_no_forms_on_surface_is_provisional() -> None:
	from navigation.component_intelligence.probes import form_probe as fp

	class FakeSession:
		current_url = "http://127.0.0.1:3001/"

		async def navigate_to(self, url: str) -> None:
			raise AssertionError(f"should not navigate on form-less portfolio, got {url}")

	async def _zero(_session, _script):
		return 0

	orig = fp.evaluate_js
	fp.evaluate_js = _zero  # type: ignore[assignment]
	try:
		result = asyncio.run(fp.probe_validation_form(FakeSession(), "http://127.0.0.1:3001"))
	finally:
		fp.evaluate_js = orig  # type: ignore[assignment]
	assert result.ok is True
	assert result.error == "no_forms_on_surface"
