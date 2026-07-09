"""
Build the CRG graph on the sandbox and exercise the perception engine wrapper.

Usage:
    python src/test_perception.py
    python src/test_perception.py --task "complete checkout for Pulse Watch"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from navigation.browser_use import BrowserUseNavigator
from navigation.codeGraph import create_code_graph

ROOT = Path(__file__).resolve().parent.parent
SANDBOX = ROOT / "sandbox"


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _print_result(label: str, result) -> None:
    status = "OK" if result.ok else "FAIL"
    print(f"\n[{status}] {label}")
    print(f"  summary: {result.summary}")
    if result.error:
        print(f"  error:   {result.error}")
    if result.payload:
        # Show compact payload highlights
        payload = result.payload
        for key in ("status", "build_type", "result_count", "nodes", "results", "impacted_files"):
            if key in payload:
                val = payload[key]
                if isinstance(val, list):
                    print(f"  {key}: {len(val)} item(s)")
                    for item in val[:3]:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("qualified_name") or item.get("file_path") or str(item)[:60]
                            print(f"    - {name}")
                        else:
                            print(f"    - {item}")
                else:
                    print(f"  {key}: {val}")


def build_and_test_graph() -> object:
    _print_section("1. BUILD GRAPH (sandbox)")
    graph = create_code_graph(repo_root=SANDBOX, enabled=True)
    print(f"  graph backend: {type(graph).__name__}")

    _print_section("2. GRAPH STATS")
    stats = graph.query("stats")
    _print_result("stats", stats)

    return graph


def run_graph_queries(graph) -> None:
    _print_section("3. GRAPH QUERIES — navigation-relevant")

    queries = [
        ("search: checkout", lambda: graph.search("checkout", limit=5)),
        ("search: login", lambda: graph.search("login", limit=5)),
        ("search: ProtectedRoute", lambda: graph.search("ProtectedRoute", kind="Function", limit=5)),
        ("search: router", lambda: graph.search("router", limit=5)),
        ("file: router.jsx", lambda: graph.get_file("src/router.jsx")),
        ("file: Cart.jsx", lambda: graph.get_file("src/pages/shop/Cart.jsx")),
        ("neighbors: CheckoutLayout", lambda: graph.get_neighbors("CheckoutLayout", relation="children_of")),
        ("neighbors: useCart imports", lambda: graph.get_neighbors("useCart", relation="callers_of")),
        ("shortest_path: checkout flow", lambda: graph.shortest_path("checkout", depth=4)),
        ("route: impact on shop files", lambda: graph.get_route(["src/pages/shop/Cart.jsx", "src/pages/shop/checkout/ShippingStep.jsx"])),
        ("find_navigation_hint: checkout button", lambda: graph.find_navigation_hint("Locate checkout button and continue flow")),
        ("find_likely_route: admin report", lambda: graph.find_likely_route("admin report dashboard")),
        ("find_entry_point: shop", lambda: graph.find_entry_point("shop checkout")),
        ("find_button_candidates: Add to cart", lambda: graph.find_button_candidates("Add to cart")),
        ("find_related_files: Cart", lambda: graph.find_related_files("Cart")),
    ]

    passed = 0
    for label, fn in queries:
        try:
            result = fn()
            _print_result(label, result)
            if result.ok:
                passed += 1
        except Exception as exc:
            print(f"\n[FAIL] {label}")
            print(f"  exception: {exc}")

    print(f"\n  Queries passed: {passed}/{len(queries)}")


def run_browser_use_tests(graph, tasks: list[str]) -> None:
    _print_section("4. BROWSER USE + OPTIONAL GRAPH HINTS")

    for task in tasks:
        print(f"\n--- Task: {task!r} ---")
        navigator = BrowserUseNavigator(code_graph=graph)
        steps = navigator.execute(task)
        for idx, step in enumerate(steps, start=1):
            print(f"  {idx}. {step.action}")
            for k, v in step.details.items():
                print(f"       {k}: {v}")


def run_null_fallback_test() -> None:
    _print_section("5. NULL FALLBACK (graph disabled)")
    graph = create_code_graph(repo_root=SANDBOX, enabled=False)
    print(f"  backend: {type(graph).__name__}")
    navigator = BrowserUseNavigator(code_graph=graph)
    steps = navigator.execute("Navigate to settings without graph")
    for step in steps:
        print(f"  {step.action} -> {step.details}")
    assert all(s.action != "code_graph.query" or not s.details.get("ok") for s in steps if s.action == "code_graph.query" or True)
    print("  Browser continued without graph: OK")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the perception engine on the sandbox")
    parser.add_argument("--task", action="append", default=[], help="Extra Browser Use task to run")
    parser.add_argument("--skip-build", action="store_true", help="Skip graph rebuild")
    parser.add_argument("--live", action="store_true", help="Run real Browser Use agent (needs AWS creds + sandbox)")
    args = parser.parse_args()

    print(f"Repo root : {ROOT}")
    print(f"Sandbox   : {SANDBOX}")
    print(f"JSX files : {len(list(SANDBOX.rglob('*.jsx')))}")

    if not SANDBOX.exists():
        print("ERROR: sandbox/ not found. Run from project root.")
        return 1

    graph = build_and_test_graph()
    if type(graph).__name__ == "NullCodeGraph":
        print("\nWARNING: CRG unavailable — running degraded tests only.")
        run_null_fallback_test()
        return 1

    if not args.skip_build:
        _print_section("1b. FULL REBUILD")
        rebuild = graph.rebuild()
        _print_result("rebuild", rebuild)

    run_graph_queries(graph)

    default_tasks = [
        "Locate checkout button and continue flow",
        "Log in as admin and open the admin report",
        "Add Pulse Watch to cart and complete checkout",
        "Navigate to settings profile and save changes",
    ]
    tasks = args.task or default_tasks
    run_browser_use_tests(graph, tasks)
    run_null_fallback_test()

    if args.live:
        from navigation.browser_use import PerceptionAgentRunner, credentials_available
        if not credentials_available():
            print("\nSkipping --live: AWS credentials not configured.")
        else:
            _print_section("6. LIVE BROWSER USE AGENT")
            runner = PerceptionAgentRunner(code_graph=graph, start_url="http://localhost:5173")
            import asyncio
            result = asyncio.run(runner.run(tasks[0]))
            print(result.summary())

    _print_section("DONE")
    print("  Graph built, queries exercised, Browser Use continued in all cases.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
