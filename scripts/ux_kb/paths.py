"""Paths for UX KB."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_ROOT = REPO_ROOT / "ForOpenCode" / "kb"
DB_PATH = KB_ROOT / "ux_kb.sqlite"
URL_QUEUE = KB_ROOT / "url_queue.yaml"
TOPIC_BUDGETS = KB_ROOT / "topic_budgets.yaml"
CARD_SCHEMA = KB_ROOT / "schemas" / "card.schema.json"
REPORTS = KB_ROOT / "reports"
RAW = KB_ROOT / "raw"
PILOT_QUEUE = KB_ROOT / "pilot_queue.yaml"
GRAPH_EXPORTS = KB_ROOT / "graph_exports"
GUIDES = REPO_ROOT / "ForOpenCode" / "07_guides"
GRAPHS = REPO_ROOT / "ForOpenCode" / "08_graphs"
RUNTIME = REPO_ROOT / "ForOpenCode" / "09_runtime"
NORMALIZED_SEED = REPO_ROOT / "ForOpenCode" / "06_corpus" / "normalized"
QUERY_CATALOG = KB_ROOT / "query_catalog.yaml"
GAP_CLUSTERS = KB_ROOT / "gap_clusters.yaml"
EXPANSION_PLANS = KB_ROOT / "expansion_plans.yaml"
TAXONOMY = REPO_ROOT / "ForOpenCode" / "02_taxonomy" / "TOPIC_TAXONOMY.yaml"
