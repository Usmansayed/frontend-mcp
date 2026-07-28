# Inspiration sources curation

**Date:** 2026-07-27  
**Seed file:** [`google-resource-links.txt`](../../google-resource-links.txt)  
**Machine corpus:** [`inspiration_sources_corpus.json`](../../src/navigation/inspiration_intelligence/data/inspiration_sources_corpus.json)

## Product rule (locked)

| Layer | Job |
|-------|-----|
| **Inspiration Intelligence** | Visit galleries + **showcase/demo pages**, acquire **images/screenshots**, agent LOOKS → borrow/ignore → copy-adapt |
| **Component Intelligence** | Separate — find/install primitives when implementing. **Do not merge** into inspiration cascade |

Component/animation sites (shadcn, Aceternity, Magic UI, GSAP demos, …) are valid **inspiration screenshot targets**. They are **not** auto-wired into component search/install.

## What we ingested from your list

Structured into categories:

- `ui_gallery` / `landing_gallery` / `dashboard_gallery`
- `flow_library` (Mobbin, SaaSFrame, … — careful with paywalls)
- `component_showcase` (demo URLs for viewport capture)
- `motion_showcase`
- `design_system_live`
- `mobile_gallery` / `experimental` / `email_gallery`

**Tiers:** `fast_http` | `browser_gallery` | `screenshot_demo` | `flow_library` | `research_only`

**Next provider candidates** (highest ROI after OPL/LAPA/Behance/Httpster): Minimal Gallery, Landing Love, Saaspo, Landing.Gallery, SaaS Interface, Dark Mode Design, SaaS Landing Page, Collect UI, Curated Design, Siiimple.

Icons/fonts stay out of inspiration collect (Resource Intelligence).

## Gemini research prompt (paste as-is)

```text
You are researching websites for an AI coding agent’s “Inspiration Intelligence” layer.

GOAL
Build a curated registry of sites the agent can visit to collect visual design references (preview images or viewport screenshots). The agent will LOOK at those images and copy-adapt UI. This is NOT for installing component packages and NOT for Google SERP scraping.

OUTPUT FORMAT (strict JSON array). Each object:
{
  "id": "snake_case_id",
  "name": "Display Name",
  "url": "https://...",
  "category": one of [
    "ui_gallery",
    "landing_gallery",
    "dashboard_gallery",
    "flow_library",
    "component_showcase",
    "motion_showcase",
    "design_system_live",
    "mobile_gallery",
    "experimental",
    "email_gallery"
  ],
  "tier": one of [
    "fast_http",        // listing pages expose CDN/thumb URLs without login
    "browser_gallery",  // SPA/WAF — needs browser extract or screenshot
    "screenshot_demo",  // curated demo/docs page worth viewport capture
    "flow_library",     // screen/flow archives (note paywall if any)
    "research_only"     // useful humans; not default agent cascade
  ],
  "intent_hints": ["landing", "saas", "dashboard", ...],
  "demo_urls": ["https://..."]  // 1–5 best pages to screenshot (required for screenshot_demo / component_showcase / motion_showcase),
  "auth_paywall": "none|freemium|paid|unknown",
  "preview_image_likely": true/false,
  "tos_risk": "low|medium|high",
  "why_for_agents": "one sentence",
  "duplicate_of": null or "existing_id"
}

COVERAGE TARGETS
- At least 40 DISTINCT inspiration/gallery sites (full website showcases, landing galleries, SaaS UI galleries).
- At least 15 component/animation SHOWCASE or demo sites (Aceternity-like, Magic UI-like, shadcn examples, Codrops demos, etc.) with concrete demo_urls to screenshot.
- At least 10 real product marketing sites worth live screenshots (Stripe-class) if not already famous — optional category design_system_live or a new "famous_product".
- Prefer sites updated 2024–2026. Deduplicate aliases (godly.website ≈ recent.design).

ALREADY HAVE (do not waste slots re-describing; mark duplicate_of if you rediscover):
One Page Love, Lapa Ninja, Behance, Httpster, SiteInspire, Dribbble, Awwwards, Godly/recent.design, Land-book,
Minimal Gallery, CSS Nectar, Best Website Gallery, Refero, Siiimple, Curated Design, Collect UI,
Landing Love, Saaspo, Dark Mode Design, Landingfolio, SaaS Landing Page, Landing.Gallery, Commerce Cream,
SaaS Interface, Screenlane, SaaSFrame, SaaSUI, Mobbin, Page Flows, UI Sources, UXArchive,
shadcn/ui, Aceternity, Magic UI, Flowbite, daisyUI, Mantine, Chakra, Ant Design, Radix,
Material, Polaris, Carbon, Primer, Fluent, Spectrum, Atlassian,
Hover States, Brutalist Websites, Codrops, Details Matter.

HARD RULES
- Exclude pure icon packs, font directories, npm registries, and AI “generate my app” builders unless they have a public visual gallery.
- For component libraries: list SHOWCASE/demo URLs only — not “install with npm”.
- Flag auth_paywall honestly.
- Prefer sources where an automated browser can capture a useful first viewport in <5s.
- Return ONLY the JSON array, no markdown.
```

## How Inspiration should use this (build preview)

1. **fast** — existing HTTP providers only (unchanged latency budget).  
2. **broad** — + 1–2 `screenshot_demo` from `component_showcase` / `motion_showcase` matching intent.  
3. **deep** — + browser galleries from `next_provider_candidates`.  
4. Agent LOOK → `visual_feedback(purpose=inspiration)` → implement (Component Intelligence only if they choose to install).

## After Gemini returns JSON

1. Merge into `inspiration_sources_corpus.json` (dedupe by `id` / canonical host).  
2. Promote 3–5 `candidate_provider` entries with HTTP thumbs into real adapters.  
3. Wire `screenshot_demo` into the existing live-capture queue (same exclusive browser path as famous sites).

## Counts in current corpus (seed)

Roughly **90+** source entries across categories from your Google research file, tagged for admission — not all wired as live providers yet.
