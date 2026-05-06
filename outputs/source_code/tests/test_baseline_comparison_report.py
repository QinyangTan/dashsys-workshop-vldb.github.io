from __future__ import annotations

import json

from scripts.generate_baseline_comparison_report import generate_report


def test_baseline_comparison_report_from_minimal_inputs(tiny_project):
    tiny_project.outputs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "by_strategy": {
                "LLM_FREE_AGENT_BASELINE": {"avg_correctness_score": 0.5, "avg_final_score": 0.4, "avg_tool_call_count": 3, "avg_estimated_tokens": 1000, "avg_runtime": 1},
                "SQL_FIRST_API_VERIFY": {"avg_correctness_score": 0.8, "avg_final_score": 0.75, "avg_tool_call_count": 1, "avg_estimated_tokens": 800, "avg_runtime": 0.5},
            }
        },
        "rows": [],
    }
    (tiny_project.outputs_dir / "eval_results.json").write_text(json.dumps(payload), encoding="utf-8")
    report = generate_report(tiny_project)
    systems = {row["system"] for row in report["systems"]}
    assert "LLM_FREE_AGENT_BASELINE" in systems
    assert "SQL_FIRST_API_VERIFY" in systems
    assert report["improvement_vs_naive"]
    assert "flowchart" in report["mermaid"]


def test_failed_real_llm_baseline_is_not_marked_successful(tiny_project):
    tiny_project.outputs_dir.mkdir(parents=True, exist_ok=True)
    (tiny_project.outputs_dir / "eval_results.json").write_text(
        json.dumps({"summary": {"by_strategy": {}}, "rows": []}),
        encoding="utf-8",
    )
    (tiny_project.outputs_dir / "llm_baseline_eval.json").write_text(
        json.dumps(
            {
                "skipped": False,
                "rows": [
                    {
                        "query_id": "example_000",
                        "system": "REAL_LLM_TWO_TOOLS_BASELINE",
                        "real_llm_called": True,
                        "tool_calls_executed": False,
                        "valid_agent_run": False,
                        "skipped_or_failed": True,
                        "failure_reason": "invalid_tool_call_format_after_retry",
                        "tool_call_count": 0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = generate_report(tiny_project)
    real_status = next(row for row in report["systems"] if row["system"] == "REAL_LLM_TWO_TOOLS_BASELINE")["llm_status"]
    assert real_status["status"] == "real_llm_called_but_tool_loop_failed"
    assert real_status["valid_rows"] == 0
    assert report["failed_real_llm_tool_loops"]
    assert report["real_llm_tool_loop_warning"] is True
    assert not report["successful_real_llm_tool_loops"]


def test_valid_real_llm_baseline_is_marked_successful(tiny_project):
    tiny_project.outputs_dir.mkdir(parents=True, exist_ok=True)
    (tiny_project.outputs_dir / "eval_results.json").write_text(
        json.dumps({"summary": {"by_strategy": {}}, "rows": []}),
        encoding="utf-8",
    )
    (tiny_project.outputs_dir / "llm_baseline_eval.json").write_text(
        json.dumps(
            {
                "skipped": False,
                "rows": [
                    {
                        "query_id": "example_000",
                        "system": "REAL_LLM_TWO_TOOLS_BASELINE",
                        "real_llm_called": True,
                        "tool_calls_executed": True,
                        "valid_agent_run": True,
                        "skipped_or_failed": False,
                        "tool_call_count": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = generate_report(tiny_project)
    real_status = next(row for row in report["systems"] if row["system"] == "REAL_LLM_TWO_TOOLS_BASELINE")["llm_status"]
    assert real_status["status"] == "valid_tool_agent_run"
    assert real_status["valid_rows"] == 1
    assert report["successful_real_llm_tool_loops"]
    assert not report["failed_real_llm_tool_loops"]
