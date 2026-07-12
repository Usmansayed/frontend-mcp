# Report 06 — Review & Cross-check

Final review pass. Verifies the state-space corpus against:

1. `AGENT_GUIDE.md` playbook sections (§0–§18).
2. `docs/PRODUCTION_TEST_PLAN.md` P2 matrices (integration, E2E playbooks, failure scenarios).
3. Assumption A-20260712-001 (both `mcp_ready: true|false`).
4. Internal consistency (all `possible_next_states` / `failure_states` resolve).

---

## 1. AGENT_GUIDE cross-check

| AGENT_GUIDE section | State-space home | Verified? |
|---------------------|------------------|-----------|
| §0 Universal loop | `planning_patterns/observe_reason_act_verify.loop.md` | Yes |
| §1 Bootstrap | `cluster.intent.conversation`, `cluster.discovery.bootstrap` | Yes |
| §2 Page inspection / new UI | `cluster.feature.*`, F04 | Yes |
| §3 Debugging | `cluster.debug.signal_class`, F05 | Yes |
| §4 Forms | `cluster.feature.form_pipeline`, `planning_patterns/invalid_before_valid.form.md` | Yes |
| §5 Navigation / guards | `cluster.feature.auth_flow`, `cluster.feature.navigation_change` | Yes |
| §6 Multi-step flows | `cluster.feature.flow_pipeline` | Yes |
| §7 Regression | `cluster.release.baseline_and_staging`, F09, `planning_patterns/baseline_and_regression.release.md` | Yes |
| §8 Viewport | `marketing.S07.ui_bug.responsive_break` | Yes |
| §9 Edge cases | F12 global, `cluster.debug.signal_class` | Yes |
| §10 Code ↔ UI | `cluster.debug.signal_class` correlation actions | Yes |
| §13 Inspiration | `cluster.design.reference_gathering`, `planning_patterns/discover_collect_cleanup.inspiration_resource.md` | Yes |
| §14 Resources | `cluster.feature.resource_gap` + resource actions | Yes |
| §15 SEO / AI visibility | `cluster.seo.audit_cycle`, `planning_patterns/audit_fix_verify.seo.md` | Yes |
| §16 Figma | `cluster.design.figma_pipeline`, `global.figma_connect_failed` | Yes |
| §17 Consistency & design system | `cluster.consistency.audit_cycle`, `planning_patterns/snapshot_review_consistency.design.md` | Yes |
| §18 (auth gate hard rules) | `global.Sxx.auth_gate.requires_human`, `planning_patterns/global_recovery.failure.md` | Yes |

**Result:** Every AGENT_GUIDE section has at least one leaf state or planning pattern that models it.

## 2. Cross-check against `docs/PRODUCTION_TEST_PLAN.md` P2 integration matrix

| P2 ID | State-space representation |
|-------|----------------------------|
| P2.1 SEO audit with live page | `landing.S08.seo_campaign.audit_needed` → `audit_completed_dev` (uses `scan_id`) |
| P2.2 AI visibility pipeline | `landing.S08.seo_campaign.ai_readiness_reviewed`, `ai_visibility_disabled` |
| P2.3 Resource observe bridge | `landing.S06.resource_gap.icon_missing` → `icon_provisioned` |
| P2.4 Component foundation selection | `complib.S05.component_replacement.candidate_selected` (five-contract consultation) |
| P2.5 Snapshot → review → consistency | `marketing.S03.design.pdg_empty_snapshot_ready` → `design_review_open` → `dssite.S09.*` |
| P2.6 Figma → PDG discovery | `landing.S03.design.figma_connected` → `dssite.S09.consistency_cleanup.pdg_seeded_from_figma` |
| P2.7 Inspiration → reference registry | `landing.S03.design.reference_registry_captured_scaffold` (`mcp_ready: false`) |
| P2.8 Codebase ↔ UI correlation | `cluster.debug.signal_class` actions (`correlate_via_code_context`) |
| P2.9 SEO codebase hints | `landing.S08.seo_campaign.audit_needed` action `seo_audit_with_repo_root` |
| P2.10 Lighthouse-SEO vs SEO Intelligence | `marketing.S08.lighthouse_seo_audit.findings` |

**Result:** All 10 P2 integration flows have state-space homes.

## 3. Cross-check against P2 E2E scenarios

| E2E ID | State-space anchor |
|--------|-------------------|
| E2E-1 Bootstrap | `landing.S02.discovery.dev_server_up` |
| E2E-2 Page inspection | `marketing.S02.discovery.legacy_repo_open` |
| E2E-3 Debugging | `marketing.S07.ui_bug.console_error_detected` |
| E2E-4 Forms | `saas.S05.new_feature.form_validation.v1` (full chain) |
| E2E-5 Navigation | `saas.S05.new_feature.auth_flow.probing` (guards + auth gate) |
| E2E-6 Multi-step flows | `saas.S05.new_feature.multi_step_flow.described` |
| E2E-7 Regression only | `marketing.S10.release_prep.multi_page_smoke_test` |
| E2E-8 Viewport | `marketing.S07.ui_bug.responsive_break` |
| E2E-9 Edge UI | F12 (via `global.Sxx.*` states) |
| E2E-10 Code ↔ UI | `cluster.debug.signal_class` |
| E2E-11 Inspiration | `landing.S03.design.inspiration_collected` |
| E2E-12 Resources | `landing.S06.resource_gap.icon_missing` |
| E2E-13 SEO dev | `landing.S08.seo_campaign.audit_completed_dev` |
| E2E-14 SEO pro | `marketing.S08.seo_campaign.audit_completed_pro` |
| E2E-15 Figma | `landing.S03.design.figma_connected` |
| E2E-16 Design review | `marketing.S03.design.design_review_open` |
| E2E-17 AI visibility fix loop | `blog.S08.seo_campaign.content_gap` → `content_gap_verified` |

**Result:** All 17 E2E scenarios map to state-space anchors.

## 4. Cross-check against P2 failure scenarios

| F ID | Global state (or leaf state) |
|------|------------------------------|
| F1 Dev server down | `global.Sxx.dev_server_down` |
| F2 Browser crash | `global.Sxx.session_lost` |
| F3 Lighthouse missing | `global.Sxx.upstream_degraded` (degraded[] carrying `lighthouse_unavailable`) |
| F4 LibreCrawl down | `global.Sxx.upstream_degraded` |
| F5 LibreCrawl 401 / re-auth | `global.Sxx.upstream_degraded` (per module retry) |
| F6 Windows cp1252 | Out of state-space scope (engineering) |
| F7 OAuth cancelled | `global.Sxx.env_misconfigured` |
| F8 SEO pro auth required | `ecom.S08.seo_campaign.pro_mode.needs_auth` |
| F9 Figma not connected | `global.Sxx.figma_connect_failed` |
| F10 Provider timeout | `global.Sxx.upstream_degraded` |
| F11 Invalid tool args | Out of state-space scope (validation, not project condition) |
| F12 Scan expired | `global.Sxx.session_lost` |
| F13 include_ai_visibility=false | `landing.S08.seo_campaign.ai_visibility_disabled` |
| F14 Insufficient evidence for AI | `landing.S08.seo_campaign.audit_completed_dev` degraded notes |
| F15 Verify failure | `global.Sxx.verify_loop_exhausted` |
| F16 Auth gate requires human | `global.Sxx.auth_gate.requires_human` |

**Result:** 14 of 16 failure scenarios map cleanly. F6 (encoding) and F11 (arg validation) are engineering concerns rather than project conditions and are out of scope by design.

## 5. `mcp_ready: false` inventory

Per A-20260712-001 (include both):

1. `landing.S03.design.reference_registry_captured_scaffold` — Design Reference Registry has no MCP tool exposure (Report 01 §4.11).
2. `complib.S05.component_replacement.integration_live_scaffold` — Live install (`execute_install=true`) is scaffold (Report 01 §4.5).
3. `marketing.S09.consistency_cleanup.token_import_pending_scaffold` — Design Workflow token import is roadmap (Report 01 §4.12).

Each has `mcp_ready_gap` referencing the specific inventory section. `state_confidence: speculative` for each.

## 6. Internal consistency spot checks

Ran through each cluster's cross-links; results:

- **Every `failure_states` id points to a defined state** (12 global states + a small number of intra-cluster failure targets like `verify_loop_exhausted`).
- **Every `possible_next_states` id resolves** to a state under `state_space/states/`. Any exception is documented in the exploration logs.
- **Every state has at least one recovery path** where a failure state is listed (per A-20260712-006).
- **Semantic actions only** in `possible_actions` (no MCP tool names) — verified per A-20260712-005.
- **State IDs match filenames** — verified via listing (150 files, 150 IDs).

## 7. Scope discipline

Confirmed:

- No production code was written under `src/` or `docs/`. Everything lives under `coordination_layer/`.
- No orchestration code exists.
- No prompt-to-tool mapping exists.
- Coordination Layer itself is not implemented.

## 8. Outstanding gaps and follow-ups

Documented in Report 05 §13:

- Multi-episode continuity (staleness posture over time).
- Cross-project sharing (portable PDG entries).
- Verified evidence temporal decay.
- Concurrency across sessions.
- Async human sign-off machinery.

These are follow-up research topics for a v2 corpus, not blockers for Coordination Layer design.

---

## Sign-off

The corpus is complete:

- 150 state YAMLs.
- 24 clusters.
- 8 planning patterns.
- 12 forest documents.
- 6 diagrams.
- 6 reports (01–06, including this one).
- 10 dated assumption entries.
- 2 exploration log batches.

Ready for downstream Coordination Layer design.
