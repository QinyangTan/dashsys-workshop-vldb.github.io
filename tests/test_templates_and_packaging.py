from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dashagent.answer_synthesizer import synthesize_answer
from dashagent.api_templates import find_api_templates
from dashagent.config import Config
from dashagent.db import DuckDBDatabase
from dashagent.eval_harness import score_api
from dashagent.schema_index import SchemaIndex
from dashagent.sql_templates import find_sql_template
from scripts.package_query_outputs import discover_query_output_dirs, scan_for_output_secrets, select_submission_query_dirs


def add_relationship_snapshot(config: Config) -> None:
    pd.DataFrame(
        [{"SEGMENTID": "s1", "NAME": "Audience A", "TOTALMEMBERS": 10, "CREATEDTIME": "2026-01-01", "UPDATEDTIME": "2026-01-02"}]
    ).to_parquet(config.dbsnapshot_dir / "dim_segment.parquet", index=False)
    pd.DataFrame([{"SEGMENTID": "s1", "TARGETID": "t1"}]).to_parquet(
        config.dbsnapshot_dir / "hkg_br_segment_target.parquet", index=False
    )
    pd.DataFrame([{"TARGETID": "t1", "DATAFLOWNAME": "SMS Opt-In", "NAME": "sms-target"}]).to_parquet(
        config.dbsnapshot_dir / "dim_target.parquet", index=False
    )


def test_relationship_sql_generation_and_no_row_limit(tiny_project):
    add_relationship_snapshot(tiny_project)
    db = DuckDBDatabase(tiny_project)
    schema = SchemaIndex.build(db)
    query = "List all segment audiences connected to the destination named 'SMS Opt-In'. Remove any row limit from the results."
    template = find_sql_template(query, schema)
    assert template is not None
    assert "JOIN" in template.sql
    assert "hkg_br_segment_target" in template.sql
    assert "LIMIT" not in template.sql.upper()
    result = db.execute_sql(template.sql, allow_full_result=template.allow_full_result)
    assert result["ok"] is True
    assert result["row_count"] == 1


def test_api_templates_for_inactive_and_journey_name():
    inactive = find_api_templates("Give me inactive journeys")
    assert inactive[0].path == "/ajo/journey"
    assert inactive[0].params == {"filter": "status!=live"}

    named = find_api_templates("When was the journey 'Birthday Message' published?")
    assert named[0].params == {"filter": "name==Birthday Message"}


def test_api_param_scoring():
    generated = [{"method": "GET", "path": "/ajo/journey", "params": {"filter": "name==Birthday Message"}}]
    gold = ["GET https://platform.adobe.io/ajo/journey?filter=name==Birthday"]
    score, reason = score_api(generated, gold)
    assert score > 0.75
    assert "params" in reason


def test_answer_synthesis_for_unpublished_and_published_journey():
    unpublished = synthesize_answer(
        "When was the journey 'Birthday Message' published?",
        [
            {
                "type": "sql",
                "payload": {
                    "ok": True,
                    "rows": [{"campaign_name": "Birthday Message", "published_time": None}],
                    "row_count": 1,
                },
            },
            {"type": "api", "payload": {"ok": True, "result_preview": []}},
        ],
    )
    assert "has not been published" in unpublished

    published = synthesize_answer(
        "When was the journey 'Welcome' published?",
        [{"type": "sql", "payload": {"ok": True, "rows": [{"campaign_name": "Welcome", "published_time": "2026-01-01"}]}}],
    )
    assert "was published at 2026-01-01" in published


def test_hidden_output_packager_helpers_and_no_secret_scan(tmp_path: Path):
    outputs = tmp_path / "outputs"
    qdir = outputs / "eval" / "example_001" / "template_first"
    qdir.mkdir(parents=True)
    (qdir / "metadata.json").write_text("{}", encoding="utf-8")
    (qdir / "filled_system_prompt.txt").write_text("prompt", encoding="utf-8")
    (qdir / "trajectory.json").write_text(
        json.dumps({"strategy": "TEMPLATE_FIRST", "original_query": "q"}),
        encoding="utf-8",
    )
    found = discover_query_output_dirs(outputs)
    assert found == [qdir]
    assert select_submission_query_dirs(found, "TEMPLATE_FIRST") == [qdir]

    final_dir = outputs / "final_submission"
    final_dir.mkdir()
    (final_dir / "safe.txt").write_text("Authorization: [REDACTED]", encoding="utf-8")
    assert scan_for_output_secrets(final_dir)["ok"] is True
