"""Phase 3 resolver unit tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.resolver_intelligence import ResolverIntelligenceService
from navigation.resolver_intelligence.live.correlate import correlate_live
from navigation.resolver_intelligence.plugins.api_endpoint.patterns import resolve_api_endpoint
from navigation.resolver_intelligence.plugins.component.shadcn import find_shadcn_matches
from navigation.resolver_intelligence.plugins.design_token.dtcg import find_dtcg_matches
from navigation.resolver_intelligence.plugins.layout.snapshot import resolve_layout
from navigation.resolver_intelligence.context import build_resolver_context

SANDBOX = ROOT / "sandbox"


@pytest.mark.unit
def test_shadcn_components_json(tmp_path: Path) -> None:
    ui = tmp_path / "src" / "components" / "ui"
    ui.mkdir(parents=True)
    (ui / "button.tsx").write_text("export function Button() {}", encoding="utf-8")
    (tmp_path / "components.json").write_text(
        json.dumps({"aliases": {"ui": "@/components/ui"}}),
        encoding="utf-8",
    )
    ctx = build_resolver_context(tmp_path)
    matches = find_shadcn_matches("Button", ctx)
    assert matches
    assert matches[0].file_path.endswith("Button.tsx")


@pytest.mark.unit
def test_dtcg_token_lookup(tmp_path: Path) -> None:
    (tmp_path / "tokens.json").write_text(
        json.dumps({"color": {"accent": {"$value": "#112233"}}}),
        encoding="utf-8",
    )
    ctx = build_resolver_context(tmp_path)
    matches, _ = find_dtcg_matches("accent", ctx)
    assert matches
    assert matches[0].metadata["value"] == "#112233"


@pytest.mark.unit
def test_api_endpoint_next_filesystem_route(tmp_path: Path) -> None:
    api = tmp_path / "app" / "api" / "users"
    api.mkdir(parents=True)
    (api / "route.ts").write_text("export async function GET() {}", encoding="utf-8")
    ctx = build_resolver_context(tmp_path)
    result = resolve_api_endpoint("/api/users", ctx, method="GET")
    assert result.status.value == "resolved"
    assert "route.ts" in result.matches[0].file_path


@pytest.mark.unit
def test_resolve_layout_from_snapshot() -> None:
    snapshot = {
        "layout": {
            "regions": [
                {"name": "header", "role": "banner"},
                {"name": "main", "role": "main"},
            ],
            "layout_tree": [{"tag": "div"}],
        }
    }
    result = resolve_layout(snapshot, region="main")
    assert result.ok is True
    assert any(m.summary == "main" for m in result.matches)


@pytest.mark.unit
def test_correlate_live_dom_text() -> None:
    scan = {
        "dom_text": '<form data-testid="validation-form">ValidationForm fields</form>',
    }
    resolution = {"matches": [{"symbol": "ValidationForm"}]}
    result = correlate_live(scan, resolution=resolution)
    assert result.ok is True
    assert result.matches


@pytest.mark.unit
def test_validate_component_claim_sandbox() -> None:
    svc = ResolverIntelligenceService()
    result = svc.validate_component_claim(
        SANDBOX.resolve(),
        {
            "component": {"name": "ValidationForm"},
            "file": "src/pages/forms/ValidationForm.jsx",
        },
    )
    assert result.valid is True


@pytest.mark.unit
def test_resolve_api_endpoint_not_found_sandbox() -> None:
    svc = ResolverIntelligenceService()
    result = svc.resolve_api_endpoint(SANDBOX.resolve(), "/api/nonexistent")
    assert result.status.value == "not_found"


@pytest.mark.unit
def test_mcp_correlate_handler_with_scan_registry() -> None:
    import asyncio

    from navigation.mcp.handlers import handle_correlate_live

    scans = ScanRegistry()
    rec = scans.register(
        session_id="sess_test",
        run_id="run_test",
        url="http://localhost:5173/forms/validation",
        observation={"dom_text": "ValidationForm submit button"},
    )
    env = asyncio.run(
        handle_correlate_live(
            scans,
            {
                "scan_id": rec.scan_id,
                "resolution": {"matches": [{"symbol": "ValidationForm"}]},
            },
        )
    )
    assert env["ok"] is True
    resolution = (env.get("data") or {}).get("resolution") or {}
    assert resolution.get("matches")


@pytest.mark.unit
def test_resolve_layout_via_snapshot_registry() -> None:
    import asyncio

    from navigation.mcp.handlers import handle_resolve_layout

    snapshots = SnapshotRegistry()
    snapshots.register(
        snapshot={
            "layout": {"regions": [{"name": "sidebar", "role": "navigation"}]},
        },
        url="http://localhost:5173",
        snapshot_id="snap_test_layout",
    )
    env = asyncio.run(
        handle_resolve_layout(
            snapshots,
            {"snapshot_id": "snap_test_layout"},
        )
    )
    assert env["ok"] is True
