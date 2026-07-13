"""Phase 2 resolver unit tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.resolver_intelligence import ResolverIntelligenceService

SANDBOX = ROOT / "sandbox"


@pytest.mark.unit
def test_resolve_route_validation_form() -> None:
    svc = ResolverIntelligenceService()
    result = svc.resolve_route(SANDBOX.resolve(), "/forms/validation")
    assert result.status.value == "resolved"
    assert result.matches
    assert result.matches[0].file_path.endswith("ValidationForm.jsx")
    assert result.latency_ms < 200


@pytest.mark.unit
def test_validate_route_claim_passes() -> None:
    svc = ResolverIntelligenceService()
    result = svc.validate_route_claim(
        SANDBOX.resolve(),
        {
            "route": "/forms/validation",
            "file": "src/pages/forms/ValidationForm.jsx",
            "component": {"name": "ValidationForm"},
        },
    )
    assert result.valid is True


@pytest.mark.unit
def test_resolve_component_by_name() -> None:
    svc = ResolverIntelligenceService()
    result = svc.resolve_component(SANDBOX.resolve(), "ValidationForm")
    assert result.ok is True
    assert any("ValidationForm" in m.file_path for m in result.matches)


@pytest.mark.unit
def test_resolve_design_token_accent() -> None:
    svc = ResolverIntelligenceService()
    result = svc.resolve_design_token(SANDBOX.resolve(), "accent")
    assert result.ok is True
    assert result.matches[0].metadata.get("value")


@pytest.mark.unit
def test_resolve_state_owner_cart() -> None:
    svc = ResolverIntelligenceService()
    result = svc.resolve_state_owner(SANDBOX.resolve(), key="addItem", store_name="Cart")
    assert result.ok is True
    assert "CartContext" in result.matches[0].file_path
