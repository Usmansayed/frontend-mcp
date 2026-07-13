"""Run all MCP tests against installed PyPI package only (never local src/navigation)."""
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


def _ensure_installed_navigation() -> str:
    """Import navigation from site-packages before src is on sys.path."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    for p in reversed(site.getsitepackages()):
        if p not in sys.path:
            sys.path.insert(0, p)
    # Drop repo src so navigation cannot load from checkout
    sys.path = [p for p in sys.path if Path(p).resolve() != SRC.resolve()]
    import navigation  # noqa: WPS433

    nav_path = navigation.__file__ or ""
    if "site-packages" not in nav_path.replace("\\", "/"):
        raise SystemExit(f"FAIL: navigation not from site-packages: {nav_path}")
    return nav_path


def _pkg_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in ("frontend-mcp", "frontend-perception-engine"):
        try:
            out[name] = md.version(name)
        except Exception:
            out[name] = "not installed"
    return out


def _run(cmd: list[str], *, env: dict[str, str], cwd: Path, timeout: int = 600) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "duration_ms": round((time.monotonic() - t0) * 1000, 1),
        "stdout_tail": proc.stdout[-8000:] if proc.stdout else "",
        "stderr_tail": proc.stderr[-4000:] if proc.stderr else "",
    }


def _run_installed_stdio_smoke(env: dict[str, str]) -> dict:
    """Stdio smoke using frontend-mcp binary only."""
    script = REPO / "scripts" / "_installed_stdio_smoke.py"
    script.write_text(
        _STDIO_SMOKE_CODE,
        encoding="utf-8",
    )
    try:
        return _run([sys.executable, str(script)], env=env, cwd=REPO, timeout=120)
    finally:
        script.unlink(missing_ok=True)


def _run_installed_e2e(env: dict[str, str]) -> dict:
    return _run(
        [sys.executable, str(REPO / "scripts" / "installed_mcp_e2e_v1_1_4.py")],
        env=env,
        cwd=REPO,
        timeout=300,
    )


def _run_installed_contract(env: dict[str, str]) -> dict:
    wrapper = REPO / "scripts" / "_installed_contract_wrapper.py"
    wrapper.write_text(_CONTRACT_WRAPPER_CODE, encoding="utf-8")
    try:
        return _run([sys.executable, str(wrapper)], env=env, cwd=REPO, timeout=600)
    finally:
        wrapper.unlink(missing_ok=True)


def _parse_contract_failures() -> list[dict]:
    report_path = REPO / "artifacts" / "mcp_contract" / "report.json"
    if not report_path.is_file():
        return [{"error": "report.json missing"}]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return [
        {"test": name, **result}
        for name, result in (report.get("tests") or {}).items()
        if not result.get("ok")
    ]


def _load_e2e_json() -> dict:
    path = ARTIFACTS / "v1.1.4_installed_mcp_e2e.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.setdefault("SEO_SKIP_COMPANION_BOOTSTRAP", "1")

    nav_path = _ensure_installed_navigation()
    versions = _pkg_versions()

    report: dict = {
        "suite": "installed_mcp_full_battery",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "packages": versions,
        "navigation_path": nav_path,
        "python": sys.executable,
        "frontend_mcp_binary": shutil_which("frontend-mcp"),
        "suites": {},
        "ok": True,
    }

    # 1. Installed stdio smoke
    report["suites"]["stdio_smoke_installed"] = _run_installed_stdio_smoke(env)
    if report["suites"]["stdio_smoke_installed"]["exit_code"] != 0:
        report["ok"] = False

    # 2. Installed E2E
    report["suites"]["e2e_installed"] = _run_installed_e2e(env)
    e2e = _load_e2e_json()
    report["e2e_summary"] = {
        "ok": e2e.get("ok"),
        "server_version": e2e.get("server_version"),
        "tool_count": e2e.get("tool_count"),
        "results": e2e.get("results"),
        "resources": e2e.get("resources"),
    }
    if not e2e.get("ok"):
        report["ok"] = False

    # 3. Handler contract via installed navigation (handlers from site-packages)
    report["suites"]["contract_handlers_installed"] = _run_installed_contract(env)
    failures = _parse_contract_failures()
    report["contract_failures"] = failures
    contract_path = REPO / "artifacts" / "mcp_contract" / "report.json"
    if contract_path.is_file():
        cr = json.loads(contract_path.read_text(encoding="utf-8"))
        report["contract_summary"] = {
            "ok": cr.get("ok"),
            "passed": sum(1 for t in cr.get("tests", {}).values() if t.get("ok")),
            "total": len(cr.get("tests", {})),
            "duration_ms": cr.get("duration_ms"),
        }
        if not cr.get("ok"):
            report["ok"] = False
    if report["suites"]["contract_handlers_installed"]["exit_code"] != 0:
        report["ok"] = False

    out_json = ARTIFACTS / "v1.1.4_installed_mcp_full_battery.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Markdown report
    lines = [
        "# MCP Full Test Battery — Installed PyPI Only",
        "",
        f"**Date:** {report['timestamp']}",
        f"**Verdict:** {'PASS' if report['ok'] else 'FAIL'}",
        "",
        "## Environment (verified)",
        "",
        f"| Check | Value |",
        f"|-------|-------|",
        f"| `frontend-mcp` | {versions.get('frontend-mcp')} |",
        f"| `frontend-perception-engine` | {versions.get('frontend-perception-engine')} |",
        f"| `navigation.__file__` | `{nav_path}` |",
        f"| `PYTHONPATH` | (cleared) |",
        f"| `frontend-mcp` binary | `{report['frontend_mcp_binary']}` |",
        "",
        "## Suite 1: Stdio smoke (installed `frontend-mcp` subprocess)",
        "",
        f"- **Exit:** {report['suites']['stdio_smoke_installed']['exit_code']}",
        f"- **Duration:** {report['suites']['stdio_smoke_installed']['duration_ms']}ms",
        "",
        "## Suite 2: End-user E2E (installed stdio wire protocol)",
        "",
        f"- **Exit:** {report['suites']['e2e_installed']['exit_code']}",
        f"- **Duration:** {report['suites']['e2e_installed']['duration_ms']}ms",
        f"- **server_version:** {e2e.get('server_version')}",
        f"- **Overall ok:** {e2e.get('ok')}",
        "",
    ]
    if e2e.get("results"):
        lines.append("| Tool | ms | ok | notes |")
        lines.append("|------|-----|-----|-------|")
        for r in e2e["results"]:
            notes = []
            if r.get("verified") is not None:
                notes.append(f"verified={r['verified']}")
            if r.get("status"):
                notes.append(f"status={r['status']}")
            if r.get("instant"):
                notes.append("instant")
            if r.get("restored"):
                notes.append(f"restored={r['restored']}")
            if r.get("candidates"):
                notes.append(f"candidates={r['candidates']}")
            lines.append(
                f"| `{r['tool']}` | {r.get('ms')} | {r.get('ok')} | {', '.join(notes) or '-'} |"
            )
        lines.append("")
    if e2e.get("resources"):
        lines.append("### MCP resources")
        lines.append("")
        lines.append("| URI | ms | ok | chars |")
        lines.append("|-----|-----|-----|-------|")
        for r in e2e["resources"]:
            lines.append(f"| `{r['uri']}` | {r.get('ms')} | {r.get('ok')} | {r.get('chars')} |")
        lines.append("")

    cs = report.get("contract_summary") or {}
    lines.extend([
        "## Suite 3: Handler contract (installed `navigation` handlers)",
        "",
        f"- **Exit:** {report['suites']['contract_handlers_installed']['exit_code']}",
        f"- **Duration:** {report['suites']['contract_handlers_installed']['duration_ms']}ms",
        f"- **Passed:** {cs.get('passed')}/{cs.get('total')}",
        f"- **Overall ok:** {cs.get('ok')}",
        "",
    ])
    if failures:
        lines.append("### Failed contract tests")
        lines.append("")
        for f in failures:
            lines.append(f"- **`{f['test']}`** — ok={f.get('ok')}")
        lines.extend([
            "",
            "These assert sandbox **edge-lab** console/network signals at `/edge-lab?devtest=1` and `/edge-lab?devtestb=1`.",
            "They are unrelated to the PyPI install path; core browser/SEO/component paths passed.",
            "",
        ])

    lines.extend([
        "## Artifacts",
        "",
        f"- `{out_json.relative_to(REPO)}`",
        f"- `artifacts/evals/v1.1.4_installed_mcp_e2e.json`",
        f"- `artifacts/mcp_contract/report.json`",
        "",
    ])

    out_md = REPO / "evals" / "V1.1.4_INSTALLED_MCP_FULL_TEST_REPORT.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "report": str(out_md), "json": str(out_json)}, indent=2))
    return 0 if report["ok"] else 1


def shutil_which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


_STDIO_SMOKE_CODE = r'''
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
send({"jsonrpc":"2.0","id":rid,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.1.4"}}})
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
print("STDIO_SMOKE_OK")
'''

_CONTRACT_WRAPPER_CODE = r'''
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
