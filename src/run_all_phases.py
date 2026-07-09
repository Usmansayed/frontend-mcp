"""Run all phases sequentially; stop on first failure."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHASES = [
    "run_phase1.py",
    "run_phase2.py",
    "run_phase3.py",
    "run_phase4.py",
    "run_hardening.py",
    "run_mcp_contract_tests.py",
    "run_mcp_eval_validation_form.py",
]


def main() -> int:
    for script in PHASES:
        print("\n" + "=" * 72)
        print(f"Running {script}")
        print("=" * 72)
        rc = subprocess.call([sys.executable, str(ROOT / "src" / script), "--headless"])
        if rc != 0:
            print(f"\nStopped: {script} failed (exit {rc})")
            return rc
    print("\n" + "=" * 72)
    print("ALL PHASES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
