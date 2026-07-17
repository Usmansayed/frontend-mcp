# Flaw Gallery Eval

Hidden-flaw surfaces for coordination quality loops (catch rate + decision quality).

## Spec

[`docs/superpowers/specs/2026-07-17-flaw-gallery-eval-design.md`](../../docs/superpowers/specs/2026-07-17-flaw-gallery-eval-design.md)

## Prerequisites

```bash
cd sandbox
npm run dev   # http://localhost:5173
```

## Run

```bash
$env:PYTHONPATH="src"
python scripts/run_flaw_gallery.py
python scripts/run_flaw_gallery.py --case F1
```

Report: `evals/flaw_gallery/reports/latest.json`

## Cases (tricky pack F1–F6)

| ID | Trap | Layer |
|----|------|-------|
| F1 | `position:sticky` but `top:auto` (never pins) | verify |
| F2 | Micro overflow `100vw+10px` (not loud 112vw) | verify |
| F3 | Near-equal KPI type scale 1.58→1.50rem | ship |
| F4 | Subtle ~58vw marketing shell | ship |
| F5 | Sticky on inner list; outer `<aside>` static | verify |
| F6 | F1 chrome trap + near-equal KPIs | both |

## Cases (hard pack F7–F12)

| ID | Trap | Layer |
|----|------|-------|
| F7 | Transform containing-block (`translateZ(0)`) kills sticky | verify |
| F8 | Barely-over overflow `+3px` vs `+2` tolerance | verify |
| F9 | Exact-equal KPI type (identical rem) | ship |
| F10 | Left-aligned compressed main ~62vw (not centered) | ship |
| F11 | Decoy sticky breadcrumb nav; real `<aside>` static | verify |
| F12 | Transform + left shell + exact-equal KPIs | both |

## Cases (expert pack F13–F15)

| ID | Trap | Layer |
|----|------|-------|
| F13 | `overflow-x:hidden` ancestor breaks viewport sticky | verify |
| F14 | `sticky; top:-80px` (pins off-screen) | verify |
| F15 | ox-hidden + decoy nav + exact-equal KPIs | both |

Soft text criteria alone must not clear verify cases. Chrome permanence uses a **real scroll** of the scrollport, prefers sidebar/`aside` over short decoy navs, rejects sticky under transform/filter/non-scrolling overflow containment, and rejects sticky with largely negative `top`.

**Important:** Passing this gallery in-repo proves detectors catch planted flaws. It does **not** prove production agents will *use* MCP. That depends on the Cursor rule, MCP server `instructions`, and `perception://getting-started` — guarded by `tests/test_mcp_bootstrap_contract.py`.
