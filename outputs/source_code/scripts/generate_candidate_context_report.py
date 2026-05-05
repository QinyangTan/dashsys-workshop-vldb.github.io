#!/usr/bin/env python
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashagent.candidate_context_builder import build_candidate_context, build_full_schema_context
from dashagent.config import Config
from dashagent.endpoint_catalog import EndpointCatalog
from dashagent.eval_harness import EvalHarness, extract_api_calls
from dashagent.executor import AgentExecutor
from dashagent.trajectory import estimate_tokens


def main() -> int:
    config = Config.from_env(ROOT)
    report = generate_candidate_context_report(config)
    json_path = config.outputs_dir / "candidate_context_report.json"
    md_path = config.outputs_dir / "candidate_context_report.md"
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "examples": report["examples"]}, indent=2, sort_keys=True))
    return 0


def generate_candidate_context_report(config: Config) -> dict[str, Any]:
    executor = AgentExecutor(config)
    harness = EvalHarness(config, executor)
    examples = harness.load_examples()
    full_context = build_full_schema_context(executor.schema_index, executor.endpoint_catalog)
    full_tokens = estimate_tokens(full_context)
    rows = []
    table_recall3 = []
    table_recall5 = []
    api_recall3 = []
    api_recall5 = []
    candidate_tokens = []
    for example in examples:
        context = build_candidate_context(example.query, executor.schema_index, executor.endpoint_catalog)
        candidate_tokens.append(context.get("estimated_tokens", 0))
        gold_tables = extract_sql_tables(example.gold_sql)
        gold_apis = [call.get("path") for call in extract_api_calls(example.gold_api)]
        tables = context.get("candidate_tables", [])
        apis = [api.get("path") for api in context.get("candidate_apis", [])]
        row = {
            "query_id": example.query_id,
            "query": example.query,
            "candidate_tables": tables,
            "candidate_join_hints": context.get("candidate_join_hints", []),
            "candidate_apis": context.get("candidate_apis", []),
            "confidence": context.get("confidence"),
            "score_margin": context.get("score_margin"),
            "used_gold_patterns": context.get("used_gold_patterns", False),
            "candidate_context_tokens": context.get("estimated_tokens", 0),
            "full_schema_context_tokens": full_tokens,
            "gold_tables": sorted(gold_tables),
            "gold_api_paths": gold_apis,
        }
        if gold_tables:
            r3 = recall_at_k(tables, gold_tables, 3)
            r5 = recall_at_k(tables, gold_tables, 5)
            table_recall3.append(r3)
            table_recall5.append(r5)
            row["table_recall_at_3"] = r3
            row["table_recall_at_5"] = r5
        if gold_apis:
            r3 = recall_at_k(apis, set(gold_apis), 3, normalize=False)
            r5 = recall_at_k(apis, set(gold_apis), 5, normalize=False)
            api_recall3.append(r3)
            api_recall5.append(r5)
            row["api_recall_at_3"] = r3
            row["api_recall_at_5"] = r5
        rows.append(row)
    avg_candidate = avg(candidate_tokens)
    return {
        "examples": len(examples),
        "used_gold_patterns": False,
        "summary": {
            "avg_candidate_context_tokens": avg_candidate,
            "avg_full_schema_context_tokens": full_tokens,
            "compression_ratio": round(avg_candidate / full_tokens, 4) if full_tokens else 0.0,
            "table_recall_at_3": avg(table_recall3),
            "table_recall_at_5": avg(table_recall5),
            "api_recall_at_3": avg(api_recall3),
            "api_recall_at_5": avg(api_recall5),
        },
        "rows": rows,
    }


def extract_sql_tables(sql: str | None) -> set[str]:
    if not sql:
        return set()
    identifier = r"(?:\"[^\"]+\"|`[^`]+`|[A-Za-z_][\w$]*)(?:\s*\.\s*(?:\"[^\"]+\"|`[^`]+`|[A-Za-z_][\w$]*))*"
    matches = re.findall(rf"\b(?:FROM|JOIN)\s+({identifier})", sql, flags=re.IGNORECASE)
    return {match for match in matches}


def normalize_table_name(name: str) -> str:
    value = str(name or "").strip().rstrip(";")
    parts = [part.strip().strip('"').strip("`").strip("'") for part in re.split(r"\s*\.\s*", value) if part.strip()]
    return (parts[-1] if parts else value.strip('"').strip("`").strip("'")).lower()


def recall_at_k(candidates: list[str], gold: set[str], k: int, *, normalize: bool = True) -> float:
    normalized_gold = {normalize_table_name(item) for item in gold if normalize_table_name(item)} if normalize else set(gold)
    if not normalized_gold:
        return 0.0
    if normalize:
        top = {normalize_table_name(item) for item in candidates[:k] if normalize_table_name(item)}
    else:
        top = set(candidates[:k])
    return round(len(top & normalized_gold) / len(normalized_gold), 4)


def avg(values: list[float | int]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Candidate Context Report",
        "",
        "Candidate context is schema/API retrieval only. It does not use public gold patterns or decide final SQL.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report.get("summary", {}).items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Per Example",
            "",
            "| Query ID | Tables | APIs | Confidence | Used gold patterns |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in report.get("rows", [])[:50]:
        tables = ", ".join(row.get("candidate_tables", [])[:5])
        apis = ", ".join(api.get("id", "") for api in row.get("candidate_apis", [])[:5])
        lines.append(f"| `{row.get('query_id')}` | {tables} | {apis} | {row.get('confidence')} | {row.get('used_gold_patterns')} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
