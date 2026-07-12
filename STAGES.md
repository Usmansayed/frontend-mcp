# Staged build plan

Build → test on sandbox → move to next phase. Do not start phase N+1 until phase N passes.

## Phase 1 — Observation + verification ✅ target

| Item | Module | Test |
|------|--------|------|
| Unified observation (a11y + DOM + screenshot + Tier A/B dev insights + **scan()**) | `observation.py`, `dev_insights.py`, `scan.py` | `run_hardening.py` nested collectors, cookie restore, scan |
| Success criteria + live verify | `verification.py` | URL/text checks on validation form |
| Form probe (invalid → rules → valid) | `form_probe.py` | Extract 4 validation rules from maze |
| Human-auth gate (no loop on login/MFA) | `auth_gate.py` | `/login` → `requires_human` |

```bash
cd sandbox && npm run dev   # :5173
python src/run_phase1.py --headless
```

**Done when:** `artifacts/phase1/report.json` shows `"ok": true`.

---

## Phase 2 — State + route guards

| Item | Module | Test |
|------|--------|------|
| Snapshot/restore cookies + storage | `state_manager.py` | Login → snapshot `logged_in` → reload → still authed |
| Guard detection + prerequisites | `route_guards.py` | `/dashboard` anon → `/login`; admin route needs role |

```bash
python src/run_phase2.py --headless
```

**Done when:** `artifacts/phase2/report.json` shows `"ok": true`.

---

## Phase 3 — Flow graph

| Item | Module | Test |
|------|--------|------|
| Checkpoint + flow graph schema | `flow_graph.py` | `validation-form` flow JSON emitted |
| Verified checkpoint runner | `runner.py` | 3-checkpoint validation playbook passes |

```bash
python src/run_phase3.py --headless
```

**Done when:** `artifacts/phase3/report.json` shows `"ok": true`.

---

## Phase 4 — Edge cases ✅

| Item | Module | Test |
|------|--------|------|
| CRG-guided exploration + verify | `exploration.py` | Find `/edge-lab` via hints |
| Feature flags | `feature_flags.py` | `?beta=1` gates beta UI |
| iframe context | `iframe_context.py` | Click button inside srcdoc frame |
| Virtualized lists | `virtual_scroll.py` | Scroll until row #150 in DOM |
| Rich editors | `rich_editors.py` | Fill contenteditable, verify |
| File uploads | `file_upload.py` | CDP `setFileInputFiles` |
| Live DOM / WebSockets | `websocket_observer.py` | Counter increases, URL unchanged |

Sandbox page: `/edge-lab` (`sandbox/src/pages/edge/EdgeLab.jsx`)

```bash
python src/run_phase4.py --headless
```

**Done when:** `artifacts/phase4/report.json` shows `"ok": true`.

---

## Run everything

```bash
cd sandbox && npm run dev
cd ..
$env:PYTHONPATH="src"
python src/run_all_phases.py
```

---

## Test tier matrix

| Tier | What it covers | How to run locally | Marker | CI job |
|------|----------------|--------------------|--------|--------|
| **T0** | Fast unit — no browser, no network | `pytest -m unit` | `unit` | `unit-and-golden` on every PR |
| **T1** | Golden regression — committed fixtures | `pytest -m golden` | `golden` | `unit-and-golden` |
| **T2** | MCP handler contract — needs sandbox on :5173 | `python src/run_mcp_contract_tests.py --headless` | (script) | `contract-and-eval` |
| **T3** | Phase integration — sandbox + companions | `python src/run_all_phases.py --headless` | `integration` | `phase-integration` (manual / nightly) |
| **T4** | Agent eval — validation-form scenario | `python src/run_mcp_eval_validation_form.py --headless` | `eval` | `contract-and-eval` |
| **T5** | MCP stdio wire protocol smoke | `pytest -m stdio` | `stdio` | `contract-and-eval` |
| **T6** | Cross-module end-to-end | `pytest -m "integration and slow"` | `integration` + `slow` | manual |
| **T7** | Failure / chaos | `pytest -m failure` | `failure` | manual |
| **T8** | Performance / soak | `pytest -m slow` (with perf runners) | `slow` | manual |

Standard artifact layout: `artifacts/{suite}/report.json` — CI uploads these on failure.
See `docs/PRODUCTION_TEST_PLAN.md` for the full production master test plan.
