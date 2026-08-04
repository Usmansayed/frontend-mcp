"""CLI for Decision Layer Lab — interactive REPL + pack runner."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from navigation.coordination_intelligence.lab.core import DecisionLayerLab
from navigation.coordination_intelligence.lab.runner import (
    default_scenarios_dir,
    list_scenarios,
    resolve_pack_scenario_paths,
    run_pack,
    run_scenario,
    write_scorecard,
)


def cmd_run(args: argparse.Namespace) -> int:
    if args.scenario:
        result = run_scenario(args.scenario)
        print(json.dumps(result.to_dict(), indent=2, default=str))
        if not result.passed:
            print("FAILED:", *result.failures, sep="\n  ")
            return 1
        print("PASS", result.id)
        return 0

    # Prefer named/manifest pack; legacy --pack as directory still works.
    pack_arg = args.pack
    if pack_arg and Path(pack_arg).is_dir():
        pack = run_pack(directory=pack_arg)
    else:
        pack = run_pack(pack=pack_arg)  # None → baseline

    print(pack.scorecard())
    if args.json:
        print(json.dumps(pack.to_dict(), indent=2, default=str))
    if args.scorecard:
        path = write_scorecard(pack, args.scorecard)
        print(f"wrote {path}")
    return 0 if pack.passed else 1


def cmd_list(args: argparse.Namespace) -> int:
    pack_arg = args.pack
    if pack_arg and Path(pack_arg).is_dir():
        for p in list_scenarios(pack_arg):
            print(p.name)
        return 0
    try:
        pack_id, paths = resolve_pack_scenario_paths(pack_arg)
    except FileNotFoundError:
        for p in list_scenarios(default_scenarios_dir()):
            print(p.name)
        return 0
    print(f"# pack={pack_id} ({len(paths)})")
    for p in paths:
        print(p.as_posix())
    return 0


def cmd_repl(args: argparse.Namespace) -> int:
    lab = DecisionLayerLab(session_id=args.session_id or "lab_repl")
    intent = args.intent or "build a new SaaS analytics dashboard"
    lab.start(
        intent,
        lifecycle_stage=args.lifecycle or "S03_design",
        project_maturity=args.maturity or "M1",
    )
    print(lab.show())
    print("\nCommands: show | feed <tool> [ok|fail] | expect key=value | quit")
    print("Example: feed perception_verify ok")
    while True:
        try:
            line = input("lab> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("q", "quit", "exit"):
            break
        if line == "show":
            print(lab.show())
            continue
        if line.startswith("feed "):
            parts = line.split()
            tool = parts[1]
            ok = True
            if len(parts) > 2 and parts[2] in ("fail", "false", "0"):
                ok = False
            data: dict = {}
            if tool == "perception_verify" and ok:
                data = {"verified": True, "reasons": []}
            elif tool == "perception_verify" and not ok:
                data = {"verified": False, "reasons": ["lab fail"]}
            lab.feed(tool, ok=ok, data=data, error=None if ok else "lab fail")
            print(lab.show())
            continue
        if line.startswith("expect "):
            assertions: dict = {}
            for token in line[len("expect "):].split():
                if "=" not in token:
                    continue
                k, v = token.split("=", 1)
                if v in ("true", "false"):
                    assertions[k] = v == "true"
                else:
                    assertions[k] = v
            try:
                lab.expect(**assertions)
                print("OK")
            except Exception as exc:  # noqa: BLE001 — REPL surface
                print(f"FAIL: {exc}")
            continue
        print("unknown command")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="decision_lab", description="Decision Layer Lab")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run scenario or pack (default: baseline)")
    run_p.add_argument("--scenario", "-s", help="Path to one scenario YAML")
    run_p.add_argument(
        "--pack",
        "-p",
        help="Pack name (baseline|smoke), manifest YAML, or scenarios directory",
    )
    run_p.add_argument("--json", action="store_true")
    run_p.add_argument("--scorecard", help="Write JSON scorecard to this path")
    run_p.set_defaults(func=cmd_run)

    list_p = sub.add_parser("list", help="List scenarios in a pack")
    list_p.add_argument("--pack", "-p", help="Pack name/manifest/dir (default baseline)")
    list_p.set_defaults(func=cmd_list)

    repl_p = sub.add_parser("repl", help="Interactive decision lab")
    repl_p.add_argument("--intent", "-i")
    repl_p.add_argument("--lifecycle", default="S03_design")
    repl_p.add_argument("--maturity", default="M1")
    repl_p.add_argument("--session-id", default="lab_repl")
    repl_p.set_defaults(func=cmd_repl)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
