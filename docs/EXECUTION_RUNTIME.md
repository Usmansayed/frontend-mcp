# Execution Runtime — Production (Frozen v1.0.0)

**Status:** E1–E4 complete — production-grade, frozen  
**Frozen:** 2026-07-12  
**Prerequisite:** [`coordination_layer/RELEASE.md`](../coordination_layer/RELEASE.md) (coordination v1.0.0 frozen)

---

## Architecture (frozen)

```
Host LLM
    ↓
Coordination Intelligence (frozen — planning only)
    ↓
CompiledStep
    ↓
Execution Runtime (deterministic infrastructure)
    ↓
Existing MCP Handlers (unchanged)
    ↓
Envelope v1.0 (unchanged)
    ↓
Coordinator Bridge (unchanged)
    ↓
PSM Runtime
```

**Package:** `src/navigation/execution_runtime/`

**Public API:**

```python
from navigation.execution_runtime import execute, ExecutionRuntime

batch = await execute(compiled_step)
```

---

## Responsibilities (execution runtime only)

| Owns | Does NOT own |
|------|----------------|
| Dispatch Registry | Reasoning |
| Tool Executor | Playbook selection |
| Execution Ledger | Capability routing |
| Timeout policies | Cluster resolution |
| Retry policies | User intent |
| Idempotency / dedupe | Coordinator logic duplication |
| Correlation IDs | |
| Structured logging / traces / metrics | |
| Cancellation | |
| Recovery hooks (advisory) | |

---

## E1 — Foundation

| Component | Path |
|-----------|------|
| Dispatch Registry | `execution_runtime/dispatch_registry.py` |
| Tool Executor | `execution_runtime/executor.py` |
| Execution Ledger | `execution_runtime/ledger.py` |
| Runtime facade | `execution_runtime/runtime.py` |
| MCP integration | `mcp/server.py` uses `ExecutionRuntime` |

---

## E2 — Reliability (complete)

| Component | Path |
|-----------|------|
| Failure classification | `policies/failures.py` |
| Retry policies | `policies/retry.py` |
| Timeout policies | `policies/timeout.py` |
| Recovery hints (R6 triggers) | `policies/recovery.py` |
| Cancellation | `policies/cancellation.py` |
| Safe-tool registry | `policies/safe_tools.py` |
| Failure injection (tests) | `policies/config.py` |

Deterministic rules: retry transient/timeouts on safe tools; abort permanent/cancelled; map verify failures to `TR_VERIFY_FAIL`.

---

## E3 — Idempotency (complete)

| Component | Path |
|-----------|------|
| Idempotency store | `idempotency.py` |
| Key computation + dedupe | `executor.py` |
| `data.execution` metadata | `models.py` |

Safe tools auto-dedupe by correlation scope; mutating tools never dedupe unless `allow_repeat=True`.

---

## E4 — Observability (complete)

| Component | Path |
|-----------|------|
| Correlation IDs | `observability.py` |
| Execution traces | `observability.py` |
| Execution metrics | `observability.py` |
| EVW validation suite | `execution_layer/validation/workflows.yaml` |
| EVW harness | `src/execution_validation/` |

Run EVW: `python src/run_execution_validation.py`

---

## Validation baseline

| Suite | Baseline |
|-------|----------|
| EVW | **10/10 (100%)** |
| Execution runtime unit tests | **19/19** |
| MCP contract (via runtime) | **PASS** |
| CVW regression | **14/14** (unchanged) |

Evidence: `evals/execution/reports/latest.json`, `evals/production/readiness_report.json`

---

## Production gate

Full platform sign-off:

```bash
# Sandbox dev server required for live gates
cd sandbox && npm run dev

python src/run_production_validation.py
```

Release gate G1–G10: `artifacts/release_gate/report.json`

---

## Change policy

- Do not modify coordination layer unless CVW regression proves artifact gap.
- Do not add new execution-runtime abstractions without EVW coverage.
- Handler behavior unchanged except shared dispatch extraction.
- Infrastructure frozen at v1.0.0 — future work from product usage only.

---

## References

- [`coordination_layer/RELEASE.md`](../coordination_layer/RELEASE.md)
- [`AGENT_GUIDE.md`](../AGENT_GUIDE.md)
- [`evals/coordination/COORDINATION_VALIDATION_SUITE.md`](../evals/coordination/COORDINATION_VALIDATION_SUITE.md)
