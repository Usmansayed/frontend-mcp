"""End-user E2E eval — installed PyPI frontend-mcp v1.1.5 (no local src PYTHONPATH)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "sandbox"
URL = "http://localhost:5173"
REPO = str(SANDBOX.resolve())
EXPECTED_VERSION = "1.1.5"


def _find_mcp_command() -> list[str]:
    exe = shutil.which("frontend-mcp")
    if exe:
        return [exe]
    return [sys.executable, "-m", "navigation.mcp"]


def spawn() -> subprocess.Popen:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
    return subprocess.Popen(
        _find_mcp_command(),
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


def read(proc: subprocess.Popen, timeout_s: float = 60.0, expected_id: int | None = None) -> dict:
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
            msg = json.loads(text)
        except json.JSONDecodeError:
            continue
        if expected_id is not None and msg.get("id") != expected_id:
            continue
        return msg
    raise TimeoutError(f"no JSON within {timeout_s}s")


def envelope(resp: dict) -> dict:
    result = resp.get("result") or {}
    if result.get("isError"):
        content = result.get("content", [])
        for c in content:
            if c.get("type") == "text" and c.get("text"):
                return {"ok": False, "error": c["text"]}
    content = result.get("content", [])
    for c in content:
        if c.get("type") == "text" and c.get("text"):
            try:
                return json.loads(c["text"])
            except json.JSONDecodeError:
                return {"ok": False, "error": c["text"]}
    err = resp.get("error") or {}
    return {"ok": False, "error": err.get("message") or str(err)}


def call(proc: subprocess.Popen, req_id: int, name: str, arguments: dict | None = None, timeout_s: float = 120.0) -> tuple[float, dict]:
    t0 = time.monotonic()
    send(proc, {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    resp = read(proc, timeout_s, expected_id=req_id)
    ms = (time.monotonic() - t0) * 1000.0
    return ms, envelope(resp)


def read_resource(proc: subprocess.Popen, req_id: int, uri: str) -> tuple[float, dict]:
    t0 = time.monotonic()
    send(proc, {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "resources/read",
        "params": {"uri": uri},
    })
    resp = read(proc, 30.0, expected_id=req_id)
    ms = (time.monotonic() - t0) * 1000.0
    contents = resp.get("result", {}).get("contents", [])
    text = contents[0].get("text", "") if contents else ""
    return ms, {"ok": bool(text), "chars": len(text), "error": resp.get("error")}


def record(results: list[dict], name: str, ms: float, env: dict, **extra) -> None:
    row = {
        "tool": name,
        "ms": round(ms, 1),
        "ok": env.get("ok"),
        "error": env.get("error"),
        **extra,
    }
    exec_block = env.get("execution") or {}
    if exec_block.get("latency_ms") is not None:
        row["execution_ms"] = exec_block.get("latency_ms")
    results.append(row)


def main() -> int:
    import importlib.metadata as md

    try:
        pkg_ver = md.version("frontend-mcp")
        engine_loc = md.distribution("frontend-perception-engine").locate_file("")
    except Exception as exc:
        print(json.dumps({"error": f"frontend-mcp not installed: {exc}"}))
        return 2

    report: dict = {
        "suite": "v1.1.5_installed_mcp_e2e",
        "package": "frontend-mcp",
        "version": pkg_ver,
        "engine_location": str(engine_loc),
        "url": URL,
        "repo_root": REPO,
        "results": [],
        "resources": [],
        "ok": True,
    }

    proc = spawn()
    req = 1
    try:
        send(proc, {
            "jsonrpc": "2.0",
            "id": req,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "installed-e2e", "version": EXPECTED_VERSION},
            },
        })
        init = read(proc, 30.0, expected_id=req)
        req += 1
        server_ver = init.get("result", {}).get("serverInfo", {}).get("version")
        report["server_version"] = server_ver
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        send(proc, {"jsonrpc": "2.0", "id": req, "method": "tools/list", "params": {}})
        tools_resp = read(proc, 15.0, expected_id=req)
        req += 1
        tool_names = {t["name"] for t in tools_resp.get("result", {}).get("tools", [])}
        report["tool_count"] = len(tool_names)

        for uri in (
            "perception://agent-guide",
            "perception://resolver-guide",
            "perception://seo-guide",
            "perception://inspiration-guide",
            "perception://resource-guide",
            "perception://figma-guide",
        ):
            ms, res = read_resource(proc, req, uri)
            req += 1
            report["resources"].append({"uri": uri, "ms": round(ms, 1), **res})

        ms, env = call(proc, req, "perception_health", {"url": URL})
        req += 1
        record(report["results"], "perception_health", ms, env, reachable=(env.get("data") or {}).get("reachable"))

        ms, env = call(proc, req, "perception_session_start", {"base_url": URL, "headless": True})
        req += 1
        record(report["results"], "perception_session_start", ms, env)
        session_id = env.get("session_id") or (env.get("data") or {}).get("session_id")
        if not session_id:
            report["ok"] = False
            print(json.dumps(report, indent=2))
            return 1

        ms, env = call(proc, req, "perception_navigate_and_observe", {
            "session_id": session_id,
            "url": f"{URL}/forms/validation",
        })
        req += 1
        data = env.get("data") or {}
        record(report["results"], "perception_navigate_and_observe", ms, env,
               scan_id=env.get("scan_id"), has_observation="observation" in data,
               detail_default=not bool(data.get("observation")))

        scan_id = env.get("scan_id")

        ms, env = call(proc, req, "perception_resolve_route", {
            "repo_root": REPO,
            "path": "/forms/validation",
        })
        req += 1
        resolution = (env.get("data") or {}).get("resolution") or {}
        record(report["results"], "perception_resolve_route", ms, env, status=resolution.get("status"))

        ms, env = call(proc, req, "perception_search_components", {"query": "date picker"})
        req += 1
        search = (env.get("data") or {}).get("component_search") or {}
        record(report["results"], "perception_search_components", ms, env,
               candidates=len(search.get("candidates") or []))

        ms, env = call(proc, req, "perception_integrate_component", {
            "query": "date picker",
            "plan_only": True,
        })
        req += 1
        record(report["results"], "perception_integrate_component", ms, env,
               degraded=env.get("degraded"))

        ms, env = call(proc, req, "perception_verify", {
            "session_id": session_id,
            "criteria": {"url_contains": ["/forms/validation"]},
        })
        req += 1
        record(report["results"], "perception_verify", ms, env,
               verified=(env.get("data") or {}).get("verified"))

        ms, env = call(proc, req, "perception_probe_guards", {
            "session_id": session_id,
            "mode": "maze",
        })
        req += 1
        hygiene = (env.get("data") or {}).get("session_hygiene") or {}
        record(report["results"], "perception_probe_guards", ms, env, restored=hygiene.get("restored"))

        ms, env = call(proc, req, "perception_seo_status", {})
        req += 1
        record(report["results"], "perception_seo_status", ms, env)

        if scan_id:
            ms, env = call(proc, req, "perception_seo_audit_start", {
                "website_url": URL,
                "scan_id": scan_id,
                "repo_root": REPO,
            }, timeout_s=30.0)
            req += 1
            seo_data = env.get("data") or {}
            record(report["results"], "perception_seo_audit_start_dev", ms, env,
                   instant=seo_data.get("instant"),
                   status=seo_data.get("status"),
                   has_audit=bool(seo_data.get("seo_audit")))
        else:
            report["results"].append({"tool": "perception_seo_audit_start_dev", "ok": False, "error": "no scan_id"})

        ms, env = call(proc, req, "perception_flow_describe", {"flow_id": "validation-form"})
        req += 1
        record(report["results"], "perception_flow_describe", ms, env)

        ms, env = call(proc, req, "perception_session_end", {"session_id": session_id})
        req += 1
        record(report["results"], "perception_session_end", ms, env)

        for r in report["results"]:
            if r.get("ok") is not True and r.get("tool") != "perception_resolve_api_endpoint":
                if r.get("tool") == "perception_seo_audit_start_dev" and r.get("status") in ("completed", "partial"):
                    continue
                report["ok"] = False

        for res in report["resources"]:
            if not res.get("ok"):
                report["ok"] = False

        if server_ver != EXPECTED_VERSION:
            report["version_mismatch"] = server_ver
            report["ok"] = False

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    out = ROOT / "artifacts" / "evals" / "v1.1.5_installed_mcp_e2e.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
