# Coordinator Implementation Readiness Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Frontend MCP teach and govern pre-code methodology so structural work cannot treat failed or provisional calls as resolved engineering decisions.

**Architecture:** Add focused methodology resources and concise tool metadata for progressive discovery. Extend the existing PSM with a deterministic capability-outcome ledger, compile an `implementation_gate` and ordered `evidence_plan`, and surface the required resource/capability on every coordinator-enriched response. Preserve envelope v1: top-level `ok` remains transport success while optional `data.coordination_evidence` governs posture and playbook advancement.

**Tech Stack:** Python dataclasses, existing Coordination Intelligence PSM/runtime, Engineering Strategy, Frontend Engineering Spec, pytest.

---

### Task 1: Capability outcome ledger

**Files:**
- Modify: `src/navigation/coordination_intelligence/models.py`
- Modify: `src/navigation/coordination_intelligence/psm/normalize.py`
- Test: `tests/test_implementation_readiness.py`

- [ ] Write failing tests proving a failed inspiration/component call is recorded as `failed`, weak inspiration as `provisional`, and successful component selection as `succeeded`.
- [ ] Run `python -m pytest tests/test_implementation_readiness.py -q` and confirm failures are caused by the missing ledger.
- [ ] Add `capability_ledger` to `EvidenceState` and a deterministic outcome classifier that records status, failure/degraded reasons, artifact references, and timestamp.
- [ ] Consume optional `data.coordination_evidence` before legacy `ok` inference; support `success | degraded | failure | noop` and `advancement_eligible`.
- [ ] Ensure `component_select` updates design-system posture only after a usable successful selection; attempts alone never resolve foundation posture.
- [ ] Run the focused tests to green.

### Task 2: Implementation readiness compiler

**Files:**
- Create: `src/navigation/coordination_intelligence/planning/implementation_readiness.py`
- Modify: `src/navigation/coordination_intelligence/planning/engineering_strategy.py`
- Modify: `src/navigation/coordination_intelligence/models.py`
- Test: `tests/test_implementation_readiness.py`

- [ ] Write failing tests for `blocked | provisional | ready` behavior:
  - structural greenfield starts blocked;
  - weak/failed inspiration remains blocked and routes to a supported fallback;
  - successful reference evidence plus foundation selection becomes ready;
  - minimal/hotfix work remains ready for narrow implementation.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Compile `implementation_gate`, `evidence_plan`, `allowed_actions`, `prohibited_actions`, `next_required_capability`, and `completion_criteria` using existing unresolved decisions and ledger state.
- [ ] Add the fields to `EngineeringStrategy.to_dict()` without changing the V1 decision catalog.
- [ ] Run the focused tests to green.

### Task 3: Fix false resolution and weak reference binding

**Files:**
- Modify: `src/navigation/coordination_intelligence/planning/situation_policy.py`
- Modify: `src/navigation/engineering_knowledge/reference_binding.py`
- Modify: `src/navigation/mcp/handlers.py`
- Test: `tests/test_implementation_readiness.py`
- Test: `tests/test_reference_binding.py`

- [ ] Write failing tests showing capability attempts do not create `inspiration`/`selected` posture and low-coverage inspiration binding is provisional.
- [ ] Run tests and verify red.
- [ ] Derive posture from successful ledger outcomes instead of attempt counts.
- [ ] Return binding quality (`provisional | implementation_ready`) from reference binding; inspiration seed bindings remain provisional until measured evidence hardens them.
- [ ] Make inspiration collect report unusable image/blob evidence as degraded/blocking for structural readiness while preserving the tool envelope contract.
- [ ] Make Loop Governor require evidence `advancement_eligible` when present, preventing cleanup, status, connect-only, plan-only, and failed-review outputs from completing intelligence steps.
- [ ] Run focused tests to green.

### Task 4: Focused methodology resources and tool discovery

**Files:**
- Modify: `src/navigation/mcp/resources.py`
- Create: `src/navigation/mcp/guides/GETTING_STARTED.md`
- Create: `src/navigation/mcp/guides/FRONTEND_METHODOLOGY.md`
- Create: `src/navigation/mcp/guides/DESIGN_WORKFLOW.md`
- Create: `src/navigation/mcp/guides/REDESIGN_WORKFLOW.md`
- Create: `src/navigation/mcp/guides/BUGFIX_WORKFLOW.md`
- Create: `src/navigation/mcp/guides/ENGINEERING_STRATEGY.md`
- Create: `src/navigation/mcp/guides/DECISION_LEDGER.md`
- Create: `src/navigation/mcp/guides/VERIFICATION_GUIDE.md`
- Create: `src/navigation/mcp/guides/BROWSER_LIFECYCLE.md`
- Modify: `src/navigation/mcp/tools.py`
- Test: `tests/test_methodology_resources.py`
- Test: `tests/test_tool_description_quality.py`

- [ ] Write failing tests proving focused resources list/read, the compatibility guide indexes them, and high-impact tool descriptions state Does/Use when/Returns/Next within a size budget.
- [ ] Run resource and metadata tests and verify red.
- [ ] Add focused resources with stable URIs and compact decision-led workflows.
- [ ] Convert `AGENT_GUIDE.md` into a compatibility index while preserving specialist guide links.
- [ ] Rewrite high-impact Session, Coordinator, Design, Component, Inspiration, Figma, Resolver, and Verify descriptions.
- [ ] Run resource and metadata tests to green.

### Task 5: Surface required-next execution guidance

**Files:**
- Modify: `src/navigation/coordination_intelligence/service.py`
- Modify: `src/navigation/coordination_intelligence/integration/bridge.py`
- Modify: `src/navigation/mcp/instructions.py`
- Modify: `src/navigation/mcp/AGENT_GUIDE.md`
- Modify: `docs/cursor-rules/frontend-mcp.mdc`
- Test: `tests/test_coordination_integration.py`

- [ ] Write a failing integration test proving every coordinator-enriched response exposes the gate and that structural failures add a high-priority blocking directive.
- [ ] Run the integration test and verify red.
- [ ] Surface gate fields under both `data.coordinator` and `agent_summary`.
- [ ] Surface `recommended_resource` and `required_resources`; choose one workflow resource from task scope and evidence state.
- [ ] Change host wording from optional evidence to required-next capability while blocked.
- [ ] Add the rule: calling a tool is not evidence; unresolved/partial/degraded results cannot lock structural decisions.
- [ ] Define scaffold-only recovery when the dev server is unavailable.
- [ ] Run focused integration tests to green.

### Task 6: Regression, package, and installed-interface validation

**Files:**
- Modify: `tests/test_engineering_strategy.py`
- Modify: `tests/test_coordination_integration.py`
- Modify: `tests/test_reference_binding.py`
- Modify: `coordination_sandbox/brain/engineering_strategy.py`

- [ ] Add a regression scenario matching the reported failure: session unavailable, inspiration blobs unusable, agent must remain blocked from broad visual implementation.
- [ ] Synchronize sandbox strategy output with production strategy fields.
- [ ] Run:
  - `python -m pytest tests/test_implementation_readiness.py tests/test_engineering_strategy.py tests/test_coordination_integration.py tests/test_reference_binding.py -q`
  - `python -m pytest tests/test_mcp_envelope_contract.py tests/test_mcp_agent_ux.py -q`
  - `python -m coordination_sandbox.run --scenarios coordination_sandbox/scenarios/default.yaml`
- [ ] Inspect failures for contract regressions and correct them before completion.
- [ ] Bump all package versions consistently, build both distributions, check artifacts, and publish the next development build to PyPI.
- [ ] Stop the currently installed MCP process only when installation requires replacing the executable; install the published build with a clean force reinstall.
- [ ] After Cursor restarts, test installed `resources/list`, `resources/read`, `tools/list`, health/session strategy routing, evidence outcome normalization, and readiness fields.
