# Perfect Coordination Layer Phase A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slim `data.coordinator` to `coordinator_card.v1` and skip redundant `compile_engineering_strategy` when the PSM fingerprint is unchanged — without changing gate/host/evidence behavior (baseline 22/22).

**Architecture:** Extract pure helpers (`build_coordinator_card`, `strategy_fingerprint`) used by `CoordinationIntelligenceService._enrich_envelope` and `_compile_engineering_strategy`. Keep full strategy on `agent_summary` via existing `surface_engineering_strategy`. Add a Decision Lab lock + optional bridge bench script.

**Tech Stack:** Python 3, existing PSM / pytest / Decision Lab YAML.

---

## File map

| File | Responsibility |
|------|----------------|
| `src/navigation/coordination_intelligence/planning/coordinator_card.py` | `build_coordinator_card`, `strategy_fingerprint` |
| `src/navigation/coordination_intelligence/service.py` | Slim enrich; fingerprint skip before compile |
| `evals/decision_lab/experiments/EXP-022-perfect-layer-phase-a/` | Lab scenario + README |
| `evals/decision_lab/packs/baseline.yaml` | Promote EXP-022 when green |
| `scripts/bench_coordinator_bridge.py` | p50/p95 timing harness |
| `tests/test_coordinator_card.py` | Unit tests for card + fingerprint + skip |
| `tests/decision_lab/test_exp022_perfect_layer.py` | Lab runner test |

---

### Task 1: Coordinator card pure function (TDD)

**Files:**
- Create: `src/navigation/coordination_intelligence/planning/coordinator_card.py`
- Create: `tests/test_coordinator_card.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_coordinator_card.py
from navigation.coordination_intelligence.planning.coordinator_card import (
    build_coordinator_card,
)

def test_build_coordinator_card_schema_and_slim_keys():
    strategy = {
        "host_action": "BLOCKED: read perception://getting-started",
        "implementation_gate": {
            "state": "blocked",
            "next_required_capability": "inspiration_workflow",
            "prohibited_actions": ["claim_complete"],
        },
        "episode_confidence": {"score": 0.2, "band": "low"},
        "episode_portfolio": {
            "paid": [{"family": "verify"}],
            "unpaid": [{"family": "inspiration"}, {"family": "snapshot"}],
        },
        "evidence_quality_alerts": ["EVIDENCE THIN: last snapshot advanced"],
        "recommended_resource": "perception://getting-started",
    }
    card = build_coordinator_card(
        episode_id="ep1",
        strategy=strategy,
        suggested_capability="inspiration_workflow",
        suggested_semantic_action="follow_gate:inspiration_workflow",
        stop_reason=None,
    )
    assert card["schema"] == "coordinator_card.v1"
    assert card["episode_id"] == "ep1"
    assert card["integrated"] is True
    assert card["host_action"].startswith("BLOCKED")
    assert card["gate"]["state"] == "blocked"
    assert card["implementation_gate"]["state"] == "blocked"  # alias
    assert "briefing" not in card
    assert "evidence_plan" not in card
    assert card["portfolio"]["paid"] == ["verify"]
    assert card["portfolio"]["unpaid"] == ["inspiration", "snapshot"]
    assert card["evidence_quality_alerts"][0].startswith("EVIDENCE THIN")
    assert card["confidence"]["band"] == "low"
```

- [ ] **Step 2: Run test — expect FAIL (module missing)**

```bash
python -m pytest tests/test_coordinator_card.py::test_build_coordinator_card_schema_and_slim_keys -q
```

- [ ] **Step 3: Implement `build_coordinator_card`**

```python
# src/navigation/coordination_intelligence/planning/coordinator_card.py
from __future__ import annotations
from typing import Any

CARD_SCHEMA = "coordinator_card.v1"

def build_coordinator_card(
    *,
    episode_id: str,
    strategy: dict[str, Any] | None,
    suggested_capability: str | None = None,
    suggested_semantic_action: str | None = None,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    strategy = strategy or {}
    gate = dict(strategy.get("implementation_gate") or {})
    conf = strategy.get("episode_confidence") or {}
    portfolio = strategy.get("episode_portfolio") or {}
    paid = [
        str(p.get("family"))
        for p in (portfolio.get("paid") or [])
        if isinstance(p, dict) and p.get("family")
    ]
    unpaid = [
        str(u.get("family"))
        for u in (portfolio.get("unpaid") or [])
        if isinstance(u, dict) and u.get("family")
    ]
    return {
        "schema": CARD_SCHEMA,
        "episode_id": episode_id,
        "integrated": True,
        "host_action": strategy.get("host_action"),
        "gate": {
            "state": gate.get("state"),
            "next_required_capability": gate.get("next_required_capability"),
            "prohibited_actions": list(gate.get("prohibited_actions") or []),
        },
        "implementation_gate": gate,  # one-cycle alias
        "suggested_capability": suggested_capability,
        "suggested_semantic_action": suggested_semantic_action,
        "stop_reason": stop_reason,
        "confidence": {
            "score": conf.get("score"),
            "band": conf.get("band"),
        },
        "portfolio": {"paid": paid, "unpaid": unpaid},
        "evidence_quality_alerts": list(strategy.get("evidence_quality_alerts") or []),
        "recommended_resource": strategy.get("recommended_resource"),
    }
```

- [ ] **Step 4: Run test — expect PASS**

```bash
python -m pytest tests/test_coordinator_card.py::test_build_coordinator_card_schema_and_slim_keys -q
```

- [ ] **Step 5: Commit** (only if user requested commits)

```bash
git add src/navigation/coordination_intelligence/planning/coordinator_card.py tests/test_coordinator_card.py
git commit -m "feat(coordination): add slim coordinator_card.v1 builder"
```

---

### Task 2: Strategy fingerprint (TDD)

**Files:**
- Modify: `src/navigation/coordination_intelligence/planning/coordinator_card.py`
- Modify: `tests/test_coordinator_card.py`

- [ ] **Step 1: Write failing tests**

```python
from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.coordinator_card import strategy_fingerprint

def test_strategy_fingerprint_stable_for_same_psm():
    psm = ProjectSituationModel()
    psm.evidence.capability_ledger["design_snapshot"] = {
        "status": "succeeded",
        "advancement_eligible": True,
        "quality": {"thin": True, "revision_required": False},
    }
    psm.episode.verification_status = "passed"
    a = strategy_fingerprint(psm)
    b = strategy_fingerprint(psm)
    assert a == b
    assert isinstance(a, str) and len(a) >= 8

def test_strategy_fingerprint_changes_when_thin_flips():
    psm = ProjectSituationModel()
    psm.evidence.capability_ledger["design_snapshot"] = {
        "status": "succeeded",
        "advancement_eligible": True,
        "quality": {"thin": True},
    }
    before = strategy_fingerprint(psm)
    psm.evidence.capability_ledger["design_snapshot"]["quality"]["thin"] = False
    after = strategy_fingerprint(psm)
    assert before != after
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_coordinator_card.py -k fingerprint -q
```

- [ ] **Step 3: Implement `strategy_fingerprint`**

```python
import hashlib
import json

_QUALITY_FLAGS = (
    "thin",
    "thin_clear",
    "revision_required",
    "soft_seed_partial",
    "evidence_useful",
    "seed_unresolved_count",
    "usable_image_refs",
)

def strategy_fingerprint(psm: ProjectSituationModel) -> str:
    ledger_bits = []
    for cap, outcome in sorted((psm.evidence.capability_ledger or {}).items()):
        if not isinstance(outcome, dict):
            continue
        q = outcome.get("quality") if isinstance(outcome.get("quality"), dict) else {}
        flags = {k: q.get(k) for k in _QUALITY_FLAGS if k in q}
        ledger_bits.append({
            "cap": cap,
            "status": outcome.get("status"),
            "adv": outcome.get("advancement_eligible"),
            "flags": flags,
        })
    residual = {
        "verify": psm.episode.verification_status,
        "surface": getattr(psm.episode, "surface_type", None),
        "ship_clear": bool(psm.episode.retry_counters.get("ship_council_clear")),
        "ship_run": bool(psm.episode.retry_counters.get("ship_council_run")),
        "residue": psm.episode.retry_counters.get("residue_scan"),
        "sections": sorted(
            (psm.episode.retry_counters.get("section_checklist") or {}).keys()
            if isinstance(psm.episode.retry_counters.get("section_checklist"), dict)
            else []
        ),
        "lifecycle": psm.situation.lifecycle_stage,
        "maturity": psm.situation.project_maturity,
        "sclass": psm.situation.situation_class,
        "intent": "|".join(f.intent for f in psm.episode.intent_stack),
    }
    payload = {"ledger": ledger_bits, "ep": residual}
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
```

(Import `ProjectSituationModel` at type-check time or runtime in the module.)

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_coordinator_card.py -q
```

---

### Task 3: Wire slim enrich + fingerprint skip in service

**Files:**
- Modify: `src/navigation/coordination_intelligence/service.py`
- Modify: `tests/test_coordinator_card.py` (integration via service)

- [ ] **Step 1: Write failing service test**

```python
def test_enrich_envelope_uses_coordinator_card_v1_not_full_briefing():
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService
    svc = CoordinationIntelligenceService()
    # start episode with redesign intent, then apply a thin snapshot envelope
    # assert envelope["data"]["coordinator"]["schema"] == "coordinator_card.v1"
    # assert "briefing" not in envelope["data"]["coordinator"]
    # assert "engineering_strategy" in envelope.get("agent_summary", {}) or in data
```

Fill using existing patterns from `tests/test_coordination_initiative.py` / service episode_start + apply_envelope.

- [ ] **Step 2: Change `_enrich_envelope`**

Replace building `data["coordinator"]` with:

```python
from navigation.coordination_intelligence.planning.coordinator_card import build_coordinator_card

data["coordinator"] = build_coordinator_card(
    episode_id=briefing.episode_id,
    strategy=briefing.engineering_strategy,
    suggested_capability=briefing.suggested_capability,
    suggested_semantic_action=briefing.suggested_semantic_action,
    stop_reason=briefing.stop_reason,
)
# then still call surface_engineering_strategy(...) for full strategy on agent_summary
```

Remove duplication of `implementation_gate` / `evidence_plan` / `required_resources` already covered by card + strategy surface (keep `recommended_resource` on card only).

- [ ] **Step 3: Change `_compile_engineering_strategy`**

```python
from navigation.coordination_intelligence.planning.coordinator_card import strategy_fingerprint

def _compile_engineering_strategy(self, psm: ProjectSituationModel) -> None:
    catalog = self._bundle.situation_policy_catalog or {}
    if not catalog:
        return
    fp = strategy_fingerprint(psm)
    cached = psm.briefing.engineering_strategy
    if cached and psm.episode.retry_counters.get("strategy_fingerprint") == fp:
        self._align_suggestion_with_gate(psm)
        return
    strategy = compile_engineering_strategy(psm, catalog)
    psm.briefing.engineering_strategy = strategy.to_dict()
    psm.episode.retry_counters["strategy_fingerprint"] = fp
    self._align_suggestion_with_gate(psm)
```

- [ ] **Step 4: Test skip path**

```python
def test_compile_skipped_when_fingerprint_unchanged(monkeypatch):
    # compile once, capture call count via wrapper, apply noop envelope that doesn't change ledger
    # assert compile called once not twice
```

- [ ] **Step 5: Run unit suite**

```bash
python -m pytest tests/test_coordinator_card.py tests/test_coordination_initiative.py -q
```

Expected: PASS

---

### Task 4: Decision Lab lock + baseline promote

**Files:**
- Create: `evals/decision_lab/experiments/EXP-022-perfect-layer-phase-a/README.md`
- Create: `evals/decision_lab/experiments/EXP-022-perfect-layer-phase-a/scenarios/slim_coordinator_card.yaml`
- Create: `tests/decision_lab/test_exp022_perfect_layer.py`
- Modify: `evals/decision_lab/packs/baseline.yaml`
- Modify: `evals/decision_lab/experiments/INDEX.md`
- Modify: `src/navigation/coordination_intelligence/lab/expect.py` (if needed for `path:`)

Lab limitation: Decision Lab snapshots strategy from briefing, not full MCP envelopes. Two options:

**A (preferred):** Unit/service test asserts card on real `process_tool_envelope` / `_enrich_envelope`.  
**B:** Lab assert host/gate unchanged after double feed (fingerprint skip) — behavioral lock.

Do **both**:

1. Service test for card shape (Task 3).  
2. Lab scenario: feed thin snapshot twice; expect host still contains `EVIDENCE THIN` and gate stable (proves skip doesn't stale).

```yaml
# slim_coordinator_card.yaml — behavioral fingerprint lock
id: exp022_fingerprint_skip_preserves_host
intent: redesign Meridian analytics dashboard
lifecycle_stage: S03_design
project_maturity: M1
feeds:
  - tool: perception_build_design_snapshot
    ok: true
    data: {snapshot_id: thin_022}
  - tool: perception_build_design_snapshot
    ok: true
    data: {snapshot_id: thin_022}
expect:
  host_contains: ["EVIDENCE THIN"]
  path:capability_ledger.design_snapshot.quality.thin: true
```

- [ ] **Step 1: Add scenario + test; run**

```bash
python -m pytest tests/decision_lab/test_exp022_perfect_layer.py -q
python scripts/decision_lab.py run
```

Expected: baseline still green; after promote → **23/23**.

- [ ] **Step 2: Append to `baseline.yaml`:**

```yaml
  - experiments/EXP-022-perfect-layer-phase-a/scenarios/slim_coordinator_card.yaml
```

- [ ] **Step 3: Update INDEX + bump exp011/020 baseline count asserts to >= 23**

---

### Task 5: Bridge bench script

**Files:**
- Create: `scripts/bench_coordinator_bridge.py`

- [ ] **Step 1: Implement CLI**

```python
# scripts/bench_coordinator_bridge.py
"""Time CoordinatorBridge.process on fixture envelopes. Report-only (no CI fail)."""
# - episode_start redesign intent
# - loop N times: navigate_and_observe ok envelope
# - print p50/p95 ms
# - optional --json out path
```

- [ ] **Step 2: Run once and paste numbers into EXP-022 README**

```bash
python scripts/bench_coordinator_bridge.py --n 50
```

Expected: prints p50/p95; no assertion failure.

---

### Task 6: Methodology one-liner

**Files:**
- Modify: `src/navigation/mcp/methodology_resources.py` (engineering-strategy or getting-started snippet)

- [ ] Add one line: `data.coordinator` is `coordinator_card.v1` (slim); full strategy under `agent_summary.engineering_strategy`.

- [ ] Run:

```bash
python -m pytest tests/test_methodology_resources.py tests/decision_lab/ -q
python scripts/decision_lab.py run
```

Expected: all green; baseline **23/23**.

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Slim coordinator card | 1, 3 |
| Fingerprint skip | 2, 3 |
| Baseline 22→23 lock | 4 |
| Profile harness | 5 |
| Docs / methodology | 6 |
| Phase B deferred | (no task — intentional) |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-18-perfect-coordination-layer-phase-a.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — implement in this session with checkpoints  

Which approach?
