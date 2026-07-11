# Research: NATURALIZE

**Paper:** [Learning Natural Coding Conventions](https://arxiv.org/abs/1402.4182) (Allamanis, Barr, Bird, Sutton — FSE 2014)  
**Code:** [mast-group/naturalize](https://github.com/mast-group/naturalize) (archived, Java)  
**Local clone:** `research/consistency_intelligence/repos/naturalize/`

---

## What problem does it solve?

Developers violate project-specific style conventions because conventions are **implicit** — they emerge from thousands of local decisions across a codebase. One third of code reviews mention convention violations. NATURALIZE learns conventions **from the codebase itself** and suggests renames/formatting that improve consistency with learned norms.

**Our parallel:** CSS/design values are the "identifiers." A project may use 16px padding everywhere except three legacy pages. NATURALIZE's insight is that we should learn **emergent norms**, not impose global design rules.

---

## How does it work internally?

### Pipeline

```text
Training corpus (project files)
        │
        ▼
Tokenization (language-specific: JavaTokenizer)
        │
        ▼
N-gram language model (default n=5)
        │
        ▼
Scope extraction (local variable, method, type scopes)
        │
        ▼
For each identifier in scope:
  substitute candidate names into n-grams
  score via log-likelihood under LM
        │
        ▼
Rank alternatives → Renaming suggestions with confidence
        │
        ▼
SnippetScorer: log-likelihood ratio vs current name
        │
        ▼
Threshold gate (PreCommitVerifier, default threshold 7)
```

### Key classes (reverse-engineered)

| Class | Role |
|-------|------|
| `AbstractIdentifierRenamings` | Core scoring: `buildRenamingModel()`, `calculateScores()`, `getRenamings()` |
| `BaseIdentifierRenamings` | Concrete LM-backed renamer |
| `InterpolatedIdentifierRenamings` | Interpolates n-gram + grammar priors (λ=0.35) |
| `IdentifierNeighborsNGramLM` | N-gram LM over token sequences |
| `SnippetScorer` | Log-likelihood ratio confidence per snippet |
| `PreCommitVerifier` | Blocks commit when confidence exceeds threshold |
| `FormattingRenamings` | Separate track for formatting conventions |

### Scoring algorithm (simplified)

For identifier `x` in scope `S` with context n-grams `N`:

1. Build multiset of alternative names from LM (`getAlternativeNamings`)
2. For each alternative `a`, score = Σ log₂(P(ngram | a substituted)) × count
3. Add scope priors (`addScopePriors`)
4. Normalize by n-gram count
5. Compare current name score vs best alternative → log-likelihood ratio = confidence

**94% top-1 accuracy** on identifier renaming; **14/18 patches accepted** on open source projects.

### Tools shipped

| Tool | Purpose |
|------|---------|
| `styleprofile` | Profile files, suggest renames |
| `buildlm` | Train serialized n-gram model from directory |
| `stylish?` / `naturalizecheck` | Pre-commit hook — abort if unnatural |
| `devstyle` | Eclipse plugin |

---

## Data structures

- **NGram&lt;String&gt;** — token sequence windows
- **Scope** — lexical scope (LOCAL, METHOD, TYPE) with AST bounds
- **Renaming** — `(name, score, ngramCoverage, scope)`
- **SnippetSuggestions** — `(score, SortedSet<Suggestion>)`
- **Serialized LM** — Kryo-serialized 5-gram model (~536MB pretrained)

---

## Algorithms worth borrowing

| Idea | Application to Consistency Intelligence |
|------|----------------------------------------|
| **Learn from corpus, don't dictate** | Style Discovery Engine mines computed styles + code, not Figma ideals |
| **N-gram / co-occurrence models** | "When `button.primary`, padding is usually 16px and radius 8px" |
| **Scope-aware priors** | Card padding norms ≠ button padding norms |
| **Log-likelihood ratio confidence** | "This 13px padding is 4.2σ unlikely given button context" |
| **Threshold-based surfacing** | Only report violations above confidence cutoff |
| **Exception tolerance** | Current value always in candidate set — must beat it to suggest change |
| **Pre-commit / incremental** | Re-learn on changed files; cache global model |

---

## What to avoid

| Weakness | Why |
|----------|-----|
| Java-only, AST-dependent | We need DOM + CSS + tokens, not source AST |
| Archived 2015 codebase | Use philosophy, reimplement in Python |
| Identifier renaming focus | We care about numeric/style property distributions |
| No explicit graph model | We need Project Design Graph for relationships |
| Black-box LM | Agents need **evidence** (which examples support the norm) |

---

## Fit in our MCP architecture

NATURALIZE is the **philosophical foundation** for the **Discovery Pipeline**:

```text
Knowledge Sources (snapshot, codebase, tokens, …)
        │
        ▼
Discovery Pipeline
  - cluster property values by component context
  - build probabilistic standards per (component × property)
  - score deviations with confidence
  - register exceptions (low-frequency but intentional)
        │
        ▼
Project Design Graph (learned standards as nodes/edges)
        │
        ▼
Knowledge API (agents query — never receive hardcoded mandates)
```

Design Sense consumes **learned standards + confidence**. Component Intelligence asks "does this component match project norms?" Browser Intelligence feeds observations.

**Not** a reviewer. **Not** an LLM. A **statistical convention learner** with explainable evidence.
