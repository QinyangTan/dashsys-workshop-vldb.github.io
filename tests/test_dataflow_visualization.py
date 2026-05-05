from __future__ import annotations

from dashagent.dataflow_visualizer import build_checkpoint_effect_table, build_html_report, build_markdown_report, build_mermaid_graph


def fake_trajectory():
    return {
        "query_id": "fake",
        "original_query": "Is the 'Birthday Message' journey published?",
        "strategy": "SQL_FIRST_API_VERIFY",
        "tool_call_count": 1,
        "final_answer": "Birthday Message has not been published.",
        "checkpoints": [
            {"checkpoint_id": "checkpoint_00_prompt_router", "technique": "routing", "output": {"mode": "SQL_PLUS_API", "api_policy": "API_OPTIONAL"}},
            {"checkpoint_id": "checkpoint_02_query_normalization", "technique": "normalization", "output": {"normalized_query": "is birthday message journey published"}},
            {"checkpoint_id": "checkpoint_03_query_tokens", "technique": "tokens", "output": {"quoted_entities": ["Birthday Message"]}},
            {"checkpoint_id": "checkpoint_16_answer_verification", "technique": "verification", "output": {"verifier_passed": True}},
        ],
        "steps": [
            {"kind": "sql_call", "sql": "SELECT * FROM dim_campaign", "result": {"row_count": 1}},
            {"kind": "api_call", "method": "GET", "url": "/ajo/journey", "params": {"access_token": "secret-token-123456789"}},
        ],
    }


def test_dataflow_outputs_mermaid_markdown_html_and_redacts():
    trajectory = fake_trajectory()
    graph = build_mermaid_graph(trajectory)
    md = build_markdown_report(trajectory)
    html = build_html_report(trajectory)
    table = build_checkpoint_effect_table(trajectory)
    assert "flowchart" in graph
    assert "Prompt Router" in graph
    assert "checkpoint_00_prompt_router" in table
    assert "Checkpoint Effect Table" in md
    assert "mermaid" in html
    assert "secret-token-123456789" not in md
