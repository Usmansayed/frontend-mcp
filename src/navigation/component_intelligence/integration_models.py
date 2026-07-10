"""Selection, integration, and validation models for Component Intelligence."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .models import ComponentCandidate, ComponentSearchResponse


class IntegrationStatus(str, Enum):
	COMPLETED = 'completed'
	FAILED = 'failed'
	DEGRADED = 'degraded'
	NOT_IMPLEMENTED = 'not_implemented'
	IN_PROGRESS = 'in_progress'


# --- Guidance models (structured; no fixed percentage scores) ---


@dataclass(slots=True)
class ModificationHint:
	category: str
	description: str
	from_value: str | None = None
	to_value: str | None = None
	selector: str | None = None
	file_glob: str | None = None
	required: bool = True

	def to_dict(self) -> dict[str, Any]:
		return {
			'category': self.category,
			'description': self.description,
			'from_value': self.from_value,
			'to_value': self.to_value,
			'selector': self.selector,
			'file_glob': self.file_glob,
			'required': self.required,
		}


@dataclass(slots=True)
class FrameworkGuidance:
	compatible: bool
	issues: list[str] = field(default_factory=list)
	compatibility_warnings: list[str] = field(default_factory=list)
	required_dependencies: list[str] = field(default_factory=list)
	peer_dependencies: list[str] = field(default_factory=list)
	required_configuration: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'compatible': self.compatible,
			'issues': list(self.issues),
			'compatibility_warnings': list(self.compatibility_warnings),
			'required_dependencies': list(self.required_dependencies),
			'peer_dependencies': list(self.peer_dependencies),
			'required_configuration': list(self.required_configuration),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class CodebaseGuidance:
	existing_patterns: list[str] = field(default_factory=list)
	reusable_utilities: list[str] = field(default_factory=list)
	existing_libraries: dict[str, str] = field(default_factory=dict)
	preferred_implementations: list[str] = field(default_factory=list)
	duplicate_risks: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'existing_patterns': list(self.existing_patterns),
			'reusable_utilities': list(self.reusable_utilities),
			'existing_libraries': dict(self.existing_libraries),
			'preferred_implementations': list(self.preferred_implementations),
			'duplicate_risks': list(self.duplicate_risks),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class DesignSenseGuidance:
	ux_recommendation: str = ''
	layout_recommendation: str = ''
	interaction_recommendation: str = ''
	notes: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'ux_recommendation': self.ux_recommendation,
			'layout_recommendation': self.layout_recommendation,
			'interaction_recommendation': self.interaction_recommendation,
			'notes': list(self.notes),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class ConsistencyGuidance:
	required_modifications: list[ModificationHint] = field(default_factory=list)
	token_adjustments: list[ModificationHint] = field(default_factory=list)
	spacing_adjustments: list[ModificationHint] = field(default_factory=list)
	typography_adjustments: list[ModificationHint] = field(default_factory=list)
	color_adjustments: list[ModificationHint] = field(default_factory=list)
	radius_adjustments: list[ModificationHint] = field(default_factory=list)
	shadow_adjustments: list[ModificationHint] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def all_adjustments(self) -> list[ModificationHint]:
		return (
			self.required_modifications
			+ self.token_adjustments
			+ self.spacing_adjustments
			+ self.typography_adjustments
			+ self.color_adjustments
			+ self.radius_adjustments
			+ self.shadow_adjustments
		)

	def to_dict(self) -> dict[str, Any]:
		return {
			'required_modifications': [m.to_dict() for m in self.required_modifications],
			'token_adjustments': [m.to_dict() for m in self.token_adjustments],
			'spacing_adjustments': [m.to_dict() for m in self.spacing_adjustments],
			'typography_adjustments': [m.to_dict() for m in self.typography_adjustments],
			'color_adjustments': [m.to_dict() for m in self.color_adjustments],
			'radius_adjustments': [m.to_dict() for m in self.radius_adjustments],
			'shadow_adjustments': [m.to_dict() for m in self.shadow_adjustments],
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class SynthesisResult:
	"""Component Intelligence synthesis of all module guidance — no fixed weights."""

	eligible: bool
	summary: str
	strengths: list[str] = field(default_factory=list)
	concerns: list[str] = field(default_factory=list)
	rank_factors: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'eligible': self.eligible,
			'summary': self.summary,
			'strengths': list(self.strengths),
			'concerns': list(self.concerns),
			'rank_factors': dict(self.rank_factors),
		}


@dataclass(slots=True)
class CandidateGuidance:
	candidate_id: str
	framework: FrameworkGuidance
	codebase: CodebaseGuidance
	design_sense: DesignSenseGuidance
	consistency: ConsistencyGuidance
	synthesis: SynthesisResult

	def to_dict(self) -> dict[str, Any]:
		return {
			'candidate_id': self.candidate_id,
			'framework': self.framework.to_dict(),
			'codebase': self.codebase.to_dict(),
			'design_sense': self.design_sense.to_dict(),
			'consistency': self.consistency.to_dict(),
			'synthesis': self.synthesis.to_dict(),
		}


@dataclass(slots=True)
class FoundationSelection:
	chosen: ComponentCandidate
	guidance: CandidateGuidance
	runner_ups: list[ComponentCandidate] = field(default_factory=list)
	rationale: str = ''
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'chosen': self.chosen.to_dict(),
			'guidance': self.guidance.to_dict(),
			'runner_ups': [c.to_dict() for c in self.runner_ups],
			'rationale': self.rationale,
			'degraded': list(self.degraded),
		}


# --- Integration pipeline models ---


@dataclass(slots=True)
class DocumentationBundle:
	installation_steps: list[str] = field(default_factory=list)
	required_dependencies: list[str] = field(default_factory=list)
	peer_dependencies: list[str] = field(default_factory=list)
	required_configuration: list[str] = field(default_factory=list)
	tailwind_plugins: list[str] = field(default_factory=list)
	css_variables: list[str] = field(default_factory=list)
	fonts: list[str] = field(default_factory=list)
	icons: list[str] = field(default_factory=list)
	common_issues: list[str] = field(default_factory=list)
	breaking_changes: list[str] = field(default_factory=list)
	provider_notes: list[str] = field(default_factory=list)
	citations: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'installation_steps': list(self.installation_steps),
			'required_dependencies': list(self.required_dependencies),
			'peer_dependencies': list(self.peer_dependencies),
			'required_configuration': list(self.required_configuration),
			'tailwind_plugins': list(self.tailwind_plugins),
			'css_variables': list(self.css_variables),
			'fonts': list(self.fonts),
			'icons': list(self.icons),
			'common_issues': list(self.common_issues),
			'breaking_changes': list(self.breaking_changes),
			'provider_notes': list(self.provider_notes),
			'citations': list(self.citations),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class InstallationStep:
	action: str
	target: str = ''
	details: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {'action': self.action, 'target': self.target, 'details': dict(self.details)}


@dataclass(slots=True)
class InstallationPlan:
	steps: list[InstallationStep] = field(default_factory=list)
	install_commands: list[str] = field(default_factory=list)
	config_updates: list[dict[str, Any]] = field(default_factory=list)
	css_updates: list[dict[str, Any]] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'steps': [s.to_dict() for s in self.steps],
			'install_commands': list(self.install_commands),
			'config_updates': list(self.config_updates),
			'css_updates': list(self.css_updates),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class DependencyPlan:
	packages: list[str] = field(default_factory=list)
	peer_packages: list[str] = field(default_factory=list)
	install_commands: list[str] = field(default_factory=list)
	conflicts: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'packages': list(self.packages),
			'peer_packages': list(self.peer_packages),
			'install_commands': list(self.install_commands),
			'conflicts': list(self.conflicts),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class CompatibilityPlan:
	resolutions: list[str] = field(default_factory=list)
	adaptations: list[str] = field(default_factory=list)
	config_patches: list[dict[str, Any]] = field(default_factory=list)
	blockers: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'resolutions': list(self.resolutions),
			'adaptations': list(self.adaptations),
			'config_patches': list(self.config_patches),
			'blockers': list(self.blockers),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class InstallResult:
	status: str
	executed_commands: list[str] = field(default_factory=list)
	installed_files: list[str] = field(default_factory=list)
	error: str | None = None
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'status': self.status,
			'executed_commands': list(self.executed_commands),
			'installed_files': list(self.installed_files),
			'error': self.error,
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class AdaptationPatch:
	file_path: str
	description: str
	source_guidance: str = ''
	diff_preview: str = ''
	applied_modifications: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'file_path': self.file_path,
			'description': self.description,
			'source_guidance': self.source_guidance,
			'diff_preview': self.diff_preview,
			'applied_modifications': list(self.applied_modifications),
		}


@dataclass(slots=True)
class IntegrationArtifacts:
	documentation: DocumentationBundle | None = None
	installation_plan: InstallationPlan | None = None
	dependencies: DependencyPlan | None = None
	compatibility: CompatibilityPlan | None = None
	install: InstallResult | None = None
	adaptations: list[AdaptationPatch] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'documentation': self.documentation.to_dict() if self.documentation else None,
			'installation_plan': self.installation_plan.to_dict() if self.installation_plan else None,
			'dependencies': self.dependencies.to_dict() if self.dependencies else None,
			'compatibility': self.compatibility.to_dict() if self.compatibility else None,
			'install': self.install.to_dict() if self.install else None,
			'adaptations': [a.to_dict() for a in self.adaptations],
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class ValidationReport:
	passed: bool
	blocking: list[str] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)
	checks: dict[str, bool] = field(default_factory=dict)
	scan_id: str | None = None
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'passed': self.passed,
			'blocking': list(self.blocking),
			'warnings': list(self.warnings),
			'checks': dict(self.checks),
			'scan_id': self.scan_id,
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class FixPlan:
	issue: str
	actions: list[str] = field(default_factory=list)
	consulted_modules: list[str] = field(default_factory=list)
	documentation_refs: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'issue': self.issue,
			'actions': list(self.actions),
			'consulted_modules': list(self.consulted_modules),
			'documentation_refs': list(self.documentation_refs),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class RepairAttempt:
	attempt: int
	issue: str
	fix_plan: FixPlan
	validation: ValidationReport | None = None

	def to_dict(self) -> dict[str, Any]:
		return {
			'attempt': self.attempt,
			'issue': self.issue,
			'fix_plan': self.fix_plan.to_dict(),
			'validation': self.validation.to_dict() if self.validation else None,
		}


@dataclass(slots=True)
class IntegrationRequest:
	query: str = ''
	candidate_id: str | None = None
	repo_root: str = ''
	preview_url: str | None = None
	search_plan: dict[str, Any] | None = None
	max_repair_attempts: int = 3
	max_candidates_for_guidance: int = 12
	execute_install: bool = False
	execute_repairs: bool = False

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query,
			'candidate_id': self.candidate_id,
			'repo_root': self.repo_root,
			'preview_url': self.preview_url,
			'search_plan': self.search_plan,
			'max_repair_attempts': self.max_repair_attempts,
			'max_candidates_for_guidance': self.max_candidates_for_guidance,
			'execute_install': self.execute_install,
			'execute_repairs': self.execute_repairs,
		}


@dataclass(slots=True)
class IntegrationResult:
	status: IntegrationStatus
	request: IntegrationRequest
	search: ComponentSearchResponse | None = None
	selection: FoundationSelection | None = None
	integration: IntegrationArtifacts | None = None
	validation: ValidationReport | None = None
	repair_attempts: list[RepairAttempt] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'status': self.status.value,
			'request': self.request.to_dict(),
			'search': self.search.to_dict() if self.search else None,
			'selection': self.selection.to_dict() if self.selection else None,
			'integration': self.integration.to_dict() if self.integration else None,
			'validation': self.validation.to_dict() if self.validation else None,
			'repair_attempts': [a.to_dict() for a in self.repair_attempts],
			'degraded': list(self.degraded),
		}
