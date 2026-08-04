# Research: Robustness for forms / auth / input inspiration

**Date:** 2026-07-27  
**Scope:** Inspiration layer only (forms, text inputs, auth, checkout, settings)  
**Evidence:** `scripts/eval_inspiration_forms_sections.py` (4/11), live collect traces, HTTP spikes

---

## 1. Verdict

Parallel diverse queries are working. Failures in this area are **not** latency/parallelism —
they are **coverage + routing + quality-gate** gaps:

| Layer | Status for forms/auth |
|-------|------------------------|
| Parallel query fan-out | OK — 3 distinct angles emit |
| Pattern specialists | **Missing** — no auth/checkout/form gallery wired |
| Daisy CDN | **Partial** — `textarea` exists but unmapped; `form.webp` **404** |
| Query scope routing | **Broken** for search-bar (`button` steals scope) |
| Web SERP Channel C | Runs but often **0 organic / 0 OG** for auth hunts |
| Multi-scout | Finds winners, but **relevance filter drops** most (title ≠ query tokens) |
| Provider cascade (OPL) | Candidates found, **preview materialize = 0** for auth |

**Robustness thesis:** Treat form/auth like navbar/pricing — **specialist HTTP galleries + healthy CDN packs first**; web/scout as rescue, not primary.

---

## 2. Failure taxonomy (from battery + traces)

### A. Chrome control thin packs

| Case | Observed | Root cause |
|------|----------|------------|
| checkbox/toggle | 2 daisy hits | Companion bundle = `['checkbox','toggle']` only — never reaches min_pattern=3 |
| textarea | aceternity only, no daisy | `textarea` **not in daisy map** even though CDN `textarea.webp` returns **200** |
| search bar | 8 button specialists | Query contains `button` → chrome/button path before `search` rule |

### B. Section/page form surfaces thin packs

| Case | Observed | Root cause |
|------|----------|------------|
| login/auth | 2 hits (`daisyui` + `dark_mode_design`) | No specialist; daisy `form.webp` is **404**; web_search count=0; scout winners filtered by relevance |
| checkout | 2 hits | Same — saasframe **has** `/categories/checkout` but match keywords only cover pricing |
| signup onboarding | 2 hits, dark_mode only | Scope=section/auth; no specialist; no daisy slug match |
| settings profile | 16 hits, “fail” | **False negative** — battery expected wrong providers; galleries actually worked |

### C. Pipeline traps (auth collect trace)

```text
pattern:   1 target (daisy:form) — CDN 404 risk
web:       parallel 3 queries → search_hits=0, og=0
scout:     probed 24, winners=[dark_mode, saas_landing, landingfolio, landing_love]
           acquired=8 → only 1 survives relevance (titles don't mention login/form)
OPL:       12 candidates, with_urls=0 (preview materialize failed)
→ stop='', total_hits=2
```

Relevance example:

| Title | Score vs login ask | Kept? |
|-------|--------------------|-------|
| Login form email password | 0.82 | yes |
| Sign in page | 0.00 | no (token gap: `sign`/`in` vs hunt tokens) |
| Dark Mode Design #1 | 0.00 | should reject (sometimes leaks via thin-pack keep-best) |
| SaaS Landing Page #1 | 0.00 | no |

---

## 3. What already works (reuse pattern)

Navbar/footer/pricing became robust by **specialist galleries with CDN thumbs**, not by more SERP:

| Grain | Specialist | Why it works |
|-------|------------|--------------|
| navbar | navbar.gallery | Webflow CDN, match keywords |
| footer | footer.design | same |
| pricing | saasframe.io | same |
| buttons | aceternity / ibelick / daisy | dedicated chrome sources |

**Auth/checkout need the same shape.** Spike (2026-07-27):

| Source | HTTP | Previews | Fit |
|--------|------|----------|-----|
| `saasframe.io/categories/sign-up-flow` | 200 / ~0.7s | 8 Webflow CDN | **signup/auth P0** |
| `saasframe.io/categories/checkout` | 200 / ~0.1s | 8 Webflow CDN | **checkout P0** |
| `saasframe.io/categories/login` | 200 / ~50ms | 8 Webflow CDN | **login P0** |
| `nicelydone.club/tags/authentication` | 200 / ~2.6s | 8 CDN thumbs | auth P1 |
| daisy `textarea.webp` | 200 | direct CDN | chrome P0 |
| daisy `form.webp` | **404** | — | remove / remap |
| daisy `fieldset`/`label`/`file-input`/`range` | 200 | companions | chrome P1 |
| Flowbite forms docs | 200 | mostly generic OG | weak (docs_page only) |

Mobbin / Gummble are strong for humans but paywalled / anti-bot — keep as `research_only` or screenshot_demo later, not default HTTP path.

---

## 4. Robustness plan (priority order)

### P0 — Close the specialist gap (same recipe as pricing)

1. **Wire saasframe category URLs as specialists** (or expand existing `saasframe` match + URL templates):
   - login / sign-in / signup / registration → `/categories/login` + `/categories/sign-up-flow`
   - checkout / payment / cart → `/categories/checkout`
2. **Add `nicelydone` auth tag** as secondary specialist (`any_img`, assets.nicelydone.club).
3. **Daisy map fix:**
   - Add `textarea` → `textarea`
   - Remove or replace dead `form` → use companions `input, select, checkbox, toggle, textarea, label`
   - Expand checkbox companions to ≥4 so min_pattern soft-stop can fire honestly

### P0 — Scope routing (search bar)

4. In `query_flex._SCOPE_RULES`, add **`search bar` / `search field` / `search input`** **before** the button rule.
5. Optionally: require word-boundary for `button` so “…clear button” does not force chrome/button specialists.

### P1 — Relevance + synonym hygiene (auth)

6. Expand `_SYNONYMS`: `login`↔`signin`/`sign-in`/`authentication`; `signup`↔`registration`/`onboarding`.
7. Tokenize hyphen/space variants so “Sign in page” scores against login hunts.
8. For `intent_class in {auth, checkout}`, **boost multi-scout winners from flow/landing categories** instead of hard-dropping zero-token titles — or require specialist path so scout isn’t the only hope.

### P1 — Thin-pack rescue contract

9. **Intent soft-floor:** for auth/checkout/forms, do not end collect while `hits < 4` if any of {web, specialist, scout} still unpaid — today hunting “finishes” with stop=`''` and 2 hits.
10. When web returns 0 SERP hits across parallel queries, log `web_empty_rescue` and **force specialist category URLs** (saasframe) even if keyword match missed.
11. Fix OPL auth materialize (`with_urls=0`) — separate bug; until fixed, don’t count OPL candidates toward pack readiness.

### P2 — Chrome depth

12. Flowbite form/input/textarea docs only if real component imgs appear (today OG-only → skip or mark degraded).
13. Region crop: `_INPUT_TOKENS` / `_FORM_TOKENS` boost (`input`, `textarea`, `form`, `[type=search]`) like buttons.
14. Battery expectations: accept `onepagelove` / `saas_landing_page` / `saasframe` for settings; lower checkbox min to 2 **or** fix companions so min=3 is honest.

### P2 — Eval / CI gate

15. Promote forms battery cases that matter into hardcore (or a `forms_gate` script) with **honest** min_hits + `expect_provider_any` including saasframe/nicelydone.
16. Unit tests: daisy slug existence HEAD checks; scope order for search-bar; specialist selection for login/checkout.

---

## 5. Recommended architecture (forms/auth path)

```text
collect(auth|checkout|form|input)
  ├─ 1. Pattern specialists (saasframe login/signup/checkout, nicelydone)
  │     + daisy CDN (textarea/input/checkbox companions — no dead form.webp)
  ├─ 2. Parallel diverse queries (already shipped)
  │     → web SERP ∥ multi-scout ∥ provider wave
  ├─ 3. Soft-floor rescue: if hits < 4 for auth/checkout → force specialist URLs
  └─ 4. Relevance: expanded auth synonyms; don’t soft-stop on 2 junk/landing cards
```

**Do not** rely on Mobbin as the default path. **Do** copy the navbar.gallery success model onto saasframe category pages we already proved.

---

## 6. Success criteria

| Metric | Target |
|--------|--------|
| `chrome/textarea` | ≥3 hits including `daisyui` |
| `chrome/checkbox_toggle` | ≥3 hits (daisy companions) |
| `component/search_bar` | scope=`component` (or chrome without button specialists) |
| `section/login_auth` | ≥4 hits; providers include `saasframe` (or nicelydone) |
| `section/checkout` | ≥4 hits; saasframe checkout category |
| `page/settings_profile` | pass with gallery providers (loosen expect list) |
| Forms battery | ≥9/11 after P0–P1 |
| Hardcore battery | stay 13/13 (no regression) |

---

## 7. What not to do

- Don’t merge Component Intelligence install into inspiration.
- Don’t raise Chromium live-SS as the auth fix (WAF/hang history).
- Don’t treat more parallel suffix queries as the fix — **sources** are the bottleneck.
- Don’t soft-stop on dark_mode/landing thumbs for an auth ask.

---

## 8. Suggested next implementation slice

1. Daisy map + companions + search-bar scope rule (hours, high confidence).  
2. Saasframe login/signup/checkout specialists (hours, spike already green).  
3. Auth synonym + thin-pack soft-floor (half day).  
4. Re-run forms battery + hardcore; write pass/fail note.

---

## 9. P0 shipped (2026-07-27)

| Change | Result |
|--------|--------|
| Daisy `textarea` + form→input companions | checkbox 5 hits, textarea 4 daisy |
| Search-bar rule before button | scope=`component` |
| saasframe_login / signup / checkout + nicelydone_auth | login 10 hits, checkout 8, signup 8 |
| Forms battery | **11/11** |
| Hardcore battery | **13/13** |

## 10. P1 + P2 shipped (2026-07-27)

| Change | Result |
|--------|--------|
| Hyphen tokenize + auth synonyms | "Sign in page" relevant vs login ask |
| Scout intent_flow_boost | auth/checkout prefer flow/landing |
| Soft-floor `_need_more_refs` | auth/checkout stay hunting under 4 |
| Web-empty / soft-floor specialist rescue | force saasframe/nicelydone |
| Intent force specialists in pattern acquire | always include category URLs |
| Region crop input/form/search | before nav/button |
| Search-bar skips button-only specialists | |
| Forms cases in hardcore battery | forms/textarea, login, checkout, search_bar |
