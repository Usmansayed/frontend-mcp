# tests/test_browser_flight_lock.py
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.execution_runtime.dispatch_registry import DispatchRegistry
from navigation.execution_runtime.executor import ToolExecutor
from navigation.execution_runtime.policies.browser_flight import (
	BROWSER_FLIGHT_TOOLS,
	browser_flight,
	flight_snapshot,
	requires_browser_flight,
	reset_browser_flight_for_tests,
)
from navigation.execution_runtime.policies.config import ExecutionPolicies


@pytest.fixture(autouse=True)
def _reset_lock(monkeypatch):
	monkeypatch.setenv("PERCEPTION_BROWSER_LOCK", "1")
	monkeypatch.setenv("PERCEPTION_BROWSER_LOCK_MODE", "queue")
	monkeypatch.setenv("PERCEPTION_BROWSER_LOCK_WAIT_S", "2")
	reset_browser_flight_for_tests()
	yield
	reset_browser_flight_for_tests()


@pytest.mark.unit
def test_classification_browser_vs_http():
	assert requires_browser_flight("perception_observe")
	assert requires_browser_flight("perception_verify")
	assert requires_browser_flight("perception_inspiration_collect")
	assert not requires_browser_flight("perception_inspiration_discover")
	assert not requires_browser_flight("perception_creative_assets")
	assert not requires_browser_flight("perception_resource_search")
	assert not requires_browser_flight("perception_search_components")
	assert not requires_browser_flight("perception_health")
	assert "perception_navigate" in BROWSER_FLIGHT_TOOLS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_serializes_two_browser_tools(monkeypatch):
	order: list[str] = []

	async def slow_observe(args):
		order.append("observe_start")
		await asyncio.sleep(0.15)
		order.append("observe_end")
		return {
			"contract_version": "1.0",
			"tool": "perception_observe",
			"ok": True,
			"session_id": args.get("session_id"),
			"data": {},
		}

	async def fast_verify(args):
		order.append("verify_start")
		await asyncio.sleep(0.01)
		order.append("verify_end")
		return {
			"contract_version": "1.0",
			"tool": "perception_verify",
			"ok": True,
			"session_id": args.get("session_id"),
			"data": {"verified": True},
		}

	registry = DispatchRegistry(
		{
			"perception_observe": slow_observe,
			"perception_verify": fast_verify,
		}
	)
	executor = ToolExecutor(registry, policies=ExecutionPolicies())

	async def run_observe():
		return await executor.execute_tool(
			"perception_observe",
			{"session_id": "sess_a"},
			allow_repeat=True,
		)

	async def run_verify():
		await asyncio.sleep(0.02)  # start slightly later so it queues
		return await executor.execute_tool(
			"perception_verify",
			{"session_id": "sess_a"},
			allow_repeat=True,
		)

	obs, ver = await asyncio.gather(run_observe(), run_verify())
	assert obs.ok
	assert ver.ok
	# Verify must not start until observe finishes.
	assert order == ["observe_start", "observe_end", "verify_start", "verify_end"]
	flight = (ver.envelope.get("data") or {}).get("browser_flight") or {}
	assert flight.get("wait_ms", 0) >= 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_browser_tools_run_in_parallel():
	started = asyncio.Event()
	release = asyncio.Event()
	parallel_hits = 0

	async def hold_browser(args):
		nonlocal parallel_hits
		started.set()
		await release.wait()
		return {
			"contract_version": "1.0",
			"tool": "perception_observe",
			"ok": True,
			"session_id": args.get("session_id"),
			"data": {},
		}

	async def http_search(args):
		nonlocal parallel_hits
		# Should run while observe holds the flight lock.
		if started.is_set() and not release.is_set():
			parallel_hits += 1
		return {
			"contract_version": "1.0",
			"tool": "perception_creative_assets",
			"ok": True,
			"data": {"assets": []},
		}

	registry = DispatchRegistry(
		{
			"perception_observe": hold_browser,
			"perception_creative_assets": http_search,
		}
	)
	executor = ToolExecutor(registry, policies=ExecutionPolicies())

	async def run_obs():
		return await executor.execute_tool(
			"perception_observe",
			{"session_id": "sess_b"},
			allow_repeat=True,
		)

	async def run_assets():
		await started.wait()
		result = await executor.execute_tool(
			"perception_creative_assets",
			{"query": "gear icon"},
			allow_repeat=True,
		)
		release.set()
		return result

	obs, assets = await asyncio.gather(run_obs(), run_assets())
	assert obs.ok
	assert assets.ok
	assert parallel_hits >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reject_mode_returns_busy(monkeypatch):
	monkeypatch.setenv("PERCEPTION_BROWSER_LOCK_MODE", "reject")

	async def hold_browser(args):
		await asyncio.sleep(0.2)
		return {
			"contract_version": "1.0",
			"tool": "perception_observe",
			"ok": True,
			"session_id": args.get("session_id"),
			"data": {},
		}

	async def other_browser(args):
		return {
			"contract_version": "1.0",
			"tool": "perception_verify",
			"ok": True,
			"session_id": args.get("session_id"),
			"data": {},
		}

	registry = DispatchRegistry(
		{
			"perception_observe": hold_browser,
			"perception_verify": other_browser,
		}
	)
	executor = ToolExecutor(registry, policies=ExecutionPolicies())

	async def run_obs():
		return await executor.execute_tool(
			"perception_observe",
			{"session_id": "sess_c"},
			allow_repeat=True,
		)

	async def run_verify():
		await asyncio.sleep(0.03)
		return await executor.execute_tool(
			"perception_verify",
			{"session_id": "sess_c"},
			allow_repeat=True,
		)

	obs, ver = await asyncio.gather(run_obs(), run_verify())
	assert obs.ok
	assert not ver.ok
	assert "browser_session_busy" in (ver.envelope.get("error") or "")
	assert "browser_session_busy" in (ver.envelope.get("degraded") or [])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_timeout(monkeypatch):
	monkeypatch.setenv("PERCEPTION_BROWSER_LOCK_WAIT_S", "0.15")

	async def hold_browser(args):
		await asyncio.sleep(0.4)
		return {
			"contract_version": "1.0",
			"tool": "perception_observe",
			"ok": True,
			"session_id": args.get("session_id"),
			"data": {},
		}

	async def other_browser(args):
		return {
			"contract_version": "1.0",
			"tool": "perception_verify",
			"ok": True,
			"data": {},
		}

	registry = DispatchRegistry(
		{
			"perception_observe": hold_browser,
			"perception_verify": other_browser,
		}
	)
	executor = ToolExecutor(registry, policies=ExecutionPolicies())

	async def run_obs():
		return await executor.execute_tool(
			"perception_observe",
			{"session_id": "sess_d"},
			allow_repeat=True,
		)

	async def run_verify():
		await asyncio.sleep(0.02)
		return await executor.execute_tool(
			"perception_verify",
			{"session_id": "sess_d"},
			allow_repeat=True,
		)

	obs, ver = await asyncio.gather(run_obs(), run_verify())
	assert obs.ok
	assert not ver.ok
	assert "browser_session_busy" in (ver.envelope.get("error") or "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lock_disabled_allows_overlap(monkeypatch):
	monkeypatch.setenv("PERCEPTION_BROWSER_LOCK", "0")
	overlap = 0

	async def a(args):
		nonlocal overlap
		overlap += 1
		await asyncio.sleep(0.1)
		overlap -= 1
		return {"contract_version": "1.0", "tool": "perception_observe", "ok": True, "data": {}}

	async def b(args):
		nonlocal overlap
		await asyncio.sleep(0.02)
		# If lock disabled, observe still running → overlap > 0
		seen = overlap
		await asyncio.sleep(0.02)
		return {
			"contract_version": "1.0",
			"tool": "perception_verify",
			"ok": True,
			"data": {"seen_overlap": seen},
		}

	registry = DispatchRegistry({"perception_observe": a, "perception_verify": b})
	executor = ToolExecutor(registry, policies=ExecutionPolicies())
	obs, ver = await asyncio.gather(
		executor.execute_tool("perception_observe", {"session_id": "x"}, allow_repeat=True),
		executor.execute_tool("perception_verify", {"session_id": "x"}, allow_repeat=True),
	)
	assert obs.ok and ver.ok
	assert (ver.envelope.get("data") or {}).get("seen_overlap", 0) >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager_direct():
	async with browser_flight(tool="perception_observe", session_id="s1") as hold:
		assert hold is not None
		assert hold.wait_ms >= 0
		snap = flight_snapshot()
		assert snap["locked"] is True
		assert snap["holder_tool"] == "perception_observe"
	assert flight_snapshot()["locked"] is False
