from __future__ import annotations

from typing import Any

from .endpoint_catalog import EndpointCatalog
from .query_normalizer import normalize_query
from .query_tokens import extract_query_tokens
from .relevance_scorer import RelevanceItem, score_relevance
from .schema_index import SchemaIndex
from .trajectory import estimate_tokens


IMPORTANT_COLUMN_TOKENS = ("id", "name", "status", "state", "time", "date", "count", "type")


def build_full_schema_context(
    schema_index: SchemaIndex,
    endpoint_catalog: EndpointCatalog | None = None,
) -> dict[str, Any]:
    endpoints = endpoint_catalog.as_list() if endpoint_catalog else []
    return {
        "mode": "full_schema",
        "tables": {
            table: {
                "columns": [column["name"] for column in meta.get("columns", [])],
                "id_columns": meta.get("id_columns", []),
                "primary_like_id": meta.get("primary_like_id"),
                "is_bridge": meta.get("is_bridge", False),
            }
            for table, meta in schema_index.tables.items()
        },
        "join_hints": [hint.to_dict() for hint in schema_index.join_hints],
        "apis": [
            {
                "id": endpoint["id"],
                "method": endpoint["method"],
                "path": endpoint["path"],
                "use_when": endpoint.get("use_when", ""),
                "domains": endpoint.get("domains", []),
            }
            for endpoint in endpoints
        ],
        "used_gold_patterns": False,
    }


def build_candidate_context(
    query: str,
    schema_index: SchemaIndex,
    endpoint_catalog: EndpointCatalog,
    top_k_tables: int = 5,
    top_k_columns: int = 16,
    top_k_joins: int = 8,
    top_k_apis: int = 5,
) -> dict[str, Any]:
    normalization = normalize_query(query)
    tokens = extract_query_tokens(query, normalization)
    relevance = score_relevance(query, schema_index, endpoint_catalog, tokens=tokens)
    table_items = _with_fallback_tables(relevance.tables, schema_index, top_k_tables)
    candidate_tables = [item.name for item in table_items[:top_k_tables]]
    candidate_columns = {
        table: _candidate_columns(table, relevance.columns.get(table, []), schema_index, top_k_columns)
        for table in candidate_tables
    }
    join_hints = _candidate_joins(relevance.join_hints, top_k_joins)
    apis = _candidate_apis(relevance.apis, endpoint_catalog, top_k_apis)
    scores = {
        "tables": {item.name: round(item.score, 4) for item in table_items[:top_k_tables]},
        "apis": {item.name: round(item.score, 4) for item in relevance.apis[:top_k_apis]},
        "joins": {item.name: round(item.score, 4) for item in relevance.join_hints[:top_k_joins]},
    }
    top_scores = [item.score for item in table_items[:2]]
    top_score = top_scores[0] if top_scores else 0.0
    margin = (top_scores[0] - top_scores[1]) if len(top_scores) > 1 else top_score
    confidence = max(0.0, min(1.0, (top_score / 3.0) + min(max(margin, 0.0), 1.0) * 0.2))
    notes = ["Candidate context is retrieval-only and not a hard SQL constraint."]
    if confidence < 0.45 or margin < 0.15:
        notes.append("Low confidence or small score margin; full-schema fallback is preferred.")
    payload = {
        "query": query,
        "normalized_query": normalization.get("normalized"),
        "tokens": tokens.compact(),
        "candidate_tables": candidate_tables,
        "candidate_columns": candidate_columns,
        "candidate_join_hints": join_hints,
        "candidate_apis": apis,
        "scores": scores,
        "confidence": round(confidence, 4),
        "score_margin": round(margin, 4),
        "used_gold_patterns": False,
        "notes": notes,
    }
    payload["estimated_tokens"] = estimate_tokens(payload)
    return payload


def _with_fallback_tables(items: list[RelevanceItem], schema_index: SchemaIndex, top_k: int) -> list[RelevanceItem]:
    if items:
        return items
    fallback = []
    for table, meta in schema_index.tables.items():
        score = 0.2
        if meta.get("is_bridge"):
            score += 0.05
        fallback.append(RelevanceItem(table, score, "fallback schema table"))
    return sorted(fallback, key=lambda item: (-item.score, item.name))[:top_k]


def _candidate_columns(
    table: str,
    scored_columns: list[RelevanceItem],
    schema_index: SchemaIndex,
    top_k: int,
) -> list[str]:
    selected = [item.name for item in scored_columns[:top_k]]
    for column in schema_index.columns_for(table):
        lowered = column.lower()
        if column not in selected and any(token in lowered for token in IMPORTANT_COLUMN_TOKENS):
            selected.append(column)
        if len(selected) >= top_k:
            break
    return selected[:top_k]


def _candidate_joins(items: list[RelevanceItem], top_k: int) -> list[dict[str, Any]]:
    joins = []
    for item in items[:top_k]:
        joins.append({"path": item.name, "score": round(item.score, 4), "reason": item.reason})
    return joins


def _candidate_apis(items: list[RelevanceItem], catalog: EndpointCatalog, top_k: int) -> list[dict[str, Any]]:
    apis = []
    for item in items[:top_k]:
        endpoint = catalog.by_id(item.name)
        if not endpoint:
            continue
        apis.append(
            {
                "id": endpoint.id,
                "method": endpoint.method,
                "path": endpoint.path,
                "use_when": endpoint.use_when,
                "score": round(item.score, 4),
            }
        )
    return apis
