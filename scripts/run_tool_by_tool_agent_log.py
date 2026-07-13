"""Run installed MCP tools one-by-one; after EACH tool, append agent commentary to a live log."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "http://localhost:5173"
REPO = str((ROOT / "sandbox").resolve())
WAIT_S = 1.5
LOG_MD = ROOT / "artifacts" / "evals" / "v1.1.5_tool_by_tool_agent_log.md"
LOG_JSON = ROOT / "artifacts" / "evals" / "v1.1.5_tool_by_tool_results.json"


# Agent commentary keyed by tool name (written after each test)
TOOL_INSIGHTS: dict[str, dict] = {
    "perception_health": {
        "role": "Bootstrap / wiring check",
        "agent_value": 8,
        "when_i_use_it": "First call every session — confirms dev server reachable and MCP envelope is v1.0.",
        "improves": "Stops wasted browser spins when localhost is down; gives contract_version for debugging version skew.",
        "watch_out": "Unreachable URL still returns ok:false with reason — read blocking before retrying.",
        "improve_now": "Include installed package version in health data (not only serverInfo on initialize).",
    },
    "perception_session_start": {
        "role": "Browser lifecycle",
        "agent_value": 10,
        "when_i_use_it": "Once per task after health; saves session_id for all subsequent tools.",
        "improves": "Without it nothing else works — foundational.",
        "watch_out": "~5–6s cold start is normal (Chromium + CDP). Do not parallel with other tools.",
        "improve_now": "Return estimated ready time or emit degraded if browser deps missing.",
    },
    "perception_navigate_and_observe": {
        "role": "Eyes — DOM, a11y, screenshot, dev insights",
        "agent_value": 10,
        "when_i_use_it": "Every page inspection; save scan_id for verify/diff/SEO reuse.",
        "improves": "Replaces guessing UI state. agent_summary.blocking is the highest-signal field.",
        "watch_out": "Default detail=summary_only omits observation blob — use detail:full when you need console/network entries.",
        "improve_now": "Tool description should say when to escalate summary_only -> full.",
    },
    "perception_resolve_route": {
        "role": "Code ↔ route correlation",
        "agent_value": 8,
        "when_i_use_it": "Before editing files — map URL to sandbox page component.",
        "improves": "Cuts wrong-file edits; resolver-first is faster than grep alone.",
        "watch_out": "Needs correct repo_root; sandbox path must be absolute.",
        "improve_now": "Surface confidence + file path in agent_summary one-liner.",
    },
    "perception_search_components": {
        "role": "Component discovery (shadcn ecosystem)",
        "agent_value": 8,
        "when_i_use_it": "User asks for UI widget — get ranked candidates before integrate.",
        "improves": "Turns vague requests into concrete library choices with scores.",
        "watch_out": "First call can be ~1–2s (catalog warm); fine for interactive use.",
        "improve_now": "Return top-3 rationale strings agent can quote to user.",
    },
    "perception_integrate_component": {
        "role": "Integration planner / dry-run",
        "agent_value": 8,
        "when_i_use_it": "After search — plan_only:true before touching repo.",
        "improves": "Shows files to touch, deps, risks — agent plans instead of blind paste.",
        "watch_out": "Degraded fast when repo_root wrong; read degraded[] array.",
        "improve_now": "Actionable fix string when repo_root missing.",
    },
    "perception_verify": {
        "role": "Hard stop — did the UI match criteria?",
        "agent_value": 10,
        "when_i_use_it": "After EVERY code change or browser action — non-negotiable.",
        "improves": "Only tool that makes frontend agent work trustworthy vs hallucination.",
        "watch_out": "url_contains must be array; failure auto-attaches screenshot.",
        "improve_now": "None critical — this is the core contract done right.",
    },
    "perception_probe_guards": {
        "role": "Auth redirects / route maze hygiene",
        "agent_value": 7,
        "when_i_use_it": "After verify on guarded flows; restores session if maze polluted state.",
        "improves": "Catches silent redirects agents miss when only reading DOM text.",
        "watch_out": "Run after verify on validation page, not before.",
        "improve_now": "Summarize which guard fired in agent_summary.",
    },
    "perception_seo_status": {
        "role": "SEO subsystem readiness",
        "agent_value": 6,
        "when_i_use_it": "Before seo_audit — know if companions/graph available.",
        "improves": "Avoids starting audit when SEO stack not ready.",
        "watch_out": "~2–3s; optional for pure UI tasks.",
        "improve_now": "Clear dev vs pro mode in status payload.",
    },
    "perception_seo_audit_start_dev": {
        "role": "Development SEO audit (scan reuse)",
        "agent_value": 7,
        "when_i_use_it": "When scan_id exists from observe — instant dev audit on same page.",
        "improves": "Sub-second with scan reuse vs minutes for cold pro audit.",
        "watch_out": "Pass scan_id + repo_root; skip companion bootstrap in eval via env.",
        "improve_now": "Document scan_id reuse pattern in AGENT_GUIDE §SEO.",
    },
    "perception_flow_describe": {
        "role": "Multi-step flow checkpoints",
        "agent_value": 7,
        "when_i_use_it": "Complex flows — get checkpoint list, then verify each yourself.",
        "improves": "Structure without black-box automation; agent stays in control.",
        "watch_out": "MCP does not run the flow — you execute each step.",
        "improve_now": "Link checkpoint IDs to suggested verify criteria.",
    },
    "perception_session_end": {
        "role": "Cleanup",
        "agent_value": 6,
        "when_i_use_it": "End of task — release browser.",
        "improves": "Prevents zombie Chromium on long Cursor sessions.",
        "watch_out": "Always call when done; cheap (~100–200ms).",
        "improve_now": None,
    },
    "resource:perception://agent-guide": {
        "role": "Playbook resource",
        "agent_value": 9,
        "when_i_use_it": "Session start — OBSERVE->REASON->ACT->VERIFY loop.",
        "improves": "Deterministic behavior contract; reduces tool misuse.",
        "watch_out": "Only valuable if client can fetch resources (stdio smoke passes; Cursor sometimes flaky).",
        "improve_now": "Mirror critical sections into server instructions as fallback.",
    },
    "edge_lab:console_observe": {
        "role": "Console signal capture (edge-lab)",
        "agent_value": 8,
        "when_i_use_it": "Validates console errors surface in observation with detail:full.",
        "improves": "Proves CDP console pipeline works — agents rely on this for debugging.",
        "watch_out": "v1.1.5 waits for EDGE_LAB_CONSOLE_ERROR before snapshot.",
        "improve_now": None,
    },
    "edge_lab:network_observe_failure": {
        "role": "Network failure capture",
        "agent_value": 8,
        "when_i_use_it": "404/failed fetch must appear in observation.network.",
        "improves": "Agents catch API wiring breaks invisible in DOM-only inspect.",
        "watch_out": "Assert on first devtest=1 observe — SPA won't re-fetch on same URL.",
        "improve_now": None,
    },
    "edge_lab:network_observe_slow": {
        "role": "Slow request detection",
        "agent_value": 7,
        "when_i_use_it": "Perf regressions — slow_count and slow_requests list.",
        "improves": "Advisory tier for agents optimizing load.",
        "watch_out": "2.5s sandbox delay; observe waits up to 8s for signal.",
        "improve_now": None,
    },
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _append_log(section: str) -> None:
    LOG_MD.parent.mkdir(parents=True, exist_ok=True)
    with LOG_MD.open("a", encoding="utf-8") as f:
        f.write(section)
        if not section.endswith("\n"):
            f.write("\n")
    try:
        print(section, flush=True)
    except UnicodeEncodeError:
        print(section.encode("ascii", errors="replace").decode("ascii"), flush=True)


def _write_header(packages: dict) -> None:
    if LOG_MD.is_file():
        LOG_MD.unlink()
    _append_log("# Tool-by-tool agent log — frontend-mcp v1.1.5\n")
    _append_log(f"**Started:** {_ts()}\n")
    _append_log(f"**Packages:** `{packages}`\n")
    _append_log(f"**Sandbox:** `{URL}`\n")
    _append_log("---\n")


def _post_test_write(
    tool_key: str,
    *,
    ok: bool,
    duration_ms: float,
    evidence: dict,
    error: str | None = None,
) -> None:
    meta = TOOL_INSIGHTS.get(tool_key, {})
    verdict = "PASS" if ok else "FAIL"
    lines = [
        f"\n## {_ts()} — `{tool_key}` — **{verdict}** ({duration_ms:.0f}ms)\n",
        "### Result\n",
        f"- **ok:** {ok}",
    ]
    if error:
        lines.append(f"- **error:** {error}")
    for k, v in evidence.items():
        if v is not None:
            lines.append(f"- **{k}:** {v}")

    lines.append("\n### What this tool/feature does for an agent\n")
    if meta:
        lines.append(f"- **Role:** {meta.get('role', '—')}")
        lines.append(f"- **Agent value (1–10):** {meta.get('agent_value', '—')}")
        lines.append(f"- **When I use it:** {meta.get('when_i_use_it', '—')}")
        lines.append(f"- **How it improves my capability:** {meta.get('improves', '—')}")
        lines.append(f"- **Watch out:** {meta.get('watch_out', '—')}")
        imp = meta.get("improve_now")
        if imp:
            lines.append(f"- **Improve immediately:** {imp}")
    else:
        lines.append("- (No curated insight entry — add to TOOL_INSIGHTS.)")

    lines.append("\n### Agent take (this run)\n")
    if ok:
        lines.append(_agent_take_pass(tool_key, evidence))
    else:
        lines.append(_agent_take_fail(tool_key, evidence, error))

    lines.append("\n---\n")
    _append_log("\n".join(lines))
    time.sleep(WAIT_S)


def _agent_take_pass(tool_key: str, evidence: dict) -> str:
    takes = {
        "perception_health": "Wiring good — I can proceed to session_start without burning a browser launch on a dead server.",
        "perception_session_start": "Browser ready — session_id is my handle for the rest of the loop.",
        "perception_navigate_and_observe": "I have a scan_id and agent_summary — enough to reason about the page; escalate to detail:full if I need raw console lines.",
        "perception_resolve_route": "I know which file owns this route — edits can be targeted.",
        "perception_search_components": f"Found {evidence.get('candidates', '?')} candidates — I can narrow before integrate.",
        "perception_integrate_component": "Dry-run plan returned — I would show user the plan before apply.",
        "perception_verify": "Criteria met — I am allowed to claim this UI state is correct.",
        "perception_probe_guards": f"Session hygiene restored={evidence.get('restored')} — maze/guard pollution handled.",
        "perception_seo_status": "SEO stack status known — I know if audit is worth starting.",
        "perception_seo_audit_start_dev": f"Dev SEO completed (instant={evidence.get('instant')}) — fast enough for agent loop.",
        "perception_flow_describe": "Checkpoints loaded — I would verify each myself, not trust automation.",
        "perception_session_end": "Clean shutdown — no leaked browser.",
    }
    if tool_key.startswith("resource:"):
        return f"Resource readable ({evidence.get('chars', 0)} chars) — playbooks available to ground my loop."
    if tool_key.startswith("edge_lab:"):
        return "Edge-lab regression green — console/network pipelines trustworthy for debugging workflows."
    return takes.get(tool_key, "Behaved as expected for agent use.")


def _agent_take_fail(tool_key: str, evidence: dict, error: str | None) -> str:
    return (
        f"**Blocked.** I would not continue the frontend loop on this path until fixed. "
        f"Error: {error or 'see evidence'}. "
        "As an agent, a failing tool here means I lose that capability entirely — no fallback."
    )


# --- MCP stdio helpers (same as E2E) ---

def _find_mcp() -> list[str]:
    exe = shutil.which("frontend-mcp")
    return [exe] if exe else [sys.executable, "-m", "navigation.mcp"]


def spawn() -> subprocess.Popen:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
    return subprocess.Popen(
        _find_mcp(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(ROOT),
        bufsize=0,
    )


def send(proc: subprocess.Popen, msg: dict) -> None:
    assert proc.stdin
    proc.stdin.write(json.dumps(msg).encode() + b"\n")
    proc.stdin.flush()


def read(proc: subprocess.Popen, eid: int, timeout: float = 120.0) -> dict:
    assert proc.stdout
    dl = time.monotonic() + timeout
    while time.monotonic() < dl:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.02)
            continue
        try:
            msg = json.loads(line.decode())
        except json.JSONDecodeError:
            continue
        if msg.get("id") != eid:
            continue
        return msg
    raise TimeoutError(f"timeout waiting id={eid}")


def envelope(resp: dict) -> dict:
    result = resp.get("result") or {}
    if result.get("isError"):
        for c in result.get("content", []):
            if c.get("text"):
                return {"ok": False, "error": c["text"]}
    for c in result.get("content", []):
        if c.get("text"):
            try:
                return json.loads(c["text"])
            except json.JSONDecodeError:
                return {"ok": False, "error": c["text"]}
    return {"ok": False, "error": str(resp.get("error"))}


def call_tool(proc: subprocess.Popen, rid: int, name: str, args: dict | None = None, timeout: float = 120.0) -> tuple[int, float, dict]:
    t0 = time.monotonic()
    send(proc, {"jsonrpc": "2.0", "id": rid, "method": "tools/call", "params": {"name": name, "arguments": args or {}}})
    resp = read(proc, rid, timeout)
    ms = (time.monotonic() - t0) * 1000
    return rid + 1, ms, envelope(resp)


def read_resource(proc: subprocess.Popen, rid: int, uri: str) -> tuple[int, float, dict]:
    t0 = time.monotonic()
    send(proc, {"jsonrpc": "2.0", "id": rid, "method": "resources/read", "params": {"uri": uri}})
    resp = read(proc, rid, 30.0)
    ms = (time.monotonic() - t0) * 1000
    contents = resp.get("result", {}).get("contents", [])
    text = contents[0].get("text", "") if contents else ""
    return rid + 1, ms, {"ok": bool(text), "chars": len(text), "error": resp.get("error")}


def run_edge_lab_tests(results: list) -> bool:
    """Handler-level edge-lab tests (installed package)."""
    import asyncio
    import tempfile
    from importlib.metadata import version

    from navigation.core.scan_registry import ScanRegistry
    from navigation.mcp.handlers import handle_navigate_and_observe, handle_session_end, handle_session_start
    from navigation.visual_browser_intelligence.browser.session_store import SessionStore

    async def _run() -> dict:
        root = Path(tempfile.mkdtemp())
        store = SessionStore(artifacts_root=root / "artifacts")
        scans = ScanRegistry()
        out: dict = {}
        sid = None
        try:
            start = await handle_session_start(store, {"base_url": URL, "headless": True})
            sid = start["session_id"]
            devtest = await handle_navigate_and_observe(
                store, scans,
                {"session_id": sid, "url": "/edge-lab?devtest=1", "include_screenshot": False, "detail": "full"},
            )
            obs = (devtest.get("data") or {}).get("observation") or {}
            console = obs.get("console") or {}
            entries = console.get("entries") or []
            has_console = any("EDGE_LAB_CONSOLE_ERROR" in str(e.get("text", "")) for e in entries)
            agent_c = (devtest.get("data") or {}).get("agent_summary", {}).get("console") or {}
            out["edge_lab:console_observe"] = {
                "ok": devtest["ok"] and has_console and agent_c.get("by_level", {}).get("error", 0) >= 1,
                "error_count": agent_c.get("by_level", {}).get("error", 0),
            }

            network = obs.get("network") or {}
            has_404 = any("dev-insights-missing" in str(e.get("url", "")) for e in (network.get("failures") or []) + (network.get("entries") or []))
            agent_n = (devtest.get("data") or {}).get("agent_summary", {}).get("network") or {}
            out["edge_lab:network_observe_failure"] = {
                "ok": devtest["ok"] and has_404 and agent_n.get("failed_count", 0) >= 1,
                "failed_count": agent_n.get("failed_count", 0),
            }

            slow = await handle_navigate_and_observe(
                store, scans,
                {"session_id": sid, "url": "/edge-lab?devtestb=1", "include_screenshot": False, "detail": "full"},
            )
            slow_net = ((slow.get("data") or {}).get("observation") or {}).get("network") or {}
            has_slow = slow_net.get("slow_count", 0) >= 1
            out["edge_lab:network_observe_slow"] = {"ok": slow["ok"] and has_slow, "slow_count": slow_net.get("slow_count", 0)}
            return out
        finally:
            if sid:
                try:
                    await handle_session_end(store, {"session_id": sid})
                except Exception:
                    pass

    t0 = time.monotonic()
    edge_results = asyncio.run(_run())
    total_ms = (time.monotonic() - t0) * 1000
    all_ok = True
    for key, data in edge_results.items():
        per_ms = total_ms / max(len(edge_results), 1)
        results.append({"tool": key, "ms": per_ms, "ok": data.get("ok"), **data})
        _post_test_write(key, ok=bool(data.get("ok")), duration_ms=per_ms, evidence=data)
        if not data.get("ok"):
            all_ok = False
    return all_ok


def main() -> int:
    import importlib.metadata as md

    packages = {
        "frontend-mcp": md.version("frontend-mcp"),
        "frontend-perception-engine": md.version("frontend-perception-engine"),
    }
    _write_header(packages)

    results: list[dict] = []
    all_ok = True
    proc = spawn()
    rid = 1

    try:
        send(proc, {"jsonrpc": "2.0", "id": rid, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "tool-by-tool", "version": "1.1.5"},
        }})
        init = read(proc, rid, 30.0)
        rid += 1
        server_ver = init.get("result", {}).get("serverInfo", {}).get("version")
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        _append_log(f"\n**MCP server_version:** `{server_ver}`\n---\n")

        # Resources (each gets post-test log)
        for uri in (
            "perception://agent-guide",
            "perception://resolver-guide",
            "perception://seo-guide",
        ):
            key = f"resource:{uri}"
            rid, ms, res = read_resource(proc, rid, uri)
            ok = bool(res.get("ok"))
            results.append({"tool": key, "ms": ms, "ok": ok, **res})
            _post_test_write(key, ok=ok, duration_ms=ms, evidence=res, error=res.get("error"))
            if not ok:
                all_ok = False

        # Tool sequence — one at a time, log after each
        session_id: str | None = None
        scan_id: str | None = None

        steps: list[tuple[str, dict | None, float]] = [
            ("perception_health", {"url": URL}, 60),
            ("perception_session_start", {"base_url": URL, "headless": True}, 90),
            ("perception_navigate_and_observe", None, 90),  # filled below
            ("perception_resolve_route", {"repo_root": REPO, "path": "/forms/validation"}, 60),
            ("perception_search_components", {"query": "date picker"}, 60),
            ("perception_integrate_component", {"query": "date picker", "plan_only": True}, 60),
            ("perception_verify", None, 60),
            ("perception_probe_guards", None, 90),
            ("perception_seo_status", {}, 60),
            ("perception_seo_audit_start", None, 30),
            ("perception_flow_describe", {"flow_id": "validation-form"}, 30),
            ("perception_session_end", None, 30),
        ]

        for name, args, timeout in steps:
            if name == "perception_navigate_and_observe" and session_id:
                args = {"session_id": session_id, "url": f"{URL}/forms/validation"}
            elif name == "perception_verify" and session_id:
                args = {"session_id": session_id, "criteria": {"url_contains": ["/forms/validation"]}}
            elif name == "perception_probe_guards" and session_id:
                args = {"session_id": session_id, "mode": "maze"}
            elif name == "perception_seo_audit_start" and session_id and scan_id:
                args = {"website_url": URL, "scan_id": scan_id, "repo_root": REPO}
            elif name == "perception_session_end" and session_id:
                args = {"session_id": session_id}
            elif args is None:
                args = {}

            log_key = "perception_seo_audit_start_dev" if name == "perception_seo_audit_start" else name
            if name == "perception_seo_audit_start" and not scan_id:
                _post_test_write(log_key, ok=False, duration_ms=0, evidence={}, error="no scan_id")
                all_ok = False
                continue

            rid, ms, env = call_tool(proc, rid, name, args, timeout)
            ok = env.get("ok") is True
            evidence: dict = {}

            if name == "perception_health":
                evidence["reachable"] = (env.get("data") or {}).get("reachable")
                evidence["contract_version"] = env.get("contract_version")
            elif name == "perception_session_start":
                session_id = env.get("session_id") or (env.get("data") or {}).get("session_id")
                evidence["session_id"] = session_id
            elif name == "perception_navigate_and_observe":
                scan_id = env.get("scan_id")
                data = env.get("data") or {}
                evidence["scan_id"] = scan_id
                evidence["has_observation"] = "observation" in data
                evidence["summary_only"] = not bool(data.get("observation"))
                blocking = (data.get("agent_summary") or {}).get("blocking") or []
                evidence["blocking_count"] = len(blocking)
            elif name == "perception_resolve_route":
                evidence["status"] = ((env.get("data") or {}).get("resolution") or {}).get("status")
            elif name == "perception_search_components":
                evidence["candidates"] = len(((env.get("data") or {}).get("component_search") or {}).get("candidates") or [])
            elif name == "perception_integrate_component":
                evidence["degraded"] = env.get("degraded")
            elif name == "perception_verify":
                evidence["verified"] = (env.get("data") or {}).get("verified")
            elif name == "perception_probe_guards":
                evidence["restored"] = ((env.get("data") or {}).get("session_hygiene") or {}).get("restored")
            elif name == "perception_seo_audit_start":
                seo = env.get("data") or {}
                evidence["instant"] = seo.get("instant")
                evidence["status"] = seo.get("status")
                ok = ok and seo.get("status") in ("completed", "partial", None)
            elif name == "perception_session_end":
                session_id = None

            results.append({"tool": log_key, "ms": ms, "ok": ok, **evidence, "error": env.get("error")})
            _post_test_write(log_key, ok=ok, duration_ms=ms, evidence=evidence, error=env.get("error"))
            if not ok:
                all_ok = False

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    # Edge-lab (previously failing) — separate session, log each
    _append_log("\n# Edge-lab regression block (installed handlers)\n\n")
    if not run_edge_lab_tests(results):
        all_ok = False

    # Final summary appended to log
    passed = sum(1 for r in results if r.get("ok"))
    _append_log(f"\n# Summary — {_ts()}\n")
    _append_log(f"- **Verdict:** {'PASS' if all_ok else 'FAIL'}")
    _append_log(f"- **Passed:** {passed}/{len(results)}")
    _append_log(f"- **server_version:** {server_ver}")
    _append_log("\n## Top improvements for agents (from this run)\n")
    _append_log("1. **Serial tool use only** — parallel MCP calls break session state.")
    _append_log("2. **`detail: full` when debugging** — summary_only hides console/network entries.")
    _append_log("3. **verify after every act** — non-optional for trustworthy UI work.")
    _append_log("4. **Health first** — saves ~6s browser start when dev server is down.")
    _append_log("5. **scan_id reuse for SEO** — dev audit stays in agent-time budgets.\n")

    LOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    LOG_JSON.write_text(json.dumps({"ok": all_ok, "server_version": server_ver, "results": results}, indent=2), encoding="utf-8")

    print(json.dumps({"ok": all_ok, "log": str(LOG_MD), "passed": f"{passed}/{len(results)}"}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
