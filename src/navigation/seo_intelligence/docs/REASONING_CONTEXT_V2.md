# reasoning_context_v2 — Frozen Public Contract

**ADR-027** | Schema version: **`2.0`** | Status: **FROZEN** (Sprint 1)

> Everything downstream consumes this structure. No module bypasses it.

## Pipeline

```text
Providers
      │
      ▼
Normalized Evidence (deterministic IDs)
      │
      ▼
Page Graph
      │
      ▼
Audit Snapshot
      │
      ▼
reasoning_context_v2
      │
 ┌────┴────┐
 │         │
AI      Deterministic
Reasoning  Fallback
 │         │
 └────┬────┘
      ▼
Recommendations
      ▼
Metric Verification
```

## Top-level schema

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `"2.0"` | Contract version — bump only with ADR |
| `meta` | object | `audit_id`, `snapshot_id`, `previous_audit_id`, `mode`, `collected_at`, `website_url` |
| `providers` | object | Provider connection status this audit |
| `pages` | array | Page entities — primary reasoning unit |
| `site_correlations` | array | Cross-page hypotheses only |
| `reasoning_units` | array | **AI consumption bundles** (deterministic today) |
| `snapshot_diff` | object \| null | Delta vs `previous_audit_id` |
| `verification_state` | object | Per-recommendation verification history |
| `knowledge_graph` | object | Graph summary counts |
| `evidence_count` | number | Total evidence items |
| `constraints` | object | `must_cite_evidence_ids`, `must_not_invent_metrics`, `ai_consumes_this_only` |
| `sprint` | `"intelligence_v2"` \| `"ai_reasoning_v3"` | Enrichment marker; `ai_reasoning_v3` when LLM recommendations validated |
| `ai_reasoning` | object | Sprint 3 — `source`, `draft_count`, `validated_count`, `validation_errors`, `degraded` |
| `ai_readiness` | object \| absent | AI Visibility layer summary — `schema_version`, `overall_score`, `analyzers_run`, `analyzers_skipped`, `dimensions{analyzer_id → {status, score, evidence_id, source_evidence_ids, rationale_url}}`, `sources_documented_in`. Absent when `include_ai_visibility=false`. |

## Page entity (`pages[]`)

| Field | Description |
|-------|-------------|
| `url` | Canonical page URL (empty for `__site__`) |
| `page_key` | Graph key (`__site__` or normalized URL) |
| `evidence_ids` | Stable evidence IDs on this page |
| `evidence` | Full evidence payloads |
| `metrics` | Extracted: `lcp_ms`, `cls`, `index_verdict`, `http_status`, `queries[]`, `sessions` |
| `correlations` | URL-scoped correlation hypotheses |
| `confidence` | Composed confidence for page evidence |
| `codebase_hints` | Sprint 2 — likely code locations (heuristic + optional CRG search) |
| `browser_code_links` | Sprint 2 — `scan_id` + rendering evidence IDs → `likely_files` |
| `impact` | Sprint 2 — traffic-weighted impact score for page evidence |

## Reasoning unit (`reasoning_units[]`)

| Field | Description |
|-------|-------------|
| `unit_id` | `ru:{page}:{correlation_id}` |
| `page_url` | Target URL |
| `kind` | `cross_analysis`, `opportunity`, `development_practice`, … |
| `title`, `summary`, `root_cause`, `business_impact` | Human + LLM readable |
| `evidence_ids` | Required citations |
| `correlation_id` | Stable hypothesis ID |
| `metrics` | Page metrics snapshot |
| `confidence` | Composed score + breakdown |
| `impact` | Traffic-weighted impact score |
| `codebase_hints` | Likely fix locations from codebase bridge |
| `constraints` | `must_cite_evidence_ids`, `must_not_invent_metrics` |

## Stable evidence IDs

```text
ev:{provider_id}:{kind}:{fingerprint}

fingerprint = sha256(page_url + kind + normalized_title + source_ref + metric_key)[:12]
```

Same issue on the same page → same ID across audits.

## Composed confidence

```text
confidence.score =
    provider_agreement
  × data_freshness
  × metric_strength
  × sample_size_factor
```

Exposed in `confidence.composition` and `confidence.explanation`.

## Consumers

| Consumer | Reads | Writes |
|----------|-------|--------|
| Deterministic fallback | `reasoning_units`, `pages` | Recommendations |
| Host LLM (Sprint 3) | `reasoning_units` | Draft recommendations → validated → or deterministic fallback |
| Verification | `meta.audit_id`, evidence metrics | `verification_state` |
| Browser Intelligence | Enriches `pages[].evidence` | — |
| Codebase Intelligence (Sprint 2) | `pages[].codebase_hints` | — |

## Implementation

- Builder: `reasoning/context_v2.py` → `build_reasoning_context_v2()`
- Enrichment: `reasoning/enrichment.py` → `enrich_reasoning_context_v2()` (Sprint 2)
- Impact: `reasoning/impact.py` → `score_impact()`
- Codebase bridge: `reasoning/codebase_bridge.py` → `build_codebase_hints()`
- Dedupe: `recommendations/dedupe.py` → correlations, units, recommendations
- AI reasoning: `reasoning/ai_reasoner.py` → `try_ai_recommendations()` (Sprint 3)
- Validation: `reasoning/validate.py` → `validate_draft_recommendations()`
- LLM client: `reasoning/llm_client.py` → Bedrock (optional `[aws]` extra)
- Identity: `evidence/identity.py` → `stable_evidence_id()`
- Confidence: `reasoning/confidence.py` → `compose_confidence()`
- Graph: `knowledge/graph/store.py` → `save_audit_snapshot()`

**Do not** add recommendation logic that reads provider payloads directly. Extend v2 instead.
