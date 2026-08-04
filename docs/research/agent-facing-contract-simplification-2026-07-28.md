# Research: Agent-facing MCP contracts — progressive disclosure vs our coordination layer

**Date:** 2026-07-28  
**Status:** Research + **experimental face landed on `exp/agent-face-simple`** — no cutover until A/B.  
**Experiment notes:** [`exp-agent-face-simple.md`](./exp-agent-face-simple.md)

---

## 0. Verdict (read this first)

Your instinct matches industry practice and our own surface audit:

| Claim | Evidence |
|-------|----------|
| Agents ignore long always-on contracts | Cursor / Claude Skills / MCP client docs all push **short always-on + on-demand depth** |
| Primary workflow should be very short | Anthropic Skills: L1 metadata always; L2 ≤ ~1.5–5k tokens; L3 on demand |
| Our agent surface is over-exposed | Always-on: rule (~530 words) + MCP instructions (~670 words) + ~80 tools + scoreboard fields; deep: 19 methodology URIs + 684-line AGENT_GUIDE |
| Simplify **interface**, not **brain** | Keep PSM / gate / portfolio / Ship Council internally; expose one card + class spine |

**Recommended next step (still no product cutover):** experimental branch that only changes agent-facing text + scoreboard shape; A/B the same frontend tasks; replace current contract **only if** the simplified face wins on measured adherence.

---

## 1. Research questions → answers

### 1.1 How much documentation should an MCP expose to an agent?

**Default: almost none beyond a bootstrap contract.**

Successful systems expose:

1. **Always-on (tiny):** when to use the system + 5–15 hard rules + how to get the next step.  
2. **On-demand:** full schemas, playbooks, edge cases — loaded when the task (or tool result) points at them.  
3. **Never by default:** encyclopedias, duplicate explanations of the same loop, research corpora.

MCP client best practices ([modelcontextprotocol.io — Client Best Practices](https://modelcontextprotocol.io/docs/develop/clients/client-best-practices.md)): progressive discovery of *tools* when definitions eat context; catalog → inspect → execute.

Anthropic Agent Skills ([engineering post](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)): three-level progressive disclosure — metadata → SKILL.md → linked files. Guidance: keep SKILL.md lean (~1.5–2k words / ~5k tokens); put edge cases in `references/`.

Cursor rules docs: keep rules focused; under ~500 lines ceiling, **instruction-style rules work best well under ~100 lines**; reference files instead of inlining manuals; start simple and add only for repeated mistakes.

**Practical budget for Frontend MCP (proposed):**

| Layer | Budget | Content |
|-------|--------|---------|
| Always-on (rule + MCP `instructions`) | **≤ ~400–600 words combined** (today ~1.2k overlapping) | Bootstrap + class switch + done check + hard fails |
| Per-turn scoreboard | **≤ ~150 tokens structured** | One next action, gate, owed ≤3 |
| Methodology resources | Unlimited, **one URI per task class** | Loaded when recommended |
| AGENT_GUIDE / deep docs | Human + rare agent lookup | Not in default path |

### 1.2 Should the primary workflow be very short, with deeper docs only when needed?

**Yes — this is the dominant pattern.**

| System | Always-on | Depth |
|--------|-----------|-------|
| Anthropic Skills | name + description | SKILL.md then references/scripts |
| MCP progressive disclosure | tool names / search | full schema on inspect |
| Cursor / OpenCode AGENTS.md | short project contract | linked docs / nested AGENTS.md |
| Successful MCP servers | short `instructions` + tool one-liners | resources for manuals |

Your desired shape is correct:

```text
If frontend → bootstrap
If greenfield → A, B, C
If redesign → X, Y, Z
Before implement → pay owed evidence
Before claim done → verify (+ ladder only if required)
```

That *is* a system-prompt-shaped contract. Depth (Ship Council, SpecDiff, residue, right-sizing theory) should not compete with it in the always-on channel.

### 1.3 How do successful MCPs guide agents without overwhelming them?

Patterns that recur:

1. **One voice for “what next”** — not five synonymous fields.  
2. **Hard rules as bullets**, not essays.  
3. **Tool results carry the next step** (so the agent doesn’t need the manual).  
4. **Class routing** (hotfix ≠ greenfield) instead of one mega-playbook.  
5. **Failure modes named once** (`ok ≠ verified`), not restated in every resource.  
6. **Progressive disclosure is opt-in depth**, not “read getting-started then 8 more guides before coding.”

Anti-patterns we see in weaker agent setups:

- Always-on walls of process  
- Multiple competing “next” signals  
- Asking the agent to reconstruct policy from scattered docs  
- Soft advisory that looks optional while claim fails later  

### 1.4 Should the contract look more like a system prompt with hard rules?

**Yes for Layer 1.** That matches Cursor always-apply rules, Claude Skills L2, and AGENTS.md conventions.

But:

- System-prompt style ≠ dump everything into the prompt.  
- Hard rules must be **few, checkable, and repeated in tool outcomes** (gate / verified).  
- Internal intelligence can stay rich; the *contract* stays dumb and sharp.

Best split:

| Kind of knowledge | Form |
|-------------------|------|
| Must never skip | Hard rule in always-on + enforced in gate/verify |
| Class procedure | Short spine in always-on + one resource |
| Edge cases / theory | Resource or code comments, not always-on |

### 1.5 When should information live in resources vs tool descriptions vs rules?

Industry consensus (MCP + Skills + Cursor):

| Location | Put here | Don’t put here |
|----------|----------|----------------|
| **Always-on rule / MCP instructions** | Apply-when, bootstrap, hard fails, done definition, “read scoreboard” | Full playbooks, tool catalogs, YAML theory |
| **Tool description** | What this tool does + critical params + one “when to use” | Entire workflow, philosophy, other tools’ jobs |
| **Tool result / scoreboard** | Next action, unpaid, gate, recommended resource URI | Essays |
| **Resources** | Class cards, deep workflows, eval harnesses | Anything required every turn |
| **Repo docs / research** | Humans, design history | Agent default context |

**Our bug today:** the same loop is restated in (a) cursor rule, (b) MCP instructions, (c) getting-started, (d) agent-coordination, (e) AGENT_GUIDE §0, (f) situation cards. Agents treat redundancy as noise and tunnel on one fragment.

### 1.6 How much context can agents realistically remember and consistently follow?

There is no fixed token number that guarantees obedience, but empirical product guidance converges:

- **Instruction density beats length** — short concrete rules > long polite manuals.  
- **Always-on attention is scarce** — Cursor community / practice: long always-apply rules get skimmed; Vercel-ish skill activation is unreliable when discovery is optional.  
- **Repeated mid-task signals beat preloaded manuals** — a 1-line `recommended_next` on every tool response outperforms a 600-line guide the agent read once.  
- **3–7 hard constraints** is a workable always-on set; beyond that, compliance drops unless enforced by tools.  
- **Working memory for procedures:** agents follow a **linear spine** (3–6 steps) better than a graph of optional ceremonies.

Implication for us: **enforce with gate/verify**; **remind with scoreboard**; **document in resources**. Do not rely on the agent “remembering” Ship Council + SpecDiff + unpaid ∩ owed ∩ right-sizing from bootstrap alone.

### 1.7 Best practices for progressive disclosure in MCPs

Synthesized checklist:

1. **L1 always-on:** triggers + hard rules + pointer to L2.  
2. **L2 activation:** one short workflow for the classified task (or `recommended_resource`).  
3. **L3 depth:** references only when the step needs them.  
4. **Prefer results over manuals:** next action in the envelope.  
5. **One recommended resource**, not a reading list of ten.  
6. **Don’t make bootstrap itself a book** — `getting-started` should be ≤1 screen.  
7. **Measure:** token cost of always-on + % of turns where agent ignored `recommended_next`.  
8. **Host thresholds:** if tool defs dominate context, use progressive tool discovery (host concern; we still help with short descriptions + groups).

---

## 2. What others do (brief)

| System | Agent-facing style | Lesson for us |
|--------|-------------------|---------------|
| **MCP clients (spec guidance)** | Progressive tool discovery when scale hurts | Our ~80 tools already stress hosts; instructions must stay short |
| **Anthropic Skills** | Metadata → short SKILL → references | Our “situation cards” should be L2, not always-on tables |
| **Claude Code** | Short CLAUDE.md / skills; tools do work | Don’t teach YAML corpus to the agent |
| **Cursor rules** | Short always-on; glob/agent-requested for depth | Shrink `.mdc`; stop duplicating MCP instructions |
| **AGENTS.md / OpenCode** | Project contract + links | One spine; deep docs linked, not inlined |
| **Progressive disclosure MCP blogs** | Catalog → get schema → invoke; docs on demand | Resources = depth; not mandatory pre-read marathon |

---

## 3. Audit of *our* agent-facing surface (today)

### 3.1 Always-on / near-always channels (duplicated)

| Artifact | Size (approx) | Role today |
|----------|---------------|------------|
| `.cursor/rules/frontend-perception-mcp.mdc` | ~84 lines / ~530 words | Short contract (good intent) |
| `MCP_INSTRUCTIONS` in `instructions.py` | ~100 lines / ~670 words | Server preamble — overlaps rule heavily |
| Tool list | ~80 `perception_*` tools | Large context tax on hosts |
| Scoreboard fields | coordinator + recommended_next + episode_card + engineering_strategy + unpaid + gate + backlog… | Multiple “next” voices |

### 3.2 Progressive / deep (good idea, too many doors)

| Artifact | Size | Issue |
|----------|------|-------|
| `methodology_resources.py` | **19 resource keys** | Getting-started already points at more cards + workflows |
| `perception://guide/*` | 8 situation cards | Right idea; still listed in always-on |
| `AGENT_GUIDE.md` | **684 lines / ~3.8k words / ~21 sections** | Explicitly “don’t load by default” but still competes as canon |
| Coordination research doc | ~300 lines | Human map (good) — not agent always-on |

### 3.3 Internal intelligence (keep)

Episode, PSM, portfolio unpaid, implementation gate, Ship Council, SpecDiff, inspiration routing, bridge refresh — **these should stay**. The problem is not that the brain is powerful; it’s that the **mouth talks too much in too many dialects**.

### 3.4 Where we’re likely over-complicating (ranked)

1. **Duplicate always-on prose** (rule ≈ instructions ≈ getting-started bootstrap).  
2. **Too many next-step signals** (agents tunnel on one; ignore unpaid). Already called out in inventory §9.  
3. **Reading list bootstrap** (getting-started → recommended_resource → situation card → maybe AGENT_GUIDE).  
4. **Done ladder always in face** even when light/hotfix should be “verify and stop.”  
5. **Owed ∩ class ∩ gate ∩ backlog** as agent-reconstructed math — should be precomputed as `owed: [...]`.  
6. **19 methodology URIs** for what is really **~5 spines** (greenfield / redesign / feature / hotfix / forms).  
7. **Invisible ceremony** (sticky design scope, advisory demotions) surprising agents mid-hotfix.

---

## 4. Proposed simplified design (agent-facing only)

### 4.1 Design principle

> **Internally powerful, externally a system prompt + one scoreboard card.**

```text
ALWAYS-ON (≤1 page)
  apply? → bootstrap → classify → follow class spine → done check

PER TURN (tool envelope)
  { next, owed[≤3], gate, stop_claim_unless }

ON DEMAND
  perception://spine/{class}   // one short card
  deep resources only if next says so
```

### 4.2 Target always-on contract (sketch — not implemented)

```text
Frontend MCP — you are the brain; MCP is evidence + scoreboard.

IF UI/CSS/design/forms/landing/dashboard/verify task:
  1. Bootstrap: health({url,intent}) → session_start → READ card.next / card.owed
  2. Classify: greenfield | redesign | feature | hotfix | forms
  3. Before large UI: pay card.owed (≤3). Do not invent layout while owed non-empty.
  4. One browser tool at a time. LOOK at screenshots.
  5. Before claim done: data.verified=true; if card.claim_extra set, finish those too.

Class spines (minimum):
  greenfield: inspiration → LOOK/lock → implement → verify
  redesign:   snapshot → LOOK → implement → verify
  feature:    observe affected → implement → verify
  hotfix:     observe blocking → fix → verify
  forms:      probe_form → invalid+valid verify

Hard fails:
  ok ≠ verified
  skip bootstrap on structural UI
  tunnel on gate.next while owed still has structural unpaid
  claim while gate prohibits claim_complete
```

Everything else (Ship Council theory, residue, SpecDiff math, right-sizing essays) → **L3 resources**, surfaced only when `card.next` or `card.claim_extra` says so.

### 4.3 Scoreboard: one card

Collapse to something like:

```json
{
  "card": {
    "class": "greenfield",
    "next": "perception_inspiration_collect",
    "owed": ["inspiration", "visual_feedback"],
    "gate": "blocked",
    "claim_extra": [],
    "resource": "perception://spine/greenfield"
  }
}
```

Keep full `engineering_strategy` internally / under a `detail` key for humans and rare deep agents — **not** competing for first glance.

### 4.4 What changes vs what does not

| Change in experiment | Do **not** change |
|----------------------|-------------------|
| Cursor rule text (shorten) | Coordination brain / YAML corpus |
| MCP `instructions` (align + shorten) | Tool implementations |
| Scoreboard presentation (one card) | Portfolio / gate computation |
| Methodology: 5 spines + archive rest | Inspiration / verify / VF engines |
| Getting-started: ≤40 lines | Episode / PSM persistence |

### 4.5 Mapping your desired prompt → our classes

| Your prompt | Spine |
|-------------|--------|
| If frontend → bootstrap | Always-on §1 |
| If greenfield → A,B,C | inspiration → LOOK → implement → verify |
| If redesign → X,Y,Z | snapshot → LOOK → implement → verify |
| Before implementation → evidence | `owed` must be empty or paid |
| Before claiming done → verify | `data.verified` + optional `claim_extra` |

---

## 5. Experimental plan (required before replacing anything)

### 5.1 Branch strategy

```text
main (control)  — current agent-facing contract
exp/agent-face-simple — only agent-facing diffs:
  - .cursor/rules/frontend-perception-mcp.mdc
  - src/navigation/mcp/instructions.py
  - optional: coordinator card serializer (add `card`, hide duplicates in agent_summary)
  - optional: perception://spine/* (5 short resources)
NO deletion of coordination_intelligence logic
NO removal of tools
```

Flag: `AGENT_FACE_SIMPLE=1` or build-time instructions variant so the same server binary can A/B.

### 5.2 Task battery (same prompts both faces)

Minimum 6 tasks × 2 faces (ideally 2 model hosts if available: Cursor + one other):

| ID | Class | Prompt sketch |
|----|-------|---------------|
| T1 | greenfield | New landing page for X — distinctive, brand-first |
| T2 | redesign | Match this mockup / redesign hero of existing page |
| T3 | feature | Add pricing section to existing page |
| T4 | hotfix | Fix overlapping button on mobile |
| T5 | forms | Build / fix checkout or login validation |
| T6 | polish | Tighten spacing on existing dashboard KPI row |

Use the **same app URL**, same model settings, fresh chat per run.

### 5.3 Metrics (compare control vs simple)

| Metric | How to score | Win condition for simple |
|--------|--------------|--------------------------|
| **MCP tool usage** | Count perception_* calls; bootstrap within first 3 tool calls? | Higher early bootstrap rate |
| **Workflow adherence** | Checklist: bootstrap, class-appropriate evidence before large UI, verify before claim | Higher % steps hit |
| **Ignored recommendations** | Times `card.next` / `recommended_next` ≠ next tool (allow explore±1) | Lower ignore rate |
| **UI quality** | Blind rubric 1–5 (hierarchy, brand, verify-backed, no false-green) by human | ≥ control |
| **Time / turns to verified** | Wall + agent turns to first `data.verified=true` | ≤ control or better quality at similar cost |
| **False-green claims** | Claimed done without verified / while gate blocked | Lower |
| **Token / doc load** | resources/read count + chars of always-on | Lower always-on; not necessarily fewer tools |

**Decision rule:** ship simplified face only if it wins on adherence + false-green **without** losing UI quality ≥1 rubric point on average across the battery.

### 5.4 What we will *not* conclude from one run

- One lucky greenfield  
- “Feels better” without metrics  
- Deleting Ship Council because a hotfix got faster  

### 5.5 Execution order (when you say go)

1. Freeze this research as the plan.  
2. Create `exp/agent-face-simple`.  
3. Implement **only** face changes.  
4. Run control battery → record JSON.  
5. Run simple battery → record JSON.  
6. Write compare report; decide cutover / iterate / abort.

---

## 6. Risks of over-simplifying

| Risk | Mitigation |
|------|------------|
| Agents skip inspiration again | Keep inspiration on `owed` for greenfield; gate blocks broad UI |
| Hotfix still hits sticky design | Face must show `claim_extra` clearly; consider demoting sticky in light tiers later (separate experiment) |
| Hosts that don’t load cursor rules | MCP instructions must carry the same short spine |
| Losing tribal knowledge | Archive AGENT_GUIDE as L3 `perception://archive/agent-guide` |

---

## 7. Bottom line

- Research supports **short always-on + progressive depth + one next signal**.  
- Our coordination *inventory* already diagnosed the same overbuild (§9–10 of the companion doc).  
- Your proposed system-prompt shape is the right external UX.  
- **Do not replace the coordination layer yet** — replace the **face**, measure, then decide.

**Ready when you are:** create `exp/agent-face-simple` and implement the face-only diff for the A/B battery. No cutover without the compare report.
