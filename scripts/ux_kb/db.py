"""SQLite schema and connection helpers."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .paths import DB_PATH, KB_ROOT

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  topic TEXT NOT NULL,
  priority TEXT DEFAULT 'B',
  get_notes TEXT,
  skip_notes TEXT,
  max_cards INTEGER DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'queued',
  checksum_sha256 TEXT,
  snapshot_path TEXT,
  bytes INTEGER,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  claimed_at TEXT,
  finished_at TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_type ON jobs(status, job_type);

CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  title TEXT NOT NULL,
  rule TEXT NOT NULL,
  detect TEXT NOT NULL,
  when_to_apply TEXT NOT NULL,
  when_not_to_apply TEXT NOT NULL,
  tradeoff TEXT NOT NULL,
  quote TEXT,
  source_ids_json TEXT NOT NULL,
  evidence_class TEXT NOT NULL,
  confidence REAL NOT NULL,
  supersedes_json TEXT,
  conflicts_with_json TEXT,
  embedding_text TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  frozen INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_topic_status ON cards(topic, status);

CREATE TABLE IF NOT EXISTS conflicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_a TEXT NOT NULL,
  card_b TEXT NOT NULL,
  summary TEXT NOT NULL,
  decision TEXT,
  decision_hint TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS packs (
  topic TEXT PRIMARY KEY,
  budget INTEGER NOT NULL,
  card_ids_json TEXT NOT NULL DEFAULT '[]',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  stage TEXT NOT NULL,
  ok_count INTEGER NOT NULL DEFAULT 0,
  fail_count INTEGER NOT NULL DEFAULT 0,
  pending_review_count INTEGER NOT NULL DEFAULT 0,
  summary_json TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS principle_clusters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  principle_key TEXT NOT NULL,
  principle_label TEXT NOT NULL,
  topic TEXT NOT NULL,
  canonical_card_id TEXT NOT NULL,
  member_ids_json TEXT NOT NULL,
  supporting_source_ids_json TEXT NOT NULL,
  conflicting_source_ids_json TEXT NOT NULL DEFAULT '[]',
  conflict_summary TEXT,
  cluster_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (canonical_card_id) REFERENCES cards(id)
);

CREATE INDEX IF NOT EXISTS idx_clusters_topic ON principle_clusters(topic);
CREATE INDEX IF NOT EXISTS idx_clusters_canonical ON principle_clusters(canonical_card_id);

CREATE TABLE IF NOT EXISTS graph_nodes (
  id TEXT PRIMARY KEY,
  node_type TEXT NOT NULL,
  label TEXT NOT NULL,
  ref TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  payload_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);

CREATE TABLE IF NOT EXISTS graph_edges (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  context TEXT,
  confidence REAL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_relation ON graph_edges(relation);
"""


def utcnow() -> str:
	return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
	path = db_path or DB_PATH
	path.parent.mkdir(parents=True, exist_ok=True)
	conn = sqlite3.connect(str(path))
	conn.row_factory = sqlite3.Row
	conn.execute("PRAGMA foreign_keys=ON")
	return conn


@contextmanager
def db_session(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
	conn = connect(db_path)
	try:
		yield conn
		conn.commit()
	except Exception:
		conn.rollback()
		raise
	finally:
		conn.close()


def init_db(db_path: Path | None = None) -> Path:
	KB_ROOT.mkdir(parents=True, exist_ok=True)
	path = db_path or DB_PATH
	with db_session(path) as conn:
		conn.executescript(SCHEMA_SQL)
	return path


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
	if row is None:
		return None
	return dict(row)


def dumps(obj: Any) -> str:
	return json.dumps(obj, ensure_ascii=False)


def loads(text: str | None, default: Any = None) -> Any:
	if not text:
		return default
	return json.loads(text)
