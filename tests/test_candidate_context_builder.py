from __future__ import annotations

from dashagent.candidate_context_builder import build_candidate_context, build_full_schema_context
from dashagent.endpoint_catalog import EndpointCatalog
from dashagent.executor import AgentExecutor


def test_candidate_context_is_retrieval_only(tiny_project):
    executor = AgentExecutor(tiny_project)
    context = build_candidate_context("List all journeys", executor.schema_index, EndpointCatalog(tiny_project))
    assert context["used_gold_patterns"] is False
    assert context["candidate_tables"]
    assert "candidate_columns" in context
    assert "candidate_join_hints" in context
    assert "candidate_apis" in context


def test_full_schema_context_contains_all_tables(tiny_project):
    executor = AgentExecutor(tiny_project)
    context = build_full_schema_context(executor.schema_index, EndpointCatalog(tiny_project))
    assert set(context["tables"]) == set(executor.schema_index.tables)
