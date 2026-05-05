from __future__ import annotations

from scripts.generate_candidate_context_report import generate_candidate_context_report


def test_candidate_context_report_parseable(tiny_project):
    report = generate_candidate_context_report(tiny_project)
    assert report["examples"] >= 1
    assert report["used_gold_patterns"] is False
    assert "compression_ratio" in report["summary"]
