"""Phase 2 resolver MCP stdio smoke."""
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
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
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
    resp = read(proc, 30.0)
    return time.monotonic() - t0, envelope(resp)


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
                "clientInfo": {"name": "phase2-smoke", "version": "0.0.1"},
            },
        })
        read(proc, 30.0)
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        repo = str(SANDBOX.resolve())
        ms, env = call(proc, 2, "perception_resolve_route", {
            "repo_root": repo,
            "path": "/forms/validation",
        })
        resolution = (env.get("data") or {}).get("resolution") or {}
        match = (resolution.get("matches") or [{}])[0]
        results.append({
            "tool": "perception_resolve_route",
            "ms": round(ms * 1000),
            "ok": env.get("ok"),
            "status": resolution.get("status"),
            "file": match.get("file_path"),
            "fast": ms < 0.2,
        })

        ms, env = call(proc, 3, "perception_validate_route_claim", {
            "repo_root": repo,
            "claim": {
                "route": "/forms/validation",
                "file": "src/pages/forms/ValidationForm.jsx",
                "component": {"name": "ValidationForm"},
            },
        })
        validation = (env.get("data") or {}).get("validation") or {}
        results.append({
            "tool": "perception_validate_route_claim",
            "ms": round(ms * 1000),
            "ok": env.get("ok"),
            "valid": validation.get("valid"),
        })

        ms, env = call(proc, 4, "perception_resolve_component", {
            "repo_root": repo,
            "name": "ValidationForm",
        })
        comp = (env.get("data") or {}).get("resolution") or {}
        results.append({
            "tool": "perception_resolve_component",
            "ms": round(ms * 1000),
            "ok": env.get("ok"),
            "status": comp.get("status"),
        })

        ms, env = call(proc, 5, "perception_resolve_design_token", {
            "repo_root": repo,
            "token": "accent",
        })
        token = (env.get("data") or {}).get("resolution") or {}
        results.append({
            "tool": "perception_resolve_design_token",
            "ms": round(ms * 1000),
            "ok": env.get("ok"),
            "status": token.get("status"),
        })

        ms, env = call(proc, 6, "perception_resolve_state_owner", {
            "repo_root": repo,
            "store_name": "Cart",
            "key": "addItem",
        })
        state = (env.get("data") or {}).get("resolution") or {}
        results.append({
            "tool": "perception_resolve_state_owner",
            "ms": round(ms * 1000),
            "ok": env.get("ok"),
            "status": state.get("status"),
        })

        print(json.dumps({"phase2_mcp_smoke": results}, indent=2))
        failed = [
            r for r in results
            if not r.get("ok")
            or (r["tool"] == "perception_resolve_route" and r.get("status") != "resolved")
            or (r["tool"] == "perception_validate_route_claim" and not r.get("valid"))
        ]
        return 1 if failed else 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
