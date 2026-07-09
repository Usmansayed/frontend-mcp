"""
Run Browser Use with optional CRG graph hints against the Navigation Maze sandbox.

Prerequisites:
  1. Sandbox running:  cd sandbox && npm run dev
  2. AWS credentials:  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
  3. Bedrock model:    BEDROCK_MODEL=amazon.nova-pro-v1:0  (default)

Usage:
  python src/run_agent.py
  python src/run_agent.py --task "Add Pulse Watch to cart and complete checkout"
  python src/run_agent.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from navigation.browser_use import PerceptionAgentRunner, credentials_available
from navigation.codeGraph import create_code_graph

ROOT = Path(__file__).resolve().parent.parent
SANDBOX = ROOT / "sandbox"
DEFAULT_TASK = "Add Pulse Watch to cart and complete checkout"


def detect_sandbox_url() -> str:
    import os
    import urllib.request

    explicit = os.getenv("SANDBOX_URL")
    if explicit:
        return explicit
    for port in (5173, 5174, 5175):
        url = f"http://localhost:{port}"
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return "http://localhost:5173"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run perception engine with Browser Use + graph hints")
    parser.add_argument("--task", default=DEFAULT_TASK, help="Natural-language browser task")
    parser.add_argument("--url", default=None, help="Sandbox URL (default: SANDBOX_URL or http://localhost:5173)")
    parser.add_argument("--model", default=None, help="Bedrock model id (default: BEDROCK_MODEL env)")
    parser.add_argument("--region", default=None, help="AWS region (default: AWS_REGION)")
    parser.add_argument("--max-steps", type=int, default=25, help="Max agent steps")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--no-graph", action="store_true", help="Disable code graph hints")
    parser.add_argument("--dry-run", action="store_true", help="Resolve hints only, skip browser")
    parser.add_argument("--sandbox", type=Path, default=SANDBOX, help="Path to sandbox for graph indexing")
    return parser.parse_args()


async def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv()
    args = parse_args()

    print(f"Sandbox graph root: {args.sandbox}")
    code_graph = None if args.no_graph else create_code_graph(args.sandbox, enabled=True)
    print(f"Graph backend: {type(code_graph).__name__}")

    runner = PerceptionAgentRunner(
        code_graph=code_graph,
        start_url=args.url or detect_sandbox_url(),
        model=args.model,
        region=args.region,
        max_steps=args.max_steps,
        headless=args.headless,
    )

    if args.dry_run:
        hint = runner.hint_resolver.resolve(args.task)
        print("\n--- Graph hints ---")
        print(f"ok: {hint.ok}")
        print(f"summary: {hint.summary}")
        for h in hint.hits:
            print(f"  hit: {h.get('name')} -> {h.get('file_path')}")
        print("\n--- Agent system message preview ---")
        from navigation.browser_use import format_hints_for_agent

        print(format_hints_for_agent(hint, runner.start_url))
        return 0

    if not credentials_available():
        print("\nERROR: AWS credentials not found.")
        print("Create .env in the project root (see .env.example) or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.")
        print("Or use --dry-run to test graph hints without Browser Use.")
        return 1

    print(f"\nRunning task: {args.task!r}")
    print(f"Start URL: {runner.start_url}")
    print(f"Model: {args.model or 'BEDROCK_MODEL default'}")

    result = await runner.run(args.task)

    print("\n--- Timeline ---")
    for step in result.timeline:
        print(f"  {step.action}: {step.details}")

    print("\n--- Result ---")
    print(result.summary())

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
