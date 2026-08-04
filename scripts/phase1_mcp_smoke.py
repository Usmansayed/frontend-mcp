"""Phase 1 MCP stdio smoke — one tool at a time over wire protocol."""
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
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue
    raise TimeoutError(f"no JSON within {timeout_s}s")


def envelope(resp: dict) -> dict:
    content = resp.get("result", {}).get("content", [])
    for c in content:
        if c.get("type") == "text":
            return json.loads(c["text"])
    return {}


def call(proc: subprocess.Popen, req_id: int, name: str, arguments: dict | None = None) -> tuple[float, dict]:
    t0 = time.monotonic()
    send(proc, {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    resp = read(proc, timeout_s=120.0)
    elapsed = time.monotonic() - t0
    return elapsed, envelope(resp)


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
                "clientInfo": {"name": "phase1-smoke", "version": "0.0.1"},
            },
        })
        init = read(proc, 30.0)
        assert "result" in init, init

        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp = read(proc, 15.0)
        names = {t["name"] for t in tools_resp["result"]["tools"]}
        for required in (
            "perception_health",
            "perception_code_context",
        ):
            results.append({"check": f"tool_registered:{required}", "ok": required in names})
            if required not in names:
                print(f"MISSING TOOL: {required}")
                return 1

        # 1. health baseline
        ms, env = call(proc, 3, "perception_health", {"url": "http://localhost:5173"})
        results.append({
            "tool": "perception_health",
            "ms": round(ms * 1000),
            "ok": env.get("ok"),
            "reachable": (env.get("data") or {}).get("reachable"),
        })

        # SEO Intelligence tools are MVP-excluded (parked/MVP_EXCLUDE_SEO.md) — not exercised here.

        # 2. code_context offload (sandbox repo)
        ms, env = call(proc, 4, "perception_code_context", {
            "repo_root": str(SANDBOX),
            "query": "validation form",
            "max_files": 5,
        })
        results.append({
            "tool": "perception_code_context",
            "ms": round(ms * 1000),
            "ok": env.get("ok"),
            "has_data": bool(env.get("data")),
        })

        print(json.dumps({"phase1_mcp_smoke": results}, indent=2))

        failed = [
            r for r in results
            if r.get("ok") is False
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
