#!/usr/bin/env python3
"""CLI for the Coordination Sandbox — decision simulation only (no MCP / no tools).

Examples:
  python -m coordination_sandbox.run --prompt "Build a landing page"
  python -m coordination_sandbox.run --scenarios coordination_sandbox/scenarios/default.yaml
  python -m coordination_sandbox.run --scenarios ... --jsonl coordination_sandbox/output/batch.jsonl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from coordination_sandbox.simulator.engine import simulate_prompt
from coordination_sandbox.simulator.report import (
    append_jsonl,
    format_text_report,
    load_scenarios_yaml,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Coordination Sandbox — simulate engineering investment decisions (no MCP)."
    )
    parser.add_argument("--prompt", "-p", help="Single engineering prompt to simulate")
    parser.add_argument(
        "--scenarios",
        "-s",
        type=Path,
        help="YAML file with a list of scenarios",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("coordination_sandbox/output"),
        help="Directory for per-scenario JSON reports",
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        help="Append all results to this JSONL file",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress text reports (still write JSON if requested)",
    )
    parser.add_argument(
        "--existing-product",
        action="store_true",
        help="Force existing-product bootstrap for --prompt",
    )
    args = parser.parse_args(argv)

    jobs: list[dict] = []
    if args.prompt:
        jobs.append({"id": "adhoc", "prompt": args.prompt, "existing_product": args.existing_product})
    if args.scenarios:
        jobs.extend(load_scenarios_yaml(args.scenarios))
    if not jobs:
        parser.error("Provide --prompt and/or --scenarios")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.jsonl and args.jsonl.exists():
        args.jsonl.unlink()

    for i, job in enumerate(jobs, start=1):
        prompt = str(job["prompt"])
        existing = job.get("existing_product")
        result = simulate_prompt(
            prompt,
            existing_product=bool(existing) if existing is not None else None,
        )
        sid = str(job.get("id") or f"scenario_{i:03d}")
        write_json(result, args.out_dir / f"{sid}.json")
        if args.jsonl:
            append_jsonl(result, args.jsonl)
        if not args.quiet:
            report = format_text_report(result)
            try:
                print(report)
            except UnicodeEncodeError:
                print(report.encode("ascii", "replace").decode("ascii"))
            print(f"[wrote] {args.out_dir / (sid + '.json')}")

    if not args.quiet:
        print(f"\nRan {len(jobs)} scenario(s). Production MCP untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
