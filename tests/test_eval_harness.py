from __future__ import annotations

from dashagent.eval_harness import EvalHarness


def test_eval_harness_runs_on_tiny_example(tiny_project):
    harness = EvalHarness(tiny_project)
    result = harness.run(strategies=["SQL_ONLY_BASELINE"])
    assert result["examples"] == 1
    assert result["rows"]
    assert (tiny_project.outputs_dir / "eval_results.json").exists()
    assert (tiny_project.outputs_dir / "strategy_comparison.md").exists()
