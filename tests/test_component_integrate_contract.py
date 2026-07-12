"""Contract test for perception_integrate_component in dry-run mode (T2).

The dry-run mode disables all mutating side effects (`execute_install=False`,
`execute_repairs=False`). The handler must still return a valid contract v1.0
envelope with either ``ok: true`` or an explicit ``degraded`` list, so the
host agent can plan installation without CI ever touching the sandbox
filesystem.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SANDBOX_ROOT = ROOT / "sandbox"

from navigation.mcp.handlers import handle_integrate_component


def _integrate(**args) -> dict:
    return asyncio.run(handle_integrate_component(args))


@pytest.mark.contract
@pytest.mark.unit
def test_integrate_component_requires_query_or_candidate_id() -> None:
    result = _integrate()
    assert result["ok"] is False
    assert "query or candidate_id required" in (result.get("error") or "")
    assert result["contract_version"] == "1.0"


@pytest.mark.contract
@pytest.mark.slow
def test_integrate_component_dry_run_returns_envelope() -> None:
    result = _integrate(
        query="modern login form",
        repo_root=str(SANDBOX_ROOT) if SANDBOX_ROOT.exists() else str(ROOT),
        execute_install=False,
        execute_repairs=False,
    )
    assert result["contract_version"] == "1.0"
    assert result["tool"] == "perception_integrate_component"
    assert "data" in result
    assert isinstance(result.get("degraded", []), list)
    if not result["ok"]:
        assert result.get("degraded") or result.get("error"), (
            "failed integrate must surface degraded[] or error"
        )


@pytest.mark.contract
@pytest.mark.slow
def test_integrate_component_dry_run_does_not_mutate_repo(tmp_path: Path) -> None:
    """Dry run against a temp empty repo must not create or edit files."""
    (tmp_path / "package.json").write_text('{"name":"probe","version":"0.0.0"}', encoding="utf-8")
    before = {p.name: p.stat().st_size for p in tmp_path.iterdir()}

    result = _integrate(
        query="button",
        repo_root=str(tmp_path),
        execute_install=False,
        execute_repairs=False,
    )
    after = {p.name: p.stat().st_size for p in tmp_path.iterdir()}

    assert result["contract_version"] == "1.0"
    assert before == after, "dry run must not add or resize files in repo root"


@pytest.mark.contract
@pytest.mark.slow
def test_integrate_component_dry_run_ignores_truthy_install_flag_when_not_wired() -> None:
    """execute_install=False is the safe default; result must never claim install completed."""
    result = _integrate(
        query="button",
        repo_root=str(SANDBOX_ROOT) if SANDBOX_ROOT.exists() else str(ROOT),
        execute_install=False,
        execute_repairs=False,
    )
    data = result.get("data") or {}
    integration = data.get("integration_result") or data.get("integration") or {}
    if integration:
        install = integration.get("install") or {}
        if install:
            assert install.get("executed") is not True, (
                "dry run must not report install.executed=True"
            )
