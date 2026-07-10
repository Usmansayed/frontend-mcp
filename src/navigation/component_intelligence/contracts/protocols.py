"""Stable public contracts between Component Intelligence and peer modules."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..integration_models import (
	CodebaseGuidance,
	ConsistencyGuidance,
	DesignSenseGuidance,
	DocumentationBundle,
	FixPlan,
	FrameworkGuidance,
	FoundationSelection,
	ValidationReport,
)
from ..models import ComponentCandidate, ParsedQuery

CONTRACT_VERSION = '1.0'


@runtime_checkable
class FrameworkIntelligenceContract(Protocol):
	"""Framework compatibility, dependencies, and install documentation."""

	module_name: str

	async def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
	) -> FrameworkGuidance: ...

	async def fetch_install_documentation(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
		selection: FoundationSelection | None = None,
	) -> DocumentationBundle: ...

	async def plan_framework_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
		documentation: DocumentationBundle | None,
		repo_root: Path,
	) -> FixPlan: ...


@runtime_checkable
class CodebaseIntelligenceContract(Protocol):
	"""Project patterns, libraries, and architecture alignment."""

	module_name: str

	def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
		parsed_query: ParsedQuery | None = None,
	) -> CodebaseGuidance: ...

	def plan_codebase_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
		repo_root: Path,
	) -> list[str]: ...


@runtime_checkable
class DesignSenseIntelligenceContract(Protocol):
	"""UX, layout, and interaction recommendations."""

	module_name: str

	def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		parsed_query: ParsedQuery | None = None,
	) -> DesignSenseGuidance: ...

	def plan_design_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
	) -> list[str]: ...


@runtime_checkable
class ConsistencyIntelligenceContract(Protocol):
	"""Design-system alignment — modifications only, never hard reject."""

	module_name: str

	def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
		parsed_query: ParsedQuery | None = None,
	) -> ConsistencyGuidance: ...

	def plan_consistency_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
		repo_root: Path,
	) -> list[str]: ...


@runtime_checkable
class BrowserIntelligenceContract(Protocol):
	"""Runtime validation after component integration."""

	module_name: str

	async def validate_component_integration(
		self,
		*,
		preview_url: str | None,
		repo_root: Path,
		installed_files: list[str] | None = None,
	) -> ValidationReport: ...
