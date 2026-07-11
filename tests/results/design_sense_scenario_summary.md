# Design Sense Scenario Results

Generated: 2026-07-10T16:43:16.355237+00:00

## Run summary

- Scenarios: **10**
- Completed: **10**
- Errors: **0**
- Total findings: **154**
- Total blocking: **3**
- Sandbox: **live** (http://localhost:5173)

## Per scenario

### fake_checkout_overflow (fixture) — REVIEW

Ecommerce checkout with blocking horizontal overflow

- Findings: 27 (blocking: 1, major: 0)
- Lanes: objective=11, subjective=23
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Complete checkout and pay for cart items": 27 consolidated findings. 1 blocking issue(s) require immediate attention. Top priority: Resolve blocking visual issues before polish revi…
- Top findings:
  - [blocking] scrollWidth=2400 viewport=1280
  - [minor] Color not from design token
  - [minor] Spacing off design scale

### fake_login_form (fixture) — PASS

Sign-in flow with clean layout signals

- Findings: 12 (blocking: 0, major: 0)
- Lanes: objective=1, subjective=11
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Sign in to dashboard as admin": 12 consolidated findings. No blocking or major issues detected. Top priority: Pass design_tokens or enable token snapshot from Consistency Intelligen…
- Top findings:
  - [minor] Design tokens not supplied — cannot verify token compliance
  - [advisory] Verify: Contrast ratio compliant on text and interactive elements
  - [advisory] Verify: Semantic colors restricted to recognized states

### fake_dashboard_analytics (fixture) — PASS

Dashboard analytics page — layout and hierarchy review

- Findings: 16 (blocking: 0, major: 0)
- Lanes: objective=1, subjective=15
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Review dashboard analytics charts and navigation": 16 consolidated findings. No blocking or major issues detected.
- Top findings:
  - [advisory] Verify: Contrast ratio compliant on text and interactive elements
  - [advisory] Verify: Semantic colors restricted to recognized states
  - [advisory] Verify: Accent color reserved for clickable targets

### fake_validation_form (fixture) — REVIEW

Form with interaction and error-prevention checks

- Findings: 26 (blocking: 2, major: 0)
- Lanes: objective=12, subjective=21
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Fill validation form and submit with invalid data first": 26 consolidated findings. 2 blocking issue(s) require immediate attention. Top priority: Resolve blocking visual issues bef…
- Top findings:
  - [blocking] Submit
  - [blocking] Blocking visual issues detected: ['zero_size_clickable']
  - [minor] Color not from design token

### fake_minimal_task (fixture) — PASS

Task-only request — tests knowledge graph and providers without DOM

- Findings: 16 (blocking: 0, major: 0)
- Lanes: objective=2, subjective=14
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Improve mobile navigation for SaaS onboarding": 16 consolidated findings. No blocking or major issues detected. Top priority: Pass design_tokens or enable token snapshot from Consis…
- Top findings:
  - [minor] Design tokens not supplied — cannot verify token compliance
  - [advisory] Color review awaiting Design Snapshot (colors section)
  - [advisory] Icons must be optically sized alongside text.

### fake_lint_only (fixture) — PASS

Computed styles only — objective design_lint lane

- Findings: 18 (blocking: 0, major: 0)
- Lanes: objective=10, subjective=13
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Audit button and text styles": 18 consolidated findings. No blocking or major issues detected. Top priority: color uses raw value #ff0000 — Hardcoded color value detected on element…
- Top findings:
  - [minor] Color not from design token
  - [minor] Spacing off design scale
  - [minor] Design tokens not supplied — cannot verify token compliance

### sandbox_login (sandbox) — PASS

Live sandbox page /login

- Findings: 8 (blocking: 0, major: 0)
- Lanes: objective=5, subjective=4
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Sign in to access protected dashboard": 8 consolidated findings. No blocking or major issues detected. Top priority: vs Stripe Checkout: Typography families differ from reference
- Top findings:
  - [minor] 16 elements use non-token colors
  - [minor] h1 font-size 22.4px
  - [minor] label font-size 13.6px

### sandbox_checkout_shipping (sandbox) — PASS

Live sandbox page /shop/checkout/shipping

- Findings: 12 (blocking: 0, major: 0)
- Lanes: objective=10, subjective=7
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Complete checkout shipping step": 12 consolidated findings. No blocking or major issues detected. Top priority: vs Stripe Checkout: Typography families differ from reference
- Top findings:
  - [minor] 25 elements use non-token colors
  - [minor] h1 font-size 32.0px
  - [minor] span font-size 13.6px

### sandbox_validation_form (sandbox) — PASS

Live sandbox page /forms/validation

- Findings: 12 (blocking: 0, major: 0)
- Lanes: objective=12, subjective=5
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Submit validation form with required fields": 12 consolidated findings. No blocking or major issues detected. Top priority: vs Stripe Checkout: Typography families differ from refer…
- Top findings:
  - [minor] 46 elements use non-token colors
  - [minor] h1 font-size 32.0px
  - [minor] h3 font-size 18.72px

### sandbox_home (sandbox) — PASS

Live sandbox page /

- Findings: 7 (blocking: 0, major: 0)
- Lanes: objective=9, subjective=2
- Reviewers: layout_reviewer, typography_reviewer, color_reviewer, accessibility_reviewer, hierarchy_reviewer…
- Summary: Design review for "Navigate home page and evaluate layout hierarchy": 7 consolidated findings. No blocking or major issues detected. Top priority: vs Stripe Checkout: Typography families differ from r…
- Top findings:
  - [minor] 37 elements use non-token colors
  - [minor] h1 font-size 32.0px
  - [minor] h3 font-size 18.72px
