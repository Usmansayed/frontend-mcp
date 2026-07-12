# Forest F07 — SEO and AI Visibility

**Root:** S08 (post-implementation growth stage)
**Target leaves:** ~16
**Archetype coverage:** all indexable sites (landing, marketing, blog, ecommerce, docs).

## Root decision points

1. **Mode** — `development` (no auth) vs `professional` (GSC/GA4 connected).
2. **Prior graph state** — empty vs seeded vs stale.
3. **AI visibility** — `include_ai_visibility` on/off; upstream SEO evidence sufficient?
4. **Verification target** — one recommendation vs suite vs baseline capture.

## Notable branches

- First SEO audit → seed graph → produce recommendations → present to user.
- Repeat audit → graph diff → change-scoped recommendations.
- Pro mode without auth → `auth_required` → connect flow → retry.
- `include_ai_visibility=true` (default) → 12 analyzers derive AI signals → attached to reasoning_context_v2.
- `include_ai_visibility=false` → skip AI analyzers, state records absent AI block.
- Fix loop: recommendation → implementation (F04) → `perception_seo_verify` → verified or regressed.
- Reasoning context frozen (schema 2.0) — coordinated across audit and verify.

## Pruning notes

- Individual recommendation types not enumerated as separate states; they share the "recommendation-open" state with tags.
- Off-page factors (backlinks) marked outside scope; state stays `unknown_evidence: [off_page]`.

## Cross-links out

- F04 (fix implementation)
- F06 (Lighthouse-SEO parallel run)
- F09 (regression check pre-release)
- F10 (post-release monitoring)
- F12 (GSC token invalid, LibreCrawl down)
