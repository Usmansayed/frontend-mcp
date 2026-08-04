"""Controlled multi-session concurrency experiment (pre-GA durability probe).

One MCP process (one SessionStore + one BrowserSessionManager), N logical sessions.

Phased (not gather-on-browser) so browser_use hangs cannot wedge the whole suite:
  1. session_start × N (sequential)
  2. navigate_and_observe × N — concurrent OR serialized
  3. observe × N — check URL still matches each session's intended route
  4. audit_accessibility × K under live sessions
  5. session_end × N
  6. boot_id check

Scorecard schema aligned with hardcore-mcp-scorecard.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from navigation.core.process_identity import PROCESS_BOOT_ID, process_identity_dict
from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import (
    handle_audit_accessibility,
    handle_navigate_and_observe,
    handle_observe,
    handle_session_end,
    handle_session_start,
)
from navigation.visual_browser_intelligence.browser.browser_session_manager import (
    BrowserSessionManager,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

ROUTES = ["/", "/about/", "/work/", "/essays/"]


@dataclass
class CallResult:
    agent: int
    tool: str
    family: str
    status: str
    latency_ms: float | None
    notes: str
    key_fields: dict[str, Any] = field(default_factory=dict)
    response_bytes: int = 0
    process_boot_id: str | None = None


def _utcnow() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _size(envelope: dict[str, Any]) -> int:
    return len(json.dumps(envelope, default=str).encode("utf-8"))


def _path_of(url: str) -> str:
    if not url:
        return ""
    after = url.split("://", 1)[-1]
    path = "/" + after.split("/", 1)[-1] if "/" in after else "/"
    if path != "/" and path.endswith("/"):
        return path
    return path or "/"


def _route_matches(expected: str, url: str) -> bool:
    want = expected if expected != "/" else "/"
    got = _path_of(url)
    if want == "/":
        return got in {"/", ""} or got.rstrip("/") == ""
    return want.rstrip("/") in got.rstrip("/") or want in url


async def _call(
    *,
    agent: int,
    tool: str,
    family: str,
    factory,
    results: list[CallResult],
    timeout_s: float | None = None,
) -> dict[str, Any]:
    t0 = time.monotonic()
    try:
        if timeout_s is not None:
            # Note: browser_use navigates are often not cancellation-safe; timeout
            # may only fire after the underlying call returns. Prefer phased design.
            envelope = await asyncio.wait_for(factory(), timeout=timeout_s)
        else:
            envelope = await factory()
    except Exception as exc:
        ms = round((time.monotonic() - t0) * 1000, 1)
        kind = "timeout" if isinstance(exc, asyncio.TimeoutError) else type(exc).__name__
        print(f"  [agent {agent}] {tool} -> {kind} {ms}ms", flush=True)
        results.append(
            CallResult(
                agent=agent,
                tool=tool,
                family=family,
                status="FAIL",
                latency_ms=ms,
                notes=f"exception: {kind}: {exc}",
                response_bytes=0,
                process_boot_id=PROCESS_BOOT_ID,
            )
        )
        return {"ok": False, "error": str(exc)}

    ms = round((time.monotonic() - t0) * 1000, 1)
    ok = bool(envelope.get("ok"))
    err = envelope.get("error")
    degraded = list(envelope.get("degraded") or [])
    size = _size(envelope)
    status = "PASS" if ok else "FAIL"
    note = str(err)[:200] if err else ("ok" if ok else "not ok")
    if degraded:
        note = f"{note}; degraded={degraded}"
    print(f"  [agent {agent}] {tool} -> {status} {ms}ms bytes={size}", flush=True)
    results.append(
        CallResult(
            agent=agent,
            tool=tool,
            family=family,
            status=status,
            latency_ms=ms,
            notes=note,
            key_fields={
                "session_id": envelope.get("session_id"),
                "url": envelope.get("url"),
                "scan_id": envelope.get("scan_id") or (envelope.get("data") or {}).get("scan_id"),
            },
            response_bytes=size,
            process_boot_id=PROCESS_BOOT_ID,
        )
    )
    return envelope


async def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-session concurrency experiment")
    parser.add_argument("--url", default="http://127.0.0.1:3001")
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--mode", choices=["concurrent", "serialized"], default="serialized")
    parser.add_argument("--audit-agents", type=int, default=2)
    parser.add_argument("--audit-timeout-s", type=int, default=90)
    parser.add_argument(
        "--out",
        default=str(
            Path(r"C:\Users\usman\Desktop\artful-portfolio-main\newUi")
            / "hardcore-mcp-concurrency-scorecard.json"
        ),
    )
    args = parser.parse_args()
    n = max(1, int(args.agents))

    print(
        f"concurrency experiment mode={args.mode} agents={n} url={args.url} boot={PROCESS_BOOT_ID}",
        flush=True,
    )

    BrowserSessionManager.reset_default()
    store = SessionStore(
        artifacts_root=ROOT / "artifacts" / "concurrency",
        manager=BrowserSessionManager.get(),
    )
    scans = ScanRegistry()
    results: list[CallResult] = []
    conflicts: list[dict[str, Any]] = []
    session_ids: dict[int, str] = {}
    routes = {i: ROUTES[i % len(ROUTES)] for i in range(n)}

    boot_start = PROCESS_BOOT_ID
    identity_start = process_identity_dict()
    t_suite = time.monotonic()

    # --- Phase 1: session_start (always sequential — shared acquire is locked) ---
    print("PHASE 1 session_start", flush=True)
    for i in range(n):
        env = await _call(
            agent=i,
            tool="perception_session_start",
            family="Session",
            factory=lambda: handle_session_start(
                store,
                {
                    "base_url": args.url,
                    "intent": f"concurrency agent durability probe",
                    "headless": True,
                },
            ),
            results=results,
        )
        sid = env.get("session_id") or (env.get("data") or {}).get("session_id")
        if sid:
            session_ids[i] = sid
            results[-1].key_fields["session_id"] = sid
        else:
            conflicts.append({"agent": i, "phase": "session_start", "detail": "no session_id"})

    mgr_after_start = store.manager.diagnostics()
    print(f"  manager after start: {mgr_after_start}", flush=True)

    # --- Phase 2: navigate ---
    print(f"PHASE 2 navigate ({args.mode})", flush=True)

    async def navigate_one(i: int) -> None:
        sid = session_ids.get(i)
        if not sid:
            return
        route = routes[i]
        env = await _call(
            agent=i,
            tool=f"perception_navigate_and_observe:{route}",
            family="Browser",
            factory=lambda s=sid, r=route: handle_navigate_and_observe(
                store,
                scans,
                {"session_id": s, "url": r, "detail": "metadata_only", "no_images": True},
            ),
            results=results,
        )
        url = str(env.get("url") or "")
        if env.get("ok") and not _route_matches(route, url):
            detail = f"url_mismatch:expected={route} got={url}"
            conflicts.append({"agent": i, "session_id": sid, "phase": "navigate", "detail": detail})
            results[-1].status = "MIXED"
            results[-1].notes = f"{results[-1].notes}; LEASE/URL_CONFLICT: {detail}"
        results[-1].key_fields["manager"] = {
            "active_sessions": store.manager.diagnostics().get("active_sessions"),
            "active_leases": store.manager.diagnostics().get("active_leases"),
            "browser_id": store.manager.diagnostics().get("browser_id"),
        }

    if args.mode == "concurrent":
        # True overlap — expected to surface shared-browser races / EventBus deadlocks.
        # Bound the whole phase: wait_for on a single navigate is often not
        # cancellation-safe inside browser_use.
        tasks = [asyncio.create_task(navigate_one(i), name=f"nav-{i}") for i in range(n)]
        done, pending = await asyncio.wait(tasks, timeout=90.0)
        for t in pending:
            t.cancel()
            conflicts.append(
                {
                    "agent": int(t.get_name().split("-")[-1]) if t.get_name() else -1,
                    "phase": "navigate",
                    "detail": "phase_timeout: concurrent navigate hung >90s (EventBus deadlock)",
                }
            )
            results.append(
                CallResult(
                    agent=int(t.get_name().split("-")[-1]) if t.get_name() else -1,
                    tool="perception_navigate_and_observe:hung",
                    family="Browser",
                    status="FAIL",
                    latency_ms=90000.0,
                    notes="exception: phase_timeout: concurrent navigate hung >90s",
                    response_bytes=0,
                    process_boot_id=PROCESS_BOOT_ID,
                )
            )
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    else:
        for i in range(n):
            await navigate_one(i)

    # --- Phase 3: observe each session — isolation check ---
    print("PHASE 3 observe (isolation check)", flush=True)
    for i in range(n):
        sid = session_ids.get(i)
        if not sid:
            continue
        route = routes[i]
        env = await _call(
            agent=i,
            tool="perception_observe",
            family="Browser",
            factory=lambda s=sid: handle_observe(
                store,
                scans,
                {"session_id": s, "detail": "metadata_only", "no_images": True},
            ),
            results=results,
        )
        url = str(env.get("url") or "")
        # After N navigates on one browser, later observes should NOT all still match
        # their own route unless isolation exists. Record mismatch as lease conflict.
        if env.get("ok") and not _route_matches(route, url):
            detail = f"url_mismatch:expected={route} got={url}"
            conflicts.append({"agent": i, "session_id": sid, "phase": "observe", "detail": detail})
            results[-1].status = "MIXED"
            results[-1].notes = f"{results[-1].notes}; LEASE/URL_CONFLICT: {detail}"

    # --- Phase 4: audits under live multi-session ---
    print("PHASE 4 audit_accessibility", flush=True)
    audit_indexes = list(range(min(args.audit_agents, n)))

    async def audit_one(i: int) -> None:
        sid = session_ids.get(i)
        if not sid:
            return
        route = routes[i]
        env = await _call(
            agent=i,
            tool="perception_audit_accessibility",
            family="Diagnostics",
            factory=lambda s=sid, r=route: handle_audit_accessibility(
                store,
                {
                    "session_id": s,
                    "url": f"{args.url.rstrip('/')}{r}",
                    "timeout_s": args.audit_timeout_s,
                },
            ),
            results=results,
        )
        score = ((env.get("data") or {}).get("audit") or {}).get("score")
        results[-1].key_fields["score"] = score
        if results[-1].status == "PASS" and score is None:
            results[-1].status = "MIXED"
            results[-1].notes = f"{results[-1].notes}; ok but no score"

    if args.mode == "concurrent" and len(audit_indexes) > 1:
        await asyncio.gather(*(audit_one(i) for i in audit_indexes))
    else:
        for i in audit_indexes:
            await audit_one(i)

    # --- Phase 5: end ---
    print("PHASE 5 session_end", flush=True)
    for i in range(n):
        sid = session_ids.get(i)
        if not sid:
            continue
        await _call(
            agent=i,
            tool="perception_session_end",
            family="Session",
            factory=lambda s=sid: handle_session_end(store, {"session_id": s}),
            results=results,
        )

    elapsed_s = round(time.monotonic() - t_suite, 2)
    boot_end = PROCESS_BOOT_ID
    mgr_final = store.manager.diagnostics()
    try:
        await store.end_all()
    except Exception:
        pass

    boots = {r.process_boot_id for r in results if r.process_boot_id}
    boot_stable = boots <= {boot_start} and boot_start == boot_end
    sessions_started = len(session_ids)
    ends_ok = sum(1 for r in results if r.tool == "perception_session_end" and r.status == "PASS")
    unknown = any("unknown session" in (r.notes or "").lower() for r in results)
    session_held = sessions_started == n and ends_ok == n and not unknown

    audits = [r for r in results if r.tool == "perception_audit_accessibility"]
    audits_pass = sum(
        1 for r in audits if r.status == "PASS" and r.key_fields.get("score") is not None
    )
    sizes = [r.response_bytes for r in results if r.response_bytes]
    size_stats = {
        "count": len(sizes),
        "min": min(sizes) if sizes else 0,
        "max": max(sizes) if sizes else 0,
        "avg": int(sum(sizes) / len(sizes)) if sizes else 0,
        "p95": sorted(sizes)[max(0, int(len(sizes) * 0.95) - 1)] if sizes else 0,
    }
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    if not session_held or not boot_stable:
        verdict = "FAIL"
    elif conflicts or audits_pass < len(audits):
        verdict = "MIXED"
    else:
        verdict = "PASS"

    scorecard = {
        "run": "concurrency",
        "experiment": "multi_session_one_process",
        "mcp_version": "1.2.0.dev44",
        "mode": args.mode,
        "agents": n,
        "audit_agents": args.audit_agents,
        "base_url": args.url,
        "started_at": _utcnow(),
        "elapsed_s": elapsed_s,
        "process_boot_id_start": boot_start,
        "process_boot_id_end": boot_end,
        "process_identity_start": identity_start,
        "session_ids": {str(k): v for k, v in session_ids.items()},
        "routes": {str(k): v for k, v in routes.items()},
        "metrics": {
            "session_held": session_held,
            "sessions_started": sessions_started,
            "session_ends_ok": ends_ok,
            "boot_id_stable": boot_stable,
            "distinct_boot_ids_seen": sorted(b for b in boots if b),
            "lease_conflict_count": len(conflicts),
            "lease_conflicts": conflicts,
            "audit_under_contention": {
                "attempted": len(audits),
                "passed_with_score": audits_pass,
                "pass_rate": (audits_pass / len(audits)) if audits else None,
            },
            "response_size_bytes": size_stats,
            "browser_manager_after_start": mgr_after_start,
            "browser_manager_final": mgr_final,
            "note": (
                "All logical sessions share one ManagedBrowser (single-owner). "
                "URL mismatches on observe after other agents navigated = expected "
                "lease/isolation conflict, not an app bug."
            ),
        },
        "totals": {"calls": len(results), **by_status},
        "results": [
            {
                "agent": r.agent,
                "tool": r.tool,
                "family": r.family,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "response_bytes": r.response_bytes,
                "notes": r.notes,
                "key_fields": r.key_fields,
                "process_boot_id": r.process_boot_id,
            }
            for r in results
        ],
        "verdict": verdict,
        "baseline_scorecard": "hardcore-mcp-scorecard.json (run 4)",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    mirror = ROOT / "artifacts" / "concurrency" / out.name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")

    summary = {
        "verdict": verdict,
        "session_held": session_held,
        "boot_id_stable": boot_stable,
        "lease_conflicts": len(conflicts),
        "audits_pass": f"{audits_pass}/{len(audits)}",
        "response_bytes_avg": size_stats["avg"],
        "response_bytes_max": size_stats["max"],
        "elapsed_s": elapsed_s,
        "out": str(out),
    }
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if verdict != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
