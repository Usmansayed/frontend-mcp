# Methodology Discovery and Implementation Readiness

## Goal

Make Frontend MCP influence engineering decisions before broad frontend implementation by combining:

1. focused methodology resources,
2. compact decision-oriented tool descriptions,
3. coordinator-selected resource and capability routing, and
4. a machine-readable implementation readiness gate.

No new intelligence family is introduced. Existing Coordination, Design, Component, Inspiration, Figma, Engineering Spec, and Browser capabilities are orchestrated more deliberately.

## Why the Hybrid Is Required

MCP resources are application-controlled. A server can expose excellent methodology, but cannot assume every host will automatically read it. Tool descriptions are model-visible and improve discovery, but descriptions alone cannot distinguish a failed call from usable evidence. Rules help cooperative hosts, but cannot enforce runtime state.

The four layers have separate responsibilities:

- **Resources teach:** task-specific workflow and decision criteria.
- **Tool descriptions trigger:** what the tool does, when to use it, what it returns, and what should follow.
- **Coordinator routes:** the smallest relevant resource and required capability for the current unresolved decision.
- **Readiness gate governs:** whether broad visual implementation is blocked, provisional, or ready based on actual evidence outcomes.

## Focused Resources

The server will expose these stable resources:

- `perception://getting-started`
- `perception://frontend-methodology`
- `perception://design-workflow`
- `perception://redesign-workflow`
- `perception://bugfix-workflow`
- `perception://engineering-strategy`
- `perception://decision-ledger`
- `perception://inspiration-guide`
- `perception://verification-guide`
- `perception://browser-lifecycle`

Existing specialist guides (`resolver-guide`, `seo-guide`, `resource-guide`, `figma-guide`) remain. `perception://agent-guide` becomes a concise compatibility index pointing to focused resources; it is no longer the methodology monolith agents must remember.

Every workflow resource uses the same compact structure:

1. **Use when**
2. **Decisions to resolve**
3. **Minimum evidence**
4. **Failure/fallback behavior**
5. **Implementation boundary**
6. **Done condition**

## Tool Description Contract

High-impact tools in Session, Coordinator, Design, Component, Inspiration, Figma, Resolver, and Verification groups use this semantic shape:

> **Does:** concrete operation. **Use when:** decision or precondition. **Returns:** decision-relevant evidence and quality state. **Next:** deterministic successor or stop condition.

Descriptions remain short. Examples are omitted unless an argument is otherwise ambiguous, matching the research finding that targeted descriptions can retain value without the execution-step overhead of fully augmented metadata.

Descriptions must not claim that invocation equals evidence. They explicitly distinguish:

- successful, usable evidence;
- provisional/degraded evidence;
- failed evidence;
- verification evidence.

## Coordinator Resource Routing

`EngineeringStrategy` gains:

- `recommended_resource`: the one best methodology resource for the current situation;
- `required_resources`: resources that must be read before the current structural decision can be treated as resolved;
- `implementation_gate`;
- `evidence_plan`.

Routing examples:

- greenfield/design-driven → `perception://design-workflow`
- redesign → `perception://redesign-workflow`
- bug/hotfix/surgical → `perception://bugfix-workflow`
- unresolved reference quality → `perception://inspiration-guide`
- post-draft drift/verification → `perception://verification-guide`
- browser ownership/restore issue → `perception://browser-lifecycle`

The coordinator surfaces these URIs in both `data.coordinator` and `agent_summary`. Because hosts vary in resource support, the response also includes a one-line fallback instruction containing the critical boundary.

## Evidence Ledger

The PSM evidence state records one latest outcome per capability:

- `status`: `succeeded | provisional | failed`
- `quality`: deterministic capability-specific measurements
- `artifact_refs`
- `failure_reason`
- `degraded_reasons`
- `updated_at`

Capability attempts remain useful for retry budgets but no longer resolve engineering posture. Examples:

- inspiration with fewer than three host-viewable images is provisional;
- inspiration with blob/image failures is provisional or failed;
- component selection resolves foundation only when a usable chosen component exists and blocking compatibility issues are empty;
- Figma resolves design source only when context is loaded;
- a reference Spec with low concrete coverage is bound as provisional, not implementation-ready;
- a missing reference cannot produce a passing revision gate.

## Implementation Gate

The gate states are:

- `blocked`: unresolved structural decisions or failed required evidence;
- `provisional`: minimum direction exists, but only scaffold/runtime setup and a bounded draft are safe;
- `ready`: required structural decisions have usable evidence; broad implementation may proceed;
- `maintenance`: narrow bug/hotfix work may proceed with observe/fix/verify.

The gate returns:

- `blocking_decisions`
- `evidence_failures`
- `allowed_actions`
- `prohibited_actions`
- `next_required_capability`
- `required_resource`
- `completion_criteria`

If the dev server is unavailable, structural work permits only runtime scaffolding and server startup. It does not permit broad visual implementation. If inspiration fails, the coordinator routes to a supported alternative such as Figma context when supplied, or browser observation followed by Design Snapshot measurement. It never silently converts weak priors into locked decisions.

## Data Flow

1. Health/session bootstrap classifies the task and recommends one workflow resource.
2. The host reads that resource where supported.
3. Each MCP result is normalized into the PSM evidence ledger.
4. Engineering Strategy recomputes unresolved decisions.
5. The readiness compiler computes the gate and ordered evidence plan.
6. Coordinator output promotes the gate/resource/required-next capability.
7. After implementation, Design Snapshot, SpecDiff, Design Review, and Verify close the loop.

## Compatibility

- Existing tool names and input schemas remain stable.
- Existing resources remain readable.
- Existing envelope fields remain unchanged; new fields are additive.
- Existing `AGENT_GUIDE.md` content is split, then retained as a generated/maintained index to avoid breaking clients.
- The coordinator stays advisory at the protocol level: it does not block file writes, but emits an unambiguous machine-readable prohibition that host rules can enforce.

## Testing

Tests cover:

- all focused resources list and read successfully;
- the agent guide links to focused resources and stays below a size budget;
- high-impact descriptions contain the four semantic elements and remain below a length budget;
- coordinator chooses the correct resource per situation;
- failed/provisional evidence does not resolve design or foundation posture;
- structural readiness stays blocked after failed session start and unusable inspiration;
- component/design intelligence success advances the gate;
- missing reference makes the revision gate fail closed;
- existing MCP envelope and resource contracts remain compatible.

## Out of Scope

- adding new design/component/browser tools;
- requiring all resources to be read for every task;
- putting complete workflows into every tool description;
- protocol-level interception of host file edits;
- replacing user rules for clients that do not consume coordinator guidance.
