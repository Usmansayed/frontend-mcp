# Agent Guide — Programming the Host Agent

**Audience:** Cursor, Claude Code, Codex, or any MCP-connected coding agent.

**Purpose:** This is not API documentation. It is a **behavior program** for how you work with the Frontend Perception MCP. Read it once at session start; follow it for every frontend task.

The MCP has **no LLM**. **You are the brain.** The MCP only navigates, observes, executes your scripts, and verifies outcomes. These playbooks tell you **what to do, in what order, and when to stop**.

---

## 0. Universal loop (every task)

```text
STRATEGIZE  →  OBSERVE  →  REASON  →  ACT  →  VERIFY  →  (repeat or STOP)
```

| Phase | Who | What |
|-------|-----|------|
| **STRATEGIZE** | You read MCP | `agent_summary.engineering_strategy` from `perception_health` / `perception_session_start` / observe responses — unresolved decisions, influence level, risks, stop conditions |
| **OBSERVE** | You call MCP | `perception_navigate_and_observe` or `perception_observe` — save `scan_id` |
| **REASON** | You (in IDE) | Read `agent_summary.blocking`, DOM, dev insights; edit code or plan script |
| **ACT** | You call MCP | `perception_execute_script` / `perception_execute_actions` — save `scan_id_before` |
| **VERIFY** | You call MCP | `perception_verify(criteria)` — never skip |
| **STOP** | You | Task done when verify passes; or stop and ask user (auth gate, ambiguous requirements) |

**Hard rules:**
1. Read `engineering_strategy` before planning implementation — especially `unresolved_decisions` and `influence_level`.
2. Never claim a UI change works without `perception_verify`.
3. Never loop login/MFA — if `perception_auth_gate` → `requires_human: true`, ask the user.
4. Always read `blocking` before `advisory` in dev insights.
5. On verify failure: re-observe with screenshot, then `perception_diff`.
6. After a draft UI: remeasure with `perception_build_design_snapshot` and honor `spec_revision_gate` — if `revision_required`, revise before claiming done.

**Closed loop (reference Spec → draft → SpecDiff gate):**

```text
Reference Spec bound
  (inspiration seed / Figma seed / build_design_snapshot bind_as_reference=true)
       ↓
Host implements from Spec decisions
       ↓
Remeasure: perception_build_design_snapshot (default / current)
       ↓
spec_revision_gate → revision_required?
       ↓ yes → revise drifts → remeasure
       ↓ no  → perception_verify → STOP
```

| Step | Tool | What to read |
|------|------|----------------|
| Bind reference | `perception_inspiration_collect` / `perception_build_design_snapshot({ bind_as_reference: true })` / Figma `bind_as_reference` | `engineering_spec`, `reference_bind` |
| Draft | Your code edits | Spec decisions by impact — not gallery tags |
| Gate | `perception_build_design_snapshot` (default) or `perception_design_review` | `agent_summary.spec_revision_gate` |
| Pass | `passed: true` | Then `perception_verify` |

Do not treat gallery URLs or English design-review prose as the engineering source of truth — the Spec and SpecDiff are.

**Influence levels** (`engineering_strategy.influence_level`):

| Level | Meaning |
|-------|---------|
| `structural` | Resolve layout, foundation, and hierarchy decisions before substantial coding |
| `balanced` | Gather missing evidence, then implement with verify |
| `minimal` | Hotfix / surgical — observe, fix, verify only |
| `maintenance` | Production posture — verify correctness; defer new design investment |

---

## 1. Session bootstrap

**When:** Start of any frontend work in a repo.

```text
1. perception_health({ url: base_url, intent?: task_description })
2. perception_session_start({ base_url, intent: '<engineering task>' })  → save session_id
   → Read agent_summary.engineering_strategy before planning
3. (optional) perception_detect_framework({ repo_root })  → stack hints
4. (optional) perception_resolve_route({ repo_root, path }) → file hints before opening pages
```

Read `perception://resolver-guide` before any `perception_resolve_*` tool.

**Stop when:** `session_id` obtained and health OK.

**Do not:** Start multiple sessions unless you ended the previous one. The MCP keeps **one** Chromium window per process — inspiration/design tools reuse it. You may close that window anytime; the next browser tool recreates it.

**Health response fields:** `package_version`, `server_version`, `browser_runtime_available`, `browser_manager` (alive/connected/idle/restarts), `recommended_next_tool`.

---

## 1b. Observe detail levels & scan reuse

| `detail` | Payload | When to use |
|----------|---------|-------------|
| `summary_only` (default) | `agent_summary`, images, no `observation` blob | First pass, layout/copy checks |
| `full` | Includes `observation` with console/network entries | Debugging errors, API failures, console lines |
| `metadata_only` | `agent_summary` only, no images | Cheapest status check |

**Scan reuse:** Save `scan_id` from every `navigate_and_observe` / `observe`. Reuse for:
- `perception_diff` (before/after)
- `perception_seo_audit_start` (development mode — instant audit)
- `perception_correlate_live` (with resolver resolution)
- Scan resources (`perception://scan/{scan_id}/…`)

**Serial execution:** Call browser tools **one at a time** per `session_id`. Parallel MCP batches can corrupt session state.

---

## 2. Playbook: Page inspection (new or changed UI)

**When:** User asks to build, review, or fix a page/component; after editing JSX/TSX/CSS.

```text
OBSERVE
  → perception_navigate_and_observe({ url: affected_route, include_screenshot: true })
  → Record scan_id_baseline

REASON
  → Check agent_summary.blocking (console errors, HTTP 4xx/5xx, uncaught exceptions)
  → If blocking non-empty: fix code first before visual polish
  → Read dom_text / a11y_tree for missing labels, wrong copy, layout clues
  → (optional) perception_resolve_component({ repo_root, name }) for the component you edited

ACT
  → Edit source files in repo (primary action for coding agents)
  → OR perception_execute_script to toggle UI state for inspection

VERIFY
  → perception_verify({
       url_contains: [expected_path],
       text_contains: [expected_visible_copy],
       text_absent: [error_strings_that_should_be_gone]
     })

RE-OBSERVE (if verify failed or after significant act)
  → perception_observe → perception_diff(scan_id_baseline, scan_id_new)

STOP
  → verify passed AND blocking issues empty (or explicitly accepted by user)
```

**Screenshot:** Always `include_screenshot: true` on first observe and on any verify failure.

---

## 3. Playbook: Debugging (something looks broken)

**When:** User reports error UI, blank page, wrong behavior, console errors.

```text
OBSERVE
  → perception_health
  → perception_navigate_and_observe({ url: broken_route })
  → Read dev_insights.summary.blocking_issues FIRST

REASON
  → Classify:
      A) Console/exception → fix JS/runtime in repo
      B) HTTP failure → fix API route, env, proxy
      C) Blank/degraded → check ready_state, degraded[] on response
      D) Wrong content → compare dom_text to expectation

ACT
  → Fix code; do not only patch via execute_script unless reproducing

VERIFY
  → perception_verify that blocking issues are gone
  → perception_diff(before, after) — confirm new_blocking_issues empty

RE-OBSERVE
  → After each fix, full observe on same route

STOP
  → blocking empty + verify passes + user-visible symptom gone
```

**Do not:** Guess the fix without observing. **Do not:** Mark done while `HTTP 4xx` or console errors remain.

---

## 4. Playbook: Forms (validation, submit, fields)

**When:** Any form, login (non-MFA), settings, checkout step with inputs.

```text
OBSERVE
  → perception_navigate_and_observe({ url: form_route })

PROBE (before filling)
  → perception_probe_form({ form: "validation" })
  → Learn rules: field → message
  → Re-navigate to form route if probe left the page in a filled/valid state

ACT — phase 1 (invalid)
  → perception_execute_actions([
       { type: "click_button", text: "Validate & submit" }
     ])
  OR execute_script to clear required fields and submit

VERIFY — invalid
  → perception_verify({ text_contains: [expected_error_from_probe] })

ACT — phase 2 (valid)
  → perception_execute_actions([
       { type: "set_input", label: "Email", value: "user@example.com" },
       { type: "set_input", label: "Phone", value: "1234567890" },
       { type: "set_input", label: "Age", value: "25" },
       { type: "click_button", text: "Validate & submit" }
     ])
  → For checkboxes / custom controls, use execute_script (e.g. toggle terms checkbox)

VERIFY — valid
  → perception_verify({
       text_contains: [success_message],
       text_absent: [validation_error_strings]
     })

RE-OBSERVE
  → If API errors in network_failures after submit, fix client/API code, re-run from OBSERVE

STOP
  → probe rules matched + invalid verify + valid verify all pass
```

**Inputs:** Prefer `set_input` with `label`. For custom React controlled inputs or checkboxes, use `execute_script` with `input` + `change` events.

**Stop (auth):** Login form that triggers `perception_auth_gate` → `requires_human` → ask user, do not brute-force.

---

## 5. Playbook: Navigation & routing

**When:** Links, redirects, protected routes, 404 vs guard.

```text
OBSERVE
  → perception_probe_guards({ routes: ["/dashboard", "/admin", ...] })  // once per session if unknown

OBSERVE target
  → perception_navigate_and_observe({ url: target_route })

REASON
  → If redirected to /login → guard hit, not necessarily a bug
  → perception_auth_gate — if requires_human, STOP

ACT
  → If authenticated flow needed:
       perception_state_restore({ state_id: "logged_in" })  // if previously saved
       OR guide user through login (human)
       perception_state_save({ state_id: "logged_in" }) after success

VERIFY
  → perception_verify({
       url_contains: [expected_route],
       url_not_contains: ["/login"]  // when auth should be satisfied
     })

STOP
  → correct URL + expected content for auth level
```

---

## 6. Playbook: Multi-step flows

**When:** Checkout, onboarding, wizard, any sequenced UX.

```text
DESCRIBE
  → perception_flow_describe({ flow_name: "validation-form" })
  → Get ordered checkpoints + success criteria each

FOR each checkpoint:
  OBSERVE  → navigate to checkpoint URL if specified
  REASON   → checkpoint instruction is for YOU, not the MCP
  ACT      → code edits and/or execute_script / execute_actions
  VERIFY   → perception_verify(checkpoint.success criteria)
  → if fail: do not advance; fix and retry this checkpoint only

STOP
  → all checkpoints verified
```

**Do not:** Skip checkpoints. **Do not:** Ask MCP to run the whole flow autonomously.

---

## 7. Playbook: Verification-only (regression check)

**When:** User asks "does it still work?" after unrelated changes.

```text
OBSERVE
  → perception_navigate_and_observe({ url })

VERIFY
  → perception_verify({ ... known good criteria ... })

STOP
  → pass or report reasons[] to user with screenshot
```

No code act unless verify fails.

---

## 8. Playbook: Responsive / viewport checks (basic)

**When:** Layout breakpoints, mobile nav, overflow.

```text
OBSERVE
  → perception_session_start with viewport { width: 375, height: 812 }
  → perception_navigate_and_observe({ include_screenshot: true })

REASON
  → Inspect screenshot resource + dom_text for horizontal overflow clues

ACT
  → Fix CSS in repo

VERIFY
  → Re-observe at same viewport; perception_verify text visible / not absent

REPEAT
  → perception_session_end → new session with desktop viewport if needed

STOP
  → criteria met at target viewport(s)
```

---

## 9. Playbook: Feature flags & edge UI

**When:** Beta toggles, iframe embeds, virtual lists, file upload, rich editors.

```text
OBSERVE
  → perception_navigate_and_observe({ url: "/edge-lab" or feature route })

REASON
  → Match scenario to engine probe pattern:
      feature flag  → URL param or localStorage per probe docs
      iframe        → may need execute_script in parent to reach frame
      virtual list  → scroll via execute_script before verify item visible
      file upload   → perception_execute_actions cannot upload files; use dedicated probe pattern when exposed

ACT + VERIFY
  → Per feature: act, then verify specific text/selector/state

STOP
  → feature-specific criteria met
```

Use `perception_flow_describe` or codebase search when unsure which probe applies.

---

## 10. Playbook: Correlating code ↔ live UI

**When:** You need the file that drives a route or component, or to confirm your edit matches the live page.

**Read first:** `perception://resolver-guide`

```text
OBSERVE
  → perception_navigate_and_observe({ url })  → save scan_id

RESOLVE (pick one)
  → perception_resolve_route({ repo_root, path: "/forms/validation" })
  → perception_resolve_component({ repo_root, name: "ValidationForm" })
  → perception_resolve_design_token({ repo_root, token: "accent" })

REASON
  → Read data.resolution.status and matches[].file_path
  → If ambiguous: perception_validate_route_claim or perception_validate_component_claim
  → If not_found: use IDE search (follow fallback.host_search)

ACT
  → Edit matched file in repo

VERIFY
  → perception_observe → perception_verify → perception_diff

CORRELATE (optional)
  → perception_correlate_live({ scan_id, resolution: data.resolution })

STOP
  → verify passes + resolution status resolved (or claim validated)
```

**Do not** use `perception_code_context` for routes — it is deprecated (slow CRG graph).

---

## 11. When to re-observe vs diff vs verify

| Situation | Tool |
|-----------|------|
| First look at page | `navigate_and_observe` |
| After code edit, same URL | `observe` or `navigate_and_observe` |
| After execute_script | `verify` then `diff(before, after)` |
| "What changed?" | `perception_diff` |
| "Is requirement met?" | `perception_verify` |
| Verify failed | `perception_verify` (auto-screenshot) + `perception_diff` |

---

## 12. Visual evidence (v0.5)

Observe, verify-fail, and diff tools **inline PNG images** in the MCP tool response (annotated viewport by default).

| Field | Meaning |
|-------|---------|
| `data.visual.screenshot_uri` | Raw viewport PNG resource |
| `data.visual.annotated_screenshot_uri` | Boxes for interactive + blocking issues |
| `data.visual.crop_screenshot_uri` | Element crop when `screenshot_mode: element` |
| `data.visual.visual_insights` | Deterministic layout signals (overflow, overlaps, zero-size clickables) |
| `screenshot_mode` | `viewport` \| `full` \| `element` (+ `screenshot_selector` for element) |

**Rules:**
- Images are attached to the tool result — you do not need a separate fetch for normal UI work.
- Use `annotate_screenshot: true` (default) on first observe and all verify failures.
- Use `screenshot_mode: element` with a CSS selector for focused form/checkout debugging.
- `perception_diff` returns side-by-side + heatmap images when both scans have screenshots.

---

## 12.1 Observe detail levels (M4)

Use `detail` on observe tools when payload size matters:

- `detail: "summary_only"` (default): compact `agent_summary` + visual block + inline images (no DOM text)
- `detail: "full"`: full observation payload (DOM/a11y/dev insights) + visual block + inline images

Guideline:
- Start with `full` on first look and on failures.
- Never use `summary_only` on first observe or after verify failure.
- `summary_only` is only for tight loops when you already saw the page visually.

---

## 13. When to STOP and ask the human

| Signal | Action |
|--------|--------|
| `perception_auth_gate` → `requires_human: true` | Stop; ask user to log in or complete MFA/CAPTCHA |
| `perception_health` → unreachable | Stop; ask user to start dev server |
| `degraded` contains critical signals | Tell user observation is partial |
| Requirements ambiguous | Ask user for expected text/URL/selectors |
| Verify fails 3+ times after fixes | Stop; report `reasons[]`, screenshot, diff summary |

---

## 14. Playbook: Design inspiration (public galleries)

**When:** User asks for landing page / dashboard / UI inspiration from Dribbble, Behance, gallery sites.

**Read first:** MCP resource `perception://inspiration-guide` — per-site URLs, selectors, preview rules, anti-bot.

**Mode: image-first.** Prefer CDN/preview image URLs → ephemeral compressed blobs for host vision. Do **not** open gallery sites in the shared browser unless image retrieval fails or interaction/animation inspection is required.

```text
1. Read engineering_strategy.recommended_evidence.suggested_queries (when present)
2. perception_inspiration_collect({ query })   → 3–5 image refs + blobs + seed Spec
     (stops early when enough high-quality previews exist; reuses progressive query ladder)
3. Feed inspiration_blob / preview_url to vision — not browser screenshots
4. Optionally measure a live reference page only if needed:
   perception_navigate_and_observe → perception_build_design_snapshot({ bind_as_reference: true })
5. Implement from Spec decisions; then remeasure:
   perception_build_design_snapshot → read spec_revision_gate
6. perception_inspiration_session_end({ session_id })  → delete blobs when done
```

| Field | Use |
|-------|-----|
| `preview_url` / `agent_view_url` | Prefer CDN/og:image for host vision |
| `inspiration_blob` | Ephemeral medium JPEG (~512–1024px, ~24h TTL) |
| `blob_session_id` | Reuse within session; pass to session_end when finished |
| `engineering_spec` | Seed Spec (soft priors) — bind as reference; harden via Snapshot |
| `spec_revision_gate` | Post-draft SpecDiff vs bound reference |

**Provider notes (summary):**
- **Behance / One Page Love** — HTTP-first (preferred for collect)
- **Dribbble** — HTTP WAF 202; browser only when needed for discovery (+ optional `DRIBBBLE_SESSION_COOKIE`)
- **Awwwards / SiteInspire / Godly** — HTTP first; browser extract as fallback
- **Land-book** — browser required for discovery; skip generic og-image blobs

**Do not:** Scrape galleries ad-hoc. Dump dozens of images. Leave the shared browser on external gallery URLs. Permanent download is optional (`download_images`); blobs are ephemeral.

**Stop when:** 3–5 high-quality references exist, or user confirms stop. Do not re-search if blobs already cover the decision. Always end blob session when design work completes.

---

## 15. Playbook: Creative assets (Resource Intelligence)

**When:** User needs icons, avatars, illustrations, fonts, or stock assets for a commercial project.

**Read first:** MCP resource `perception://resource-guide` — license rules, provider notes, blob fields.

```text
1. perception_resource_search({ query, icon_family: "lucide" })  → family URLs + suggested_import
2. perception_resource_preview only when family miss + reference image (blobs skipped for in-family icons)
3. Use access_url / npm import — not blobs — for matched family icons
4. perception_resource_session_end({ session_id })
```

| Field | Use |
|-------|-----|
| `access_url` | SVG/API URL for integration |
| `suggested_import` | npm import line (e.g. lucide-react) |
| `icon_family` | Active style set (lucide, heroicons, tabler-icons, ΓÇª) |
| `resource_blob` | Only on family miss + `reference_preview_url`, or avatars/photos |

**Provider notes (MVP):**
- **Iconify / Lucide** — commercial icons; NC collections skipped per asset
- **DiceBear** — preview via public API; self-host for production commercial
- **unDraw / Storyset** — in catalog; blobs skipped when automation prohibited

**Do not:** Scrape provider sites ad-hoc — use MCP tools. Respect `license_warnings`.

**Stop when:** Assets selected and integrated, or user confirms stop. Always end blob session when asset work completes.

---

## 16. Playbook: SEO orchestration (SEO Intelligence)

**When:** User asks about search rankings, indexing, CTR, Core Web Vitals, technical SEO, or site-wide SEO audit.

**Read first:** MCP resource `perception://seo-guide` — Development vs Professional modes, verify loop, boundaries.

```text
1. perception_seo_status()                         → phase + provider catalog
2. perception_observe / navigate_and_observe       → scan_id (required for development)
3. perception_seo_audit_start({ website_url, scan_id, repo_root? })
   Development (default): inline result — data.status=completed, data.instant=true (2–5s; no poll)
   Professional: data.audit_job_id → perception_seo_audit_poll until terminal
4. perception_seo_connect(...)                     → OAuth only when user asks (professional)
5. Read evidence + recommendations — every claim has evidence_ids
6. Fix code / config from evidence
7. perception_observe → perception_verify on affected pages
8. perception_seo_verify or perception_seo_audit_start again to measure gains
```

**Async rule:** Never use blocking `perception_seo_audit` in agent loops.
Development: `audit_start` only (no poll). Professional: `audit_start` + poll.
Cancel long jobs with `perception_seo_audit_cancel({ audit_job_id })`.

| Provider | Role |
|----------|------|
| Search Console | Queries, index, crawl issues, CWV in GSC |
| GA4 | Traffic, landing pages, conversions |
| LibreCrawl | Technical crawl (local — not our crawler) |
| Lighthouse | Lab CWV + SEO score |
| Browser Intelligence | Rendering evidence via `scan_id` |

**Do not:** Build keyword/backlink databases. Scrape SERPs ad-hoc. Claim SEO fixes without verify.

**Stop when:** Recommendations addressed and verified, or user confirms stop.

---

## 17. Playbook: Figma design context (Figma Intelligence)

**When:** User asks to analyze their Figma file, implement a frame, extract tokens, or compare design with code.

**Read first:** MCP resource `perception://figma-guide`.

```text
1. perception_figma_status()                         → connection + session
2. perception_figma_connect({ pat })                 → once per user (PAT stored locally)
3. perception_figma_context({ file_url, refresh? })  → normalized design context
4. Pass context to Design Sense / Consistency / Component Intelligence as needed
5. perception_observe → perception_verify for code implementation
```

| Layer | Role |
|-------|------|
| Connection Manager | PAT connect, validate, reuse |
| Session Manager | Active file, page, frame, selection |
| Console MCP Adapter | southleft/figma-console-mcp (hidden) |
| Context Normalizer | `FigmaDesignContext` for all modules |

**Do not:** Reimplement Figma APIs. Run public inspiration here — use Inspiration Intelligence. Critique designs here — use Design Sense.

**Stop when:** Context retrieved and downstream task complete, or user confirms stop.

---

## 18. Tool quick reference (secondary to playbooks)

Use tools **only as steps inside playbooks above**.

| Tool | Use when |
|------|----------|
| `perception_session_start/end` | Bootstrap / teardown |
| `perception_health` | Dev server up? |
| `perception_navigate_and_observe` | Default "open and see" |
| `perception_observe` | Same URL, fresh snapshot |
| `perception_execute_script` | Custom JS interaction |
| `perception_execute_actions` | Click/fill by label/text |
| `perception_verify` | After every act |
| `perception_diff` | Compare scan_ids |
| `perception_probe_form` | Before form work |
| `perception_auth_gate` | Login/MFA detection |
| `perception_state_save/restore` | Multi-step auth |
| `perception_flow_describe` | Multi-step flows |
| `perception_code_context` | **Deprecated** — use `perception_resolve_*` |
| `perception_resolve_route` | Route → component file |
| `perception_validate_route_claim` | Validate route/file claim |
| `perception_resolve_component` | Component name → file |
| `perception_validate_component_claim` | Validate component claim |
| `perception_resolve_design_token` | Design token lookup |
| `perception_resolve_state_owner` | State key → store file |
| `perception_resolve_api_endpoint` | API path → handler file |
| `perception_resolve_layout` | Layout from design snapshot |
| `perception_correlate_live` | DOM cross-check with scan_id |
| `perception_inspiration_discover` | Ranked inspiration candidates (fast) |
| `perception_inspiration_collect` | URLs + ephemeral vision blobs |
| `perception_inspiration_session_end` | Delete ephemeral inspiration blobs |
| `perception_resource_search` | Ranked creative assets (fast) |
| `perception_resource_preview` | URLs + ephemeral resource vision blobs |
| `perception_resource_session_end` | Delete ephemeral resource blobs |
| `perception_seo_status` | SEO module phase + provider catalog |
| `perception_seo_audit_start` | Dev: inline audit from scan_id; Pro: enqueue + poll |
| `perception_seo_audit_poll` | Poll audit job status + partial evidence |
| `perception_seo_audit_cancel` | Cancel background audit |
| `perception_seo_audit` | Legacy sync audit — prefer start + poll |
| `perception_seo_verify` | Re-audit vs graph baseline |
| `perception_figma_status` | Figma connection + session health |
| `perception_figma_connect` | Connect Figma PAT (once) |
| `perception_figma_context` | Normalized file, tokens, components, selection |

---

## 19. Success checklist (before telling user "done")

- [ ] `perception_verify` passed for stated criteria
- [ ] `agent_summary.blocking` is empty (or user accepted warnings)
- [ ] `scan_id` / screenshot saved if user may need evidence
- [ ] Auth gates respected (no credential looping)
- [ ] You edited repo code when fix was structural (not only runtime script hacks)

---

**Remember:** The MCP does not tell you what to do next. **These playbooks do.** Follow observe → reason → act → verify until the checklist passes.
