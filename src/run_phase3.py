"""Phase 3: flow graph + verified checkpoint runner."""
from __future__ import annotations

import argparse
import asyncio
import sys

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from dotenv import load_dotenv

from navigation.perception import FLOWS, FlowRunner, artifact_dir, dump_json

load_dotenv(ROOT / ".env")
load_dotenv()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: flow graph runner")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--flow", default="validation-form", choices=list(FLOWS))
    args = parser.parse_args()

    out = artifact_dir("phase3", ROOT / "artifacts" / "phase3")
    flow = FLOWS[args.flow]()
    dump_json(out / "flow.json", flow.to_dict())

    runner = FlowRunner(base_url=args.url, headless=args.headless)
    result = await runner.run_flow(flow)
    dump_json(out / "run.json", result.to_dict())

    report = {
        "phase": 3,
        "ok": result.ok,
        "flow": args.flow,
        "result": result.to_dict(),
    }
    dump_json(out / "report.json", report)
    dump_json(ROOT / "artifacts" / "phase3" / "report.json", report)

    print(f"Phase 3 ({args.flow}): {'PASS' if result.ok else 'FAIL'}")
    for cp in result.checkpoints:
        status = "ok" if cp.ok else "FAIL"
        print(f"  [{status}] {cp.name} @ {cp.url}")
    print(f"  artifacts: {out}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        sys.exit(1)
    raise SystemExit(asyncio.run(main()))
