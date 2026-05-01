from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .answer_synthesizer import synthesize_answer_with_diagnostics
from .api_client import AdobeAPIClient
from .cache import (
    api_response_cache_key,
    current_fingerprint,
    get_api_response_cache,
    get_query_analysis_cache,
    get_sql_result_cache,
    load_schema_index_from_cache,
    query_analysis_cache_key,
    set_api_response_cache,
    set_query_analysis_cache,
    set_sql_result_cache,
    sql_result_cache_key,
    write_cache_manifest,
)
from .config import Config, DEFAULT_CONFIG
from .db import DuckDBDatabase
from .endpoint_catalog import EndpointCatalog
from .evidence_bus import EvidenceBus
from .metadata_selector import MetadataSelector
from .plan_ensemble import select_plan_candidate
from .planner import STRATEGIES, StrategyPlanner
from .query_normalizer import normalize_query
from .query_tokens import extract_query_tokens
from .query_analysis import analyze_query
from .router import QueryRouter
from .schema_index import SchemaIndex
from .trajectory import TrajectoryLogger, estimate_tokens
from .validators import APIValidator, SQLValidator, ValidationResult


class AgentExecutor:
    def __init__(
        self,
        config: Config | None = None,
        db: DuckDBDatabase | None = None,
        schema_index: SchemaIndex | None = None,
        endpoint_catalog: EndpointCatalog | None = None,
        api_client: AdobeAPIClient | None = None,
    ) -> None:
        self.config = config or DEFAULT_CONFIG
        self.config.ensure_dirs()
        self.db = db or DuckDBDatabase(self.config)
        if schema_index is not None:
            self.schema_index = schema_index
        else:
            cached_schema = load_schema_index_from_cache(self.config)
            self.schema_index = cached_schema or SchemaIndex.build(self.db)
            if cached_schema is None:
                self.schema_index.save(self.config)
                write_cache_manifest(self.config)
        self.endpoint_catalog = endpoint_catalog or EndpointCatalog(self.config)
        self.api_client = api_client or AdobeAPIClient(self.config)
        self.router = QueryRouter(self.db.list_tables(), self.endpoint_catalog)
        self.metadata_selector = MetadataSelector(self.schema_index, self.endpoint_catalog, self.config)
        self.planner = StrategyPlanner(self.schema_index)
        self.sql_validator = SQLValidator(self.schema_index)
        self.api_validator = APIValidator(
            self.endpoint_catalog,
            allow_unknown=self.config.allow_unknown_api_endpoints,
        )
        self.cache_fingerprint = current_fingerprint(self.config)

    def run(
        self,
        query: str,
        *,
        strategy: str = "SQL_FIRST_API_VERIFY",
        query_id: str | None = None,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        if strategy not in STRATEGIES:
            raise ValueError(f"Unknown strategy {strategy}. Expected one of {STRATEGIES}.")
        qid = query_id or slugify(query)
        out_dir = output_dir or (self.config.outputs_dir / qid / strategy.lower())
        out_dir.mkdir(parents=True, exist_ok=True)

        preprocessing_start = time.perf_counter()
        normalization = normalize_query(query)
        tokens = extract_query_tokens(query, normalization)
        routing = self.router.route(normalization["matching_text"])
        analysis_key = query_analysis_cache_key(query, strategy, self.config, self.cache_fingerprint)
        analysis = get_query_analysis_cache(analysis_key)
        if analysis is None:
            analysis = analyze_query(
                query,
                routing,
                self.schema_index,
                strategy=strategy,
                config=self.config,
                endpoint_catalog=self.endpoint_catalog,
                normalized=normalization,
                tokens=tokens,
            )
            set_query_analysis_cache(analysis_key, analysis)
        broad = strategy == "LLM_FREE_AGENT_BASELINE"
        metadata = self.metadata_selector.select(
            query,
            routing,
            strategy=strategy,
            query_id=qid,
            broad_context=broad,
            analysis=analysis,
        )
        self.metadata_selector.save(metadata, out_dir)

        filled_prompt = render_system_prompt(self.config, metadata)
        (out_dir / "filled_system_prompt.txt").write_text(filled_prompt, encoding="utf-8")
        preprocessing_time = time.perf_counter() - preprocessing_start

        planning_start = time.perf_counter()
        plan = self.planner.create_plan(query, routing, metadata, strategy, analysis=analysis)
        ensemble_metadata = None
        if strategy == "SQL_FIRST_API_VERIFY":
            selection = select_plan_candidate(
                query=query,
                routing=routing,
                base_plan=plan,
                analysis=analysis,
                sql_validator=self.sql_validator,
                api_validator=self.api_validator,
                strategy=strategy,
            )
            plan = selection.plan
            ensemble_metadata = selection.compact()
        planning_time = time.perf_counter() - planning_start
        trajectory = TrajectoryLogger(
            query_id=qid,
            original_query=query,
            strategy=strategy,
            route_type=routing.route_type,
            domain_type=routing.domain_type,
            max_preview_chars=self.config.max_preview_chars,
        )
        trajectory.set_timing("preprocessing_time", preprocessing_time)
        trajectory.set_timing("planning_time", planning_time)
        trajectory.add_step("route", compact_routing_decision(routing.to_dict()))
        nlp_step = {
            "rewrites": analysis.normalization_rewrites[:3],
            "tokens": analysis.tokens.compact(),
            "relevance": {
                key: value[:2] if isinstance(value, list) else value
                for key, value in analysis.relevance.compact(table_k=2, api_k=2).items()
                if key in {"tables", "apis", "lookup_paths"}
            },
        }
        trajectory.add_step("nlp", {key: value for key, value in nlp_step.items() if value not in ([], {}, "", None)})
        trajectory.add_step(
            "metadata",
            {
                "estimated_tokens": estimate_tokens(metadata),
                "prompt_tokens": estimate_tokens(filled_prompt),
                "metadata_path": str(out_dir / "metadata.json"),
            },
        )
        trajectory.add_step("plan", plan.to_dict())
        if ensemble_metadata:
            trajectory.add_step("optimizer", {"plan_ensemble": ensemble_metadata})

        tool_results: list[dict[str, Any]] = []
        evidence_bus = EvidenceBus()
        execution_start = time.perf_counter()
        for step in plan.steps:
            if step.action == "sql" and step.sql:
                validation = self.sql_validator.validate(step.sql)
                if not validation.ok:
                    repaired_sql = repair_sql(step.sql, validation, self.schema_index)
                    if repaired_sql and repaired_sql != step.sql:
                        repaired_validation = self.sql_validator.validate(repaired_sql)
                        trajectory.add_validation("sql_repair_attempt", repaired_validation)
                        if repaired_validation.ok:
                            step.sql = repaired_sql
                            validation = ValidationResult(True, warnings=["SQL repaired once."], repaired=True)
                if validation.ok:
                    cache_key = sql_result_cache_key(step.sql, self.config, self.cache_fingerprint)
                    result = get_sql_result_cache(cache_key)
                    if result is None:
                        result = self.db.execute_sql(step.sql, allow_full_result=step.allow_full_result)
                        set_sql_result_cache(cache_key, result)
                else:
                    result = {"ok": False, "rows": [], "row_count": 0, "error": "; ".join(validation.errors)}
                trajectory.add_sql_call(step.sql, validation, result)
                tool_results.append({"type": "sql", "step": step.to_dict(), "validation": validation.to_dict(), "payload": result})
                evidence_bus.observe_sql(step, result)
            elif step.action == "api" and step.method and step.url:
                forwarding_actions = evidence_bus.forward_to_step(step)
                if forwarding_actions:
                    trajectory.add_step("optimizer", {"actions": forwarding_actions})
                validation = self.api_validator.validate(step.method, step.url, step.params, step.headers)
                if validation.ok:
                    api_cache_key = api_response_cache_key(step.method, step.url, step.params)
                    result = get_api_response_cache(api_cache_key) if self.api_client.dry_run else None
                    if result is None:
                        result = self.api_client.call_api(step.method, step.url, step.params, step.headers)
                        if result.get("dry_run"):
                            set_api_response_cache(api_cache_key, result)
                else:
                    result = {"ok": False, "dry_run": False, "error": "; ".join(validation.errors)}
                trajectory.add_api_call(step.method, step.url, step.params, step.headers, validation, result)
                tool_results.append({"type": "api", "step": step.to_dict(), "validation": validation.to_dict(), "payload": result})
                evidence_bus.observe_api(step, result)
        trajectory.set_timing("execution_time", time.perf_counter() - execution_start)

        answer_start = time.perf_counter()
        answer_result = synthesize_answer_with_diagnostics(query, tool_results)
        final_answer = answer_result.answer
        trajectory.add_step("answer_diagnostics", answer_result.diagnostics)
        trajectory.set_timing("answer_time", time.perf_counter() - answer_start)
        trajectory_payload = trajectory.save(out_dir / "trajectory.json", final_answer)
        return {
            "query_id": qid,
            "query": query,
            "strategy": strategy,
            "output_dir": str(out_dir),
            "metadata": metadata,
            "plan": plan.to_dict(),
            "tool_results": tool_results,
            "final_answer": final_answer,
            "trajectory": trajectory_payload,
        }


def slugify(text: str, max_length: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return (slug[:max_length] or "query").strip("_")


def render_system_prompt(config: Config, metadata: dict[str, Any]) -> str:
    template_path = config.prompts_dir / "system_prompt_template.txt"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = "You are a constrained DASHSys QA agent.\nMetadata:\n{metadata_json}\n"
    return template.replace("{metadata_json}", json.dumps(metadata, indent=2, sort_keys=True, default=str))


def repair_sql(sql: str, validation: ValidationResult, schema_index: SchemaIndex) -> str | None:
    if not validation.errors:
        return None
    fake_column_errors = [error for error in validation.errors if error.startswith("Unknown column:")]
    if not fake_column_errors:
        return None
    table_match = re.search(r"\bFROM\s+\"?([a-zA-Z_][\w$]*)\"?", sql, flags=re.IGNORECASE)
    if not table_match:
        return None
    table = table_match.group(1)
    if not schema_index.table_exists(table):
        return None
    columns = schema_index.columns_for(table)[:8]
    if not columns:
        return f"SELECT * FROM \"{table}\" LIMIT 50"
    projection = ", ".join(f'"{column}"' for column in columns)
    return f"SELECT {projection} FROM \"{table}\" LIMIT 50"


def compact_routing_decision(decision: dict[str, Any]) -> dict[str, Any]:
    compact = dict(decision)
    compact["candidate_apis"] = [
        {
            key: api[key]
            for key in ["id", "method", "path"]
            if key in api
        }
        for api in decision.get("candidate_apis", [])
    ]
    return compact
