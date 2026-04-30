from __future__ import annotations

import json

from dashagent.api_templates import find_api_templates
from dashagent.evidence_policy import API_OPTIONAL, API_SKIP, decide_api_need
from dashagent.executor import AgentExecutor
from dashagent.fast_paths import find_fast_path
from dashagent.live_response_parsers import normalize_api_evidence
from dashagent.router import QueryRouter
from dashagent.schema_index import SchemaIndex
from dashagent.trajectory import compact_preview


def test_sql_first_journey_question_obeys_tool_budget(tiny_project):
    executor = AgentExecutor(tiny_project)
    result = executor.run(
        "When was the journey 'Birthday Message' published?",
        strategy="SQL_FIRST_API_VERIFY",
        query_id="budget_journey",
    )
    assert result["trajectory"]["tool_call_count"] <= 2


def test_sql_only_local_query_skips_api_when_policy_says_skip(tiny_project):
    executor = AgentExecutor(tiny_project)
    result = executor.run("How many campaigns are there?", strategy="SQL_FIRST_API_VERIFY", query_id="local_count")
    assert result["trajectory"]["sql_call_count"] == 1
    assert result["trajectory"]["api_call_count"] == 0


def test_known_multi_call_query_can_allow_two_api_calls(tiny_project):
    router = QueryRouter(["dim_segment", "dim_target"], executor_catalog_for_test(tiny_project))
    query = "List segment audiences connected to destination named 'SMS Opt-In'"
    routing = router.route(query)
    templates = find_api_templates(query, tiny_project)
    decision = decide_api_need(query, routing, None, templates, "SQL_FIRST_API_VERIFY")
    assert decision.mode == API_OPTIONAL
    assert decision.max_api_calls == 2


def executor_catalog_for_test(tiny_project):
    from dashagent.endpoint_catalog import EndpointCatalog

    return EndpointCatalog(tiny_project)


def test_fast_path_selection(tiny_project):
    executor = AgentExecutor(tiny_project)
    schema = executor.schema_index
    assert find_fast_path("List all journeys", schema) is not None
    assert find_fast_path("Tell me something unrelated", schema) is None


def test_live_response_parser_for_merge_policy():
    payload = {
        "ok": True,
        "result_preview": {
            "children": [
                {"id": "p1", "name": "Default Timebased", "isDefault": True, "state": "enabled"},
            ],
            "total": 1,
        },
    }
    evidence = normalize_api_evidence("merge_policies", payload)
    assert evidence["count"] == 1
    assert evidence["important_fields"]["default_policy_name"] == "Default Timebased"


def test_compact_preview_keeps_evidence_small_and_useful():
    payload = {
        "items": [{"id": str(i), "name": f"item {i}", "extra": "x" * 100} for i in range(10)],
        "count": 10,
        "other": "y" * 5000,
    }
    preview = compact_preview(payload, max_chars=500)
    text = json.dumps(preview)
    assert len(text) < 650
    assert "count" in text
    assert "item 0" in text
