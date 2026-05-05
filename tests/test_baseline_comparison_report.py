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
