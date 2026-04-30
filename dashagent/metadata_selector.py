from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config, DEFAULT_CONFIG
from .endpoint_catalog import EndpointCatalog
from .router import RoutingDecision
from .schema_index import SchemaIndex


@dataclass
class MetadataSelector:
    schema_index: SchemaIndex
    endpoint_catalog: EndpointCatalog
    config: Config = DEFAULT_CONFIG

    def select(
        self,
        query: str,
        routing: RoutingDecision,
        *,
        strategy: str,
        query_id: str,
        broad_context: bool = False,
    ) -> dict[str, Any]:
        selected_tables = routing.candidate_tables
        if broad_context:
            selected_tables = list(self.schema_index.tables)[:30]
        selected_columns = {
            table: self._columns_for_strategy(table, broad_context)
            for table in selected_tables
            if table in self.schema_index.tables
        }
        selected_apis = routing.candidate_apis
        if broad_context:
            selected_apis = self.endpoint_catalog.as_list()

        metadata = {
            "query_id": query_id,
            "query": query,
            "strategy": strategy,
            "route_type": routing.route_type,
            "domain_type": routing.domain_type,
            "selected_tables": selected_tables,
            "selected_columns": selected_columns,
            "selected_join_hints": self.schema_index.selected_join_hints(selected_tables)[:30],
            "selected_apis": selected_apis,
            "known_example_patterns": self._load_relevant_gold_patterns(query, selected_apis),
            "constraints": [
                "Use only known table names and columns.",
                "Use only endpoint catalog entries unless fallback mode is explicitly enabled.",
                "Validate SQL and API calls before execution.",
                "Prefer fewer tool calls when evidence is sufficient.",
            ],
            "answer_policy": [
                "Answer from tool evidence only.",
                "Say not found when evidence is empty.",
                "Explicitly mention SQL/API disagreement when both are used.",
                "Do not invent IDs, counts, timestamps, states, or names.",
            ],
        }
        return metadata

    def _columns_for_strategy(self, table: str, broad_context: bool) -> list[str]:
        columns = self.schema_index.columns_for(table)
        if broad_context:
            return columns[:80]
        important = [
            column
            for column in columns
            if any(
                token in column.lower()
                for token in ["id", "name", "title", "status", "state", "time", "date", "count", "type"]
            )
        ]
        compact = important or columns[:16]
        return compact[:24]

    def _load_relevant_gold_patterns(
        self, query: str, selected_apis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        path = self.config.outputs_dir / "gold_api_patterns.json"
        if not path.exists():
            return []
        try:
            patterns = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        selected_paths = {api["path"] for api in selected_apis if "path" in api}
        lowered = query.lower()
        relevant = []
        for pattern in patterns:
            if pattern.get("path") in selected_paths or any(
                word in json.dumps(pattern).lower() for word in lowered.split()[:8]
            ):
                relevant.append(pattern)
        return relevant[:5]

    def save(self, metadata: dict[str, Any], output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "metadata.json"
        path.write_text(json.dumps(metadata, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path
