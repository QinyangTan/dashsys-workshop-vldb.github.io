from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import Config, DEFAULT_CONFIG
from .db import DuckDBDatabase
from .endpoint_catalog import EndpointCatalog
from .pattern_mining import mine_gold_patterns
from .schema_index import JoinHint, SchemaIndex


CACHE_MANIFEST = "cache_manifest.json"


def current_fingerprint(config: Config | None = None) -> dict[str, Any]:
    cfg = config or DEFAULT_CONFIG
    parquet_files = []
    if cfg.dbsnapshot_dir.exists():
        for path in sorted(cfg.dbsnapshot_dir.rglob("*.parquet")):
            stat = path.stat()
            parquet_files.append(
                {
                    "name": str(path.relative_to(cfg.dbsnapshot_dir)),
                    "mtime_ns": stat.st_mtime_ns,
                    "size": stat.st_size,
                }
            )
    data_stat = cfg.data_json_path.stat() if cfg.data_json_path.exists() else None
    return {
        "parquet_files": parquet_files,
        "data_json": {
            "exists": cfg.data_json_path.exists(),
            "mtime_ns": data_stat.st_mtime_ns if data_stat else None,
            "size": data_stat.st_size if data_stat else None,
        },
    }


def cache_manifest_path(config: Config | None = None) -> Path:
    cfg = config or DEFAULT_CONFIG
    return cfg.outputs_dir / CACHE_MANIFEST


def cache_is_valid(config: Config | None = None) -> bool:
    cfg = config or DEFAULT_CONFIG
    manifest_path = cache_manifest_path(cfg)
    required = [
        cfg.outputs_dir / "schema_summary.json",
        cfg.outputs_dir / "join_graph.json",
        cfg.outputs_dir / "endpoint_catalog.json",
        cfg.outputs_dir / "gold_api_patterns.json",
        cfg.outputs_dir / "gold_sql_patterns.json",
        cfg.outputs_dir / "gold_answer_patterns.json",
    ]
    if not manifest_path.exists() or any(not path.exists() for path in required):
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return manifest.get("fingerprint") == current_fingerprint(cfg)


def write_cache_manifest(config: Config | None = None) -> Path:
    cfg = config or DEFAULT_CONFIG
    cfg.outputs_dir.mkdir(parents=True, exist_ok=True)
    path = cache_manifest_path(cfg)
    path.write_text(
        json.dumps({"fingerprint": current_fingerprint(cfg)}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def warm_cache(config: Config | None = None) -> dict[str, Any]:
    cfg = config or DEFAULT_CONFIG
    cfg.ensure_dirs()
    db = DuckDBDatabase(cfg)
    schema = SchemaIndex.build(db)
    schema_path, graph_path = schema.save(cfg)
    endpoint_path = EndpointCatalog(cfg).save()
    patterns = mine_gold_patterns(cfg)
    manifest_path = write_cache_manifest(cfg)
    return {
        "ok": True,
        "cache_valid": cache_is_valid(cfg),
        "schema_summary": str(schema_path),
        "join_graph": str(graph_path),
        "endpoint_catalog": str(endpoint_path),
        "gold_sql_patterns": len(patterns["sql"]),
        "gold_api_patterns": len(patterns["api"]),
        "gold_answer_patterns": len(patterns["answer"]),
        "manifest": str(manifest_path),
    }


def load_schema_index_from_cache(config: Config | None = None) -> SchemaIndex | None:
    cfg = config or DEFAULT_CONFIG
    if not cache_is_valid(cfg):
        return None
    schema_path = cfg.outputs_dir / "schema_summary.json"
    graph_path = cfg.outputs_dir / "join_graph.json"
    try:
        schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
        graph_payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    tables = {}
    for table, meta in schema_payload.get("tables", {}).items():
        tables[table] = {
            "columns": [
                {
                    "name": column,
                    "type": None,
                    "is_id_like": column in meta.get("id_columns", []),
                    "is_name_like": "name" in column.lower(),
                }
                for column in meta.get("columns", [])
            ],
            "id_columns": meta.get("id_columns", []),
            "primary_like_id": meta.get("primary_like_id"),
            "is_bridge": meta.get("is_bridge", False),
        }
    join_hints = [
        JoinHint(
            left_table=edge["left_table"],
            left_column=edge["left_column"],
            right_table=edge["right_table"],
            right_column=edge["right_column"],
            confidence=float(edge.get("confidence", 0.0)),
            reason=edge.get("reason", "cached"),
        )
        for edge in graph_payload.get("edges", [])
        if all(key in edge for key in ["left_table", "left_column", "right_table", "right_column"])
    ]
    bridge_tables = schema_payload.get("bridge_tables", [])
    return SchemaIndex(tables=tables, join_hints=join_hints, bridge_tables=bridge_tables)
