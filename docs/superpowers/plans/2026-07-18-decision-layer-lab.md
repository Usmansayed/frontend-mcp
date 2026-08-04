# Decision Layer Lab — Implementation Plan

> **For agentic workers:** Implement task-by-task. TDD for core expect/runner.

**Goal:** In-repo Decision Lab (interactive + automated) over production coordination via fake envelopes.

**Architecture:** Thin `DecisionLayerLab` wraps `CoordinationIntelligenceService`; YAML scenarios drive feeds + expects; CLI for REPL and pack runs.

**Tech Stack:** Python, PyYAML, pytest, existing `make_envelope` / service.

---

## File map

| Path | Responsibility |
|------|----------------|
| `lab/core.py` | DecisionLayerLab |
| `lab/runner.py` | Load YAML, run pack, scorecard |
| `lab/expect.py` | Assertion helpers |
| `lab/cli.py` | `run` / `repl` / `show` |
| `evals/decision_lab/scenarios/*.yaml` | Source-of-truth pack |
| `tests/decision_lab/` | Unit + pack smoke |
| `scripts/decision_lab.py` | Entry |

### Tasks

- [x] Design doc
- [x] Lab core + expect
- [x] Runner + starter scenarios
- [x] CLI + tests green
