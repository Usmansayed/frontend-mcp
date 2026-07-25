"""Syntax-check MCP-injected verify JS assertions."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.chrome_conventions import (
    CHROME_PERMANENCE_ASSERTION,
    HORIZONTAL_OVERFLOW_ASSERTION,
)
from navigation.coordination_intelligence.planning.section_checklist import (
    build_section_verify_assertions,
)
from navigation.visual_browser_intelligence.verify.verification import evaluate_js


def wrap_like_evaluate_js(expression: str) -> str:
    expr = expression.strip()
    if expr.startswith("() =>") or expr.startswith("()=>") or expr.startswith("function"):
        return f"({expr})()"
    if not expr.startswith("(") and not expr.startswith("function"):
        return f"(() => {{ return ({expr}); }})()"
    return expr


def node_syntax_ok(expr: str) -> tuple[bool, str]:
    wrapped = wrap_like_evaluate_js(expr)
    # new Function parses without executing DOM APIs
    script = (
        "const src = "
        + json.dumps(wrapped)
        + "; try { new Function(src); console.log('OK'); } "
        + "catch (e) { console.log('FAIL:' + e.message); process.exitCode = 1; }"
    )
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    out = (r.stdout or r.stderr or "").strip()
    return r.returncode == 0, out


def main() -> int:
    cases: list[tuple[str, str]] = []
    for role in ("nav", "aside", "sidebar", "header", "main", "section", "form"):
        for a in build_section_verify_assertions({"role": role, "section_id": f"{role}:0"}):
            cases.append((f"section:{role}", a))
    cases.append(("permanence", CHROME_PERMANENCE_ASSERTION))
    cases.append(("overflow", HORIZONTAL_OVERFLOW_ASSERTION))

    failed = 0
    for name, expr in cases:
        ok, out = node_syntax_ok(expr)
        print(f"{'PASS' if ok else 'FAIL'} {name}: {out}")
        if not ok:
            failed += 1
            print("  expr head:", expr[:120])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
