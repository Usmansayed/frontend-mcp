# Cluster Index — Meta-States

This file groups the 150 leaf states into **meta-states** (clusters) that share a fingerprint. Fingerprints are `(lifecycle_stage, situation_class, evidence_posture_signature, module_eligibility_signature)`. Clustering does not delete leaves — it adds a `parent_cluster` back-reference for the Coordination Layer to reason at either level.

Cluster IDs use kebab-case: `cluster.<domain>.<intent>`.

## Cluster catalog

### cluster.intent.conversation
- **Fingerprint:** S01, `new_feature`/`inspiration_needed`, all-unknown evidence, no MCP modules must run
- **Members:** landing.S01.intent.unclear, landing.S01.intent.described
- **Coordination hint:** Never invoke tools; refine natural language.

### cluster.discovery.bootstrap
- **Fingerprint:** S02, greenfield, evidence transitioning unknown→partial, only Framework/Codebase eligible
- **Members:** landing.S02.discovery.no_repo, landing.S02.discovery.stack_chosen, landing.S02.discovery.dev_server_up, landing.S02.discovery.first_route_rendering, landing.S02.discovery.blank_page_after_start, marketing.S02.discovery.legacy_repo_open
- **Coordination hint:** Framework detection cheap; run once and cache.

### cluster.design.reference_gathering
- **Fingerprint:** S03, `inspiration_needed`/`new_feature`, `design_source: unknown|partial`
- **Members:** landing.S03.design.no_design_source, landing.S03.design.inspiration_collected, landing.S03.design.direction_agreed_no_references, landing.S03.design.direction_agreed_with_references, landing.S03.design.reference_registry_captured_scaffold
- **Coordination hint:** Blob session hygiene mandatory (session_end).

### cluster.design.figma_pipeline
- **Fingerprint:** S03, Figma connection lifecycle
- **Members:** landing.S03.design.figma_expected, landing.S03.design.figma_connected, dssite.S09.consistency_cleanup.pdg_seeded_from_figma
- **Coordination hint:** Never loop reconnect; delegate to global.figma_connect_failed on error.

### cluster.design.review_and_snapshot
- **Fingerprint:** S03/S09 with snapshot present
- **Members:** marketing.S03.design.pdg_empty_snapshot_ready, marketing.S03.design.design_review_open, marketing.S09.consistency_cleanup.design_sense_findings
- **Coordination hint:** Design Sense is advisory-only; do not gate progress on it.

### cluster.architecture.plan
- **Fingerprint:** S04, planning-only
- **Members:** landing.S04.architecture.route_plan_pending, landing.S04.architecture.route_plan_ready
- **Coordination hint:** No tool needed to reach architecture state; conversation-heavy.

### cluster.component.acquisition_pipeline
- **Fingerprint:** S05, `component_replacement`
- **Members:** complib.S05.component_replacement.{query_vague, plan_ready, candidates_ranked, zero_candidates, candidate_selected, integration_dry_run_report, integration_live_scaffold, repair_needed, provider_offline, license_check_pending}, complib.S07.component_replacement.integrated_and_verified, complib.S03.component_replacement.inspiration_fallback
- **Coordination hint:** Live install path is `mcp_ready: false`.

### cluster.feature.form_pipeline
- **Fingerprint:** S05→S07, form validation
- **Members:** saas.S05.new_feature.form_validation.v1, saas.S07.new_feature.form_validation.{invalid_path_verified, verified, blocked_by_auth}, admin.S07.functional_bug.form_regression
- **Coordination hint:** Invalid before valid (AGENT_GUIDE §4).

### cluster.feature.flow_pipeline
- **Fingerprint:** S05→S07, multi-step flows
- **Members:** saas.S05.new_feature.multi_step_flow.described, saas.S07.new_feature.multi_step_flow.{all_checkpoints_verified, checkpoint_failure}
- **Coordination hint:** MCP describes flow; agent executes and verifies each checkpoint.

### cluster.feature.data_ui
- **Fingerprint:** S05→S07, data table / chart / hero
- **Members:** admin.S05.new_feature.data_table.stub, admin.S06.new_feature.data_table.integrated, admin.S07.new_feature.data_table.verified, saas.S05.new_feature.chart_component.stub, landing.S05.new_feature.landing_hero.stub, landing.S07.new_feature.landing_hero.verified

### cluster.feature.navigation_change
- **Members:** marketing.S05.new_feature.navigation_change.v1, marketing.S07.new_feature.navigation_change.verified, marketing.S07.new_feature.change_scope_ready

### cluster.feature.auth_flow
- **Members:** saas.S05.new_feature.auth_flow.probing, saas.S07.new_feature.auth_flow.verified_and_state_saved, admin.S05.new_feature.modal_dialog.stub
- **Coordination hint:** state_save+restore is the reuse mechanism.

### cluster.feature.api_integration
- **Members:** saas.S06.new_feature.api_integration.failing, saas.S07.functional_bug.network_error_detected

### cluster.feature.resource_gap
- **Members:** landing.S06.resource_gap.icon_missing, landing.S06.resource_gap.icon_provisioned

### cluster.debug.signal_class
- **Fingerprint:** S07, blocking present
- **Members:** marketing.S07.ui_bug.{console_error_detected, visual_regression_detected, snapshot_investigation, hydration_mismatch, responsive_break, accessibility_regression, full_diagnosis_run, needs_framework_upgrade, user_report_no_repro, harden_via_regression}, saas.S07.functional_bug.{intermittent, race_condition}
- **Coordination hint:** Each signal class has a canonical playbook; verify loop retries capped.

### cluster.debug.iteration_target
- **Members:** dssite.S05.consistency_cleanup.applying_fix, marketing.S05.redesign.applying_fix
- **Coordination hint:** Same "apply → re-observe → verify" pattern regardless of finding source.

### cluster.quality.audit_cycle
- **Fingerprint:** S08, per-domain audit + findings + clean triad
- **Members:** marketing.S08.a11y_remediation.{audit_needed, findings_open, clean}, marketing.S08.perf_remediation.{audit_needed, findings_open, clean}, marketing.S08.best_practices.{audit_needed, findings_open, clean}, marketing.S08.lighthouse_seo_audit.findings
- **Coordination hint:** Perfectly parallelizable across pages; batch-audit-friendly.

### cluster.quality.session_mode
- **Members:** marketing.S08.audit_mode.rolling, marketing.S08.debug_mode.active
- **Coordination hint:** Session-scoped mode toggles; must be turned off deliberately.

### cluster.seo.audit_cycle
- **Fingerprint:** S08, SEO audit lifecycle
- **Members:** landing.S08.seo_campaign.{audit_needed, audit_completed_dev, fix_applying, re_audit_after_fix, ai_readiness_reviewed, ai_visibility_disabled}, marketing.S08.seo_campaign.{audit_needed, audit_completed_pro, audit_diff_open}, ecom.S08.seo_campaign.{pro_mode.needs_auth, ecommerce_indexability_check}, blog.S08.seo_campaign.{content_gap, content_gap_verified}
- **Coordination hint:** Persistent SEO graph enables audit.diff; Coordination Layer should prefer diff over full audit.

### cluster.consistency.audit_cycle
- **Fingerprint:** S09, PDG lifecycle
- **Members:** dssite.S09.consistency_cleanup.{pdg_empty, pdg_seeded_from_snapshot, pdg_seeded_from_figma, audit_findings_open, no_deviation_detected, multi_page_scan, propose_fix_open, exception_documented, token_drift_detected, standards_updated, knowledge_query_result, knowledge_query_empty}, marketing.S09.consistency_cleanup.token_import_pending_scaffold, complib.S09.consistency_cleanup.api_stability_check
- **Coordination hint:** Empty PDG blocks audit/assess/propose_fix — refresh first.

### cluster.release.baseline_and_staging
- **Members:** marketing.S10.release_prep.{regression_baseline_capture, baseline_stored, staging_verify, staging_verified, staging_regression, multi_page_smoke_test, baseline_stale, code_review_pending, env_misconfig_pre_release}

### cluster.production.live_and_incidents
- **Members:** marketing.S11.production.{live_and_monitored, hotfix_requested, hotfix_deployed, dependency_upgrade_offered, drift_scheduled_reaudit, user_report_received, pdg_stale_refresh_scheduled, rollback_required, documentation_update}, ecom.S11.production.checkout_incident
- **Coordination hint:** Hotfix path may compress F09→F04→F07 stages.

### cluster.migration.framework_or_redesign
- **Members:** marketing.S12.framework_migration.{plan_ready, incremental_progress, big_bang_progress, completed, rollback} → migration.rollback, marketing.S12.redesign.{baseline_before, per_page_swap, completed}, complib.S12.migration.consumer_notification, legacy.S12.legacy_maintenance.dependency_upgrade

### cluster.global.recovery
- **Fingerprint:** Sxx_any, cross-cutting recovery
- **Members:** all 12 states in `global.Sxx.*`
- **Coordination hint:** Every non-terminal state in F01–F11 lists one or more of these as failure_states.

---

## Cluster totals

- **~25 clusters** capture the 150-state graph.
- Cluster count sits at the lower end of the 40–60 target from the plan, because our states are already fairly high-signal (variants that were purely cosmetic were pruned during enumeration). Splitting further would risk over-fragmentation.

## Coordination Layer implications

- Coordination decisions can operate at the cluster level for planning ("we're in cluster.quality.audit_cycle") and drill to the leaf for execution.
- The `global.recovery` cluster is the safety net — every planner branch must reference it.
- `cluster.seo.audit_cycle` and `cluster.quality.audit_cycle` are the largest; suggests dedicated sub-planners for each.
