from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .answer_templates import classify_answer_family
from .api_templates import APITemplate, find_api_templates
from .config import Config, DEFAULT_CONFIG
from .evidence_policy import ApiNeedDecision, decide_api_need
from .fast_paths import FastPath, find_fast_path
from .lookup_paths import LookupPath, predict_lookup_path
from .router import RoutingDecision
from .schema_index import SchemaIndex
from .sql_templates import SQLTemplate, find_sql_template


@dataclass(frozen=True)
class QueryAnalysis:
    query: str
    route_type: str
    domain_type: str
    answer_family: str
    sql_template: SQLTemplate | None
    api_templates: list[APITemplate]
    api_need_decision: ApiNeedDecision
    fast_path: FastPath | None
    lookup_path: LookupPath
    confidence: float

    def to_metadata(self) -> dict[str, Any]:
        return {
            "answer_family": self.answer_family,
            "lookup_path": self.lookup_path.family,
            "api_need": self.api_need_decision.mode,
            "confidence": round(self.confidence, 4),
            "sql_template_family": self.sql_template.family if self.sql_template else None,
            "api_template_families": [template.family for template in self.api_templates],
        }


def analyze_query(
    query: str,
    routing: RoutingDecision,
    schema_index: SchemaIndex,
    *,
    strategy: str,
    config: Config | None = None,
) -> QueryAnalysis:
    cfg = config or DEFAULT_CONFIG
    answer_family = classify_answer_family(query)
    fast_path = find_fast_path(query, schema_index)
    sql_template = fast_path.sql_template if fast_path else find_sql_template(query, schema_index)
    api_templates = fast_path.api_templates if fast_path else find_api_templates(query, cfg)
    lookup_path = predict_lookup_path(query, answer_family, routing.domain_type)
    api_need = decide_api_need(query, routing, sql_template, api_templates, strategy)
    confidence = min(1.0, float(routing.confidence) + (0.1 if fast_path else 0.0) + (0.05 if sql_template else 0.0))
    return QueryAnalysis(
        query=query,
        route_type=routing.route_type,
        domain_type=routing.domain_type,
        answer_family=answer_family,
        sql_template=sql_template,
        api_templates=api_templates,
        api_need_decision=api_need,
        fast_path=fast_path,
        lookup_path=lookup_path,
        confidence=confidence,
    )
