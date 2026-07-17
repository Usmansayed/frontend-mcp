"""Hidden-flaw gallery runner — catch rate + decision-quality scorecard.

Usage:
  $env:PYTHONPATH="src"
  python scripts/run_flaw_gallery.py
  python scripts/run_flaw_gallery.py --case F1
  python scripts/run_flaw_gallery.py --base-url http://localhost:5173
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CASES_DIR = ROOT / "evals" / "flaw_gallery" / "cases"
REPORTS_DIR = ROOT / "evals" / "flaw_gallery" / "reports"


def _load_cases(only: str | None) -> list[dict[str, Any]]:
    cases = []
    for path in sorted(CASES_DIR.glob("F*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if only and str(data.get("id")).upper() != only.upper():
            continue
        cases.append(data)
    return cases


def _score_case(
    case: dict[str, Any],
    *,
    soft_ok: bool,
    reasons: list[str],
    permanence_ok: bool | None,
    overflow_ok: bool | None,
    ship_signals: set[str],
    claim_prohibited: bool,
    host_action: str,
    tools: list[str],
) -> dict[str, Any]:
    expect = case.get("expect") or {}
    layers = set(case.get("must_layers") or [])
    failures: list[str] = []

    want_verified = bool(expect.get("soft_verified"))
    soft_ok_match = soft_ok is want_verified
    if not soft_ok_match:
        failures.append(f"soft_verified expected {want_verified} got {soft_ok}")

    for needle in expect.get("verify_reason_substrings") or []:
        if soft_ok:
            break
        if not any(needle.lower() in r.lower() for r in reasons):
            failures.append(f"missing verify reason substring '{needle}'")

    if expect.get("chrome_permanence_fail") is True and permanence_ok is not False:
        failures.append("expected chrome permanence to fail")
    if expect.get("chrome_permanence_fail") is False and permanence_ok is False:
        failures.append("expected chrome permanence to pass")
    if expect.get("overflow_fail") is True and overflow_ok is not False:
        failures.append("expected horizontal overflow to fail")
    if expect.get("overflow_fail") is False and overflow_ok is False:
        failures.append("expected no horizontal overflow")

    for sig in expect.get("ship_must_include") or []:
        if sig not in ship_signals:
            failures.append(f"ship missing signal {sig}")
    for sig in expect.get("ship_must_exclude") or []:
        if sig in ship_signals:
            failures.append(f"ship unexpectedly emitted {sig}")

    want_claim = bool(expect.get("claim_complete_prohibited"))
    if claim_prohibited is not want_claim:
        failures.append(f"claim_complete_prohibited expected {want_claim} got {claim_prohibited}")

    # Layer correctness: verify cases must fail soft verify; ship-only cases must keep soft pass.
    layer_ok = True
    if "verify" in layers and soft_ok:
        layer_ok = False
        failures.append("layer: verify required but soft verify passed")
    if layers == {"ship"} and not soft_ok:
        layer_ok = False
        failures.append("layer: ship-only case should soft-verify pass (chrome clean)")
    if "ship" in layers:
        need = set(expect.get("ship_must_include") or [])
        if need and not need.issubset(ship_signals):
            layer_ok = False

    catch_ok = soft_ok_match and not any(
        f.startswith("expected chrome") or f.startswith("expected horizontal") or f.startswith("ship missing")
        for f in failures
    )
    # Broader: no failures means full pass
    full_ok = len(failures) == 0

    return {
        "case_id": case["id"],
        "path": case["path"],
        "must_layers": sorted(layers),
        "catch_ok": full_ok or (catch_ok and layer_ok and claim_prohibited == want_claim),
        "layer_ok": layer_ok and soft_ok_match,
        "claim_blocked_ok": claim_prohibited == want_claim,
        "pass": full_ok,
        "failures": failures,
        "soft_verify": soft_ok,
        "reasons": reasons[:8],
        "chrome_permanence_ok": permanence_ok,
        "overflow_ok": overflow_ok,
        "ship_signals": sorted(ship_signals),
        "host_action": (host_action or "")[:240],
        "tools_used": tools,
    }


async def _run_case(case: dict[str, Any], *, base_url: str, browser: Any) -> dict[str, Any]:
    from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
    from navigation.coordination_intelligence.planning.chrome_conventions import (
        CHROME_PERMANENCE_ASSERTION,
        HORIZONTAL_OVERFLOW_ASSERTION,
        build_chrome_convention_assertions,
    )
    from navigation.coordination_intelligence.planning.engineering_strategy import (
        compile_engineering_strategy,
    )
    from navigation.coordination_intelligence.planning.section_checklist import (
        seed_section_checklist_from_regions,
    )
    from navigation.coordination_intelligence.planning.ship_council import build_ship_council
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService
    from navigation.design_snapshot_engine.engine import DesignSnapshotEngine
    from navigation.visual_browser_intelligence.verify.verification import (
        SuccessCriteria,
        evaluate_js,
        verify,
    )

    tools = ["session_start", "navigate", "snapshot", "soft_verify", "ship_council"]
    url = base_url.rstrip("/") + case["path"]
    load_runtime_artifacts.cache_clear()
    bundle = load_runtime_artifacts()
    svc = CoordinationIntelligenceService(bundle=bundle)
    sid = f"flaw_{case['id'].lower()}"
    psm = svc.episode_start(
        session_id=sid,
        intent=str(case.get("intent") or "redesign dashboard"),
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )

    await browser.navigate_to(url)
    await asyncio.sleep(0.6)

    snapshot = await DesignSnapshotEngine().capture_from_session(browser)
    snap_id = getattr(snapshot, "scan_id", None) or f"snap_{case['id']}"
    psm.artifacts.snapshot_id = str(snap_id)
    regions = list((snapshot.layout.regions if snapshot.layout else None) or [])
    seed_section_checklist_from_regions(psm, regions)

    convention = build_chrome_convention_assertions(
        psm,
        section=None,
        strategy={"task_scope": "design_driven", "influence_level": "structural"},
    )
    permanence_ok = await evaluate_js(browser, CHROME_PERMANENCE_ASSERTION)
    overflow_ok = await evaluate_js(browser, HORIZONTAL_OVERFLOW_ASSERTION)

    soft = await verify(
        browser,
        SuccessCriteria(
            text_contains=list(case.get("soft_text") or []),
            url_contains=[case["path"]],
            js_assertions=convention,
        ),
    )
    psm.episode.verification_status = "passed" if soft.ok else "failed"

    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    ship = build_ship_council(
        psm=psm,
        strategy=strategy,
        snapshot=snapshot,
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    ship_signals = {c.get("signal") for c in (ship.get("challenges") or []) if c.get("signal")}

    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    gate = strategy.get("implementation_gate") or {}
    claim_prohibited = "claim_complete" in (gate.get("prohibited_actions") or [])
    if not soft.ok:
        claim_prohibited = True
    if ship_signals and not ship.get("ship_gate", {}).get("council_clear"):
        claim_prohibited = True

    return _score_case(
        case,
        soft_ok=soft.ok,
        reasons=list(soft.reasons or []),
        permanence_ok=bool(permanence_ok) if permanence_ok is not None else None,
        overflow_ok=bool(overflow_ok) if overflow_ok is not None else None,
        ship_signals={str(s) for s in ship_signals},
        claim_prohibited=claim_prohibited,
        host_action=str(strategy.get("host_action") or ""),
        tools=tools,
    )


async def main_async(args: argparse.Namespace) -> int:
    from navigation.visual_browser_intelligence.browser.session_store import SessionStore

    cases = _load_cases(args.case)
    if not cases:
        print("No cases found")
        return 1

    store = SessionStore()
    results: list[dict[str, Any]] = []
    rec = await store.start(base_url=args.base_url, headless=True)
    try:
        for case in cases:
            print(f"\n=== {case['id']} {case['path']} ===")
            try:
                score = await _run_case(case, base_url=args.base_url, browser=rec.browser)
            except Exception as exc:
                score = {
                    "case_id": case["id"],
                    "pass": False,
                    "catch_ok": False,
                    "layer_ok": False,
                    "claim_blocked_ok": False,
                    "failures": [f"runner_error: {exc}"],
                    "tools_used": [],
                }
            results.append(score)
            status = "PASS" if score.get("pass") else "FAIL"
            print(f"{status} catch={score.get('catch_ok')} layer={score.get('layer_ok')} claim={score.get('claim_blocked_ok')}")
            if score.get("failures"):
                for f in score["failures"]:
                    print(f"  - {f}")
            print(f"  soft_verify={score.get('soft_verify')} permanence={score.get('chrome_permanence_ok')} overflow={score.get('overflow_ok')}")
            print(f"  ship={score.get('ship_signals')}")
    finally:
        await store.end(rec.session_id)
        await store.end_all()

    passed = sum(1 for r in results if r.get("pass"))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "passed": passed,
        "total": len(results),
        "all_pass": passed == len(results),
        "results": results,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / "latest.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSuite {passed}/{len(results)} -> {out}")
    return 0 if report["all_pass"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run hidden-flaw gallery scorecard")
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--case", default=None, help="Single case id e.g. F1")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
