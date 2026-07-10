"""Registry of Design Sense provider adapters — split by objective vs subjective lanes."""
from __future__ import annotations

from ..models import ProviderContribution, ReviewLane, ReviewRequest
from .crit_rams.methodology import CritRamsMethodologyProvider
from .design_lint.methodology import DesignLintMethodologyProvider
from .knowledge.adapter import KnowledgeProvider
from .microsoft_review.workflow import MicrosoftReviewWorkflowProvider
from .open_design.adapter import OpenDesignProvider
from .protocol import DesignSenseProvider
from .uicrit.methodology import UICritMethodologyProvider


def objective_providers() -> list[DesignSenseProvider]:
	"""Deterministic: Design Lint, WCAG (future), math."""
	return [DesignLintMethodologyProvider()]


def subjective_providers() -> list[DesignSenseProvider]:
	"""Interpretive: Open Design, UICrit, Microsoft workflow, knowledge, Crit/Rams."""
	return [
		OpenDesignProvider(),
		MicrosoftReviewWorkflowProvider(),
		UICritMethodologyProvider(),
		KnowledgeProvider(),
		CritRamsMethodologyProvider(),
	]


def default_providers() -> list[DesignSenseProvider]:
	return objective_providers() + subjective_providers()


class ProviderRegistry:
	def __init__(
		self,
		*,
		objective: list[DesignSenseProvider] | None = None,
		subjective: list[DesignSenseProvider] | None = None,
	) -> None:
		self._objective = objective or objective_providers()
		self._subjective = subjective or subjective_providers()

	def list_providers(self) -> list[dict[str, str]]:
		out: list[dict[str, str]] = []
		for p in self._objective + self._subjective:
			out.append({'name': p.name, 'kind': p.kind, 'lane': p.lane})
		return out

	async def collect_lane(
		self,
		request: ReviewRequest,
		*,
		lane: str,
	) -> list[ProviderContribution]:
		providers = self._objective if lane == ReviewLane.OBJECTIVE.value else self._subjective
		return await _collect_providers(providers, request)

	async def collect_objective(self, request: ReviewRequest) -> list[ProviderContribution]:
		return await self.collect_lane(request, lane=ReviewLane.OBJECTIVE.value)

	async def collect_subjective(self, request: ReviewRequest) -> list[ProviderContribution]:
		return await self.collect_lane(request, lane=ReviewLane.SUBJECTIVE.value)

	async def collect_all(self, request: ReviewRequest) -> list[ProviderContribution]:
		obj = await self.collect_objective(request)
		sub = await self.collect_subjective(request)
		return obj + sub


async def _collect_providers(
	providers: list[DesignSenseProvider],
	request: ReviewRequest,
) -> list[ProviderContribution]:
	results: list[ProviderContribution] = []
	for provider in providers:
		try:
			results.append(await provider.contribute(request))
		except Exception as exc:
			results.append(
				ProviderContribution(
					provider=provider.name,
					degraded=[f'{provider.name}_error:{type(exc).__name__}'],
				)
			)
	return results
