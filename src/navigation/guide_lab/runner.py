"""Load scenarios and run Guide Lab pack."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from navigation.guide_lab.policies import decide_arm_a, decide_arm_b
from navigation.guide_lab.scoring import score_decision

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIOS = ROOT / "evals" / "guide_lab" / "scenarios"


def load_scenarios(dir_path: Path | None = None) -> list[dict[str, Any]]:
    base = dir_path or DEFAULT_SCENARIOS
    cases: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not data:
            continue
        if isinstance(data, list):
            cases.extend(data)
        else:
            cases.append(data)
    return cases


def run_pack(dir_path: Path | None = None) -> dict[str, Any]:
    cases = load_scenarios(dir_path)
    rows: list[dict[str, Any]] = []
    tallies = {
        "A": {"pass": 0, "fail": 0, "checks": {}},
        "B": {"pass": 0, "fail": 0, "checks": {}},
    }

    for case in cases:
        gold = case.get("gold") or {}
        cid = case.get("id") or "unknown"
        for arm, decide in (("A", decide_arm_a), ("B", decide_arm_b)):
            decision = decide(case)
            scored = score_decision(gold, decision)
            if scored["pass"]:
                tallies[arm]["pass"] += 1
            else:
                tallies[arm]["fail"] += 1
            for k, v in scored["checks"].items():
                bucket = tallies[arm]["checks"].setdefault(k, {"pass": 0, "fail": 0})
                bucket["pass" if v else "fail"] += 1
            rows.append(
                {
                    "id": cid,
                    "class": case.get("class"),
                    "arm": arm,
                    "pass": scored["pass"],
                    "checks": scored["checks"],
                    "decision": decision,
                    "gold": gold,
                }
            )

    n = len(cases) or 1
    summary = {
        "n_cases": len(cases),
        "A_accuracy": tallies["A"]["pass"] / n,
        "B_accuracy": tallies["B"]["pass"] / n,
        "winner": (
            "B"
            if tallies["B"]["pass"] > tallies["A"]["pass"]
            else "A"
            if tallies["A"]["pass"] > tallies["B"]["pass"]
            else "tie"
        ),
        "tallies": tallies,
        "rows": rows,
    }
    return summary


def main() -> None:
    summary = run_pack()
    out = {k: v for k, v in summary.items() if k != "rows"}
    print(json.dumps(out, indent=2))
    fails_a = []
    fails_b = []
    for row in summary["rows"]:
        if row["arm"] == "A" and not row["pass"]:
            fails_a.append(row["id"])
        if row["arm"] == "B" and not row["pass"]:
            fails_b.append(row["id"])
            print(
                f"B_FAIL {row['id']} class={row['class']} "
                f"pred={row['decision']} gold={row['gold']} checks={row['checks']}"
            )
    for row in summary["rows"]:
        if row["arm"] != "B":
            continue
        a = next(r for r in summary["rows"] if r["id"] == row["id"] and r["arm"] == "A")
        mark_a = "PASS" if a["pass"] else "FAIL"
        mark_b = "PASS" if row["pass"] else "FAIL"
        tag = "HARD" if str(row["id"]).startswith("H") else "BASE"
        print(f"{row['id']:6} [{tag}] class={row['class']!s:10} A={mark_a} B={mark_b}")
    print(
        f"\nSUMMARY A={summary['tallies']['A']['pass']}/{summary['n_cases']} "
        f"B={summary['tallies']['B']['pass']}/{summary['n_cases']} "
        f"winner={summary['winner']}"
    )
    print(f"A fails ({len(fails_a)}): {fails_a}")
    print(f"B fails ({len(fails_b)}): {fails_b}")


if __name__ == "__main__":
    main()
