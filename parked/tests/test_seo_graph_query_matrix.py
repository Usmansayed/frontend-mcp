"""SEO graph query matrix (T0 unit).

Exercises every registered `list_graph_queries()` id against a store that
we build via the public API — no filesystem persistence required.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.seo_intelligence.knowledge.graph.queries import (
    list_graph_queries,
    run_graph_query,
)
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore


@pytest.fixture()
def empty_store(tmp_path) -> SeoKnowledgeGraphStore:
    """Fresh store on a temp path so nothing persists between tests."""
    return SeoKnowledgeGraphStore(path=tmp_path / "seo_graph.json")


@pytest.mark.unit
def test_list_graph_queries_covers_expected_ids() -> None:
    queries = list_graph_queries()
    ids = {q["query_id"] for q in queries}
    for expected in (
        "graph.summary",
        "page.issues",
        "audit.latest",
        "audit.diff",
        "site.traffic_signals",
        "ai.readiness.summary",
        "page.ai_readiness",
    ):
        assert expected in ids, f"query {expected!r} missing from list_graph_queries"


@pytest.mark.unit
def test_query_ids_are_documented(tmp_path) -> None:
    """Each query lists its param names — enforces docs parity for agents."""
    queries = list_graph_queries()
    for q in queries:
        assert "description" in q and q["description"]
        assert isinstance(q.get("params", []), list)


@pytest.mark.unit
def test_unknown_query_id_returns_helpful_error(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "does.not.exist")
    assert result["ok"] is False
    assert "unknown_query_id" in result.get("error", "")
    assert "graph.summary" in result.get("available_queries", [])


@pytest.mark.unit
def test_graph_summary_on_empty_store(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "graph.summary")
    assert result["ok"] is True
    summary = result["result"]
    assert isinstance(summary, dict)


@pytest.mark.unit
def test_page_issues_requires_page_url(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "page.issues", {})
    assert result["ok"] is True
    assert result["result"].get("error") == "page_url_required"


@pytest.mark.unit
def test_audit_latest_on_empty_store(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "audit.latest")
    assert result["ok"] is True
    assert result["result"].get("message") == "no_audits_yet"


@pytest.mark.unit
def test_audit_diff_on_empty_store(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "audit.diff")
    assert result["ok"] is True
    r = result["result"]
    assert "error" in r or "message" in r


@pytest.mark.unit
def test_traffic_signals_on_empty_store(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "site.traffic_signals")
    assert result["ok"] is True
    assert isinstance(result["result"].get("hypotheses", []), list)


@pytest.mark.unit
def test_ai_readiness_summary_on_empty_store(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "ai.readiness.summary")
    assert result["ok"] is True
    assert result["result"].get("message") == "no_audits_yet"


@pytest.mark.unit
def test_page_ai_readiness_requires_page_url(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(empty_store, "page.ai_readiness", {})
    assert result["ok"] is True
    assert result["result"].get("error") == "page_url_required"


@pytest.mark.unit
def test_page_ai_readiness_unknown_page_returns_empty(empty_store: SeoKnowledgeGraphStore) -> None:
    result = run_graph_query(
        empty_store, "page.ai_readiness", {"page_url": "https://example.com/x"}
    )
    assert result["ok"] is True
    r = result["result"]
    assert r["ai_signal_count"] == 0
    assert r["ai_signals"] == []
    assert r["source_evidence"] == []
