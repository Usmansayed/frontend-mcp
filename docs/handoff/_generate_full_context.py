#!/usr/bin/env python3
"""Generate detailed chat handoff pack from Cursor transcript JSONL."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HANDOFF = REPO / "docs" / "handoff"
TRANSCRIPT = Path(
    r"C:\Users\usman\.cursor\projects\c-Users-usman-Projects-frontend-perception-engine"
    r"\agent-transcripts\c573bbec-56b1-4ce1-9d4f-eba50f9a5c08"
    r"\c573bbec-56b1-4ce1-9d4f-eba50f9a5c08.jsonl"
)

MAIN_OUT = HANDOFF / "2026-08-04-CHAT-CONTEXT.md"
INDEX_OUT = HANDOFF / "2026-08-04-CHAT-QUERY-INDEX.md"
RECENT_OUT = HANDOFF / "2026-08-04-CHAT-RECENT-QUERIES.md"
CACHE_DIR = REPO / ".cache"
CACHE_JSONL = CACHE_DIR / "_chat_user_queries.jsonl"
CACHE_UNIQUE = CACHE_DIR / "_chat_unique_queries.txt"

TS_RE = re.compile(r"<timestamp>(.*?)</timestamp>", re.S)
UQ_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)


def extract_text(obj: dict) -> str:
    msg = obj.get("message") or obj
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                t = p.get("text") or p.get("content") or ""
                if isinstance(t, str):
                    parts.append(t)
        return "\n".join(parts)
    return ""


def parse_user_line(raw: str) -> tuple[str | None, str]:
    ts_m = TS_RE.search(raw)
    uq_m = UQ_RE.search(raw)
    ts = ts_m.group(1).strip() if ts_m else None
    text = (uq_m.group(1).strip() if uq_m else raw.strip())
    # Drop agent harness wrappers that aren't real user asks
    if text.startswith("Your team's answer") or text.startswith("<agent_transcripts>"):
        return ts, text
    return ts, text


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


NOISE_MARKERS = (
    "<mcp_meta_tools>",
    "<agent_skills>",
    "<always_applied_workspace_rules>",
    "briefly inform the user about the task result",
    "your team's answer",
    "<agent_transcripts>",
    "you are an ai coding assistant, powered by",
)


def is_noise(text: str) -> bool:
    low = text[:2000].lower()
    if any(m in low for m in NOISE_MARKERS):
        return True
    # harness-only stubs
    if len(text) < 40 and "follow-up" in low:
        return True
    return False


_MON = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_ymd(ts: str | None) -> tuple[int, int, int] | None:
    if not ts:
        return None
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})", ts)
    if not m:
        return None
    return (int(m.group(3)), _MON[m.group(1)], int(m.group(2)))


def era_for(ts: str | None, text: str = "") -> str:
    """Date-primary eras matching the real Jul 8 → Aug 4 arc."""
    ymd = parse_ymd(ts)
    if ymd is None:
        return "E00_undated"
    y, mo, d = ymd
    if (y, mo, d) <= (2026, 7, 9):
        return "E01_founding_harness"
    if (y, mo, d) <= (2026, 7, 14):
        return "E02_browser_evidence_core"
    if (y, mo, d) <= (2026, 7, 20):
        return "E03_resolver_design_uxkb"
    if (y, mo, d) <= (2026, 7, 25):
        return "E04_inspiration_resources"
    if (y, mo, d) <= (2026, 7, 29):
        return "E05_coordination_face"
    if (y, mo, d) <= (2026, 7, 31):
        return "E06_live_redesign_pulse_fidelity"
    return "E07_p0_doctor_handoff"


ERA_TITLES = {
    "E00_undated": "Undated / unparsed timestamps",
    "E01_founding_harness": "Jul 8–9 — Founding + test harness app",
    "E02_browser_evidence_core": "Jul 10–14 — Browser evidence runtime core",
    "E03_resolver_design_uxkb": "Jul 16–20 — Resolver, design graph, ForOpenCode UX KB",
    "E04_inspiration_resources": "Jul 22–25 — Inspiration gallery + creative resources",
    "E05_coordination_face": "Jul 27–29 — Coordination face / card / hang fixes",
    "E06_live_redesign_pulse_fidelity": "Jul 30–31 — Live redesign grades + pulse/look_lock/fidelity (→dev66)",
    "E07_p0_doctor_handoff": "Aug 4 — Experience-report P0s (dev67) + laptop handoff",
}

ERA_NARRATIVE = {
    "E01_founding_harness": (
        "Started building a **frontend perception engine for coding agents** "
        "(Cursor/Claude), not another browser agent. Code Review Graph is a "
        "**library**, not a fork. Immediately asked for a complex navigable "
        "frontend-only test project (branches, buttons, forms) and to graph + "
        "test the tool against it."
    ),
    "E02_browser_evidence_core": (
        "Grew the MCP into a deterministic observe/verify/forms/guards runtime. "
        "Sessions, navigate_and_observe, probe_form, verify truthfulness "
        "(`data.verified`), and agent-facing summaries became the spine. "
        "Heavy iteration on making evidence usable by host agents."
    ),
    "E03_resolver_design_uxkb": (
        "Wired code↔UI resolvers (`resolve_route` / `resolve_component` / …), "
        "design-graph + consistency tooling, and the **ForOpenCode** UX knowledge "
        "corpus (extracts, guides, runtime packs) for principle retrieval — "
        "separate from project design-graph standards."
    ),
    "E04_inspiration_resources": (
        "Added inspiration gallery flows and creative resource search "
        "(fonts/icons/photos/patterns). Focus: agents should LOOK many refs "
        "and actually apply assets — not soft-mood text."
    ),
    "E05_coordination_face": (
        "Built/hardened the **coordination face**: `agent_summary.card`, packs, "
        "phases, unpaid evidence, claim gates. Multiple hangs / slow executes "
        "blamed on coordination vs inspiration layers — you demanded fix "
        "coordination properly, then component-level tests, then full readiness "
        "(MCP + docs + rules + coordination)."
    ),
    "E06_live_redesign_pulse_fidelity": (
        "Live GPT-Clone-style redesign sessions graded ~B−: strong evidence, "
        "weak taste/chrome match, fat envelopes, sticky ceremony. Demanded "
        "**~80–90% visual copy**, forced use of component/resources/design/"
        "consistency, and **parallel HTTP** — shipped as look_lock, inspiration "
        "pulse, then **dev66** chrome fidelity + claim-sticky families + "
        "`can_parallel` / `parallel_batch`."
    ),
    "E07_p0_doctor_handoff": (
        "Agent experience report P0s implemented as **dev67**: `perception_step`, "
        "hard `implement_blocked` on mutation tools, health `data.doctor`. "
        "Asked for laptop-switch handoff with **full chat detail** (this pack)."
    ),
}


def main() -> None:
    HANDOFF.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not TRANSCRIPT.exists():
        raise SystemExit(f"Transcript missing: {TRANSCRIPT}")

    records: list[dict] = []
    for i, line in enumerate(TRANSCRIPT.open(encoding="utf-8", errors="replace"), 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("role") != "user":
            continue
        raw = extract_text(obj)
        ts, text = parse_user_line(raw)
        if not text or len(text) < 2:
            continue
        if is_noise(text):
            continue
        # Drop huge system dumps accidentally tagged as user
        if len(text) > 20000 and "<user_query>" not in raw:
            continue
        records.append(
            {
                "n": len(records) + 1,
                "line": i,
                "ts": ts,
                "text": text,
                "norm": normalize(text),
                "ymd": parse_ymd(ts),
                "era": era_for(ts, text),
            }
        )

    # Unique by normalized text, keep first occurrence
    unique: list[dict] = []
    seen: set[str] = set()
    for r in records:
        if r["norm"] in seen:
            continue
        seen.add(r["norm"])
        unique.append(r)

    # Cache extracts
    with CACHE_JSONL.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps({"ts": r["ts"], "text": r["text"], "era": r["era"]}, ensure_ascii=False) + "\n")
    CACHE_UNIQUE.write_text(
        "\n\n---\n\n".join(f"[{u['ts'] or '?'}]\n{u['text']}" for u in unique),
        encoding="utf-8",
    )

    era_counts = Counter(u["era"] for u in unique)
    day_counts = Counter(u["ymd"] for u in records if u.get("ymd"))
    day_table = ["| Day | User msgs |\n|-----|----------:|\n"]
    for ymd, c in sorted(day_counts.items()):
        day_table.append(f"| {ymd[0]}-{ymd[1]:02d}-{ymd[2]:02d} | {c} |\n")
    day_block = "".join(day_table)

    # --- QUERY INDEX ---
    index_lines = [
        "# Chat query index — full unique user asks\n\n",
        f"**Generated:** {datetime.now().isoformat(timespec='seconds')}\n",
        f"**Transcript:** `{TRANSCRIPT}`\n",
        f"**Total user messages:** {len(records)}\n",
        f"**Unique user queries:** {len(unique)}\n\n",
        "Companion files:\n",
        "- `2026-08-04-CHAT-CONTEXT.md` — product state + era narrative\n",
        "- `2026-08-04-CHAT-RECENT-QUERIES.md` — last 120 unique asks (verbatim)\n\n",
        "## Counts by era\n\n",
        "| Era | Count |\n|------|------|\n",
    ]
    for era, title in ERA_TITLES.items():
        index_lines.append(f"| `{era}` {title} | {era_counts.get(era, 0)} |\n")
    index_lines.append("\n---\n\n## All unique queries (chronological first-seen)\n\n")
    for u in unique:
        preview = u["text"].replace("\r\n", "\n").strip()
        if len(preview) > 500:
            preview = preview[:500] + "…"
        # Escape table-breaking pipes
        preview = preview.replace("|", "\\|")
        index_lines.append(
            f"### Q{u['n']:04d} — {u['ts'] or 'no-timestamp'} — `{u['era']}`\n\n"
            f"{preview}\n\n"
        )
    INDEX_OUT.write_text("".join(index_lines), encoding="utf-8")

    # --- RECENT ---
    recent = unique[-120:]
    recent_lines = [
        "# Recent unique user queries (last 120)\n\n",
        f"**Generated:** {datetime.now().isoformat(timespec='seconds')}\n",
        f"**Of** {len(unique)} unique / {len(records)} total user messages\n\n",
        "Read these for latest intent wording. Full set: `2026-08-04-CHAT-QUERY-INDEX.md`.\n\n",
    ]
    for u in recent:
        recent_lines.append(
            f"## Q{u['n']:04d} — {u['ts'] or '?'} — `{u['era']}`\n\n"
            f"{u['text'].strip()}\n\n---\n\n"
        )
    RECENT_OUT.write_text("".join(recent_lines), encoding="utf-8")

    # --- Era narrative samples ---
    def samples(era: str, n: int = 8) -> str:
        items = [u for u in unique if u["era"] == era]
        if not items:
            return "_No tagged queries in this era bucket._\n"
        # first 4 + last 4 for arc endpoints
        pick = items[:4]
        if len(items) > 8:
            pick = items[:4] + items[-4:]
        elif len(items) > 4:
            pick = items[:4] + items[4:n]
        out = []
        for u in pick:
            snippet = u["text"].replace("\n", " ").strip()
            if len(snippet) > 280:
                snippet = snippet[:280] + "…"
            out.append(f"- ({u['ts'] or '?'}) {snippet}")
        return "\n".join(out) + "\n"

    eras_md = []
    for era, title in ERA_TITLES.items():
        if era_counts.get(era, 0) == 0:
            continue
        narr = ERA_NARRATIVE.get(era, "")
        eras_md.append(
            f"### {title}\n\n"
            f"**Tag:** `{era}` · **unique asks:** {era_counts.get(era, 0)}\n\n"
            f"{narr}\n\n"
            f"**Representative asks:**\n\n"
            f"{samples(era)}\n"
        )
    eras_block = "\n".join(eras_md)

    main_doc = f"""# Session handoff — Frontend Perception MCP (FULL chat context)

**Written:** 2026-08-04 (expanded pack)  
**Purpose:** Laptop switch / new chat resume with **product state + detailed conversation memory**.  
**Transcript id:** `c573bbec-56b1-4ce1-9d4f-eba50f9a5c08`  
**Stats:** {len(records)} user messages · **{len(unique)} unique** queries extracted into companion files.

| File | Role |
|------|------|
| **This file** | Product state, intended loop, code map, backlog, era narrative |
| `2026-08-04-CHAT-QUERY-INDEX.md` | All {len(unique)} unique user asks (first-seen order) |
| `2026-08-04-CHAT-RECENT-QUERIES.md` | Last 120 unique asks verbatim |

---

## 0. Open this first on the other laptop

```bash
cd <clone>
git fetch origin
git checkout exp/agent-face-simple
git pull origin exp/agent-face-simple
pip install -e . --upgrade
# Confirm VERSION / package == 1.2.0.dev67
# Reload Cursor MCP (user-frontend-mcp)
```

**Repo:** https://github.com/Usmansayed/frontend-mcp.git  
**Local path (old laptop):** `C:\\Users\\usman\\Projects\\frontend-perception-engine`  
**Branch:** `exp/agent-face-simple`  
**Base:** `main`

**Resume prompt for next agent:**

> @ docs/handoff/2026-08-04-CHAT-CONTEXT.md and the QUERY-INDEX / RECENT-QUERIES siblings.  
> We are on `exp/agent-face-simple` at **1.2.0.dev67**.  
> Next: [slim envelopes | maturity flags | live smoke of perception_step | push/PR].  
> Do not re-litigate fidelity/pulse unless broken.

---

## 1. Current product state (authoritative)

### Versions in this arc

| Version | What it did | Status |
|---------|-------------|--------|
| `1.2.0.dev62–dev63` | Phase/packs, observe design packs, prefetch, soft-spot fixes | Earlier in arc |
| `1.2.0.dev64` | Inspiration digest / look_lock (multi-ref + structured borrow) | Shipped earlier |
| `1.2.0.dev65` | Continuous HTTP inspiration pulse | Shipped earlier |
| `1.2.0.dev66` | Chrome fidelity 80–90%, claim-sticky resources/consistency/fidelity, parallel_batch | `0b28b2c` pushed |
| **`1.2.0.dev67`** | **P0s: `perception_step`, hard `implement_blocked`, health `data.doctor`** | **Current head of this handoff** |

### Product thesis (unchanged through the whole chat)

- MCP = **deterministic evidence runtime** (no LLM inside). Host coding agent = brain.
- Face contract = **`agent_summary.card`** (`class`, `evidence_band`, `pack`, `phase`, `implement_blocked`, `next`, `next_args`, `owed`, `claim_ok`, `finish`, `can_parallel`, `parallel_batch`, `inspiration_pulse`, `creative_kit`, …).
- Recurring user pain: with one internet image agents make a pro near-copy; with full MCP they clear verify/`claim_ok` without matching chrome, under-LOOK inspiration, underuse resources/consistency, drown in ceremony/huge envelopes.
- Desired outcome: **~80–90% visual copy** of liked refs + taste tweaks; **forced real use** of component/resources/design/consistency; **fast parallel HTTP** (not serial browser ceremony).

### Intended host loop (current)

```
perception_health({{url, intent}})
  → read data.doctor.fix_commands if critical fails
→ perception_session_start({{base_url, intent}})
→ loop: perception_step({{session_id}})   # Tier-0 = run card.next
  → when card.can_parallel / parallel_batch: fire HTTP intel concurrently
     creative_assets ∥ select_component_foundation ∥ inspiration_pulse ∥
     design_graph_refresh / consistency_audit
  → browser tools stay ONE at a time (flight lock / queue)
→ VF purpose=inspiration: LOOK many blobs; primary_ref_ids + borrow[{{ref_id,section,idea}}]
→ implement chrome as near-copy + apply assets
→ VF purpose=design + chrome_fidelity[{{zone:nav|aside|main|composer, fidelity, ref_id}}]
→ consistency → verify (sections if required) → claim only if claim_ok
```

**Hotfix / forms:** lean path — no inspiration/fidelity ladder.

### What `dev66` enforces

- **Chrome fidelity:** zones `nav|aside|main|composer` (aliases header/sidebar/thread/…); mean ≥80; each ≥75; bind `ref_id`. Soft judgment=ok without zones → next_action attest; family `fidelity` unpaid.
- **Claim-sticky after verify:** `inspiration_extract`, `resources`, `consistency`, `fidelity` still block `claim_ok` if unpaid.
- **Pack critical** (greenfield/redesign heavy+): includes component, resources, consistency, fidelity.
- **Parallel HTTP:** `PARALLEL_INTEL_FAMILIES`; card surfaces `can_parallel` + `parallel_batch`.
- **Inspiration pulse:** background HTTP scout; `perception_inspiration_pulse` reads ring; pause after look_lock.

### What `dev67` enforces (experience-report P0s)

1. **`perception_step`** — executes `card.next` + merges `next_args` / overrides. Prefer over inventing nearby tools. Nested step refused. `dry_run` resolves only.
2. **Hard `implement_blocked`** — MCP refuses while blocked:
   - `perception_execute_script`
   - `perception_execute_actions`
   - `perception_integrate_component`
   - `perception_design_review(mode=ship)`
   Short error with `owed_top` + `next` / `next_args`. Observe/verify/inspiration/resources still allowed. (Host IDE file edits cannot be blocked.)
3. **Health doctor** — `perception_health` → `data.doctor`:
   - checks: app_url, browser_use, chromium, node, repo_root, version_skew, browser_manager
   - `fix_commands` copy-paste list
   - `primary_browser: "perception"` (don’t dual-drive Cursor browser / Playwright MCP)

**Tests:** `tests/test_p0_step_block_doctor.py` (11 passed when shipped).  
**Research notes:**  
- `docs/research/2026-07-31-chrome-fidelity-parallel-intel.md`  
- `docs/research/2026-08-04-p0-step-block-doctor.md`  
- Also: pulse / look_lock / parallelism under `docs/research/2026-07-30-*.md`

---

## 2. Key code map (resume coding here)

| Concern | Path under `src/navigation/` |
|---------|------------------------------|
| Face card / claim_ok / finish | `coordination_intelligence/planning/coordinator_card.py` |
| Evidence packs / sticky / parallel families | `coordination_intelligence/planning/evidence_pack.py` |
| Chrome fidelity eval | `coordination_intelligence/planning/chrome_fidelity.py` |
| Inspiration look_lock | `coordination_intelligence/planning/inspiration_look_lock.py` |
| Inspiration pulse loop | `coordination_intelligence/planning/inspiration_pulse_loop.py` |
| Portfolio unpaid (resources/consistency/fidelity) | `coordination_intelligence/planning/episode_portfolio.py` |
| VF purpose schemas / fidelity next_actions | `visual_browser_intelligence/visual/visual_feedback_policy.py` |
| Hard implement gate | `execution_runtime/policies/implement_hard_gate.py` |
| Step resolver | `execution_runtime/policies/perception_step.py` |
| Executor hooks (gate + step) | `execution_runtime/executor.py` |
| Browser flight lock | `execution_runtime/policies/browser_flight.py` |
| Health doctor | `mcp/health_doctor.py` |
| Health handler | `mcp/handlers.py` (`handle_health`, `handle_step`) |
| Tool schemas | `mcp/tools.py` |
| Agent instructions | `mcp/instructions.py` |
| VERSION | repo `VERSION` + `pyproject.toml` |

Workspace agent rule: `.cursor/rules/frontend-perception-mcp.mdc`.

---

## 3. Whole-chat narrative (eras)

This panel spans founding (**Jul 8**) through P0 doctor + handoff (**Aug 4**).  
**{len(records)}** user messages · **{len(unique)}** unique asks. Verbatim wording: QUERY-INDEX + RECENT-QUERIES.

### Activity by day

{day_block}

### Era story + representative asks

{eras_block}

### Core problem restated in your words (recurring)

- One internet image + “build this” → coding agent makes a **pro near-copy**.
- Full MCP ladder → agents **call** inspiration/components/resources/verify, clear `claim_ok`, but **sidebar/header stay old**; LOOK only 1–2 of many refs; soft mood instead of chrome copy.
- MCP is excellent at preventing fake “done”; weaker as a **tasteful art director**. No LLM in MCP = it cannot invent “navbar looks old vs refs” unless the host files that in VF.

### Live redesign feedback (GPT Clone session, ~Jul 30–31)

- Used many intel families; verify rigorous; grade ~**B−** (outcome A−, process C+).
- Pros: evidence gates, section crops, assets when used.
- Cons: huge envelopes, sticky ceremony (initiative/very_heavy for polish), inspiration session drift, serial verifies, consistency = token math not taste.
- Ask that followed: **force 80–90% visual copy + force use of component/resources/design/consistency, fast/not serial** → `dev66`.

### Agent experience report (Aug 4)

File on old machine: `c:\\Users\\usman\\Downloads\\frontend-mcp-experience-report.md`

Praised: deterministic MCP, card OS, observe→resolve→verify, claim discipline, parallel HTTP model.  
Hurt: tool sprawl, soft ceremony, fat envelopes, env footguns, scaffold looking like GA.  
Their P0s we implemented as **`dev67`:** Tier-0/`perception_step`, hard implement_blocked, health doctor.

### Size of codebase (approx, local Python count — no LLM)

- `src/**/*.py`: ~**81k LOC**, ~**662k** tiktoken cl100k tokens  
- Product Python (`src+tests+scripts+evals`): ~**1.06M** tokens  
- Full-repo multi-million line counts = artifacts/venvs/junk — ignore for “product size”

### Git note from this panel

- Pushed: `0b28b2c` (`dev66`) on `exp/agent-face-simple`.
- `dev67` + this expanded handoff should be on the same branch after push.
- Do **not** casually commit: `ForOpenCode/`, logs, marketing drafts, shortcuts, `evals/results/`, `dist_locked_old/`, `.cache/`, etc.

---

## 4. Explicitly NOT done yet (next backlog)

| Priority | Item |
|----------|------|
| P1 | Slim envelopes: `card` always; large `data` on demand (`scan_get`-style) |
| P1 | Tool `maturity: ga \\| beta \\| scaffold` on schema + card; prefetch only GA/beta |
| P1 | Resolver eval CI (route→file, component→file) |
| P2 | Stronger Tier-0 surface (hide experimental SEO/Figma until connected) |
| P2 | Parallel batch *executor* tool (not just `can_parallel` hints) |
| P2 | Exclude `references/` / `research/` from default resolve/index |
| Soft | Right-size polish defaults (initiative/very_heavy too sticky for CSS tweaks) |
| Soft | Inspiration session ID drift (`inspiration_session_not_found`) reliability |

**Do not** add another intelligence module before thinning degrees of freedom.

---

## 5. How to talk to the next agent

Paste or `@` this file **plus** the query index if they need wording fidelity, and say:

> Resume from `docs/handoff/2026-08-04-CHAT-CONTEXT.md`. On `exp/agent-face-simple` at `1.2.0.dev67`. Next: [slim envelopes | maturity flags | push/PR | live test perception_step]. Do not re-litigate the fidelity/pulse design unless broken.

### Smoke after MCP reload

1. `perception_health({{url, intent}})` → confirm `data.doctor` present.  
2. `perception_session_start({{base_url, intent}})` → read `agent_summary.card`.  
3. `perception_step({{session_id}})` → should run `card.next`.  
4. On greenfield/redesign with `implement_blocked=true`, try `perception_execute_script` → must get `implement_blocked` refuse with `owed_top`.

---

## 6. Related docs already in repo

- `docs/research/2026-07-30-continuous-inspiration-pulse.md`  
- `docs/research/2026-07-30-inspiration-digest-enforcement.md`  
- `docs/research/2026-07-30-mcp-parallelism-architecture.md`  
- `docs/research/2026-07-31-chrome-fidelity-parallel-intel.md`  
- `docs/research/2026-08-04-p0-step-block-doctor.md`  
- `docs/AGENT_FACE_COORDINATION.md`  

Local transcript (this machine only):  
`C:\\Users\\usman\\.cursor\\projects\\c-Users-usman-Projects-frontend-perception-engine\\agent-transcripts\\c573bbec-56b1-4ce1-9d4f-eba50f9a5c08\\c573bbec-56b1-4ce1-9d4f-eba50f9a5c08.jsonl`

---

## 7. One-line memory

**Card-driven frontend agent OS:** evidence before claim, ~80–90% visual copy via fidelity + sticky resource/consistency, parallel HTTP intel, and as of **dev67** a **step tool + hard mutation block + health doctor** — next win is thinner envelopes and less tool sprawl, not more features.
"""

    MAIN_OUT.write_text(main_doc, encoding="utf-8")
    print("Wrote", MAIN_OUT, MAIN_OUT.stat().st_size)
    print("Wrote", INDEX_OUT, INDEX_OUT.stat().st_size)
    print("Wrote", RECENT_OUT, RECENT_OUT.stat().st_size)
    print("unique", len(unique), "total", len(records))


if __name__ == "__main__":
    main()
