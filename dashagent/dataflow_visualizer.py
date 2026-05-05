from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .trajectory import compact_preview, redact_secrets


def load_trajectory(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_checkpoint_map(trajectory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(checkpoint.get("checkpoint_id")): checkpoint
        for checkpoint in trajectory.get("checkpoints", []) or []
        if checkpoint.get("checkpoint_id")
    }


def extract_prompt_router_decision(trajectory: dict[str, Any]) -> dict[str, Any]:
    checkpoints = extract_checkpoint_map(trajectory)
    checkpoint = checkpoints.get("checkpoint_00_prompt_router") or {}
    output = checkpoint.get("output") or {}
    if isinstance(output, dict):
        return output
    for step in trajectory.get("steps", []):
        if step.get("kind") == "prompt_router":
            return step
    return {}


def extract_sql_api_steps(trajectory: dict[str, Any]) -> dict[str, Any]:
    sql_calls = [step for step in trajectory.get("steps", []) if step.get("kind") == "sql_call"]
    api_calls = [step for step in trajectory.get("steps", []) if step.get("kind") == "api_call"]
    return {"sql_calls": sql_calls, "api_calls": api_calls}


def extract_prompt_to_sql_api_mapping(trajectory: dict[str, Any]) -> dict[str, Any]:
    checkpoints = extract_checkpoint_map(trajectory)
    sql_api = extract_sql_api_steps(trajectory)
    return redact_secrets(
        {
            "prompt": trajectory.get("original_query"),
            "route": extract_prompt_router_decision(trajectory),
            "normalization": (checkpoints.get("checkpoint_02_query_normalization") or {}).get("output", {}),
            "tokens": (checkpoints.get("checkpoint_03_query_tokens") or {}).get("output", {}),
            "candidate_or_metadata": (checkpoints.get("checkpoint_07_context_card") or {}).get("output", {}),
            "llm_sql_generation": (checkpoints.get("checkpoint_llm_sql_generation") or {}).get("output", {}),
            "sql_calls": compact_preview(sql_api["sql_calls"], 1200),
            "api_calls": compact_preview(sql_api["api_calls"], 1200),
            "evidence_bus": (checkpoints.get("checkpoint_14_evidence_bus") or {}).get("output", {}),
            "answer_slots": (checkpoints.get("checkpoint_15_answer_slots") or {}).get("output", {}),
            "answer_verification": (checkpoints.get("checkpoint_16_answer_verification") or {}).get("output", {}),
            "final_answer": trajectory.get("final_answer"),
        }
    )


def build_mermaid_graph(trajectory: dict[str, Any]) -> str:
    mapping = extract_prompt_to_sql_api_mapping(trajectory)
    route = mapping.get("route") or {}
    sql_api = extract_sql_api_steps(trajectory)
    generated_sql = sql_api["sql_calls"][0].get("sql") if sql_api["sql_calls"] else "none"
    generated_api = "none"
    if sql_api["api_calls"]:
        first_api = sql_api["api_calls"][0]
        generated_api = f"{first_api.get('method')} {first_api.get('url')}"
    final_answer = str(trajectory.get("final_answer") or "")[:160]
    lines = [
        "flowchart TD",
        "  subgraph Input",
        f"    A[\"User Prompt<br/>{_m(str(trajectory.get('original_query') or ''))}\"]",
        f"    B[\"Prompt Router<br/>mode={_m(str(route.get('mode', 'unknown')))}<br/>policy={_m(str(route.get('api_policy', 'unknown')))}\"]",
        "    A -->|route_prompt| B",
        "  end",
        "  subgraph QueryUnderstanding[Query Understanding]",
        "    C[\"Query Normalization<br/>normalized_query + rewrites\"]",
        "    D[\"Tokens / Entities<br/>names + ids + dates + metrics\"]",
        "    E[\"Relevance / QueryAnalysis<br/>tables + APIs + answer family\"]",
        "    B -->|normalized text| C",
        "    C -->|query_tokens| D",
        "    D -->|route/domain/family| E",
        "  end",
        "  subgraph ContextPlanning[Context And Planning]",
        "    F[\"Candidate / Context Card<br/>selected tables + APIs\"]",
        "    G[\"LLM SQL or Template Plan<br/>candidate/full schema + fallback\"]",
        "    H[\"Plan Optimization<br/>budget + dedupe + placeholders\"]",
        "    E -->|selected_metadata| F",
        "    F -->|schema/API context| G",
        "    G -->|draft_plan| H",
        "  end",
        "  subgraph ValidationExecution[Validation And Execution]",
        f"    I[\"SQL Validation<br/>{_m(str(generated_sql)[:90])}\"]",
        f"    J[\"API Validation<br/>{_m(str(generated_api)[:90])}\"]",
        "    K[\"Tool Results<br/>sql_rows + api_payload/dry_run\"]",
        "    H -->|optimized_plan| I",
        "    H -->|api_steps| J",
        "    I -->|execute_sql| K",
        "    J -->|call_api or dry-run| K",
        "  end",
        "  subgraph EvidenceAnswer[Evidence And Answer]",
        "    L[\"EvidenceBus<br/>IDs + names + counts + timestamps\"]",
        "    M[\"Answer Slots<br/>entity + count + status + dry_run\"]",
        "    N[\"Answer Verification<br/>claims + caveats + reranking\"]",
        f"    O[\"Final Answer<br/>{_m(final_answer)}\"]",
        "    K -->|extract structured facts| L",
        "    L -->|forward evidence_slots| M",
        "    M -->|verify claims| N",
        "    N -->|verified_answer| O",
        "  end",
        "  subgraph Artifacts",
        "    P[\"metadata.json<br/>filled_system_prompt.txt<br/>trajectory.json<br/>reports\"]",
        "    O -->|write reproducible trace| P",
        "  end",
    ]
    return "\n".join(lines) + "\n"


def build_checkpoint_effect_table(trajectory: dict[str, Any]) -> str:
    lines = [
        "| Checkpoint | Technique | Input | Output | Effect on data flow | Correctness role | Efficiency role |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for checkpoint in trajectory.get("checkpoints", []) or []:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                _md(checkpoint.get("checkpoint_id")),
                _md(checkpoint.get("technique")),
                _md(_brief(checkpoint.get("input_summary"))),
                _md(_brief(checkpoint.get("output") or checkpoint.get("output_summary"))),
                _md(checkpoint.get("effect")),
                _md(checkpoint.get("correctness_role")),
                _md(checkpoint.get("efficiency_role")),
            )
        )
    return "\n".join(lines) + "\n"


def build_markdown_report(trajectory: dict[str, Any]) -> str:
    mapping = extract_prompt_to_sql_api_mapping(trajectory)
    return "\n".join(
        [
            "# DASHSys Prompt-To-Answer Dataflow",
            "",
            f"- Query ID: `{trajectory.get('query_id')}`",
            f"- Strategy: `{trajectory.get('strategy')}`",
            f"- Tool calls: `{trajectory.get('tool_call_count', 0)}`",
            "",
            "```mermaid",
            build_mermaid_graph(trajectory).strip(),
            "```",
            "",
            "## Prompt To SQL/API Mapping",
            "",
            "```json",
            json.dumps(redact_secrets(compact_preview(mapping, 4000)), indent=2, sort_keys=True, default=str),
            "```",
            "",
            "## Checkpoint Effect Table",
            "",
            build_checkpoint_effect_table(trajectory).strip(),
            "",
        ]
    )


def build_html_report(trajectory: dict[str, Any]) -> str:
    markdown = build_markdown_report(trajectory)
    graph = build_mermaid_graph(trajectory)
    table = build_checkpoint_effect_table(trajectory)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>DASHSys Dataflow</title>
  <script type="module">import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs'; mermaid.initialize({{startOnLoad:true}});</script>
  <style>body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:32px;line-height:1.45}} pre{{background:#f6f8fa;padding:12px;overflow:auto}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #d0d7de;padding:6px;vertical-align:top}}</style>
</head>
<body>
  <h1>DASHSys Prompt-To-Answer Dataflow</h1>
  <div class="mermaid">{html.escape(graph)}</div>
  <h2>Checkpoint Effect Table</h2>
  <pre>{html.escape(table)}</pre>
  <h2>Markdown Source</h2>
  <pre>{html.escape(markdown)}</pre>
</body>
</html>
"""


def _brief(value: Any) -> str:
    if value in (None, "", {}, []):
        return ""
    compact = compact_preview(value, 260)
    if isinstance(compact, (dict, list)):
        return json.dumps(compact, sort_keys=True, default=str)
    return str(compact)


def _m(text: str) -> str:
    return html.escape(text.replace("\n", " "))[:180]


def _md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")[:500]
