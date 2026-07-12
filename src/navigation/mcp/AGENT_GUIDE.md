# Agent Guide ΓÇö Programming the Host Agent

**Audience:** Cursor, Claude Code, Codex, or any MCP-connected coding agent.

**Purpose:** This is not API documentation. It is a **behavior program** for how you work with the Frontend Perception MCP. Read it once at session start; follow it for every frontend task.

The MCP has **no LLM**. **You are the brain.** The MCP only navigates, observes, executes your scripts, and verifies outcomes. These playbooks tell you **what to do, in what order, and when to stop**.

---

## 0. Universal loop (every task)

```text
OBSERVE  ΓåÆ  REASON  ΓåÆ  ACT  ΓåÆ  VERIFY  ΓåÆ  (repeat or STOP)
```

| Phase | Who | What |
|-------|-----|------|
| **OBSERVE** | You call MCP | `perception_navigate_and_observe` or `perception_observe` ΓÇö save `scan_id` |
| **REASON** | You (in IDE) | Read `agent_summary.blocking`, DOM, dev insights; edit code or plan script |
| **ACT** | You call MCP | `perception_execute_script` / `perception_execute_actions` ΓÇö save `scan_id_before` |
| **VERIFY** | You call MCP | `perception_verify(criteria)` ΓÇö never skip |
| **STOP** | You | Task done when verify passes; or stop and ask user (auth gate, ambiguous requirements) |

**Hard rules:**
1. Never claim a UI change works without `perception_verify`.
2. Never loop login/MFA ΓÇö if `perception_auth_gate` ΓåÆ `requires_human: true`, ask the user.
3. Always read `blocking` before `advisory` in dev insights.
4. On verify failure: re-observe with screenshot, then `perception_diff`.

---

## 1. Session bootstrap

**When:** Start of any frontend work in a repo.

```text
1. perception_health({ url: base_url })           ΓåÆ if unreachable, ask user to start dev server
2. perception_session_start({ base_url })         ΓåÆ save session_id
3. (optional) perception_code_context(...)        ΓåÆ if you need file/route hints before opening pages
```

**Stop when:** `session_id` obtained and health OK.

**Do not:** Start multiple sessions unless you ended the previous one.

---

## 2. Playbook: Page inspection (new or changed UI)

**When:** User asks to build, review, or fix a page/component; after editing JSX/TSX/CSS.

```text
OBSERVE
  ΓåÆ perception_navigate_and_observe({ url: affected_route, include_screenshot: true })
  ΓåÆ Record scan_id_baseline

REASON
  ΓåÆ Check agent_summary.blocking (console errors, HTTP 4xx/5xx, uncaught exceptions)
  ΓåÆ If blocking non-empty: fix code first before visual polish
  ΓåÆ Read dom_text / a11y_tree for missing labels, wrong copy, layout clues
  ΓåÆ (optional) perception_code_context for component file you edited

ACT
  ΓåÆ Edit source files in repo (primary action for coding agents)
  ΓåÆ OR perception_execute_script to toggle UI state for inspection

VERIFY
  ΓåÆ perception_verify({
       url_contains: [expected_path],
       text_contains: [expected_visible_copy],
       text_absent: [error_strings_that_should_be_gone]
     })

RE-OBSERVE (if verify failed or after significant act)
  ΓåÆ perception_observe ΓåÆ perception_diff(scan_id_baseline, scan_id_new)

STOP
  ΓåÆ verify passed AND blocking issues empty (or explicitly accepted by user)
```

**Screenshot:** Always `include_screenshot: true` on first observe and on any verify failure.

---

## 3. Playbook: Debugging (something looks broken)

**When:** User reports error UI, blank page, wrong behavior, console errors.

```text
OBSERVE
  ΓåÆ perception_health
  ΓåÆ perception_navigate_and_observe({ url: broken_route })
  ΓåÆ Read dev_insights.summary.blocking_issues FIRST

REASON
  ΓåÆ Classify:
      A) Console/exception ΓåÆ fix JS/runtime in repo
      B) HTTP failure ΓåÆ fix API route, env, proxy
      C) Blank/degraded ΓåÆ check ready_state, degraded[] on response
      D) Wrong content ΓåÆ compare dom_text to expectation

ACT
  ΓåÆ Fix code; do not only patch via execute_script unless reproducing

VERIFY
  ΓåÆ perception_verify that blocking issues are gone
  ΓåÆ perception_diff(before, after) ΓÇö confirm new_blocking_issues empty

RE-OBSERVE
  ΓåÆ After each fix, full observe on same route

STOP
  ΓåÆ blocking empty + verify passes + user-visible symptom gone
```

**Do not:** Guess the fix without observing. **Do not:** Mark done while `HTTP 4xx` or console errors remain.

---

## 4. Playbook: Forms (validation, submit, fields)

**When:** Any form, login (non-MFA), settings, checkout step with inputs.

```text
OBSERVE
  ΓåÆ perception_navigate_and_observe({ url: form_route })

PROBE (before filling)
  ΓåÆ perception_probe_form({ form: "validation" })
  ΓåÆ Learn rules: field ΓåÆ message
  ΓåÆ Re-navigate to form route if probe left the page in a filled/valid state

ACT ΓÇö phase 1 (invalid)
  ΓåÆ perception_execute_actions([
       { type: "click_button", text: "Validate & submit" }
     ])
  OR execute_script to clear required fields and submit

VERIFY ΓÇö invalid
  ΓåÆ perception_verify({ text_contains: [expected_error_from_probe] })

ACT ΓÇö phase 2 (valid)
  ΓåÆ perception_execute_actions([
       { type: "set_input", label: "Email", value: "user@example.com" },
       { type: "set_input", label: "Phone", value: "1234567890" },
       { type: "set_input", label: "Age", value: "25" },
       { type: "click_button", text: "Validate & submit" }
     ])
  ΓåÆ For checkboxes / custom controls, use execute_script (e.g. toggle terms checkbox)

VERIFY ΓÇö valid
  ΓåÆ perception_verify({
       text_contains: [success_message],
       text_absent: [validation_error_strings]
     })

RE-OBSERVE
  ΓåÆ If API errors in network_failures after submit, fix client/API code, re-run from OBSERVE

STOP
  ΓåÆ probe rules matched + invalid verify + valid verify all pass
```

**Inputs:** Prefer `set_input` with `label`. For custom React controlled inputs or checkboxes, use `execute_script` with `input` + `change` events.

**Stop (auth):** Login form that triggers `perception_auth_gate` ΓåÆ `requires_human` ΓåÆ ask user, do not brute-force.

---

## 5. Playbook: Navigation & routing

**When:** Links, redirects, protected routes, 404 vs guard.

```text
OBSERVE
  ΓåÆ perception_probe_guards({ routes: ["/dashboard", "/admin", ...] })  // once per session if unknown

OBSERVE target
  ΓåÆ perception_navigate_and_observe({ url: target_route })

REASON
  ΓåÆ If redirected to /login ΓåÆ guard hit, not necessarily a bug
  ΓåÆ perception_auth_gate ΓÇö if requires_human, STOP

ACT
  ΓåÆ If authenticated flow needed:
       perception_state_restore({ state_id: "logged_in" })  // if previously saved
       OR guide user through login (human)
       perception_state_save({ state_id: "logged_in" }) after success

VERIFY
  ΓåÆ perception_verify({
       url_contains: [expected_route],
       url_not_contains: ["/login"]  // when auth should be satisfied
     })

STOP
  ΓåÆ correct URL + expected content for auth level
```

---

## 6. Playbook: Multi-step flows

**When:** Checkout, onboarding, wizard, any sequenced UX.

```text
DESCRIBE
  ΓåÆ perception_flow_describe({ flow_name: "validation-form" })
  ΓåÆ Get ordered checkpoints + success criteria each

FOR each checkpoint:
  OBSERVE  ΓåÆ navigate to checkpoint URL if specified
  REASON   ΓåÆ checkpoint instruction is for YOU, not the MCP
  ACT      ΓåÆ code edits and/or execute_script / execute_actions
  VERIFY   ΓåÆ perception_verify(checkpoint.success criteria)
  ΓåÆ if fail: do not advance; fix and retry this checkpoint only

STOP
  ΓåÆ all checkpoints verified
```

**Do not:** Skip checkpoints. **Do not:** Ask MCP to run the whole flow autonomously.

---

## 7. Playbook: Verification-only (regression check)

**When:** User asks ΓÇ£does it still work?ΓÇ¥ after unrelated changes.

```text
OBSERVE
  ΓåÆ perception_navigate_and_observe({ url })

VERIFY
  ΓåÆ perception_verify({ ... known good criteria ... })

STOP
  ΓåÆ pass or report reasons[] to user with screenshot
```

No code act unless verify fails.

---

## 8. Playbook: Responsive / viewport checks (basic)

**When:** Layout breakpoints, mobile nav, overflow.

```text
OBSERVE
  ΓåÆ perception_session_start with viewport { width: 375, height: 812 }
  ΓåÆ perception_navigate_and_observe({ include_screenshot: true })

REASON
  ΓåÆ Inspect screenshot resource + dom_text for horizontal overflow clues

ACT
  ΓåÆ Fix CSS in repo

VERIFY
  ΓåÆ Re-observe at same viewport; perception_verify text visible / not absent

REPEAT
  ΓåÆ perception_session_end ΓåÆ new session with desktop viewport if needed

STOP
  ΓåÆ criteria met at target viewport(s)
```

---

## 9. Playbook: Feature flags & edge UI

**When:** Beta toggles, iframe embeds, virtual lists, file upload, rich editors.

```text
OBSERVE
  ΓåÆ perception_navigate_and_observe({ url: "/edge-lab" or feature route })

REASON
  ΓåÆ Match scenario to engine probe pattern:
      feature flag  ΓåÆ URL param or localStorage per probe docs
      iframe        ΓåÆ may need execute_script in parent to reach frame
      virtual list  ΓåÆ scroll via execute_script before verify item visible
      file upload   ΓåÆ perception_execute_actions cannot upload files; use dedicated probe pattern when exposed

ACT + VERIFY
  ΓåÆ Per feature: act, then verify specific text/selector/state

STOP
  ΓåÆ feature-specific criteria met
```

Use `perception_flow_describe` or codebase search when unsure which probe applies.

---

## 10. Playbook: Correlating code Γåö live UI

**When:** You changed a component and need to confirm the right file drives the page.

```text
OBSERVE
  ΓåÆ perception_navigate_and_observe({ url })

CODE
  ΓåÆ perception_code_context({
       query_type: "search",
       query_kwargs: { q: "ComponentName" }
     })

REASON
  ΓåÆ Match button text / labels in dom_text to CRG search results
  ΓåÆ Edit correct file

VERIFY
  ΓåÆ perception_verify + perception_diff after change

STOP
  ΓåÆ live UI reflects code change
```

---

## 11. When to re-observe vs diff vs verify

| Situation | Tool |
|-----------|------|
| First look at page | `navigate_and_observe` |
| After code edit, same URL | `observe` or `navigate_and_observe` |
| After execute_script | `verify` then `diff(before, after)` |
| ΓÇ£What changed?ΓÇ¥ | `perception_diff` |
| ΓÇ£Is requirement met?ΓÇ¥ | `perception_verify` |
| Verify failed | `perception_verify` (auto-screenshot) + `perception_diff` |

---

## 11. Visual evidence (v0.5)

Observe, verify-fail, and diff tools **inline PNG images** in the MCP tool response (annotated viewport by default).

| Field | Meaning |
|-------|---------|
| `data.visual.screenshot_uri` | Raw viewport PNG resource |
| `data.visual.annotated_screenshot_uri` | Boxes for interactive + blocking issues |
| `data.visual.crop_screenshot_uri` | Element crop when `screenshot_mode: element` |
| `data.visual.visual_insights` | Deterministic layout signals (overflow, overlaps, zero-size clickables) |
| `screenshot_mode` | `viewport` \| `full` \| `element` (+ `screenshot_selector` for element) |

**Rules:**
- Images are attached to the tool result ΓÇö you do not need a separate fetch for normal UI work.
- Use `annotate_screenshot: true` (default) on first observe and all verify failures.
- Use `screenshot_mode: element` with a CSS selector for focused form/checkout debugging.
- `perception_diff` returns side-by-side + heatmap images when both scans have screenshots.

---

## 11.1 Observe detail levels (M4)

Use `detail` on observe tools when payload size matters:

- `detail: "full"` (default): full observation payload (DOM/a11y/dev insights) + visual block + inline images
- `detail: "summary_only"`: compact `agent_summary` + visual block + inline images (no DOM text)

Guideline:
- Start with `full` on first look and on failures.
- Never use `summary_only` on first observe or after verify failure.
- `summary_only` is only for tight loops when you already saw the page visually.

---

## 12. When to STOP and ask the human

| Signal | Action |
|--------|--------|
| `perception_auth_gate` ΓåÆ `requires_human: true` | Stop; ask user to log in or complete MFA/CAPTCHA |
| `perception_health` ΓåÆ unreachable | Stop; ask user to start dev server |
| `degraded` contains critical signals | Tell user observation is partial |
| Requirements ambiguous | Ask user for expected text/URL/selectors |
| Verify fails 3+ times after fixes | Stop; report `reasons[]`, screenshot, diff summary |

---

## 13. Playbook: Design inspiration (public galleries)

**When:** User asks for landing page / dashboard / UI inspiration from Dribbble, Behance, gallery sites.

**Read first:** MCP resource `perception://inspiration-guide` ΓÇö per-site URLs, selectors, preview rules, anti-bot.

```text
1. perception_inspiration_discover({ query })     ΓåÆ ranked candidates (fast)
2. perception_inspiration_collect({ query })      ΓåÆ URLs + ephemeral vision blobs
3. Open agent_view_url for live pages; use inspiration_blob for quick visual reference
4. perception_inspiration_session_end({ session_id })  ΓåÆ delete blobs when done
```

| Field | Use |
|-------|-----|
| `agent_view_url` | Best URL to open (live page preferred) |
| `preview_url` | CDN / og:image when available |
| `inspiration_blob` | Ephemeral medium JPEG (~24h TTL) |
| `blob_session_id` | Pass to session_end when finished |

**Provider notes (summary):**
- **Dribbble** ΓÇö HTTP WAF 202; headed browser + optional `DRIBBBLE_SESSION_COOKIE`
- **Behance / One Page Love** ΓÇö HTTP works; OPL uses `/genre/` not `?s=`
- **Awwwards / SiteInspire / Godly / Land-book** ΓÇö browser extract; Godly ΓåÆ `recent.design` `/i/` links
- **Land-book** ΓÇö `land-book.com` (no www); browse fallback; skip generic og-image blobs

**Do not:** Scrape galleries ad-hoc ΓÇö use MCP tools. Permanent image download is optional (`download_images`); blobs are ephemeral.

**Stop when:** You have enough references for the task, or user confirms stop. Always end blob session when design work completes.

---

## 14. Playbook: Creative assets (Resource Intelligence)

**When:** User needs icons, avatars, illustrations, fonts, or stock assets for a commercial project.

**Read first:** MCP resource `perception://resource-guide` ΓÇö license rules, provider notes, blob fields.

```text
1. perception_resource_search({ query, icon_family: "lucide" })  ΓåÆ family URLs + suggested_import
2. perception_resource_preview only when family miss + reference image (blobs skipped for in-family icons)
3. Use access_url / npm import ΓÇö not blobs ΓÇö for matched family icons
4. perception_resource_session_end({ session_id })
```

| Field | Use |
|-------|-----|
| `access_url` | SVG/API URL for integration |
| `suggested_import` | npm import line (e.g. lucide-react) |
| `icon_family` | Active style set (lucide, heroicons, tabler-icons, ΓÇª) |
| `resource_blob` | Only on family miss + `reference_preview_url`, or avatars/photos |

**Provider notes (MVP):**
- **Iconify / Lucide** ΓÇö commercial icons; NC collections skipped per asset
- **DiceBear** ΓÇö preview via public API; self-host for production commercial
- **unDraw / Storyset** ΓÇö in catalog; blobs skipped when automation prohibited

**Do not:** Scrape provider sites ad-hoc ΓÇö use MCP tools. Respect `license_warnings`.

**Stop when:** Assets selected and integrated, or user confirms stop. Always end blob session when asset work completes.

---

## 15. Playbook: SEO orchestration (SEO Intelligence)

**When:** User asks about search rankings, indexing, CTR, Core Web Vitals, technical SEO, or site-wide SEO audit.

**Read first:** MCP resource `perception://seo-guide` ΓÇö free-first providers, verify loop, boundaries.

```text
1. perception_seo_status()                    ΓåÆ phase + provider catalog
2. Connect user GSC / GA4 (when Phase 1 ships) ΓÇö OAuth, user-owned data
3. perception_seo_audit({ website_url, scan_id? })
4. Read evidence + recommendations ΓÇö every claim has evidence_ids
5. Fix code / config based on evidence
6. perception_observe ΓåÆ perception_verify on affected pages
7. Re-run perception_seo_audit to measure gains
```

| Provider | Role |
|----------|------|
| Search Console | Queries, index, crawl issues, CWV in GSC |
| GA4 | Traffic, landing pages, conversions |
| LibreCrawl | Technical crawl (local ΓÇö not our crawler) |
| Lighthouse | Lab CWV + SEO score |
| Browser Intelligence | Rendering evidence via `scan_id` |

**Do not:** Build keyword/backlink databases. Scrape SERPs ad-hoc. Claim SEO fixes without verify.

**Stop when:** Recommendations addressed and verified, or user confirms stop.

---

## 16. Playbook: Figma design context (Figma Intelligence)

**When:** User asks to analyze their Figma file, implement a frame, extract tokens, or compare design with code.

**Read first:** MCP resource `perception://figma-guide`.

```text
1. perception_figma_status()                         ΓåÆ connection + session
2. perception_figma_connect({ pat })                 ΓåÆ once per user (PAT stored locally)
3. perception_figma_context({ file_url, refresh? })  ΓåÆ normalized design context
4. Pass context to Design Sense / Consistency / Component Intelligence as needed
5. perception_observe ΓåÆ perception_verify for code implementation
```

| Layer | Role |
|-------|------|
| Connection Manager | PAT connect, validate, reuse |
| Session Manager | Active file, page, frame, selection |
| Console MCP Adapter | southleft/figma-console-mcp (hidden) |
| Context Normalizer | `FigmaDesignContext` for all modules |

**Do not:** Reimplement Figma APIs. Run public inspiration here ΓÇö use Inspiration Intelligence. Critique designs here ΓÇö use Design Sense.

**Stop when:** Context retrieved and downstream task complete, or user confirms stop.

---

## 17. Tool quick reference (secondary to playbooks)

Use tools **only as steps inside playbooks above**.

| Tool | Use when |
|------|----------|
| `perception_session_start/end` | Bootstrap / teardown |
| `perception_health` | Dev server up? |
| `perception_navigate_and_observe` | Default ΓÇ£open and seeΓÇ¥ |
| `perception_observe` | Same URL, fresh snapshot |
| `perception_execute_script` | Custom JS interaction |
| `perception_execute_actions` | Click/fill by label/text |
| `perception_verify` | After every act |
| `perception_diff` | Compare scan_ids |
| `perception_probe_form` | Before form work |
| `perception_auth_gate` | Login/MFA detection |
| `perception_state_save/restore` | Multi-step auth |
| `perception_flow_describe` | Multi-step flows |
| `perception_code_context` | Code Γåö UI correlation |
| `perception_inspiration_discover` | Ranked inspiration candidates (fast) |
| `perception_inspiration_collect` | URLs + ephemeral vision blobs |
| `perception_inspiration_session_end` | Delete ephemeral inspiration blobs |
| `perception_resource_search` | Ranked creative assets (fast) |
| `perception_resource_preview` | URLs + ephemeral resource vision blobs |
| `perception_resource_session_end` | Delete ephemeral resource blobs |
| `perception_seo_status` | SEO module phase + provider catalog |
| `perception_seo_audit` | SEO evidence ΓåÆ graph ΓåÆ recommendations |
| `perception_figma_status` | Figma connection + session health |
| `perception_figma_connect` | Connect Figma PAT (once) |
| `perception_figma_context` | Normalized file, tokens, components, selection |

---

## 18. Success checklist (before telling user ΓÇ£doneΓÇ¥)

- [ ] `perception_verify` passed for stated criteria
- [ ] `agent_summary.blocking` is empty (or user accepted warnings)
- [ ] `scan_id` / screenshot saved if user may need evidence
- [ ] Auth gates respected (no credential looping)
- [ ] You edited repo code when fix was structural (not only runtime script hacks)

---

**Remember:** The MCP does not tell you what to do next. **These playbooks do.** Follow observe ΓåÆ reason ΓåÆ act ΓåÆ verify until the checklist passes.
