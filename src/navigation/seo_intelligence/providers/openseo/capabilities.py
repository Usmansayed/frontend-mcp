"""OpenSEO capability metadata — maps MCP tools to SEO Intelligence capabilities."""
from __future__ import annotations

# Free OpenSEO MCP tools (no DataForSEO credits) — implemented in adapter.
OPENSEO_FREE_CAPABILITIES: dict[str, dict[str, object]] = {
	'search_queries': {
		'mcp_tool': 'get_search_console_performance',
		'requires_dataforseo': False,
		'notes': 'GSC mirror — fallback when direct search-console adapter unavailable',
	},
	'index_status': {
		'mcp_tool': 'inspect_urls',
		'requires_dataforseo': False,
		'notes': 'GSC URL inspection — fallback when direct search-console adapter unavailable',
	},
}

# Paid / DataForSEO-backed capabilities — planner-gated via allow_paid_providers.
OPENSEO_PAID_CAPABILITIES: dict[str, dict[str, object]] = {
	'keyword_research': {
		'mcp_tools': ['research_keywords', 'get_keyword_metrics', 'get_domain_keyword_suggestions'],
		'requires_dataforseo': True,
	},
	'serp_analysis': {
		'mcp_tools': ['get_serp_results', 'find_serp_competitors', 'get_local_serp_results'],
		'requires_dataforseo': True,
	},
	'domain_intelligence': {
		'mcp_tools': ['get_ranked_keywords'],
		'requires_dataforseo': True,
	},
	'backlinks': {
		'mcp_tools': ['get_backlinks_profile', 'get_backlinks_overview'],
		'requires_dataforseo': True,
	},
	'rank_tracking': {
		'mcp_tools': ['get_rank_tracker'],
		'requires_dataforseo': True,
	},
	'ai_visibility': {
		'mcp_tools': [],
		'requires_dataforseo': True,
		'notes': 'AI visibility workflows in OpenSEO UI/MCP — optional OPENROUTER for SAM',
	},
}

# Legacy alias for tests and docs that reference OPENSEO_MCP_TOOLS.
OPENSEO_MCP_TOOLS: dict[str, dict[str, object]] = {
	**{k: {**v, 'capability': k, 'free_app': True} for k, v in OPENSEO_FREE_CAPABILITIES.items()},
	**{k: {**v, 'capability': k, 'free_app': True} for k, v in OPENSEO_PAID_CAPABILITIES.items()},
	'search_console_mirror': {
		'mcp_tools': ['get_search_console_performance'],
		'capability': 'search_queries',
		'requires_dataforseo': False,
		'free_app': True,
	},
}

# OpenSEO site audit overlaps LibreCrawl — planner blocks via OPENSEO_BLOCKED_CAPABILITIES
OPENSEO_DO_NOT_ROUTE: list[str] = [
	'technical_crawl',
	'core_web_vitals',
	'rendering_verification',
]
