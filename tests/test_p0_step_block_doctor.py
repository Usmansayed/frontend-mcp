# tests/test_p0_step_block_doctor.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.mark.unit
def test_health_doctor_unreachable_has_fix_command():
	from navigation.mcp.health_doctor import build_health_doctor

	doc = build_health_doctor(
		url="http://127.0.0.1:9",
		reachable=False,
		status=None,
		error="connection refused",
		browser_runtime_available=True,
		browser_manager={"active_sessions": 0, "browser_running": False, "restart_count": 0},
		package_version="1.2.0.dev67",
	)
	assert doc["ok"] is False
	assert any(c["id"] == "app_url" and not c["ok"] for c in doc["checks"])
	assert doc["fix_commands"]
	assert doc["primary_browser"] == "perception"


@pytest.mark.unit
def test_health_doctor_ok_when_reachable():
	from navigation.mcp.health_doctor import build_health_doctor

	doc = build_health_doctor(
		url="http://127.0.0.1:3000",
		reachable=True,
		status=200,
		error=None,
		browser_runtime_available=True,
		browser_manager={"active_sessions": 1, "browser_running": True, "restart_count": 0},
		package_version="1.2.0.dev67",
		repo_root_arg=str(ROOT),
	)
	assert doc["ok"] is True
	assert any(c["id"] == "app_url" and c["ok"] for c in doc["checks"])
	assert any(c["id"] == "repo_root" and c["ok"] for c in doc["checks"])


@pytest.mark.unit
def test_implement_mutation_tools_detected():
	from navigation.execution_runtime.policies.implement_hard_gate import (
		is_implement_mutation_tool,
	)

	assert is_implement_mutation_tool("perception_execute_script")
	assert is_implement_mutation_tool("perception_execute_actions")
	assert is_implement_mutation_tool("perception_integrate_component")
	assert is_implement_mutation_tool("perception_design_review", {"mode": "ship"})
	assert not is_implement_mutation_tool("perception_design_review", {"mode": "review"})
	assert not is_implement_mutation_tool("perception_observe")
	assert not is_implement_mutation_tool("perception_verify")


@pytest.mark.unit
def test_hard_gate_refuses_when_implement_blocked(monkeypatch):
	from navigation.execution_runtime.policies import implement_hard_gate as gate

	face = {
		"implement_blocked": True,
		"next": "perception_inspiration_collect",
		"next_args": {"query": "chat ui"},
		"owed": [{"family": "inspiration", "suggested": "perception_inspiration_collect"}],
		"pack": {"critical_unpaid": ["inspiration", "component"]},
		"class": "greenfield",
		"evidence_band": "heavy",
	}
	monkeypatch.setattr(
		gate,
		"resolve_episode_for_gate",
		lambda arguments=None: ("ep_test", face),
	)
	refused = gate.evaluate_implement_hard_gate(
		"perception_execute_script",
		{"session_id": "s1", "script": "1+1"},
	)
	assert refused is not None
	assert refused["implement_blocked"] is True
	assert refused["next"] == "perception_inspiration_collect"
	env = gate.blocked_envelope("perception_execute_script", refused)
	assert env["ok"] is False
	assert "implement_blocked" in env["error"]


@pytest.mark.unit
def test_hard_gate_allows_observe_while_blocked(monkeypatch):
	from navigation.execution_runtime.policies import implement_hard_gate as gate

	face = {
		"implement_blocked": True,
		"next": "perception_observe",
		"owed": [{"family": "observe"}],
		"pack": {"critical_unpaid": ["inspiration"]},
	}
	monkeypatch.setattr(
		gate,
		"resolve_episode_for_gate",
		lambda arguments=None: ("ep_test", face),
	)
	assert gate.evaluate_implement_hard_gate("perception_observe", {}) is None
	assert gate.evaluate_implement_hard_gate("perception_verify", {}) is None


@pytest.mark.unit
def test_hard_gate_allows_mutation_when_not_blocked(monkeypatch):
	from navigation.execution_runtime.policies import implement_hard_gate as gate

	face = {
		"implement_blocked": False,
		"next": "perception_verify",
		"owed": [],
		"pack": {"critical_unpaid": []},
	}
	monkeypatch.setattr(
		gate,
		"resolve_episode_for_gate",
		lambda arguments=None: ("ep_test", face),
	)
	assert (
		gate.evaluate_implement_hard_gate("perception_execute_actions", {"actions": []})
		is None
	)


@pytest.mark.unit
def test_step_resolves_dispatch(monkeypatch):
	from navigation.execution_runtime.policies import perception_step as step
	from navigation.execution_runtime.policies import implement_hard_gate as gate

	face = {
		"next": "perception_navigate_and_observe",
		"next_args": {"url": "<route>", "session_id": "sess"},
		"claim_ok": False,
		"implement_blocked": True,
		"class": "greenfield",
	}
	monkeypatch.setattr(
		gate,
		"resolve_episode_for_gate",
		lambda arguments=None: ("ep_step", face),
	)
	out = step.resolve_step_target({"session_id": "sess", "url": "/home"})
	assert out["status"] == "dispatch"
	assert out["tool"] == "perception_navigate_and_observe"
	assert out["args"]["url"] == "/home"  # filled placeholder
	assert out["args"]["session_id"] == "sess"


@pytest.mark.unit
def test_step_done_when_next_empty(monkeypatch):
	from navigation.execution_runtime.policies import perception_step as step
	from navigation.execution_runtime.policies import implement_hard_gate as gate

	face = {"next": "", "next_args": {}, "claim_ok": True}
	monkeypatch.setattr(
		gate,
		"resolve_episode_for_gate",
		lambda arguments=None: ("ep_done", face),
	)
	out = step.resolve_step_target({"session_id": "s"})
	assert out["status"] == "done"
	assert out["claim_ok"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_executor_hard_blocks_execute_script(monkeypatch):
	from navigation.execution_runtime.dispatch_registry import DispatchRegistry
	from navigation.execution_runtime.executor import ToolExecutor
	from navigation.execution_runtime.policies import implement_hard_gate as gate

	face = {
		"implement_blocked": True,
		"next": "perception_inspiration_collect",
		"next_args": {"query": "x"},
		"owed": [{"family": "inspiration"}],
		"pack": {"critical_unpaid": ["inspiration"]},
	}
	monkeypatch.setattr(
		gate,
		"resolve_episode_for_gate",
		lambda arguments=None: ("ep_ex", face),
	)

	async def _never(args):
		raise AssertionError("handler must not run while blocked")

	registry = DispatchRegistry({"perception_execute_script": _never})
	ex = ToolExecutor(registry)
	result = await ex.execute_tool(
		"perception_execute_script",
		{"session_id": "s", "script": "1"},
	)
	assert result.envelope["ok"] is False
	assert result.envelope["data"]["implement_blocked"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_executor_step_dispatches_next(monkeypatch):
	from navigation.execution_runtime.dispatch_registry import DispatchRegistry
	from navigation.execution_runtime.executor import ToolExecutor
	from navigation.execution_runtime.policies import implement_hard_gate as gate
	from navigation.execution_runtime.policies import perception_step as step_mod

	face = {
		"next": "perception_observe",
		"next_args": {"session_id": "s"},
		"claim_ok": False,
		"implement_blocked": False,
		"class": "hotfix",
	}
	monkeypatch.setattr(
		gate,
		"resolve_episode_for_gate",
		lambda arguments=None: ("ep_s", face),
	)
	# Also used inside resolve_step_target via same function
	monkeypatch.setattr(
		step_mod,
		"resolve_step_target",
		lambda arguments=None: {
			"status": "dispatch",
			"tool": "perception_observe",
			"args": {"session_id": "s"},
			"card": face,
			"episode_id": "ep_s",
		},
	)

	called = {}

	async def observe(args):
		called["args"] = args
		return {
			"contract_version": "1.0",
			"tool": "perception_observe",
			"ok": True,
			"error": None,
			"data": {"observed": True},
		}

	registry = DispatchRegistry({"perception_observe": observe})
	ex = ToolExecutor(registry)
	result = await ex.execute_tool("perception_step", {"session_id": "s"})
	assert result.envelope["ok"] is True
	assert result.envelope["tool"] == "perception_observe"
	assert result.envelope["data"]["step"]["from"] == "perception_step"
	assert called["args"]["session_id"] == "s"


@pytest.mark.unit
def test_tools_list_includes_step():
	class _T:
		def __init__(self, **kwargs):
			self.__dict__.update(kwargs)

	class _Types:
		Tool = _T

	from navigation.mcp.tools import perception_tools

	tools = perception_tools(_Types)
	names = {t.name for t in tools}
	assert "perception_step" in names
	assert "perception_health" in names
