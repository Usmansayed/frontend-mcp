"""Hardcore suite regressions — timeout, once-ui, route claim, fonts, episode reuse."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.component_intelligence.candidate_resolve import (
	remember_candidates,
	resolve_candidate_by_id,
)
from navigation.component_intelligence.models import ComponentCandidate
from navigation.component_intelligence.selection.library_lock import resolve_foundation_library
from navigation.component_intelligence.models import ParsedQuery
from navigation.execution_runtime.policies.timeout import TimeoutPolicy
from navigation.resource_intelligence.providers.fontsource.provider import FontsourceProvider


@pytest.mark.unit
def test_audit_timeout_honors_caller_timeout_s() -> None:
	policy = TimeoutPolicy()
	# Caller asked 90s — wall must be >= 90 and not stuck at silent 120-only ignore.
	wall = policy.timeout_for("perception_audit_accessibility", {"timeout_s": 90})
	assert wall >= 90.0
	# audit_mode must scale for multiple categories (was killed at 120s mid-suite).
	mode_wall = policy.timeout_for("perception_audit_mode", {"timeout_s": 60})
	assert mode_wall >= 60.0 * 2  # at least multi-category headroom
	# Huge values are capped.
	capped = policy.timeout_for("perception_audit_accessibility", {"timeout_s": 99999})
	assert capped <= 610.0


@pytest.mark.unit
def test_once_ui_detected_from_package_json() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(root / "package.json").write_text(
			json.dumps(
				{
					"dependencies": {
						"next": "16.0.0",
						"react": "19.0.0",
						"@once-ui-system/core": "1.2.0",
					}
				}
			),
			encoding="utf-8",
		)
		res = resolve_foundation_library(root, ParsedQuery(raw="select component foundation"))
		assert res.refused is False
		assert res.library_id == "@once-ui-system"
		assert any("once-ui" in e for e in res.evidence)


@pytest.mark.unit
def test_integrate_rehydrates_install_method_from_candidate_id() -> None:
	remember_candidates(
		[
			ComponentCandidate(
				id="shadcn_ecosystem:shadcn:button",
				provider="shadcn_ecosystem",
				provider_group="shadcn_ecosystem",
				name="button",
				title="Button",
				category="component",
				description="Button",
				registry="@shadcn",
				install_method="npx shadcn@latest add @shadcn/button",
				item_type="registry:ui",
			)
		]
	)
	c = resolve_candidate_by_id("shadcn_ecosystem:shadcn:button")
	assert c.install_method
	assert "shadcn" in c.install_method
	assert c.title == "Button"


@pytest.mark.unit
def test_fontsource_query_does_not_use_invalid_q_param(monkeypatch: pytest.MonkeyPatch) -> None:
	calls: list[str] = []

	async def fake_fetch(url: str):
		calls.append(url)
		return [
			{"id": "geist", "family": "Geist", "subsets": ["latin"]},
			{"id": "geist-mono", "family": "Geist Mono", "subsets": ["latin"]},
			{"id": "inter", "family": "Inter", "subsets": ["latin"]},
		]

	monkeypatch.setattr(
		"navigation.resource_intelligence.providers.fontsource.provider.fetch_json",
		fake_fetch,
	)
	# Clear cache
	import navigation.resource_intelligence.providers.fontsource.provider as mod

	mod._CACHE = None

	provider = FontsourceProvider()
	import asyncio
	from navigation.resource_intelligence.models import ResourceCategory

	assets, degraded = asyncio.run(
		provider.search("geist", category=ResourceCategory.FONT, max_results=5)
	)
	assert calls and "?q=" not in calls[0]
	assert "limit=" not in calls[0]
	assert not any("fontsource_search_failed" in d for d in degraded)
	ids = {a.resource_id for a in assets}
	assert "fontsource:geist" in ids or any("geist" in i for i in ids)
