from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .answer_templates import classify_answer_family
from .config import Config, DEFAULT_CONFIG


FAMILY_MAP = {
    "audit_destination_mapping": "audit",
    "audit_entity_created": "audit",
    "batch": "batch",
    "destination_export": "destination_dataflow",
    "failed_dataflow_runs": "destination_dataflow",
    "inactive_journeys": "journey_campaign",
    "journey_published": "journey_campaign",
    "list_journeys": "journey_campaign",
    "merge_policy": "merge_policy",
    "observability_metrics": "observability",
    "property_field": "property_field",
    "schema_dataset": "schema_dataset",
    "segment_definitions": "segment_audience",
    "segment_destination": "segment_audience",
    "segment_jobs": "segment_audience",
    "tags": "tags",
}


def query_family(query: str) -> str:
    return FAMILY_MAP.get(classify_answer_family(query), "unknown")


def generate_family_score_report(config: Config | None = None) -> dict[str, Any]:
    cfg = config or DEFAULT_CONFIG
    payload = load_eval_payload(cfg)
    rows = [row for row in payload.get("rows", []) if row.get("strategy") == "SQL_FIRST_API_VERIFY"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[query_family(row.get("query", ""))].append(row)
    families = {}
    for family, family_rows in sorted(grouped.items()):
        lowest = sorted(family_rows, key=lambda row: row.get("final_score", 0))[:3]
        families[family] = {
            "example_count": len(family_rows),
            "avg_sql_score": avg(row.get("sql_score", 0) for row in family_rows),
            "avg_api_score": avg(row.get("api_score", 0) for row in family_rows),
            "avg_answer_score": avg(row.get("answer_score", 0) for row in family_rows),
            "avg_correctness": avg(row.get("correctness_score", 0) for row in family_rows),
            "avg_final_score": avg(row.get("final_score", 0) for row in family_rows),
            "avg_tool_calls": avg(row.get("tool_call_count", 0) for row in family_rows),
            "avg_runtime": avg(row.get("runtime", 0) for row in family_rows),
            "avg_estimated_tokens": avg(row.get("estimated_tokens", 0) for row in family_rows),
            "lowest_example_ids": [row.get("query_id") for row in lowest],
            "recommended_next_fix": recommend_family_fix(family, lowest),
        }
    report = {"strategy": "SQL_FIRST_API_VERIFY", "families": families}
    write_family_outputs(cfg, report)
    return report


def generate_pareto_report(config: Config | None = None) -> dict[str, Any]:
    cfg = config or DEFAULT_CONFIG
    payload = load_eval_payload(cfg)
    summary = payload.get("summary", {})
    by_strategy = summary.get("by_strategy", {})
    rows = payload.get("rows", [])
    best_correctness = summary.get("best_correctness")
    best_final = summary.get("best_overall")
    best_efficiency = summary.get("best_efficiency")
    lowest_tool = min(by_strategy, key=lambda s: by_strategy[s].get("avg_tool_call_count", 999)) if by_strategy else None
    lowest_token = min(by_strategy, key=lambda s: by_strategy[s].get("avg_estimated_tokens", 999999)) if by_strategy else None
    by_query = defaultdict(dict)
    for row in rows:
        by_query[row["query_id"]][row["strategy"]] = row
    template_better = []
    unnecessary_api = []
    sql_only_enough = []
    for query_id, strategies in by_query.items():
        sql_first = strategies.get("SQL_FIRST_API_VERIFY")
        template = strategies.get("TEMPLATE_FIRST")
        sql_only = strategies.get("SQL_ONLY_BASELINE")
        if sql_first and template and template["correctness_score"] > sql_first["correctness_score"] and template["final_score"] <= sql_first["final_score"]:
            template_better.append({"query_id": query_id, "template_correctness": template["correctness_score"], "sql_first_final": sql_first["final_score"]})
        if sql_first and sql_first.get("api_call_count", 0) > 0 and sql_first.get("api_score", 1) >= 0.99 and not api_required_by_query(sql_first.get("query", "")):
            unnecessary_api.append({"query_id": query_id, "api_calls": sql_first.get("api_call_count"), "query": sql_first.get("query")})
        if sql_first and sql_only and sql_only["correctness_score"] >= sql_first["correctness_score"] and sql_first.get("api_call_count", 0) > 0:
            sql_only_enough.append({"query_id": query_id, "sql_only_correctness": sql_only["correctness_score"], "sql_first_api_calls": sql_first.get("api_call_count")})
    report = {
        "best_correctness_strategy": best_correctness,
        "best_final_score_strategy": best_final,
        "best_efficiency_strategy": best_efficiency,
        "lowest_tool_call_strategy": lowest_tool,
        "lowest_token_strategy": lowest_token,
        "template_first_correctness_gains_without_final_gain": template_better,
        "sql_first_unnecessary_api_candidates": unnecessary_api,
        "sql_only_enough_but_sql_first_called_api": sql_only_enough,
    }
    write_pareto_outputs(cfg, report)
    return report


def load_eval_payload(config: Config) -> dict[str, Any]:
    path = config.outputs_dir / "eval_results.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def avg(values: Any) -> float:
    values = [float(value) for value in values]
    return round(sum(values) / len(values), 4) if values else 0.0


def recommend_family_fix(family: str, lowest: list[dict[str, Any]]) -> str:
    if not lowest:
        return "No examples in this family."
    worst = lowest[0]
    if worst.get("sql_score", 1) < 0.9:
        return "Prioritize SQL template projection/filter alignment."
    if worst.get("api_score", 1) < 0.9:
        return "Prioritize endpoint/parameter template alignment."
    if worst.get("answer_score", 1) < 0.55:
        return "Add a concise evidence-grounded answer template."
    return "Mostly healthy; monitor efficiency and hidden-query generalization."


def api_required_by_query(query: str) -> bool:
    lowered = query.lower()
    return any(
        token in lowered
        for token in ["api", "audit", "batch", "current", "failed", "live", "merge polic", "observability", "sandbox", "segment definition", "segment job", "status", "tag"]
    )


def write_family_outputs(config: Config, report: dict[str, Any]) -> None:
    json_path = config.outputs_dir / "family_score_report.json"
    md_path = config.outputs_dir / "family_score_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Family Score Report",
        "",
        "| Family | Examples | SQL | API | Answer | Correctness | Final | Tools | Runtime | Tokens | Lowest | Next Fix |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for family, metrics in report["families"].items():
        lines.append(
            f"| {family} | {metrics['example_count']} | {metrics['avg_sql_score']:.4f} | {metrics['avg_api_score']:.4f} | {metrics['avg_answer_score']:.4f} | {metrics['avg_correctness']:.4f} | {metrics['avg_final_score']:.4f} | {metrics['avg_tool_calls']:.2f} | {metrics['avg_runtime']:.4f} | {metrics['avg_estimated_tokens']:.0f} | {', '.join(metrics['lowest_example_ids'])} | {metrics['recommended_next_fix']} |"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def write_pareto_outputs(config: Config, report: dict[str, Any]) -> None:
    json_path = config.outputs_dir / "pareto_report.json"
    md_path = config.outputs_dir / "pareto_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Pareto Report",
        "",
        f"- Best correctness strategy: `{report['best_correctness_strategy']}`",
        f"- Best final-score strategy: `{report['best_final_score_strategy']}`",
        f"- Best efficiency strategy: `{report['best_efficiency_strategy']}`",
        f"- Lowest tool-call strategy: `{report['lowest_tool_call_strategy']}`",
        f"- Lowest token strategy: `{report['lowest_token_strategy']}`",
        "",
        "## Template-First Correctness Gains Without Final Gain",
    ]
    for item in report["template_first_correctness_gains_without_final_gain"][:20]:
        lines.append(f"- {item['query_id']}: template correctness {item['template_correctness']}, SQL_FIRST final {item['sql_first_final']}")
    lines.extend(["", "## SQL_FIRST_API_VERIFY Unnecessary API Candidates"])
    for item in report["sql_first_unnecessary_api_candidates"][:20]:
        lines.append(f"- {item['query_id']}: {item['api_calls']} API call(s) / {item['query']}")
    lines.extend(["", "## SQL_ONLY Enough But SQL_FIRST Called API"])
    for item in report["sql_only_enough_but_sql_first_called_api"][:20]:
        lines.append(f"- {item['query_id']}: SQL-only correctness {item['sql_only_correctness']}, SQL_FIRST API calls {item['sql_first_api_calls']}")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
