"""Decision Layer Lab — assert helpers over strategy snapshots."""
from __future__ import annotations

from typing import Any


class ExpectationError(AssertionError):
    """Scenario or interactive expect failed."""


def _dig(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def check_expectations(snapshot: dict[str, Any], expect: dict[str, Any] | None) -> list[str]:
    """Return list of failure messages (empty = pass)."""
    if not expect:
        return []
    # Normalize kwarg-friendly aliases
    aliases = {
        "gate_state": "gate.state",
        "next_required_capability": "gate.next_required_capability",
    }
    normalized: dict[str, Any] = {}
    for key, value in expect.items():
        normalized[aliases.get(key, key)] = value
    expect = normalized

    failures: list[str] = []
    gate = snapshot.get("gate") or {}
    strategy = snapshot.get("strategy") or {}
    backlog = snapshot.get("backlog") or {}
    confidence = snapshot.get("episode_confidence") or {}

    mapping = {
        "gate.state": gate.get("state"),
        "gate.next_required_capability": gate.get("next_required_capability"),
        "next_capability": gate.get("next_required_capability") or snapshot.get("suggested_capability"),
        "surface_type": snapshot.get("surface_type") or strategy.get("surface_type"),
        "influence_level": strategy.get("influence_level"),
        "task_scope": strategy.get("task_scope"),
        "ship_council_required": gate.get("ship_council_required"),
        "residue_scan_required": gate.get("residue_scan_required"),
        "evidence_plan_incomplete": gate.get("evidence_plan_incomplete"),
        "section_checklist_required": gate.get("section_checklist_required"),
        "backlog.top.kind": (backlog.get("top") or {}).get("kind"),
        "backlog.top.id": (backlog.get("top") or {}).get("id"),
        "episode_confidence.band": confidence.get("band"),
        "episode_confidence.score_min": confidence.get("score"),
        "suggested_capability": snapshot.get("suggested_capability"),
        "host_theme": (snapshot.get("host_theme") or ""),
        "gate_next": snapshot.get("gate_next") or gate.get("next_required_capability"),
    }

    for key, expected in expect.items():
        if key == "host_theme":
            actual = snapshot.get("host_theme")
            if actual != expected:
                failures.append(f"host_theme expected {expected!r}, got {actual!r}")
            continue
        if key == "portfolio_paid_contains":
            paid = {
                p.get("family")
                for p in (snapshot.get("episode_portfolio") or {}).get("paid") or []
            }
            for item in expected or []:
                if item not in paid:
                    failures.append(f"portfolio.paid missing {item!r} (have {sorted(paid)})")
            continue
        if key == "portfolio_unpaid_contains":
            unpaid = {
                u.get("family")
                for u in (snapshot.get("episode_portfolio") or {}).get("unpaid") or []
            }
            for item in expected or []:
                if item not in unpaid:
                    failures.append(f"portfolio.unpaid missing {item!r} (have {sorted(unpaid)})")
            continue
        if key == "backlog_top_decision_not":
            top = (snapshot.get("backlog") or {}).get("top") or {}
            did = top.get("decision_id") or str(top.get("id") or "").removeprefix("decision:")
            if did == expected:
                failures.append(f"backlog.top still {expected!r}")
            continue
        if key == "ship_council_clear":
            actual = bool(
                (snapshot.get("retry_counters") or {}).get("ship_council_clear")
            )
            if actual != bool(expected):
                failures.append(f"ship_council_clear expected {expected!r}, got {actual!r}")
            continue
        if key == "host_contains":
            text = str(snapshot.get("host_action") or "")
            for item in expected or []:
                if str(item) not in text:
                    failures.append(f"host_action missing {item!r}")
            continue
        if key == "ship_signals_contains":
            signals = set((snapshot.get("last_ship") or {}).get("signals") or [])
            for item in expected or []:
                if item not in signals:
                    failures.append(f"ship signals missing {item!r} (have {sorted(signals)})")
            continue
        if key == "ship_signals_absent":
            signals = set((snapshot.get("last_ship") or {}).get("signals") or [])
            for item in expected or []:
                if item in signals:
                    failures.append(f"ship signals unexpectedly has {item!r}")
            continue
        if key == "prohibited_contains":
            prohibited = list(gate.get("prohibited_actions") or [])
            for item in expected or []:
                if item not in prohibited:
                    failures.append(f"prohibited_actions missing {item!r} (have {prohibited})")
            continue
        if key == "prohibited_absent":
            prohibited = list(gate.get("prohibited_actions") or [])
            for item in expected or []:
                if item in prohibited:
                    failures.append(f"prohibited_actions unexpectedly has {item!r}")
            continue
        if key == "gate.state_in":
            actual = gate.get("state")
            if actual not in list(expected or []):
                failures.append(f"gate.state={actual!r} not in {expected!r}")
            continue
        if key == "episode_confidence.score_min":
            actual = confidence.get("score")
            try:
                if actual is None or float(actual) < float(expected):
                    failures.append(f"episode_confidence.score {actual!r} < min {expected!r}")
            except (TypeError, ValueError):
                failures.append(f"episode_confidence.score invalid: {actual!r}")
            continue
        if key == "ledger_quality_keys":
            # {capability: design_snapshot, keys: [thin, region_count, ...]}
            cap = str((expected or {}).get("capability") or "")
            keys = list((expected or {}).get("keys") or [])
            quality = ((snapshot.get("capability_ledger") or {}).get(cap) or {}).get("quality") or {}
            if not isinstance(quality, dict) or not quality:
                failures.append(f"ledger_quality_keys: {cap!r} quality empty or missing")
            else:
                for k in keys:
                    if k not in quality:
                        failures.append(
                            f"ledger_quality_keys: {cap!r} missing {k!r} (have {sorted(quality)})"
                        )
            continue
        if key == "evidence_quality_alerts_contains":
            alerts = list((snapshot.get("strategy") or {}).get("evidence_quality_alerts") or [])
            joined = " | ".join(str(a) for a in alerts)
            for item in expected or []:
                if str(item) not in joined:
                    failures.append(
                        f"evidence_quality_alerts missing {item!r} (have {alerts})"
                    )
            continue
        if key.startswith("path:"):
            actual = _dig(snapshot, key[5:])
            if actual != expected:
                failures.append(f"{key} expected {expected!r}, got {actual!r}")
            continue

        actual = mapping.get(key)
        if key not in mapping:
            actual = _dig({"gate": gate, "strategy": strategy, **snapshot}, key)
        if actual != expected:
            failures.append(f"{key} expected {expected!r}, got {actual!r}")
    return failures


def assert_expectations(snapshot: dict[str, Any], expect: dict[str, Any] | None) -> None:
    failures = check_expectations(snapshot, expect)
    if failures:
        raise ExpectationError("; ".join(failures))
