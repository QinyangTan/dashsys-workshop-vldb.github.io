from __future__ import annotations

from dashagent.db import DuckDBDatabase


def test_duckdb_loads_parquet_views(tiny_project):
    db = DuckDBDatabase(tiny_project)
    assert db.list_tables() == ["dim_campaign", "dim_segment"]
    result = db.execute_sql('SELECT COUNT(*) AS count FROM "dim_campaign"')
    assert result["ok"] is True
    assert result["rows"] == [{"count": 2}]


def test_execute_sql_blocks_destructive_sql(tiny_project):
    db = DuckDBDatabase(tiny_project)
    result = db.execute_sql('DROP TABLE "dim_campaign"')
    assert result["ok"] is False
    assert "blocked" in result["error"] or "Only read-only" in result["error"]
