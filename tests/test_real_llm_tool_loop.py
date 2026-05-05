from __future__ import annotations

from dashagent.llm_tool_agent import run_real_llm_two_tools_baseline


def test_real_llm_two_tools_baseline_skips_without_key(monkeypatch, tiny_project):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_real_llm_two_tools_baseline("List all journeys", config=tiny_project)
    assert result["skipped"] is True
    assert result["real_llm_used"] is False
