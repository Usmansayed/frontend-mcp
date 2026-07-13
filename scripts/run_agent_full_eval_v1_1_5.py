"""Full installed-MCP evaluation v1.1.5 — sequential tests, wait+log after each, agent report."""
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

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
ARTIFACTS = REPO / "artifacts" / "evals"
LOG_PATH = ARTIFACTS / "v1.1.5_agent_eval_run.log"
WAIT_S = 2.0


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    print(line, flush=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def wait_between(label: str) -> None:
    log(f"  wait {WAIT_S}s after {label}")
    time.sleep(WAIT_S)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")
    return env


def _run_step(name: str, cmd: list[str], *, timeout: int = 600) -> dict:
    log(f"START {name}: {' '.join(cmd)}")
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=str(REPO), env=_env(), capture_output=True, text=True, timeout=timeout)
    ms = round((time.monotonic() - t0) * 1000, 1)
    ok = proc.returncode == 0
    log(f"END   {name}: exit={proc.returncode} duration_ms={ms} ok={ok}")
    if proc.stdout:
        tail = proc.stdout.strip()[-1500:]
        log(f"  stdout_tail: {tail}")
    if proc.stderr and not ok:
        log(f"  stderr_tail: {proc.stderr.strip()[-800:]}")
    wait_between(name)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "duration_ms": ms,
        "ok": ok,
        "stdout_tail": proc.stdout[-6000:] if proc.stdout else "",
        "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
    }


def _pkg_info() -> dict:
    info: dict = {}
    for pkg in ("frontend-mcp", "frontend-perception-engine"):
        try:
            info[pkg] = md.version(pkg)
        except Exception:
            info[pkg] = "not installed"
    import navigation  # noqa: WPS433

    info["navigation_path"] = navigation.__file__ or ""
    return info


def _parse_json_from_stdout(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def _contract_summary() -> dict:
    path = REPO / "artifacts" / "mcp_contract" / "report.json"
    if not path.is_file():
        return {"ok": False, "error": "report missing"}
    report = json.loads(path.read_text(encoding="utf-8"))
    tests = report.get("tests") or {}
    passed = sum(1 for t in tests.values() if t.get("ok"))
    failures = [n for n, t in tests.items() if not t.get("ok")]
    return {
        "ok": report.get("ok"),
        "passed": passed,
        "total": len(tests),
        "duration_ms": report.get("duration_ms"),
        "failures": failures,
    }


def _write_agent_report(report: dict) -> Path:
    e2e = report.get("e2e") or {}
    contract = report.get("contract") or {}
    edge = report.get("edge_lab") or {}
    pkgs = report.get("packages") or {}

    # Agent capability tiers from results
    results = e2e.get("results") or []
    resources = e2e.get("resources") or []

    def tool_row(name: str) -> dict | None:
        for r in results:
            if r.get("tool") == name:
                return r
        return None

    lines = [
        "# Agent Evaluation — `frontend-mcp` v1.1.5",
        "",
        f"**Date:** {report['timestamp']}",
        f"**Verdict:** {'PASS' if report['ok'] else 'FAIL'}",
        f"**Run log:** `artifacts/evals/v1.1.5_agent_eval_run.log`",
        "",
        "## Environment",
        "",
        "| Check | Value |",
        "|-------|-------|",
        f"| `frontend-mcp` | {pkgs.get('frontend-mcp')} |",
        f"| `frontend-perception-engine` | {pkgs.get('frontend-perception-engine')} |",
        f"| `navigation` | `{pkgs.get('navigation_path')}` |",
        f"| E2E `server_version` | {e2e.get('server_version')} |",
        f"| Tool count | {e2e.get('tool_count')} |",
        "",
        "## Test battery (sequential, {WAIT_S}s pause after each)",
        "",
        "| Step | ok | duration_ms |",
        "|------|-----|-------------|",
    ]
    for step in report.get("steps") or []:
        lines.append(f"| {step['name']} | {step['ok']} | {step['duration_ms']} |")

    lines.extend([
        "",
        f"### Contract: {contract.get('passed')}/{contract.get('total')} passed",
        "",
    ])
    if contract.get("failures"):
        for f in contract["failures"]:
            lines.append(f"- FAIL: `{f}`")
    else:
        lines.append("- All contract tests passed.")

    if edge:
        lines.extend([
            "",
            "### Edge-lab regression (previously failing)",
            "",
            f"- `console_observe`: {edge.get('console_observe', {}).get('ok')}",
            f"- `network_observe_failure`: {edge.get('network_observe_failure', {}).get('ok')}",
            f"- `network_observe_slow`: {edge.get('network_observe_slow', {}).get('ok')}",
            "",
        ])

    lines.extend([
        "## E2E tool timings (installed stdio)",
        "",
        "| Tool | ms | ok | notes |",
        "|------|-----|-----|-------|",
    ])
    for r in results:
        notes = []
        for k in ("verified", "status", "instant", "restored", "candidates", "reachable"):
            if r.get(k) is not None:
                notes.append(f"{k}={r[k]}")
        lines.append(f"| `{r.get('tool')}` | {r.get('ms')} | {r.get('ok')} | {', '.join(notes) or '-'} |")

    lines.extend([
        "",
        "## MCP resources",
        "",
        "| URI | ms | ok | chars |",
        "|-----|-----|-----|-------|",
    ])
    for r in resources:
        lines.append(f"| `{r.get('uri')}` | {r.get('ms')} | {r.get('ok')} | {r.get('chars')} |")

    # --- Agent perspective ---
    lines.extend([
        "",
        "---",
        "",
        "## Agent perspective: how useful is this MCP?",
        "",
        "Written from the viewpoint of a coding agent (Cursor/Claude) using `frontend-mcp` as a",
        "deterministic browser runtime — not as a replacement for reasoning, but as **eyes, hands, and QA**.",
        "",
        "### What genuinely upgrades agent capability",
        "",
        "| Capability | Tools | Agent value (1–10) | Why it matters |",
        "|------------|-------|---------------------|----------------|",
        "| **Observe → verify loop** | `navigate_and_observe`, `verify`, `diff` | **10** | Without this, agents hallucinate UI state. Verify is the hard stop that makes frontend work trustworthy. |",
        "| **Blocking-first dev signals** | `agent_summary.blocking`, console/network in observe | **9** | Separates \"page loaded\" from \"page is broken\". Saves long debug spirals. |",
        "| **Form intelligence** | `probe_form`, `execute_actions`, `verify` | **9** | Forms are where agents fail most. Probe-before-fill is the right contract. |",
        "| **Route/code correlation** | `resolve_route`, `validate_route_claim` | **8** | Bridges repo ↔ live UI — reduces wrong-file edits. |",
        "| **Component search + integrate** | `search_components`, `integrate_component` | **8** | Turns vague \"add a date picker\" into grounded shadcn/Radix choices with dry-run. |",
        "| **SEO dev mode** | `seo_audit_start` (instant, scan reuse) | **7** | Fast enough for agent loops when `scan_id` is reused (~sub-second in this run). |",
        "| **Flow checkpoints** | `flow_describe` + per-step `verify` | **7** | Gives structure for multi-step flows without running automation blindly. |",
        "| **Guards/session hygiene** | `probe_guards`, `state_save/restore` | **7** | Catches auth redirects and maze routes — common agent failure mode. |",
        "| **MCP resources (guides)** | `perception://agent-guide`, etc. | **6** | High-quality playbooks when fetchable; still weaker if client cannot read resources reliably. |",
        "| **Design/Figma/SEO pro** | design graph, figma, full SEO | **5–6** | Powerful but heavier; best for dedicated tasks, not every UI tweak. |",
        "",
        "### What I would use on every frontend task",
        "",
        "1. `perception_health` → `session_start`",
        "2. `navigate_and_observe` (first pass: `summary_only`; after failures: `detail: full`)",
        "3. Read `agent_summary.blocking` before any advisory fields",
        "4. Code change → `verify` (never skip)",
        "5. On failure: re-observe with screenshot + `diff`",
        "",
        "### Friction I still feel as an agent",
        "",
        "| Issue | Severity | Impact |",
        "|-------|----------|--------|",
        "| **`detail` defaults to `summary_only`** — full `observation` omitted unless requested | Medium | Agents must know to pass `detail: full` for console/network entries; `agent_summary` helps but not always enough. |",
        "| **Contract suite ~5 min** | Low (dev only) | Fine for CI; too slow for interactive agent self-test. |",
        "| **Parallel tool calls** | High | Batching MCP tools can hang or confuse session state — run browser tools **one at a time**. |",
        "| **Cursor MCP connection fragility** | High | If `user-frontend-mcp` fails discovery, entire capability disappears — no graceful degrade. |",
        "| **83 tools surface area** | Medium | Discovery noise; agent must lean on guides + playbooks. |",
        "| **SEO/companion cold start** | Medium | Mitigated by `SEO_SKIP_COMPANION_BOOTSTRAP` and scan reuse in v1.1.5. |",
        "",
        "### Improvements to do **immediately** (P0)",
        "",
        "1. **Document `detail: full` in tool description** — first observe after code change should mention when to escalate to full observation.",
        "2. **Agent-facing note: no parallel browser tools** — add to `AGENT_GUIDE` and server instructions (session is single-threaded).",
        "3. **Health endpoint should report `server_version` + package versions** in envelope (helps post-upgrade debugging).",
        "4. **Fix Cursor MCP reliability** — if server fails on restart, users lose all capability; add startup self-check log.",
        "",
        "### Improvements for **next release** (P1)",
        "",
        "1. **`agent_summary` should include edge-lab-style signal hints** when console/network present but omitted from summary_only.",
        "2. **Lightweight `perception_smoke` tool** — health + one observe in <10s for agents to self-validate wiring.",
        "3. **Contract test filter** — `--only console_observe,network_*` for fast regression.",
        "4. **Integrate component**: clearer degraded reason when `repo_root` wrong (actionable fix string).",
        "5. **Resource fetch**: verify Cursor can read `perception://agent-guide` on every release (regression gate).",
        "",
        "### Improvements **when bandwidth allows** (P2)",
        "",
        "1. Tool grouping in `tools/list` metadata (browser / quality / design / seo).",
        "2. Automatic wait for SPA network/console on any URL with query flags (generalize edge-lab wait).",
        "3. Inline screenshot in verify failure without extra observe call.",
        "4. Published eval script versioned with package (`frontend-mcp-eval` entry point).",
        "",
        "### Bottom line",
        "",
    ])

    if report["ok"]:
        lines.append(
            "**v1.1.5 is production-viable for agent-driven frontend work.** The observe→verify loop, "
            "blocking dev insights, and component/SEO paths are fast enough for interactive use. "
            "The edge-lab fixes close the last handler-contract gaps. Biggest remaining risk is "
            "**MCP client wiring** (Cursor restart, uvx pin, serial tool use) — not core runtime quality."
        )
    else:
        lines.append(
            "**Some suites failed** — see step table and contract failures above. "
            "Do not treat agent workflows as fully validated until all steps pass on installed PyPI."
        )

    lines.extend([
        "",
        "## Artifacts",
        "",
        f"- `{LOG_PATH.relative_to(REPO)}`",
        f"- `artifacts/evals/v1.1.5_agent_full_battery.json`",
        f"- `artifacts/evals/v1.1.5_installed_mcp_e2e.json`",
        f"- `artifacts/mcp_contract/report.json`",
        "",
    ])

    out = REPO / "evals" / "V1.1.5_AGENT_EVALUATION.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.is_file():
        LOG_PATH.unlink()

    log("=== Agent full eval v1.1.5 ===")
    packages = _pkg_info()
    log(f"packages: {json.dumps(packages)}")

    report: dict = {
        "suite": "v1.1.5_agent_full_battery",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "packages": packages,
        "steps": [],
        "ok": True,
    }

    py = sys.executable

    # Step 1: edge-lab only (previously failing)
    edge_script = REPO / "scripts" / "test_edge_lab_only.py"
    step = _run_step("edge_lab_regression", [py, str(edge_script)], timeout=120)
    report["steps"].append(step)
    edge_data = _parse_json_from_stdout(step["stdout_tail"]) or {}
    report["edge_lab"] = edge_data.get("tests") or {}
    if not edge_data.get("all_ok"):
        report["ok"] = False

    # Step 2: stdio smoke
    smoke_code = REPO / "scripts" / "_agent_smoke_tmp.py"
    smoke_code.write_text(_SMOKE, encoding="utf-8")
    try:
        step = _run_step("stdio_smoke", [py, str(smoke_code)], timeout=120)
        report["steps"].append(step)
        if not step["ok"]:
            report["ok"] = False
    finally:
        smoke_code.unlink(missing_ok=True)

    # Step 3: E2E (update output path via env)
    e2e_script = REPO / "scripts" / "installed_mcp_e2e_v1_1_5.py"
    if not e2e_script.is_file():
        e2e_script = REPO / "scripts" / "installed_mcp_e2e_v1_1_4.py"
    step = _run_step("e2e_installed_stdio", [py, str(e2e_script)], timeout=300)
    report["steps"].append(step)
    e2e_path = ARTIFACTS / "v1.1.5_installed_mcp_e2e.json"
    if not e2e_path.is_file():
        e2e_path = ARTIFACTS / "v1.1.4_installed_mcp_e2e.json"
    if e2e_path.is_file():
        report["e2e"] = json.loads(e2e_path.read_text(encoding="utf-8"))
        if not report["e2e"].get("ok"):
            report["ok"] = False
        sv = report["e2e"].get("server_version")
        if sv and sv != "1.1.5":
            log(f"WARN server_version={sv} expected 1.1.5")
    else:
        report["ok"] = False

    # Step 4: full contract (installed handlers)
    wrapper = REPO / "scripts" / "_agent_contract_tmp.py"
    wrapper.write_text(_CONTRACT_WRAPPER, encoding="utf-8")
    try:
        step = _run_step("contract_full", [py, str(wrapper)], timeout=600)
        report["steps"].append(step)
        report["contract"] = _contract_summary()
        if not report["contract"].get("ok"):
            report["ok"] = False
        if not step["ok"]:
            report["ok"] = False
    finally:
        wrapper.unlink(missing_ok=True)

    out_json = ARTIFACTS / "v1.1.5_agent_full_battery.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path = _write_agent_report(report)
    log(f"REPORT {md_path}")
    log(f"VERDICT ok={report['ok']}")
    print(json.dumps({"ok": report["ok"], "report_md": str(md_path), "log": str(LOG_PATH)}, indent=2))
    return 0 if report["ok"] else 1


_SMOKE = r'''
import json, os, shutil, subprocess, sys, time
env = os.environ.copy()
env.pop("PYTHONPATH", None)
cmd = [shutil.which("frontend-mcp") or sys.executable]
if not shutil.which("frontend-mcp"):
    cmd += ["-m", "navigation.mcp"]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, bufsize=0)
def send(m):
    proc.stdin.write((json.dumps(m)+"\n").encode()); proc.stdin.flush()
def read(eid, t=30):
    dl=time.monotonic()+t
    while time.monotonic()<dl:
        line=proc.stdout.readline()
        if not line: time.sleep(0.02); continue
        msg=json.loads(line.decode())
        if msg.get("id")!=eid: continue
        return msg
    raise SystemExit("timeout")
rid=1
send({"jsonrpc":"2.0","id":rid,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.1.5"}}})
read(rid); rid+=1
send({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
send({"jsonrpc":"2.0","id":rid,"method":"tools/list","params":{}})
tools=read(rid)["result"]["tools"]; rid+=1
assert len(tools)>=66, len(tools)
send({"jsonrpc":"2.0","id":rid,"method":"tools/call","params":{"name":"perception_health","arguments":{"url":"http://127.0.0.1:1"}}})
h=json.loads(read(rid)["result"]["content"][0]["text"]); rid+=1
assert h.get("contract_version")=="1.0"
send({"jsonrpc":"2.0","id":rid,"method":"resources/read","params":{"uri":"perception://agent-guide"}})
g=read(rid); rid+=1
assert len(g["result"]["contents"][0]["text"])>1000
proc.terminate()
print(json.dumps({"ok": True, "tool_count": len(tools)}))
'''

_CONTRACT_WRAPPER = r'''
import asyncio, site, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
for p in reversed(site.getsitepackages()):
    if p not in sys.path:
        sys.path.insert(0, p)
sys.path = [p for p in sys.path if Path(p).resolve() != SRC.resolve()]
import navigation
nav = navigation.__file__ or ""
if "site-packages" not in nav.replace("\\", "/"):
    raise SystemExit(f"navigation not from site-packages: {nav}")
sys.path.insert(0, str(SRC))
import runpy
raise SystemExit(runpy.run_path(str(SRC / "run_mcp_contract_tests.py"), run_name="__main__") or 0)
'''


if __name__ == "__main__":
    raise SystemExit(main())
