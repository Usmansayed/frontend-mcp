"""Backward-compatible shim — re-exports from intelligence modules."""
from navigation.core.artifacts import artifact_dir, dump_json
from navigation.core.budget import OutputBudget, apply_dev_insights_budget, apply_observation_budget
from navigation.design_workflow_intelligence.exploration import ExplorationResult, explore_with_hints
from navigation.design_workflow_intelligence.feature_flags import FeatureFlagResult, probe_feature_flag
from navigation.design_workflow_intelligence.flows.flow_graph import FLOWS, FlowGraph
from navigation.design_workflow_intelligence.flows.runner import FlowRunResult, FlowRunner
from navigation.design_workflow_intelligence.state.auth_gate import AuthGateResult, check_auth_gate
from navigation.design_workflow_intelligence.state.route_guards import GuardProbeResult, probe_maze_guards
from navigation.design_workflow_intelligence.state.state_manager import BrowserStateSnapshot, StateManager
from navigation.component_intelligence.probes.form_probe import FormProbeResult, probe_validation_form
from navigation.component_intelligence.probes.file_upload import FileUploadResult, upload_test_file
from navigation.component_intelligence.probes.iframe_context import IframeProbeResult, probe_iframe_interaction
from navigation.component_intelligence.probes.rich_editors import RichEditorResult, fill_rich_editor
from navigation.component_intelligence.probes.virtual_scroll import VirtualScrollResult, scroll_until_item_found
from navigation.visual_browser_intelligence.live.websocket_observer import LiveDomResult, observe_live_dom
from navigation.visual_browser_intelligence.observe.observation import PageObservation, collect_observation
from navigation.visual_browser_intelligence.observe.preflight import (
	PreflightResult,
	preflight_check,
	wait_for_page_ready,
	wait_until,
	wait_until_async,
)
from navigation.visual_browser_intelligence.observe.scan import ScanResult, scan_page
from navigation.visual_browser_intelligence.verify.verification import SuccessCriteria, VerificationResult, verify
from navigation.frontend_quality_intelligence.dev_insights import (
	ApiCallEntry,
	DevInsights,
	DevInsightsCollector,
	PageMeta,
	probe_nested_collectors,
	probe_tier_a_dev_insights,
	probe_tier_b_dev_insights,
)

__all__ = [
	'ApiCallEntry',
	'AuthGateResult',
	'BrowserStateSnapshot',
	'FlowGraph',
	'FlowRunResult',
	'FlowRunner',
	'FormProbeResult',
	'DevInsights',
	'DevInsightsCollector',
	'ExplorationResult',
	'FeatureFlagResult',
	'FileUploadResult',
	'IframeProbeResult',
	'LiveDomResult',
	'RichEditorResult',
	'VirtualScrollResult',
	'FLOWS',
	'GuardProbeResult',
	'OutputBudget',
	'PageMeta',
	'PageObservation',
	'PreflightResult',
	'ScanResult',
	'StateManager',
	'SuccessCriteria',
	'VerificationResult',
	'artifact_dir',
	'check_auth_gate',
	'collect_observation',
	'dump_json',
	'preflight_check',
	'probe_nested_collectors',
	'probe_maze_guards',
	'probe_tier_b_dev_insights',
	'probe_tier_a_dev_insights',
	'probe_validation_form',
	'explore_with_hints',
	'fill_rich_editor',
	'observe_live_dom',
	'probe_feature_flag',
	'probe_iframe_interaction',
	'scan_page',
	'scroll_until_item_found',
	'upload_test_file',
	'verify',
	'apply_dev_insights_budget',
	'apply_observation_budget',
	'wait_for_page_ready',
	'wait_until',
	'wait_until_async',
]
