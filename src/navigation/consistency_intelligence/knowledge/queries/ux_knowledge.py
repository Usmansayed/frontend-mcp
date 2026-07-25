"""UX Knowledge Brain retrieval query — ForOpenCode graph traversal."""
from __future__ import annotations

from typing import Any

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph
from navigation.ux_knowledge.influence_log import log_retrieval_influence
from navigation.ux_knowledge.retrieval_engine import retrieve_ux_knowledge, to_knowledge_response

from ..envelope import KnowledgeQuery, KnowledgeResponse


def handle_ux_retrieve(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	"""query_id=ux.retrieve — deterministic playbook/pattern/principle retrieval."""
	repo_root = graph.meta.repo_root or str(query.params.get("repo_root") or "")
	params = {k: v for k, v in query.params.items() if k != "repo_root"}
	result = retrieve_ux_knowledge(params, repo_root=repo_root or None)
	log_retrieval_influence(
		repo_root=repo_root or None,
		query_id="ux.retrieve",
		params=params,
		retrieval=result,
		source="knowledge_api",
	)
	return to_knowledge_response(result, query)


UX_KNOWLEDGE_HANDLERS: dict[str, Any] = {
	"ux.retrieve": handle_ux_retrieve,
}
