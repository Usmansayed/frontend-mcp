"""Regression tests for 1.2.0.dev43 — Lighthouse runner subprocess hardening.

Hardcore retest (dev42) showed audits timing out at the executor wall
(timeout_s + 5) with no report, plus zombie node processes pinning dev ports.
Root cause: pipe-captured output kept blocking after the cmd.exe shim was
killed, and reports written before a slow chrome cleanup were never salvaged.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

from navigation.frontend_quality_intelligence.audits import runner as runner_mod
from navigation.frontend_quality_intelligence.audits.models import AuditCategory
from navigation.frontend_quality_intelligence.audits.runner import (
    LighthouseRunError,
    run_lighthouse_sync,
)

FAKE_LHR = {"categories": {"accessibility": {"score": 0.96}}, "audits": {}}


def _fake_lighthouse_script(tmp_path: Path, *, body: str) -> Path:
    """Write a Python script that stands in for the lighthouse CLI.

    It receives the real CLI argv (url + flags); it parses --output-path.
    """
    script = tmp_path / "fake_lighthouse.py"
    script.write_text(
        textwrap.dedent(
            """
            import json, sys, time
            out = None
            for arg in sys.argv[1:]:
                if arg.startswith('--output-path='):
                    out = arg.split('=', 1)[1]
            payload = %s
            """
            % json.dumps(FAKE_LHR)
        )
        + textwrap.dedent(body),
        encoding="utf-8",
    )
    return script


def _patch_base_cmd(monkeypatch: pytest.MonkeyPatch, script: Path) -> None:
    monkeypatch.setattr(
        runner_mod, "_lighthouse_base_cmd", lambda: [sys.executable, str(script)]
    )


def test_timeout_salvages_written_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Report written, then process hangs (chrome cleanup) → salvage, don't fail."""
    script = _fake_lighthouse_script(
        tmp_path,
        body="""
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh)
        time.sleep(120)
        """,
    )
    _patch_base_cmd(monkeypatch, script)
    out = tmp_path / "lighthouse-accessibility.json"
    lhr = run_lighthouse_sync(
        "http://127.0.0.1:3001", AuditCategory.ACCESSIBILITY, out, timeout_s=4
    )
    assert lhr["categories"]["accessibility"]["score"] == 0.96


def test_timeout_without_report_raises_with_stderr_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _fake_lighthouse_script(
        tmp_path,
        body="""
        print('chrome launch stuck', file=sys.stderr, flush=True)
        time.sleep(120)
        """,
    )
    _patch_base_cmd(monkeypatch, script)
    out = tmp_path / "lighthouse-accessibility.json"
    with pytest.raises(LighthouseRunError) as exc_info:
        run_lighthouse_sync(
            "http://127.0.0.1:3001", AuditCategory.ACCESSIBILITY, out, timeout_s=3
        )
    msg = str(exc_info.value)
    assert "timed out after 3s" in msg
    assert "chrome launch stuck" in msg


def test_nonzero_exit_with_report_returns_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """chrome-launcher EPERM cleanup flips exit code after a successful audit."""
    script = _fake_lighthouse_script(
        tmp_path,
        body="""
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh)
        print('Error: EPERM, Permission denied', file=sys.stderr)
        sys.exit(1)
        """,
    )
    _patch_base_cmd(monkeypatch, script)
    out = tmp_path / "lighthouse-accessibility.json"
    lhr = run_lighthouse_sync(
        "http://127.0.0.1:3001", AuditCategory.ACCESSIBILITY, out, timeout_s=30
    )
    assert lhr["categories"]["accessibility"]["score"] == 0.96


def test_failure_surfaces_stderr_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = _fake_lighthouse_script(
        tmp_path,
        body="""
        print('No Chrome installations found', file=sys.stderr)
        sys.exit(1)
        """,
    )
    _patch_base_cmd(monkeypatch, script)
    out = tmp_path / "lighthouse-accessibility.json"
    with pytest.raises(LighthouseRunError) as exc_info:
        run_lighthouse_sync(
            "http://127.0.0.1:3001", AuditCategory.ACCESSIBILITY, out, timeout_s=30
        )
    assert "No Chrome installations found" in str(exc_info.value)


def test_child_stdin_is_devnull(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Child must not inherit the MCP JSON-RPC stdio pipe."""
    script = _fake_lighthouse_script(
        tmp_path,
        body="""
        data = sys.stdin.read()  # DEVNULL → immediate EOF, no block
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh)
        """,
    )
    _patch_base_cmd(monkeypatch, script)
    out = tmp_path / "lighthouse-accessibility.json"
    lhr = run_lighthouse_sync(
        "http://127.0.0.1:3001", AuditCategory.ACCESSIBILITY, out, timeout_s=15
    )
    assert lhr["categories"]["accessibility"]["score"] == 0.96


def test_chrome_isolation_flags_passed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Runner must isolate Chrome from the MCP Playwright browser."""
    seen: list[list[str]] = []

    class FakeProc:
        returncode = 0

        def wait(self, timeout=None):
            return 0

    def fake_popen(cmd, **kwargs):
        seen.append(list(cmd))
        # Write the report so the runner returns successfully.
        out = None
        for arg in cmd:
            if isinstance(arg, str) and arg.startswith("--output-path="):
                out = Path(arg.split("=", 1)[1])
        assert out is not None
        out.write_text(json.dumps(FAKE_LHR), encoding="utf-8")
        return FakeProc()

    monkeypatch.setattr(runner_mod, "_lighthouse_base_cmd", lambda: [sys.executable, "-c", "pass"])
    monkeypatch.setattr(runner_mod.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(runner_mod, "_find_chrome_path", lambda: r"C:\fake\chrome.exe")
    out = tmp_path / "lighthouse-accessibility.json"
    run_lighthouse_sync(
        "http://127.0.0.1:3001", AuditCategory.ACCESSIBILITY, out, timeout_s=30
    )
    assert seen, "Popen not called"
    joined = " ".join(seen[0])
    assert "--chrome-flags=" in joined
    assert "--headless=new" in joined
    assert "--user-data-dir=" in joined
    assert "--chrome-path=C:\\fake\\chrome.exe" in joined
    assert "--max-wait-for-load=20000" in joined
