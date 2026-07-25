"""Build concurrency rollup next to Run 4 hardcore scorecard."""
from __future__ import annotations

import json
from pathlib import Path

base_dir = Path(r"C:\Users\usman\Desktop\artful-portfolio-main\newUi")
ser = json.loads((base_dir / "hardcore-mcp-concurrency-scorecard-serialized.json").read_text(encoding="utf-8"))
con = json.loads((base_dir / "hardcore-mcp-concurrency-scorecard-concurrent.json").read_text(encoding="utf-8"))
base = json.loads((base_dir / "hardcore-mcp-scorecard.json").read_text(encoding="utf-8"))

rollup = {
    "run": "concurrency_vs_run4",
    "mcp_version": "1.2.0.dev44",
    "baseline_run4": {
        "file": "hardcore-mcp-scorecard.json",
        "session_id": base.get("session_id"),
        "process_boot_id": base.get("process_boot_id"),
        "base_url": base.get("base_url"),
        "note": "Single-session capability scorecard only — not multi-session load evidence.",
    },
    "serialized_cursor_like": {
        "file": "hardcore-mcp-concurrency-scorecard-serialized.json",
        "verdict": ser["verdict"],
        "session_held": ser["metrics"]["session_held"],
        "boot_id_stable": ser["metrics"]["boot_id_stable"],
        "lease_conflict_count": ser["metrics"]["lease_conflict_count"],
        "lease_conflicts": ser["metrics"]["lease_conflicts"],
        "audit_under_contention": ser["metrics"]["audit_under_contention"],
        "response_size_bytes": ser["metrics"]["response_size_bytes"],
        "shared_browser": {
            "browser_id": ser["metrics"]["browser_manager_after_start"].get("browser_id"),
            "active_sessions": ser["metrics"]["browser_manager_after_start"].get("active_sessions"),
            "active_leases": ser["metrics"]["browser_manager_after_start"].get("active_leases"),
        },
        "elapsed_s": ser["elapsed_s"],
    },
    "concurrent_true_overlap": {
        "file": "hardcore-mcp-concurrency-scorecard-concurrent.json",
        "verdict": con["verdict"],
        "metrics": con["metrics"],
        "ga_implication": con.get("ga_implication"),
    },
    "scored_dimensions": {
        "session_held": {
            "serialized": True,
            "concurrent": False,
            "notes": "Serialized: 4/4 start+end. Concurrent: navigate deadlock prevents held lifecycle.",
        },
        "boot_id_stable": {"serialized": True, "concurrent": True},
        "browser_lease_conflicts": {
            "serialized": 3,
            "concurrent": "EventBus deadlock under overlapping navigate",
            "serialized_detail": (
                "After agents 0..3 navigated /, /about/, /work/, /essays/ on one browser, "
                "observe for agents 0..2 all saw /essays/ (last writer wins)."
            ),
        },
        "audit_success_under_contention": {
            "serialized": ser["metrics"]["audit_under_contention"],
            "concurrent": con["metrics"]["audit_under_contention"],
        },
        "response_size_per_call": {
            "serialized": ser["metrics"]["response_size_bytes"],
            "note": (
                "Handler-direct envelopes avg ~1.1KB. Run 4 coordinator-wrapped MCP "
                "payloads are much larger — compare within same transport layer."
            ),
        },
    },
    "ga_gate": {
        "multi_session_isolation": "FAIL",
        "boot_id_stability": "PASS",
        "session_lifecycle_serialized": "PASS",
        "audit_under_multi_session_serialized": "PASS (2/2)",
        "true_concurrent_navigate": "FAIL",
        "vs_run4": (
            "Run 4 hardcore-mcp-scorecard.json is valid single-session capability evidence; "
            "it does not clear multi-session / multi-agent GA."
        ),
        "recommendation": (
            "Before multi-agent GA: add process-wide browser tool mutex OR per-session "
            "pages/contexts. Until then document single-owner browser as hard product limit."
        ),
    },
}

out = base_dir / "hardcore-mcp-concurrency-rollup.json"
out.write_text(json.dumps(rollup, indent=2), encoding="utf-8")
mirror = Path(r"C:\Users\usman\Projects\frontend-perception-engine\artifacts\concurrency")
mirror.mkdir(parents=True, exist_ok=True)
(mirror / out.name).write_text(json.dumps(rollup, indent=2), encoding="utf-8")
(mirror / "hardcore-mcp-concurrency-scorecard-concurrent.json").write_text(
    json.dumps(con, indent=2), encoding="utf-8"
)
print(json.dumps(rollup["ga_gate"], indent=2))
print("wrote", out)
