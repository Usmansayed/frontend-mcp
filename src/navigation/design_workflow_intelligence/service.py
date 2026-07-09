"""Design workflow intelligence service facade."""
from __future__ import annotations

from navigation.design_workflow_intelligence.flows.flow_graph import FLOWS, FlowGraph
from navigation.design_workflow_intelligence.flows.runner import FlowRunner
from navigation.design_workflow_intelligence.state.state_manager import StateManager


class DesignWorkflowService:
	"""Facade for multi-step flows, auth gates, and workflow state."""

	FLOWS = FLOWS

	def __init__(self) -> None:
		self.runner = FlowRunner()
		self.state = StateManager()
