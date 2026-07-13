"""Phase 3 MCP stdio smoke — all resolver tools."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SANDBOX = ROOT / "sandbox"


def spawn() -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), env.get("PYTHONPATH", "")])
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen(
        [sys.executable, "-m", "navigation.mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(ROOT),
        bufsize=0,
    )


def send(proc: subprocess.Popen, msg: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(msg).encode() + b"\n")
    proc.stdin.flush()


def read(proc: subprocess.Popen, timeout_s: float = 30.0) -> dict:
    assert proc.stdout is not None
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.02)
            continue
        text = line.decode("utf-8", errors="replace").strip()
        if text:
            return json.loads(text)
    raise TimeoutError("no JSON within timeout")


def envelope(resp: dict) -> dict:
    content = resp.get("result", {}).get("content", [])
    for c in content:
        if c.get("type") == "text":
            return json.loads(c["text"])
    return {}


def call(proc: subprocess.Popen, req_id: int, name: str, arguments: dict) -> tuple[float, dict]:
    t0 = time.monotonic()
    send(proc, {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })
    return time.monotonic() - t0, envelope(read(proc, 30.0))


def main() -> int:
    proc = spawn()
    results: list[dict] = []
    try:
        send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "phase3-smoke", "version": "0.0.1"},
            },
        })
        read(proc, 30.0)
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        repo = str(SANDBOX.resolve())
        req = 2

        tools = [
            ("perception_resolve_route", {"repo_root": repo, "path": "/forms/validation"}, "resolved"),
            ("perception_validate_route_claim", {
                "repo_root": repo,
                "claim": {
                    "route": "/forms/validation",
                    "file": "src/pages/forms/ValidationForm.jsx",
                    "component": {"name": "ValidationForm"},
                },
            }, "valid"),
            ("perception_resolve_component", {"repo_root": repo, "name": "ValidationForm"}, "resolved"),
            ("perception_validate_component_claim", {
                "repo_root": repo,
                "claim": {
                    "component": {"name": "ValidationForm"},
                    "file": "src/pages/forms/ValidationForm.jsx",
                },
            }, "valid"),
            ("perception_resolve_design_token", {"repo_root": repo, "token": "accent"}, "resolved"),
            ("perception_resolve_state_owner", {
                "repo_root": repo,
                "store_name": "Cart",
                "key": "addItem",
            }, "resolved"),
            ("perception_resolve_api_endpoint", {"repo_root": repo, "path": "/api/users"}, "not_found"),
        ]

        for tool_name, args, expect in tools:
            ms, env = call(proc, req, tool_name, args)
            req += 1
            data = env.get("data") or {}
            block = data.get("resolution") or data.get("validation") or {}
            status = block.get("status") or block.get("valid")
            results.append({
                "tool": tool_name,
                "ms": round(ms * 1000),
                "ok": env.get("ok"),
                "status": status,
                "expect": expect,
            })

        print(json.dumps({"phase3_mcp_smoke": results}, indent=2))

        failed = []
        for r in results:
            if r["tool"] in (
                "perception_validate_route_claim",
                "perception_validate_component_claim",
            ):
                if not r.get("status"):
                    failed.append(r)
            elif r.get("expect") == "not_found":
                if r.get("status") != "not_found":
                    failed.append(r)
            elif r.get("status") != r.get("expect"):
                failed.append(r)
        return 1 if failed else 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
