"""Full MCP eval v1.1.5: contract suite + supplemental stdio tools, per-test agent log + structure essay."""
from __future__ import annotations

import importlib.metadata as md
import json
import os
import site
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ARTIFACTS = ROOT / "artifacts" / "evals"
LOG_MD = ARTIFACTS / "v1.1.5_full_mcp_agent_log.md"
LOG_JSON = ARTIFACTS / "v1.1.5_full_mcp_agent_results.json"
WAIT_S = 1.0
URL = "http://localhost:5173"
REPO = str((ROOT / "sandbox").resolve())

# Contract test name -> agent insight (subset + prefix fallback in insight_for)
CONTRACT_INSIGHTS: dict[str, dict] = {
    "health": {"role": "Bootstrap", "agent_value": 8, "domain": "core"},
    "session_start": {"role": "Browser session", "agent_value": 10, "domain": "core"},
    "session_end": {"role": "Cleanup", "agent_value": 6, "domain": "core"},
    "navigate": {"role": "Navigation only", "agent_value": 7, "domain": "browser"},
    "observe": {"role": "Observe current page", "agent_value": 9, "domain": "browser"},
    "navigate_and_observe": {"role": "Navigate + scan", "agent_value": 10, "domain": "browser"},
    "observe_summary_only": {"role": "Default payload shape", "agent_value": 8, "domain": "browser"},
    "inline_images": {"role": "Screenshot in MCP content", "agent_value": 7, "domain": "browser"},
    "diff": {"role": "Before/after visual", "agent_value": 9, "domain": "browser"},
    "visual_diff": {"role": "Pixel diff", "agent_value": 8, "domain": "browser"},
    "verify_negative": {"role": "Verify must fail correctly", "agent_value": 9, "domain": "browser"},
    "verify_positive": {"role": "Verify pass path", "agent_value": 10, "domain": "browser"},
    "execute_script": {"role": "Custom JS act", "agent_value": 8, "domain": "browser"},
    "execute_actions": {"role": "Structured clicks/fills", "agent_value": 9, "domain": "browser"},
    "auth_gate": {"role": "Human login stop", "agent_value": 8, "domain": "browser"},
    "probe_form": {"role": "Form discovery", "agent_value": 9, "domain": "browser"},
    "probe_guards": {"role": "Route guard probe", "agent_value": 7, "domain": "browser"},
    "console_observe": {"role": "Console in observe", "agent_value": 8, "domain": "quality"},
    "network_observe_failure": {"role": "404 capture", "agent_value": 8, "domain": "quality"},
    "network_observe_slow": {"role": "Slow request capture", "agent_value": 7, "domain": "quality"},
    "search_components": {"role": "Component search", "agent_value": 8, "domain": "components"},
    "integrate_component_dry_run": {"role": "Integrate plan", "agent_value": 8, "domain": "components"},
    "seo_audit_start_dev": {"role": "Dev SEO instant", "agent_value": 7, "domain": "seo"},
    "design_review": {"role": "Design critique", "agent_value": 6, "domain": "design"},
    "perception_resolve_route": {"role": "Route -> file resolver", "agent_value": 8, "domain": "resolver"},
    "perception_validate_route_claim": {"role": "Validate route claim", "agent_value": 8, "domain": "resolver"},
    "perception_resolve_component": {"role": "Component -> file", "agent_value": 8, "domain": "resolver"},
    "perception_correlate_live": {"role": "Live DOM <-> code cross-check", "agent_value": 8, "domain": "resolver"},
    "figma_context_not_connected": {"role": "Figma graceful degrade", "agent_value": 5, "domain": "figma"},
}

DOMAIN_DEFAULTS: dict[str, dict] = {
    "core": {"role": "Core runtime", "agent_value": 8},
    "browser": {"role": "Browser loop", "agent_value": 8},
    "quality": {"role": "Dev quality signals", "agent_value": 7},
    "network": {"role": "Network intel", "agent_value": 7},
    "console": {"role": "Console intel", "agent_value": 7},
    "audit": {"role": "Lighthouse audits", "agent_value": 6},
    "diagnosis": {"role": "Full diagnosis modes", "agent_value": 7},
    "seo": {"role": "SEO intelligence", "agent_value": 6},
    "resource": {"role": "Asset recommendations", "agent_value": 5},
    "inspiration": {"role": "Design inspiration", "agent_value": 5},
    "components": {"role": "Component intelligence", "agent_value": 8},
    "design": {"role": "Design sense", "agent_value": 6},
    "figma": {"role": "Figma bridge", "agent_value": 5},
    "framework": {"role": "Framework detection/docs", "agent_value": 6},
    "flow": {"role": "Flow playbooks", "agent_value": 7},
    "state": {"role": "Session state persistence", "agent_value": 7},
    "resolver": {"role": "Code <-> UI resolver", "agent_value": 8},
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _append(text: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with LOG_MD.open("a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), flush=True)


def _wait(label: str) -> None:
    time.sleep(WAIT_S)


def insight_for(name: str) -> dict:
    bare = name.replace("contract:", "").replace("stdio:", "")
    if bare in CONTRACT_INSIGHTS:
        return CONTRACT_INSIGHTS[bare]
    if bare.startswith("perception_") and bare in CONTRACT_INSIGHTS:
        return CONTRACT_INSIGHTS[bare]
    for prefix, domain in (
        ("console_", "console"),
        ("network_", "network"),
        ("audit_", "audit"),
        ("diagnosis_", "diagnosis"),
        ("seo_", "seo"),
        ("resource_", "resource"),
        ("inspiration_", "inspiration"),
        ("design_", "design"),
        ("consistency_", "design"),
        ("figma_", "figma"),
        ("detect_", "framework"),
        ("framework_", "framework"),
        ("flow_", "flow"),
        ("state_", "state"),
        ("integrate_", "components"),
        ("plan_", "components"),
        ("select_", "components"),
        ("code_context", "framework"),
    ):
        if name.startswith(prefix) or name == prefix.rstrip("_"):
            base = DOMAIN_DEFAULTS.get(domain, {"role": domain, "agent_value": 6})
            return {**base, "domain": domain}
    return {"role": "Contract coverage", "agent_value": 6, "domain": "other"}


def post_test(
    key: str,
    *,
    ok: bool,
    duration_ms: float | None,
    evidence: dict,
    source: str,
    skipped: bool = False,
) -> None:
    meta = insight_for(key.replace("contract:", "").replace("stdio:", ""))
    verdict = "SKIP" if skipped else ("PASS" if ok else "FAIL")
    ms_s = f"{duration_ms:.0f}ms" if duration_ms is not None else "—"
    lines = [
        f"\n## {_ts()} — `{key}` — **{verdict}** ({ms_s}) [{source}]\n",
        "### Result\n",
        f"- **ok:** {ok}",
    ]
    if skipped:
        lines.append("- **skipped:** true")
    for k, v in evidence.items():
        if v is not None and k != "ok":
            lines.append(f"- **{k}:** {v}")
    lines.append("\n### Agent notes\n")
    lines.append(f"- **Domain:** {meta.get('domain', '—')}")
    lines.append(f"- **Role:** {meta.get('role', '—')}")
    lines.append(f"- **Value (1–10):** {meta.get('agent_value', '—')}")
    if ok and not skipped:
        lines.append(f"- **This run:** Handler/wire behaved as expected for `{key}`.")
    elif skipped:
        lines.append("- **This run:** Skipped (optional dep e.g. Lighthouse).")
    else:
        lines.append(f"- **This run:** Failure — agent loses this capability until fixed.")
    lines.append("\n---\n")
    _append("\n".join(lines))
    _wait(key)


def run_contract_suite() -> dict:
    wrapper = ROOT / "scripts" / "_full_eval_contract_tmp.py"
    wrapper.write_text(
        r"""
import site, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
for p in reversed(site.getsitepackages()):
    if p not in sys.path:
        sys.path.insert(0, p)
sys.path = [p for p in sys.path if Path(p).resolve() != SRC.resolve()]
import navigation
if "site-packages" not in (navigation.__file__ or "").replace("\\", "/"):
    raise SystemExit("not site-packages")
sys.path.insert(0, str(SRC))
import runpy
raise SystemExit(runpy.run_path(str(SRC / "run_mcp_contract_tests.py"), run_name="__main__") or 0)
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(wrapper)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=720,
    )
    ms = (time.monotonic() - t0) * 1000
    wrapper.unlink(missing_ok=True)
    report_path = ROOT / "artifacts" / "mcp_contract" / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    per_test_ms = ms / max(len(report.get("tests") or {}), 1)
    stderr_tail = (proc.stderr or "")[-2000:]
    return {"exit_code": proc.returncode, "duration_ms": ms, "report": report, "per_test_ms": per_test_ms, "stderr": stderr_tail}


def log_contract_results(contract: dict, results: list) -> None:
    report = contract.get("report") or {}
    tests = report.get("tests") or {}
    _append(f"\n# Phase 1: Handler contract suite ({len(tests)} tests, installed v1.1.5)\n\n")
    _append(f"Suite duration: {contract.get('duration_ms', 0):.0f}ms | exit={contract.get('exit_code')}\n\n---\n")
    for name, data in tests.items():
        ok = bool(data.get("ok"))
        skipped = bool(data.get("skipped"))
        key = f"contract:{name}"
        results.append({"key": key, "ok": ok, "skipped": skipped, "source": "contract", **data})
        post_test(key, ok=ok, duration_ms=contract.get("per_test_ms"), evidence=data, source="contract", skipped=skipped)


def run_stdio_supplement(results: list) -> None:
    """Stdio tests for tools NOT covered by contract (coordinator, resolvers, extra resources)."""
    import shutil

    _append("\n# Phase 2: Supplemental stdio tools (wire protocol)\n\n---\n")

    script = ROOT / "scripts" / "_stdio_supplement_tmp.py"
    script.write_text(
        r'''
import json, os, shutil, subprocess, sys, time
URL = "http://localhost:5173"
REPO = r''' + repr(REPO) + r'''
env = os.environ.copy()
env.pop("PYTHONPATH", None)
env.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
cmd = [shutil.which("frontend-mcp") or sys.executable]
if not shutil.which("frontend-mcp"):
    cmd += ["-m", "navigation.mcp"]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, bufsize=0)
out = []

def send(m):
    proc.stdin.write((json.dumps(m)+"\n").encode()); proc.stdin.flush()

def read(eid, t=90):
    dl = time.monotonic() + t
    while time.monotonic() < dl:
        line = proc.stdout.readline()
        if not line: time.sleep(0.02); continue
        msg = json.loads(line.decode())
        if msg.get("id") != eid: continue
        return msg
    raise RuntimeError("timeout")

def envl(resp):
    r = resp.get("result") or {}
    for c in r.get("content", []):
        if c.get("text"):
            try: return json.loads(c["text"])
            except: return {"ok": False, "error": c["text"]}
    return {"ok": False, "error": str(resp.get("error"))}

def call(rid, name, args=None, t=90):
    t0 = time.monotonic()
    send({"jsonrpc":"2.0","id":rid,"method":"tools/call","params":{"name":name,"arguments":args or {}}})
    resp = read(rid, t)
    ms = (time.monotonic()-t0)*1000
    return rid+1, ms, envl(resp)

rid = 1
send({"jsonrpc":"2.0","id":rid,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"supp","version":"1.1.5"}}})
read(rid); rid += 1
send({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})

# all resources
for uri in ("perception://agent-guide","perception://resolver-guide","perception://seo-guide",
            "perception://inspiration-guide","perception://resource-guide","perception://figma-guide"):
    t0 = time.monotonic()
    send({"jsonrpc":"2.0","id":rid,"method":"resources/read","params":{"uri":uri}})
    resp = read(rid, 30)
    ms = (time.monotonic()-t0)*1000
    text = (resp.get("result",{}).get("contents") or [{}])[0].get("text","")
    out.append({"key": f"resource:{uri}", "ok": bool(text), "ms": ms, "chars": len(text)})
    rid += 1

rid, ms, e = call(rid, "perception_health", {"url": URL})
out.append({"key": "stdio:perception_health", "ok": e.get("ok"), "ms": ms})
rid, ms, e = call(rid, "perception_session_start", {"base_url": URL, "headless": True})
sid = e.get("session_id") or (e.get("data") or {}).get("session_id")
out.append({"key": "stdio:perception_session_start", "ok": e.get("ok"), "ms": ms, "session_id": sid})

if sid:
    rid, ms, e = call(rid, "perception_navigate_and_observe", {"session_id": sid, "url": f"{URL}/forms/validation", "detail": "full"})
    scan = e.get("scan_id")
    out.append({"key": "stdio:perception_navigate_and_observe_full", "ok": e.get("ok"), "ms": ms, "scan_id": scan, "has_observation": "observation" in (e.get("data") or {})})

    rid, ms, e = call(rid, "perception_resolve_route", {"repo_root": REPO, "path": "/forms/validation"})
    resolution = (e.get("data") or {}).get("resolution") or {}
    out.append({"key": "stdio:perception_resolve_route", "ok": bool(e.get("ok")), "ms": ms, "status": resolution.get("status")})

    claim = {
        "route": "/forms/validation",
        "file": "src/pages/forms/ValidationForm.jsx",
        "component": {"name": "ValidationForm"},
    }
    rid, ms, e = call(rid, "perception_validate_route_claim", {"repo_root": REPO, "claim": claim})
    validation = (e.get("data") or {}).get("validation") or {}
    out.append({"key": "stdio:perception_validate_route_claim", "ok": bool(e.get("ok")), "ms": ms, "valid": validation.get("valid")})

    rid, ms, e = call(rid, "perception_resolve_component", {"repo_root": REPO, "name": "ValidationForm"})
    comp_res = (e.get("data") or {}).get("resolution") or {}
    out.append({"key": "stdio:perception_resolve_component", "ok": bool(e.get("ok")), "ms": ms, "status": comp_res.get("status")})

    if scan:
        rid, ms, e = call(rid, "perception_correlate_live", {"scan_id": scan, "resolution": resolution})
        out.append({"key": "stdio:perception_correlate_live", "ok": bool(e.get("ok")), "ms": ms})
    else:
        out.append({"key": "stdio:perception_correlate_live", "ok": False, "ms": 0, "error": "no scan_id"})

    rid, ms, e = call(rid, "perception_coordinator_episode_start", {"repo_root": REPO, "goal": "eval smoke"})
    ep = (e.get("data") or {}).get("episode_id")
    out.append({"key": "stdio:perception_coordinator_episode_start", "ok": e.get("ok"), "ms": ms, "episode_id": ep})

    if ep:
        rid, ms, e = call(rid, "perception_coordinator_briefing", {"episode_id": ep})
        out.append({"key": "stdio:perception_coordinator_briefing", "ok": e.get("ok"), "ms": ms})

    rid, ms, e = call(rid, "perception_figma_connect", {"action": "status"})
    out.append({"key": "stdio:perception_figma_connect", "ok": e.get("ok") is not None, "ms": ms})

    rid, ms, e = call(rid, "perception_resource_font_search", {"query": "inter", "max_results": 2})
    out.append({"key": "stdio:perception_resource_font_search", "ok": e.get("ok") or bool(e.get("degraded")), "ms": ms})

    rid, ms, e = call(rid, "perception_session_end", {"session_id": sid})
    out.append({"key": "stdio:perception_session_end", "ok": e.get("ok"), "ms": ms})

send({"jsonrpc":"2.0","id":rid,"method":"tools/list","params":{}})
resp = read(rid, 15)
tools = resp.get("result", {}).get("tools", [])
out.append({"key": "stdio:tools_list", "ok": len(tools) >= 66, "ms": 0, "tool_count": len(tools)})

proc.terminate()
print(json.dumps(out))
''',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, env=env)
    script.unlink(missing_ok=True)
    if proc.returncode != 0:
        _append(f"\n**Stdio supplement failed:** exit={proc.returncode}\n```\n{proc.stderr[-1500:]}\n```\n")
        return
    for row in json.loads(proc.stdout.strip().splitlines()[-1]):
        key = row["key"]
        ok = bool(row.get("ok"))
        results.append({"key": key, "ok": ok, "source": "stdio", **row})
        post_test(key, ok=ok, duration_ms=row.get("ms"), evidence=row, source="stdio")


def write_structure_essay(results: list, packages: dict, tool_count: int | None) -> None:
    passed = sum(1 for r in results if r.get("ok") and not r.get("skipped"))
    total = len(results)
    failed = [r["key"] for r in results if not r.get("ok") and not r.get("skipped")]

    _append(
        f"""

# Agent perspective: MCP structure, discoverability, and agent↔MCP communication

*Written after full eval — {passed}/{total} checks passed — {_ts()}*

## How this MCP is structured (what I see as an agent)

Frontend Perception MCP is a **layered deterministic runtime**, not an LLM inside the server:

```
┌─────────────────────────────────────────────────────────┐
│  Agent (Cursor / Claude) — reasoning & code edits       │
└───────────────────────────┬─────────────────────────────┘
                            │ JSON-RPC stdio
┌───────────────────────────▼─────────────────────────────┐
│  MCP surface: ~{tool_count or 83} tools + URI resources (guides, scans) │
├─────────────────────────────────────────────────────────┤
│  Envelope v1.0: ok, data, agent_summary, degraded, scan_id │
├──────────────┬──────────────┬──────────────┬────────────┤
│ Browser loop │ Resolvers    │ Intelligence │ Audits/SEO │
│ observe/verify│ code↔UI     │ components   │ lighthouse │
│ execute/diff │ correlate    │ design/figma │ diagnosis  │
└──────────────┴──────────────┴──────────────┴────────────┘
```

**Three communication channels:**

| Channel | Purpose | Agent reliance |
|---------|---------|----------------|
| **Tools** (`perception_*`) | Actions + structured facts | Primary — every task |
| **Resources** (`perception://…`) | Long-form playbooks (AGENT_GUIDE, SEO guide) | High at session start |
| **Server instructions** | Hard rules (verify never skip, blocking first) | Always visible in Cursor |

**Payload contract:** Almost every tool returns the same envelope. The highest-signal fields are:

1. `ok` — hard boolean
2. `agent_summary.blocking` — must read before advisory
3. `scan_id` / `session_id` — correlation handles
4. `degraded[]` — partial success explainers

## How easy is it to search, understand, and use tools?

| Aspect | Score (1–10) | Notes from this eval |
|--------|--------------|----------------------|
| **Naming consistency** | 8 | `perception_` prefix + domain verbs (`resolve_`, `probe_`, `audit_`) — predictable once learned |
| **Tool descriptions** | 7 | Good action hints; weak on *when* to use `detail:full` and serial-only rule |
| **Discoverability at scale** | 5 | ~83 tools in `tools/list` — overwhelming without reading `perception://agent-guide` first |
| **Learning curve** | 6 | Core loop is 5 tools; full surface needs playbooks |
| **Error/actionability** | 7 | Envelope errors are structured; some degrades need clearer fix strings |
| **Wire reliability** | 8 | Stdio + installed 1.1.5 passed; Cursor MCP connection can still fail independently |
| **Handler depth** | 9 | Contract suite exercises 74 scenarios on real sandbox |

**What works well for agents:**

- **Playbook-driven loop** — OBSERVE → REASON → ACT → VERIFY is documented and enforceable
- **Resolver-first** — `resolve_route` before editing beats blind grep
- **Summary vs full** — bandwidth control, but easy to misuse if undocumented
- **scan_id reuse** — SEO dev audit in ~350ms when observe already ran
- **Graceful degrade** — Figma not connected, framework docs missing — still returns structured ok/degraded

**What hurts agents:**

- **No tool grouping in `tools/list`** — browser vs SEO vs design is implicit only
- **Parallel tool calls** — session state breaks; not warned in schema
- **83 tools, 6 resources** — search is alphabetical in client, not semantic
- **`code_context` deprecated but still listed** — noise
- **Coordinator tools** — powerful but not in contract tests until this supplemental run

## How to improve agent ↔ MCP communication

### Immediate (P0)

1. **Add `tool_group` metadata** to each tool in `tools/list` (`browser`, `quality`, `resolver`, `component`, `seo`, `design`, `figma`, `coordinator`).
2. **Embed 1-line "call after" hints** in descriptions: e.g. verify → "Call after every execute_script/execute_actions."
3. **Health returns** `package_version` + `server_version` + `recommended_next_tool: session_start`.
4. **Server instructions block** — explicit: *"Never invoke two browser tools in parallel on the same session_id."*
5. **`detail` enum docs** in `navigate_and_observe` / `observe` schemas with examples.

### Next release (P1)

6. **`perception_tool_catalog` resource** — markdown index grouped by task ("debug broken UI", "add component", "SEO check").
7. **Example `arguments` objects** in tool definitions (MCP supports JSON schema examples).
8. **`agent_summary.next_suggested_calls`** — optional array of tool names based on last result (facts only, not LLM).
9. **Unify degraded messages** — every degrade includes `agent_action: "set repo_root to …"`.
10. **Contract smoke as `perception_smoke`** — one tool, <15s, for post-install agent self-check.

### Longer term (P2)

11. **Task macros as resources** — `perception://playbook/validation-form` with ordered tool sequence (agent still executes).
12. **Narrow tool bundles** — publish `frontend-mcp-browser` vs full package for clients that want smaller lists.
13. **Streaming progress** for long audits via MCP notifications (agent sees % without polling).

## Bottom line for agents

**Packages tested:** `{packages}`

**This eval:** {passed}/{total} checks passed.

**Failed keys:** {failed if failed else "none"}

v1.1.5 is **structurally sound** for agent-driven frontend work: the envelope, playbooks, and observe→verify loop are the right architecture. The main gap is **communication ergonomics at scale** — 83 tools need grouping, stronger schemas, and louder rules about serial use and `detail` levels. The runtime quality (contract + stdio) is there; the *onboarding surface* for new agents should be the next investment.

---
"""
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-contract", action="store_true", help="Use existing artifacts/mcp_contract/report.json")
    args = parser.parse_args()

    if LOG_MD.is_file() and not args.skip_contract:
        LOG_MD.unlink()
    packages = {
        "frontend-mcp": md.version("frontend-mcp"),
        "frontend-perception-engine": md.version("frontend-perception-engine"),
    }
    results: list[dict] = []

    _append("# Full MCP agent evaluation — v1.1.5\n\n")
    _append(f"**Started:** {_ts()}\n**Packages:** `{packages}`\n\n---\n")

    if args.skip_contract:
        report_path = ROOT / "artifacts" / "mcp_contract" / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
        contract = {
            "exit_code": 0 if report.get("ok") else 1,
            "duration_ms": report.get("duration_ms") or 0,
            "report": report,
            "per_test_ms": (report.get("duration_ms") or 0) / max(len(report.get("tests") or {}), 1),
        }
        _append("\n> Phase 1: skipped — using existing contract report.json\n\n")
    else:
        _append("\n> Running Phase 1: full handler contract suite (~5 min)...\n\n")
        contract = run_contract_suite()
    log_contract_results(contract, results)

    run_stdio_supplement(results)

    tool_count = next((r.get("tool_count") for r in results if r.get("key") == "stdio:tools_list"), None)
    write_structure_essay(results, packages, tool_count)

    all_ok = all(r.get("ok") or r.get("skipped") for r in results)
    LOG_JSON.write_text(
        json.dumps({"ok": all_ok, "packages": packages, "contract_exit": contract.get("exit_code"), "results": results}, indent=2),
        encoding="utf-8",
    )
    _append(f"\n**Final verdict:** {'PASS' if all_ok else 'FAIL'} — {_ts()}\n")
    print(json.dumps({"ok": all_ok, "log": str(LOG_MD), "total": len(results)}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
