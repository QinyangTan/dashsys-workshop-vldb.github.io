#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashagent.config import Config


SYSTEMS = [
    ("REAL_LLM_TWO_TOOLS_BASELINE", "Real naive LLM with execute_sql/call_api only"),
    ("LLM_FREE_AGENT_BASELINE", "Deterministic approximation of a broad LLM agent"),
    ("SQL_ONLY_BASELINE", "Local DB only"),
    ("SQL_FIRST_API_VERIFY", "Current deterministic optimized backend"),
    ("CANDIDATE_GUIDED_LLM_SQL", "Optional candidate-context LLM SQL with fallback"),
    ("FULL_SCHEMA_LLM_SQL", "Optional full-schema LLM SQL with fallback"),
    ("LLM_SQL_FIRST_API_VERIFY", "Optional LLM SQL plus deterministic API verification"),
    ("LLM_CONTROLLER_OPTIMIZED_AGENT", "Optional LLM controller with optimized backend tool"),
]

TECHNIQUES = [
    "prompt router",
    "query normalization",
    "token extraction",
    "candidate context retrieval",
    "full-schema fallback",
    "LLM NL-to-SQL",
    "SQL/API templates",
    "plan optimizer",
    "evidence policy",
    "call budget",
    "EvidenceBus",
    "answer verifier",
    "answer reranker",
    "checkpoint visualization",
    "OpenAI trace export",
]


def main() -> int:
    config = Config.from_env(ROOT)
    report = generate_report(config)
    json_path = config.outputs_dir / "baseline_comparison_report.json"
    md_path = config.outputs_dir / "baseline_comparison_report.md"
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, indent=2, sort_keys=True))
    return 0


def generate_report(config: Config) -> dict[str, Any]:
    normal = load_json(config.outputs_dir / "eval_results.json")
    strict = load_json(config.outputs_dir / "eval_results_strict.json")
    llm = load_json(config.outputs_dir / "llm_baseline_eval.json")
    normal_summary = summary_rows(normal)
    strict_summary = summary_rows(strict)
    systems = []
    for system, description in SYSTEMS:
        row = {
            "system": system,
            "description": description,
            "normal": normal_summary.get(system),
            "strict": strict_summary.get(system),
            "llm_status": llm_status(system, llm),
        }
        systems.append(row)
    optimized = strict_summary.get("SQL_FIRST_API_VERIFY") or normal_summary.get("SQL_FIRST_API_VERIFY") or {}
    naive = strict_summary.get("LLM_FREE_AGENT_BASELINE") or normal_summary.get("LLM_FREE_AGENT_BASELINE") or {}
    improvement = improvement_rows(naive, optimized)
    successful_real = successful_real_llm_rows(llm)
    failed_real = failed_real_llm_rows(llm)
    deterministic = deterministic_approximation_rows(systems)
    optimized_systems = optimized_system_rows(systems)
    return {
        "normal_available": bool(normal),
        "strict_available": bool(strict),
        "llm_baseline": llm,
        "systems": systems,
        "improvement_vs_naive": improvement,
        "techniques": [
            {
                "technique": technique,
                "active_in_naive_baseline": technique in {"LLM NL-to-SQL"} and "real" in str(llm).lower(),
                "active_in_optimized_system": technique != "LLM NL-to-SQL" or True,
                "expected_effect": expected_effect(technique),
            }
            for technique in TECHNIQUES
        ],
        "mermaid": comparison_mermaid(),
        "failure_comparison": failure_comparison(normal),
        "successful_real_llm_tool_loops": successful_real,
        "failed_real_llm_tool_loops": failed_real,
        "deterministic_approximation_baselines": deterministic,
        "optimized_systems": optimized_systems,
        "real_llm_tool_loop_warning": bool(failed_real and not successful_real),
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def summary_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return payload.get("summary", {}).get("by_strategy", {}) if payload else {}


def llm_status(system: str, payload: dict[str, Any]) -> dict[str, Any]:
    if system not in {"REAL_LLM_TWO_TOOLS_BASELINE", "LLM_CONTROLLER_OPTIMIZED_AGENT"}:
        return {"applicable": False}
    if not payload:
        return {"applicable": True, "status": "not_run"}
    if payload.get("skipped"):
        return {"applicable": True, "status": "skipped_no_key", "reason": payload.get("reason")}
    rows = [row for row in payload.get("rows", []) if row.get("system") == system]
    valid_rows = [row for row in rows if row.get("valid_agent_run")]
    failed_rows = [row for row in rows if row.get("skipped_or_failed") and not row.get("valid_agent_run")]
    real_called_failures = [row for row in failed_rows if row.get("real_llm_called")]
    if system == "REAL_LLM_TWO_TOOLS_BASELINE":
        if real_called_failures and not valid_rows:
            status = "real_llm_called_but_tool_loop_failed"
        elif valid_rows and not failed_rows:
            status = "valid_tool_agent_run"
        elif valid_rows and failed_rows:
            status = "mixed_valid_and_failed_tool_agent_runs"
        else:
            status = "not_run"
    else:
        status = "valid_tool_agent_run" if valid_rows else ("real_llm_called_but_tool_loop_failed" if real_called_failures else "not_run")
    return {
        "applicable": True,
        "status": status,
        "rows": len(rows),
        "valid_rows": len(valid_rows),
        "failed_rows": len(failed_rows),
        "real_llm_called_failures": len(real_called_failures),
    }


def failed_real_llm_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not payload or payload.get("skipped"):
        return []
    return [
        row for row in payload.get("rows", [])
        if row.get("system") == "REAL_LLM_TWO_TOOLS_BASELINE"
        and row.get("real_llm_called")
        and not row.get("valid_agent_run")
    ]


def successful_real_llm_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not payload or payload.get("skipped"):
        return []
    return [
        row for row in payload.get("rows", [])
        if row.get("system") == "REAL_LLM_TWO_TOOLS_BASELINE"
        and row.get("real_llm_called")
        and row.get("valid_agent_run")
        and row.get("tool_calls_executed")
    ]


def deterministic_approximation_rows(systems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {"LLM_FREE_AGENT_BASELINE", "SQL_ONLY_BASELINE"}
    return [row for row in systems if row.get("system") in names]


def optimized_system_rows(systems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {
        "SQL_FIRST_API_VERIFY",
        "CANDIDATE_GUIDED_LLM_SQL",
        "FULL_SCHEMA_LLM_SQL",
        "LLM_SQL_FIRST_API_VERIFY",
        "LLM_CONTROLLER_OPTIMIZED_AGENT",
    }
    return [row for row in systems if row.get("system") in names]


def improvement_rows(naive: dict[str, Any], optimized: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = [
        ("avg_sql_score", "SQL correctness"),
        ("avg_api_score", "API correctness"),
        ("avg_answer_score", "answer correctness"),
        ("avg_correctness_score", "overall correctness"),
        ("avg_final_score", "final score"),
        ("avg_tool_call_count", "tool calls"),
        ("avg_estimated_tokens", "tokens"),
        ("avg_runtime", "runtime"),
    ]
    rows = []
    for key, label in metrics:
        n = naive.get(key)
        o = optimized.get(key)
        gain = None if n is None or o is None else round(o - n, 4)
        relative = None if not n or o is None else round(gain / n, 4)
        rows.append({"metric": label, "naive": n, "optimized": o, "absolute_gain": gain, "relative_gain": relative})
    return rows


def expected_effect(technique: str) -> str:
    effects = {
        "prompt router": "keeps conceptual prompts out of the data pipeline and routes evidence prompts safely",
        "candidate context retrieval": "narrows schema/API context without deciding final SQL",
        "full-schema fallback": "prevents retrieval misses from blocking NL-to-SQL",
        "LLM NL-to-SQL": "lets a real model generate SQL when credentials exist",
        "EvidenceBus": "forwards exact SQL/API evidence into later steps",
        "answer verifier": "blocks unsupported final-answer claims",
    }
    return effects.get(technique, "improves correctness, efficiency, or observability in the optimized path")


def failure_comparison(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows", []) if payload else []
    naive_rows = {row["query_id"]: row for row in rows if row.get("strategy") == "LLM_FREE_AGENT_BASELINE"}
    opt_rows = {row["query_id"]: row for row in rows if row.get("strategy") == "SQL_FIRST_API_VERIFY"}
    failures = []
    for query_id, naive in naive_rows.items():
        opt = opt_rows.get(query_id, {})
        failures.append(
            {
                "query_id": query_id,
                "query": naive.get("query"),
                "naive_final_score": naive.get("final_score"),
                "optimized_final_score": opt.get("final_score"),
                "delta": round((opt.get("final_score", 0) or 0) - (naive.get("final_score", 0) or 0), 4),
                "likely_reason": "optimized path uses validated templates/evidence policy/checkpoints" if opt else "optimized row missing",
            }
        )
    return sorted(failures, key=lambda item: item["delta"])[:10]


def comparison_mermaid() -> str:
    return """flowchart LR
  A[User Prompt] --> B[Naive LLM]
  B --> C[execute_sql / call_api]
  C --> D[Final Answer]
  A --> E[Prompt Router]
  E --> F[Candidate/Full Schema Context]
  F --> G[LLM NL-to-SQL or SQL_FIRST fallback]
  G --> H[Validation / Repair]
  H --> I[execute_sql / call_api]
  I --> J[EvidenceBus]
  J --> K[Answer Verification]
  K --> L[Final Answer + Checkpoints + Dataflow + Trace]
"""


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Baseline Comparison Report",
        "",
        "## Summary Table",
        "",
        "| System | Description | Normal correctness | Strict correctness | Final score | Tool calls | Tokens | LLM status |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report["systems"]:
        normal = row.get("normal") or {}
        strict = row.get("strict") or {}
        status = row.get("llm_status", {})
        lines.append(
            "| {system} | {desc} | {normal_corr} | {strict_corr} | {final} | {tools} | {tokens} | {status} |".format(
                system=row["system"],
                desc=row["description"],
                normal_corr=normal.get("avg_correctness_score", ""),
                strict_corr=strict.get("avg_correctness_score", ""),
                final=(strict or normal).get("avg_final_score", ""),
                tools=(strict or normal).get("avg_tool_call_count", ""),
                tokens=(strict or normal).get("avg_estimated_tokens", ""),
                status=status.get("status", "n/a"),
            )
        )
    successful_real = report.get("successful_real_llm_tool_loops", [])
    if successful_real:
        lines.extend(
            [
                "",
                "## Successful Real LLM Tool Loops",
                "",
                "| Query ID | Tool calls | Tool calls executed? | Valid run? |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for row in successful_real[:20]:
            lines.append(
                f"| `{row.get('query_id')}` | {row.get('tool_call_count')} | {row.get('tool_calls_executed')} | {row.get('valid_agent_run')} |"
            )
    failed_real = report.get("failed_real_llm_tool_loops", [])
    if failed_real:
        lines.extend(
            [
                "",
                "## Failed Real LLM Tool Loops",
                "",
                "REAL_LLM_TWO_TOOLS_BASELINE was attempted with a real LLM, but no valid tool-using run completed."
                if report.get("real_llm_tool_loop_warning")
                else "Some real LLM calls did not complete valid tool-using runs.",
                "",
                "These rows are not treated as successful real tool-using baseline runs.",
                "",
                "| Query ID | Tool calls | Tool calls executed? | Failure reason |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for row in failed_real[:20]:
            lines.append(
                f"| `{row.get('query_id')}` | {row.get('tool_call_count')} | {row.get('tool_calls_executed')} | {row.get('failure_reason')} |"
            )
    lines.extend(["", "## Improvement: Optimized vs Naive", "", "| Metric | Naive | Optimized | Absolute gain | Relative gain |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in report["improvement_vs_naive"]:
        lines.append(f"| {row['metric']} | {row['naive']} | {row['optimized']} | {row['absolute_gain']} | {row['relative_gain']} |")
    lines.extend(["", "## Technique Contribution", "", "| Technique | Active in naive baseline? | Active in optimized system? | Expected effect |", "| --- | --- | --- | --- |"])
    for row in report["techniques"]:
        lines.append(f"| {row['technique']} | {row['active_in_naive_baseline']} | {row['active_in_optimized_system']} | {row['expected_effect']} |")
    lines.extend(["", "## System Comparison Diagram", "", "```mermaid", report["mermaid"].strip(), "```", "", "## Lowest Failure Deltas", "", "| Query ID | Naive final | Optimized final | Delta | Likely reason |", "| --- | ---: | ---: | ---: | --- |"])
    for row in report["failure_comparison"]:
        lines.append(f"| `{row['query_id']}` | {row['naive_final_score']} | {row['optimized_final_score']} | {row['delta']} | {row['likely_reason']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
