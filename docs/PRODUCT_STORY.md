# Frontend Perception MCP — Product Story & Landing Page Source

Use this document when writing the marketing site, README hero, launch posts, and demo scripts. It captures **what we built**, **why it matters**, and the **small details** that differentiate us from “another browser MCP.”

---

## One-liner options

Pick one for the hero; the rest work as subheads.

1. **The frontend runtime for AI coding agents** — observe, verify, and ship UI with confidence.
2. **Your agent writes code. We prove it works in the browser.**
3. **Eight intelligence modules. One MCP. Zero Chrome extensions.**
4. **Deterministic browser perception for Cursor, Claude, and Codex** — not a Playwright wrapper, not an autonomous agent.
5. **From component search to Lighthouse audits** — the full frontend loop in one protocol.

**Short descriptor (meta / footer):**  
*Frontend Perception MCP connects AI coding agents to a real Chromium session via CDP — structured observation, verification, debugging, framework docs, and component discovery. No LLM inside the server. The agent stays the brain.*

---

## The problem we solve

AI coding agents are good at generating React, Tailwind, and shadcn code. They are bad at knowing whether the UI actually works:

- Console errors hidden until deploy
- Forms that look right but fail validation
- Auth redirects and route guards that break silently
- “Done” claims without opening the browser
- Component libraries scattered across 200+ registries with different naming (`navbar` vs `navigation-menu` vs `app-bar`)
- Framework docs that are outdated or hallucinated

**Frontend Perception MCP** closes the loop: the agent edits code → the MCP observes the live app → structured facts come back → the agent verifies criteria → for visual drafts it also clears section checklist + Ship Council → only then is the task done.

---

## Core philosophy (say this clearly on the landing page)

### The agent is the brain. The MCP is the runtime.

| | Host agent (Cursor / Claude / Codex) | Frontend Perception MCP |
|---|--------------------------------------|-------------------------|
| **Role** | Plans, reasons, edits source files | Navigates, observes, executes scripts, returns facts |
| **LLM** | Yes — that’s the product you’re using | **No** — deterministic tools only |
| **Output** | Code patches, explanations | `agent_summary`, screenshots, scan IDs, pass/fail verify |
| **Playbooks** | Reads `AGENT_GUIDE.md` at session start | Exposes `perception://agent-guide` as MCP resource |

This split is intentional. We don’t compete with your model — we give it **eyes, hands, and a quality gate**.

### Observe → Reason → Act → Verify → Stop

Every frontend task follows the same loop. The landing page should show this as the **product motion**, not an implementation detail:

```text
OBSERVE   perception_navigate_and_observe / perception_observe
REASON    agent reads blocking issues, DOM, dev insights; edits repo
ACT       code changes + optional perception_execute_script
VERIFY    perception_verify — require data.verified=true (ok alone is not a pass)
STOP      Done ladder: verified + section checklist (when required) + Ship Council (when required), or ask human (auth/MFA)
```

**Hard rule to highlight:** *Never claim UI work is done on transport `ok` alone — require `data.verified=true`, then finish the Done ladder for visual drafts.*

---

## What makes us different (small details that matter)

Use these as feature bullets or “why us” cards.

### No Chrome extension

Unlike BrowserTools and similar stacks: **pip install / uvx only** → MCP → Browser Use → CDP → Chromium. No extension, no separate WebSocket server, no maintainer-abandoned dependency chain.

### Blocking-first responses

`agent_summary` separates **blocking** (console errors, HTTP 4xx/5xx, uncaught exceptions) from **advisory** (warnings, perf hints). Agents are trained to fix blocking before polish.

### Inline screenshots in MCP responses

Observe, verify-fail, and diff return **inline images** the model can actually see — not just file paths. Annotated screenshots, element crops, viewport modes, visual heatmaps.

### Verify is a first-class tool

`perception_verify` with `url_contains`, `text_contains`, `js_assertions`. On failure: auto re-observe, attach failure screenshot, return structured criterion breakdown. Then `perception_diff` for before/after regression.

### Auth that respects humans

`perception_auth_gate` returns `requires_human: true` for login/MFA/CAPTCHA — the agent stops and asks you instead of looping credentials.

### Form intelligence before blind filling

`perception_probe_form` discovers fields, validation rules, and submit behavior **before** the agent guesses input values. Invalid submit first, then valid fill — documented in playbooks.

### Route guard probing

`perception_probe_guards` for protected routes — know if you’re blocked by auth before wasting steps.

### Multi-step flows as checkpoints

`perception_flow_describe` returns a flow graph; the **agent** verifies each checkpoint — the MCP doesn’t run autonomous multi-page journeys.

### Session state you can save and restore

`perception_state_save` / `perception_state_restore` — cookies, localStorage, session snapshot for auth-heavy workflows.

### Code ↔ UI bridge

`perception_code_context` via Code Review Graph (CRG): semantic search over components, routes, files — connect what you see in the DOM to what you should edit in the repo.

### Full quality stack in one session

- **Console** — CDP ring buffer, level filters, structured in observe
- **Network** — request/response capture, slow/duplicate detection, API grouping, GraphQL operation names, **HAR 1.2 export** per scan
- **Lighthouse** — accessibility, performance, SEO, best practices
- **Diagnosis** — `perception_full_diagnosis` merges observe + console + network + audits into `diagnosis.json` / `diagnosis.md`

### Framework docs that match your project

`perception_detect_framework` reads your `package.json`, lockfiles, and config — then `perception_framework_docs` fetches version-aware documentation via **Grounded Docs** (on-demand scrape/search, cached, cross-platform). No hallucinated API signatures.

### Component search across the shadcn universe

`perception_search_components` doesn’t maintain a giant local component DB. It orchestrates **234+ registries**:

- Deterministic **search planner** — primary intent, synonyms, style keywords, page context
- **Multi-pass search** — primary → expanded terminology → broader concepts
- **Provider-aware vocabulary** — `@shadcn` gets `navigation-menu`, Aceternity gets `navbar`, Tailark gets `header`
- **Parallel catalog fetch** with merge/dedupe and full **search session** metadata for debugging
- Optional `perception_plan_component_search` + `search_plan` override for agent-refined strategies

### Eight modules, one platform

Not a monolith script — **eight intelligence modules** behind a thin MCP layer. Extend Framework Intelligence without touching Visual Browser Intelligence. Provider pattern for external services.

### Design Sense vs Consistency (future-facing, honest)

- **Design Sense** — “Is this good UX?” qualitative heuristics (overflow, overlaps, zero-size clickables today; layout reasoning planned)
- **Consistency** — “Does this match the design system?” token math, spacing scales, drift detection (scaffold shipped, validators planned)

We say what’s shipped vs planned. Credibility beats hype.

---

## The eight intelligence modules (landing page feature grid)

### 1. Visual & Browser Intelligence
*See the app like a user does.*

- Session lifecycle (`perception_session_start` / `end`)
- Navigate + observe in one call
- DOM text, accessibility tree, ready state
- Execute JavaScript and structured actions
- Visual diff with heatmaps
- MCP resources: screenshots, reports, HAR per `scan_id`

### 2. Frontend Quality Intelligence
*Production signals, not vibes.*

- Live console capture from session start
- Network waterfall with body size caps
- Lighthouse audits (four categories)
- Debug mode vs full audit mode vs full diagnosis
- Regression diff between scans

### 3. Design Workflow Intelligence
*Flows, auth, and state — without autonomous chaos.*

- Flow describe for multi-step UIs
- Auth gate for human-in-the-loop login
- Form and route-guard probes
- State save/restore for repeatable sessions

### 4. Codebase Intelligence
*Connect the pixel to the file.*

- Code Review Graph integration
- Semantic search: components, routes, files
- Impact radius and navigation hints
- CRG optional — browser works without it

### 5. Framework Intelligence
*Docs that match your stack.*

- Detect React, Next, Vite, Vue, build tools, package manager
- Grounded Docs adapter — search + scrape on demand
- Normalized knowledge responses with cache
- Node 22+ via `npx`, cross-platform paths

### 6. Component Intelligence
*Find the right component, not just any component.*

- Natural-language query parser (styles, theme, animations, SaaS context)
- Multi-pass search across shadcn ecosystem registries
- Normalized install commands (`npx shadcn@latest add @registry/name`)
- Probes: forms, rich editors, iframes, virtual scroll, file upload

### 7. Design Sense Intelligence
*UX reasoning for the agent.*

- Visual layout heuristics in observe payload
- Quality hints in diagnosis reports
- Planned: typography, color, hierarchy reasoning

### 8. Consistency Intelligence
*Design-system discipline (roadmap).*

- Scaffold in place
- Planned: token extraction, spacing/type/color validators, consistency audit MCP tools

---

## Installation (keep it stupid simple on the landing page)

```bash
# Recommended
uvx --from frontend-mcp frontend-mcp-install

# With Chromium
uvx --from frontend-mcp frontend-mcp-install --with-browser

# Run server
uvx --from frontend-mcp frontend-mcp
```

**Cursor config** — one JSON block, no API keys for core browser tools.

**Packages:** `frontend-perception-engine` and `frontend-mcp` are the same server (alias on PyPI).

---

## Suggested landing page sections

### Hero
**Headline:** The frontend runtime for AI coding agents  
**Subhead:** Observe live UI, catch blocking errors, verify changes, search 234+ component registries, and fetch real framework docs — all through one MCP. No Chrome extension. No LLM in the server.  
**CTA:** Install in Cursor · View tools · Read the agent guide

### How it works (3 steps)
1. **Connect** — Add Frontend Perception to Cursor, Claude Desktop, or any MCP host.  
2. **Loop** — Your agent observes the running app, edits code, and calls verify.  
3. **Ship** — Blocking issues surface first; verify passes before “done.”

### For agents, not humans
The MCP returns **facts**: `agent_summary`, `scan_id`, inline screenshots, structured diagnosis. Playbooks in `AGENT_GUIDE.md` tell the agent what order to call tools. You don’t click buttons in our UI — your agent does the work with better evidence.

### vs BrowserTools / Playwright MCP
| | BrowserTools | Playwright MCP | Frontend Perception |
|---|--------------|----------------|---------------------|
| Setup | Extension + server | Test runner | pip / uvx only |
| Verify gate | ❌ | partial | ✅ first-class |
| Act on page | read-only | ✅ | ✅ + playbooks |
| Code ↔ UI | ❌ | ❌ | ✅ CRG |
| Component search | ❌ | ❌ | ✅ multi-registry |
| Framework docs | ❌ | ❌ | ✅ Grounded Docs |
| LLM in server | ❌ | ❌ | ❌ (by design) |

### Trust bar / credibility
- MCP contract v1.0 with envelope responses  
- Contract test suite (`run_mcp_contract_tests.py`)  
- Eight-module architecture with ADRs  
- Active development; BrowserTools reference marked inactive by maintainers  
- Open docs: architecture, roadmap, tool reference, feature subsystems  

### Social proof placeholders (fill when ready)
- [ ] Demo video: observe → fix console error → verify pass  
- [ ] Demo video: “modern glass dashboard navbar” component search  
- [ ] GitHub stars / PyPI downloads  
- [ ] Testimonial from Cursor power user  

---

## Copy-ready feature bullets (paste into cards)

- **30+ MCP tools** across browser, quality, workflow, codebase, framework, and components  
- **Inline screenshots** on observe, verify failure, and visual diff  
- **HAR export** per scan for network debugging  
- **Lighthouse** accessibility, performance, SEO, best practices  
- **Full diagnosis** — one call merges console, network, audits, and observe  
- **Form probe** before fill — validation-aware agent workflows  
- **Auth gate** — stops for MFA instead of infinite login loops  
- **State save/restore** — reproducible authenticated sessions  
- **Visual regression** — text diff + heatmap between scan IDs  
- **Framework detection** — React, Next, Vite, Vue, and more from your repo  
- **Grounded Docs** — real documentation scraped for your versions  
- **Component search** — 234+ shadcn-compatible registries, multi-pass, provider-aware  
- **Search sessions** — every query logged with latency, passes, and matched terms  
- **No API keys** for core browser perception  
- **Deterministic** — same tool, same facts; the model decides what to do  

---

## Taglines for specific audiences

**For Cursor users:**  
*Give Cursor eyes on your localhost — and a verify step it can’t skip.*

**For agency / consultancies:**  
*One MCP for client UI QA: console, network, Lighthouse, screenshots, regression.*

**For design-system teams (future):**  
*Consistency Intelligence — catch token drift before it ships.*

**For component library authors:**  
*Your registry is searchable the moment it’s on the shadcn index — we orchestrate, we don’t fork.*

---

## Honest roadmap callouts (footer / “building in public”)

**Shipped:** Visual delivery, console, network, audits, diagnosis, framework intelligence, component search Phase 1, eight-module layout, Grounded Docs adapter.

**In progress / planned:** Consistency validators, component ranking/install, browser attach mode, multi-viewport observe packs, Next.js-specific audit hints.

**Explicitly not doing:** Chrome extension dependency, LLM inside MCP for “suggested fixes,” replacing your coding agent with autonomous Browser Use as the primary path.

---

## MCP resources (for technical landing FAQ)

| Resource | Purpose |
|----------|---------|
| `perception://agent-guide` | Full agent playbooks |
| `perception://eval/validation-form` | Smoke-test eval scenario |
| `perception://scan/{id}/screenshot.png` | Raw screenshot |
| `perception://scan/{id}/screenshot-annotated.png` | Annotated screenshot |
| `perception://scan/{id}/network.har` | HAR 1.2 trace |
| `perception://scan/{id}/diagnosis.json` | Structured perception report |

---

## Voice & tone

- **Precise** — say “deterministic MCP runtime,” not “AI-powered browser magic”  
- **Agent-native** — “your agent calls `perception_verify`,” not “you click verify”  
- **Honest** — shipped vs scaffold vs planned  
- **Confident** — we built eight modules because frontend is not one problem  
- **Short on hype** — let the tool count, playbooks, and verify loop speak  

---

## Related internal docs

- [TECHNICAL_NARRATIVE.md](./TECHNICAL_NARRATIVE.md) — **how we build** (pipelines, universal search → adapt → install, provider pattern)
- [architecture.md](./architecture.md) — system design  
- [INTELLIGENCE_MODULES.md](./INTELLIGENCE_MODULES.md) — module map  
- [tool_reference.md](./tool_reference.md) — all tools and params  
- [roadmap.md](./roadmap.md) — version history  
- [AGENT_GUIDE.md](../AGENT_GUIDE.md) — agent playbooks  
- [features/component_intelligence.md](./features/component_intelligence.md) — search engine detail  

---

*Last updated: product narrative for landing page / launch — align with roadmap when shipping new modules.*
