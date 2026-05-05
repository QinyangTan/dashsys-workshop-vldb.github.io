#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashagent.config import Config
from dashagent.eval_harness import EvalHarness, score_answer
from dashagent.llm_tool_agent import run_optimized_llm_controller_agent, run_real_llm_two_tools_baseline


def main() -> int:
    config = Config.from_env(ROOT)
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    harness = EvalHarness(config)
    examples = harness.load_examples()
    if not os.getenv("OPENAI_API_KEY"):
        payload = {
            "skipped": True,
            "reason": "OPENAI_API_KEY is not set",
            "rows": [],
            "systems": ["REAL_LLM_TWO_TOOLS_BASELINE", "LLM_CONTROLLER_OPTIMIZED_AGENT"],
        }
        write_outputs(config, payload)
        print(json.dumps({"skipped": True, "reason": payload["reason"], "json": str(config.outputs_dir / "llm_baseline_eval.json")}, indent=2, sort_keys=True))
        return 0
    rows = []
    for example in examples:
        for system, runner in [
            ("REAL_LLM_TWO_TOOLS_BASELINE", run_real_llm_two_tools_baseline),
            ("LLM_CONTROLLER_OPTIMIZED_AGENT", run_optimized_llm_controller_agent),
        ]:
            start = time.perf_counter()
            result = runner(example.query, config=config)
            elapsed = time.perf_counter() - start
            answer_score, answer_reason = score_answer(result.get("final_answer", ""), example.gold_answer)
            rows.append(
                {
                    "query_id": example.query_id,
                    "query": example.query,
                    "system": system,
                    "answer_score": round(answer_score, 4),
                    "answer_reason": answer_reason,
                    "tool_call_count": result.get("trajectory", {}).get("tool_call_count", 0),
                    "runtime": round(elapsed, 4),
                    "skipped": result.get("skipped", False),
                    "final_answer": result.get("final_answer", ""),
                }
            )
    payload = {"skipped": False, "rows": rows, "systems": ["REAL_LLM_TWO_TOOLS_BASELINE", "LLM_CONTROLLER_OPTIMIZED_AGENT"]}
    write_outputs(config, payload)
    print(json.dumps({"skipped": False, "rows": len(rows), "json": str(config.outputs_dir / "llm_baseline_eval.json")}, indent=2, sort_keys=True))
    return 0


def write_outputs(config: Config, payload: dict) -> None:
    json_path = config.outputs_dir / "llm_baseline_eval.json"
    md_path = config.outputs_dir / "llm_baseline_comparison.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    lines = ["# LLM Baseline Comparison", ""]
    if payload.get("skipped"):
        lines.append(f"REAL_LLM_TWO_TOOLS_BASELINE was skipped because {payload.get('reason')}.")
    else:
        lines.extend(["| System | Rows | Avg answer score | Avg tool calls |", "| --- | ---: | ---: | ---: |"])
        for system in payload.get("systems", []):
            rows = [row for row in payload.get("rows", []) if row.get("system") == system]
            avg_answer = sum(row.get("answer_score", 0) for row in rows) / len(rows) if rows else 0
            avg_tools = sum(row.get("tool_call_count", 0) for row in rows) / len(rows) if rows else 0
            lines.append(f"| {system} | {len(rows)} | {avg_answer:.4f} | {avg_tools:.2f} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
