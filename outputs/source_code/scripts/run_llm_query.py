#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashagent.config import Config
from dashagent.executor import AgentExecutor, slugify
from dashagent.llm_tool_agent import run_optimized_llm_controller_agent, run_real_llm_two_tools_baseline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a DASHSys query through deterministic, optimized LLM, or naive LLM baseline modes.")
    parser.add_argument("query")
    parser.add_argument("--mode", choices=["deterministic", "optimized", "baseline", "candidate-sql", "full-schema-sql"], default="optimized")
    args = parser.parse_args()
    config = Config.from_env(ROOT)
    qid = slugify(args.query)
    if args.mode == "deterministic":
        result = AgentExecutor(config).run(args.query, strategy="SQL_FIRST_API_VERIFY", query_id=qid)
        summary = _summary(args.mode, result["final_answer"], result["trajectory"], result["output_dir"], False, True)
    elif args.mode == "candidate-sql":
        result = AgentExecutor(config).run(args.query, strategy="CANDIDATE_GUIDED_LLM_SQL", query_id=qid)
        summary = _summary(args.mode, result["final_answer"], result["trajectory"], result["output_dir"], False, True)
    elif args.mode == "full-schema-sql":
        result = AgentExecutor(config).run(args.query, strategy="FULL_SCHEMA_LLM_SQL", query_id=qid)
        summary = _summary(args.mode, result["final_answer"], result["trajectory"], result["output_dir"], False, True)
    elif args.mode == "baseline":
        result = run_real_llm_two_tools_baseline(args.query, config=config)
        summary = _summary(args.mode, result.get("final_answer", ""), result.get("trajectory", {}), None, result.get("real_llm_used", False), result.get("backend_used", False))
        summary["skipped"] = result.get("skipped", False)
        summary["skipped_reason"] = result.get("skipped_reason")
    else:
        result = run_optimized_llm_controller_agent(args.query, config=config)
        summary = _summary(args.mode, result.get("final_answer", ""), result.get("trajectory", {}), None, result.get("real_llm_used", False), result.get("backend_used", False))
        summary["skipped"] = result.get("skipped", False)
        summary["skipped_reason"] = result.get("skipped_reason")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def _summary(mode: str, answer: str, trajectory: dict, output_dir: str | None, real_llm_used: bool, backend_used: bool) -> dict:
    return {
        "mode": mode,
        "final_answer": answer,
        "real_llm_used": real_llm_used,
        "backend_used": backend_used,
        "tool_call_count": trajectory.get("tool_call_count", 0),
        "output_dir": output_dir,
        "trajectory_path": str(Path(output_dir) / "trajectory.json") if output_dir else None,
        "provider": trajectory.get("llm_provider") or ("openai" if real_llm_used else "none"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
