"""MCP stdio wire protocol smoke test (T5).

Spawns the MCP server as a subprocess over stdio, performs the JSON-RPC
handshake, lists tools, and calls read-only tools that do not require a
running sandbox. Verifies contract v1.0 envelope shape and no planning hints.

Marked ``stdio`` so it can be skipped in fast tiers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


PLANNING_HINT_TOKENS = (
    "suggested_next",
    "you should next",
    "next you should",
    "your next step",
    "as your next step",
)


def _spawn_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), env.get("PYTHONPATH", "")])
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
    return subprocess.Popen(
        [sys.executable, "-m", "navigation.mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(ROOT),
        bufsize=0,
    )


def _send(proc: subprocess.Popen, message: dict) -> None:
    line = json.dumps(message).encode("utf-8") + b"\n"
    assert proc.stdin is not None
    proc.stdin.write(line)
    proc.stdin.flush()


def _read_response(proc: subprocess.Popen, timeout_s: float = 15.0) -> dict:
    """Read one JSON-RPC line from stdout with a soft timeout."""
    assert proc.stdout is not None
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        text = line.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue
    raise TimeoutError("no JSON response within timeout")


def _envelope_from_call_tool_result(result: dict) -> dict:
    """CallToolResult.content[0].text is the envelope JSON."""
    content = result.get("result", {}).get("content", [])
    if not content:
        return {}
    text_parts = [c.get("text") for c in content if c.get("type") == "text"]
    if not text_parts:
        return {}
    return json.loads(text_parts[0])


@pytest.mark.stdio
@pytest.mark.slow
def test_mcp_stdio_smoke() -> None:
    """Spawn server, initialize, list tools, call read-only tools, verify envelopes."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        pytest.skip("mcp package not installed")

    proc = _spawn_server()
    try:
        _send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "stdio-smoke", "version": "0.0.1"},
            },
        })
        init_resp = _read_response(proc, timeout_s=30.0)
        assert init_resp.get("id") == 1
        assert "result" in init_resp, init_resp

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        list_resp = _read_response(proc, timeout_s=15.0)
        tools = list_resp.get("result", {}).get("tools", [])
        assert len(tools) >= 66, f"expected >=66 tools, got {len(tools)}"
        tool_names = {t.get("name") for t in tools}
        assert "perception_health" in tool_names
        assert "perception_seo_status" in tool_names
        assert "perception_resource_pattern_search" in tool_names, (
            "orphan handler must be registered as a tool"
        )
        assert "perception_resource_animation_search" in tool_names

        _send(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "perception_health", "arguments": {"url": "http://127.0.0.1:1"}},
        })
        health_resp = _read_response(proc, timeout_s=20.0)
        health_env = _envelope_from_call_tool_result(health_resp)
        assert health_env.get("contract_version") == "1.0"
        assert health_env.get("tool") == "perception_health"
        assert "ok" in health_env
        assert "data" in health_env

        _send(proc, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "perception_seo_status", "arguments": {}},
        })
        seo_resp = _read_response(proc, timeout_s=20.0)
        seo_env = _envelope_from_call_tool_result(seo_resp)
        assert seo_env.get("contract_version") == "1.0"
        assert seo_env.get("ok") is True
        seo_data = seo_env.get("data") or {}
        assert "ai_visibility" in seo_data, "seo status must expose ai_visibility block"

        blob = json.dumps(seo_env).lower()
        for token in PLANNING_HINT_TOKENS:
            assert token not in blob, f"planning hint token {token!r} leaked into envelope"

        _send(proc, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "perception_this_tool_does_not_exist", "arguments": {}},
        })
        unknown_resp = _read_response(proc, timeout_s=15.0)
        unknown_env = _envelope_from_call_tool_result(unknown_resp)
        assert unknown_env.get("ok") is False
        assert "unknown tool" in (unknown_env.get("error") or "")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
