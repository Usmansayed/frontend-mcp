# Report 03 — State Space Methodology

Defines the state schema, ID convention, exploration-log format, and the graph index shape. Every YAML under `coordination_layer/research/state_space/states/` conforms to this schema.

---

## State ID convention

```
{archetype_abbrev}.{stage}.{situation}.{variant}
```

- `archetype_abbrev` — from `project_archetypes.yaml` (`landing`, `saas`, `ecom`, `blog`, `docs`, `admin`, `dssite`, `complib`, `marketing`, `portfolio`) or `global` for cross-cutting states.
- `stage` — one of `S01`..`S12` (see lifecycle ontology). Cross-cutting states use `Sxx`.
- `situation` — situation class from Axis E (or a compact synonym).
- `variant` — short suffix identifying the specific condition (`v1`, `v2`, or descriptive: `no_design_source`, `pdg_empty`, `verify_exhausted`).

Examples:

- `saas.S05.new_feature.form_validation.v1`
- `ecom.S08.seo_campaign.pro_mode.needs_auth`
- `global.Sxx.auth_gate.requires_human`
- `landing.S01.intent.unclear`

**IDs are stable.** Renames require a `discarded_as_duplicate_of` back-reference.

---

## State YAML schema

```yaml
# Required identity
state_id: string                     # unique, matches filename (without .yaml)
name: string                         # short human-readable label
description: |
  Multi-line prose describing the project condition.
mcp_ready: true | false              # if false, must include mcp_ready_gap reference

# Classification (Axes A–E)
project_archetype: string            # from project_archetypes.yaml site_class ids
project_maturity: M0 | M1 | M2 | M3 | M4 | M5 | M6
lifecycle_stage: S01_intent | ... | S12_evolution | Sxx_any
project_types: [string]              # optional secondary tags (csr, monorepo, existing_project, ...)
situation_class: string              # from Axis E

# Condition
current_project_condition: |
  Prose: what is true about the project right now.
entry_conditions: [string]           # what must hold to enter this state
exit_conditions: [string]            # what must hold to leave to a next state
state_confidence: high | medium | low | speculative

# Evidence (Axis C)
known_evidence:
  ui_runtime: unknown | partial | known | verified | regressed
  codebase: unknown | partial | known | verified | regressed
  design_source: unknown | partial | known | verified | regressed
  design_system: unknown | partial | known | verified | regressed
  seo: unknown | partial | known | verified | regressed
  quality: unknown | partial | known | verified | regressed
  assets: unknown | partial | known | verified | regressed
unknown_evidence: [string]           # explicit list of domain gaps to fill

# Intent
user_intents: [string]

# Transitions (semantic, NOT tool names)
possible_actions: [string]           # verbs
prerequisites: [string]              # non-evidence conditions (session, repo_root, etc.)
possible_next_states: [state_id]
failure_states: [state_id]           # at least one for non-terminal states
recovery_paths:                      # optional list, one per failure
  - from: state_id
    action: string
    notes: string | null

# Module eligibility (names from inventory report)
relevant_modules: [string]
modules_must_not_execute: [string]
dependencies: [string]               # e.g., browser_session, scan_id, repo_root

# Outputs and verification
expected_outputs: [string]
verification_requirements: [string]  # observable predicates only

# Clustering
parent_cluster: string | null        # meta-state id, filled in Phase 4
forest_id: F01 | F02 | ... | F12     # primary forest of origin

# Aspirational tagging
mcp_ready_gap: string | null         # non-null when mcp_ready: false; cites inventory section
notes: |
  Any research notes, references to AGENT_GUIDE sections, ADR ids.

# Provenance
discarded_as_duplicate_of: state_id | null
first_added_in: batch1 | batch2 | phase4
```

### Field rules

- **`possible_actions`** must be verbs describing what the project can *do* next, not tool calls. The Coordination Layer will later map these to tool sequences.
- **`possible_next_states`** may reference states in other forests. Non-existent references will be flagged by review.
- **`failure_states`** must all resolve — they either exist in another YAML or are `global.*` states from F12.
- **`verification_requirements`** must be observable predicates (URL match, text present, JS assertion, `agent_summary.blocking == []`).
- **`modules_must_not_execute`** must be justified against the anti-pattern catalog in Report 01.
- **When `mcp_ready: false`**, `mcp_ready_gap` cites the specific line in Report 01 (e.g., "Live component install/repair — inventory section 4.5, roadmap: v1.8").

### Terminal states

Terminal states satisfy at least one of:

- All `possible_next_states` are `null` or point to `done.*` terminal states.
- `failure_states` are limited to `global.session_lost` (session ended cleanly).
- `verification_requirements` all met and `blocking` empty.

---

## Exploration log entry format

Every branch we considered — including pruned ones — gets an entry under `coordination_layer/research/state_space/exploration_log/` as a dated markdown file.

```
# Exploration Log — Batch N — Forest FXX

## Branch: <short branch label>
- **Considered:** <state_id or hypothetical>
- **Origin:** <parent state_id>
- **Decision:** kept | merged | discarded
- **If discarded / merged:** cite target state and reason.
- **Assumption ties:** A-YYYYMMDD-XXX (from assumptions_log)
- **mcp_ready:** true | false
- **Notes:** <free text>
```

Discarded branches are still valuable — they document the "why not" that reviewers need.

---

## `state_graph_index.json` schema

Machine-readable summary maintained at `coordination_layer/research/state_space/state_graph_index.json`.

```json
{
  "version": 1,
  "generated_at": "YYYY-MM-DD",
  "counts": {
    "total_states": 0,
    "mcp_ready_true": 0,
    "mcp_ready_false": 0,
    "by_forest": { "F01": 0, "F02": 0 },
    "by_stage": { "S01_intent": 0 },
    "by_archetype": { "landing": 0 }
  },
  "nodes": [
    {
      "id": "state_id",
      "name": "short name",
      "forest_id": "FXX",
      "lifecycle_stage": "SNN_...",
      "archetype": "abbrev",
      "situation_class": "...",
      "mcp_ready": true,
      "parent_cluster": null
    }
  ],
  "edges": [
    {
      "from": "state_id",
      "to": "state_id",
      "kind": "next | failure | recovery",
      "action": "semantic verb (for kind=next)"
    }
  ],
  "clusters": [
    {
      "id": "cluster_id",
      "members": ["state_id", "state_id"],
      "fingerprint": {
        "lifecycle_stage": "...",
        "situation_class": "...",
        "evidence_posture_signature": "u/p/k/v/u/u/u",
        "module_eligibility_signature": "vb+fq+cb"
      }
    }
  ]
}
```

The index is generated after Phase 4. In Phases 2–3, only `nodes`/`edges` may exist and clusters is empty.

---

## Verification workflow (author-side)

Every state file must pass, before commit:

1. `state_id` matches filename.
2. All fields in the schema are present (nulls allowed where marked).
3. `mcp_ready: false` iff `mcp_ready_gap` non-null.
4. Every `possible_next_states` id either exists in `states/` or is scheduled for the next batch.
5. Every `failure_states` id is either a defined state or a `global.*` state from F12.
6. `verification_requirements` are observable predicates only.
7. `modules_must_not_execute` items are justified in the anti-pattern catalog (Report 01 § 8).

---

## Batch discipline

- **Batch 1 (forests F01–F06):** target ~90 states. Cross-forest links to F07–F12 may reference not-yet-written IDs; those IDs are reserved and finalized in Batch 2.
- **Batch 2 (forests F07–F12):** target ~90 states, plus all `global.*` states. On completion, all cross-forest links are validated.
- **Phase 4:** clusters, meta-states, merged states — no new leaves added except placeholder terminal states.
