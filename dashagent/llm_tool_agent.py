from __future__ import annotations

import json
import re
import time
from typing import Any

from .agent_tools import run_data_answer_tool, verify_answer_tool
from .api_client import AdobeAPIClient
from .candidate_context_builder import build_full_schema_context
from .checkpoints import CheckpointLogger
from .config import Config
from .db import DuckDBDatabase
from .endpoint_catalog import EndpointCatalog
from .llm_client import LLMClient, get_llm_client
from .prompt_router import LLM_DIRECT, route_prompt
from .schema_index import SchemaIndex
from .trajectory import compact_preview, estimate_tokens, redact_secrets
from .validators import APIValidator, SQLValidator


REAL_LLM_TWO_TOOLS_BASELINE = "REAL_LLM_TWO_TOOLS_BASELINE"
LLM_CONTROLLER_OPTIMIZED_AGENT = "LLM_CONTROLLER_OPTIMIZED_AGENT"


def run_real_llm_two_tools_baseline(
    query: str,
    *,
    config: Config | None = None,
    llm_client: LLMClient | None = None,
    max_turns: int = 4,
    max_tool_calls: int = 4,
) -> dict[str, Any]:
    client = llm_client or get_llm_client()
    if not client.available():
        return _skipped_result(query, REAL_LLM_TWO_TOOLS_BASELINE, client, "OPENAI_API_KEY is not set")

    cfg = config or Config.from_env()
    db = DuckDBDatabase(cfg)
    schema_index = SchemaIndex.build(db)
    endpoint_catalog = EndpointCatalog(cfg)
    sql_validator = SQLValidator(schema_index)
    api_validator = APIValidator(endpoint_catalog, allow_unknown=cfg.allow_unknown_api_endpoints)
    api_client = AdobeAPIClient(cfg)
    full_context = build_full_schema_context(schema_index, endpoint_catalog)

    system_prompt = (
        "You are a naive DASHSys LLM agent. You may use exactly two tools: execute_sql and call_api. "
        "Return strict JSON each turn with tool_calls and final_answer. Validate evidence through tools; do not invent facts. "
        "Schema/API context is broad and unoptimized."
    )
    transcript: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    final_answer = ""
    start = time.perf_counter()

    for turn in range(max_turns):
        user_payload = {
            "query": query,
            "schema_context": compact_preview(full_context, 9000),
            "previous_tool_results": compact_preview(transcript, 5000),
            "remaining_tool_calls": max_tool_calls - len(tool_calls),
            "required_json_shape": {
                "tool_calls": [
                    {"tool": "execute_sql", "arguments": {"sql": "SELECT ..."}},
                    {"tool": "call_api", "arguments": {"method": "GET", "url": "/...", "params": {}, "headers": {}}},
                ],
                "final_answer": None,
            },
        }
        response = client.generate(system_prompt, json.dumps(user_payload, indent=2, default=str))
        parsed = _parse_json(response.get("content", ""))
        requested = parsed.get("tool_calls") if isinstance(parsed.get("tool_calls"), list) else []
        if parsed.get("final_answer") and not requested:
            final_answer = str(parsed["final_answer"])
            break
        if not requested:
            final_answer = "The real LLM did not return a valid tool call or final answer."
            break
        turn_results = []
        for raw_call in requested:
            if len(tool_calls) >= max_tool_calls:
                break
            executed = _execute_llm_tool_call(raw_call, db, api_client, sql_validator, api_validator)
            tool_calls.append(executed)
            turn_results.append(executed)
        transcript.append({"turn": turn + 1, "llm_response": compact_preview(parsed, 1000), "tool_results": turn_results})
    if not final_answer:
        final_prompt = {
            "query": query,
            "tool_results": compact_preview(tool_calls, 6000),
            "instruction": "Return a concise final answer grounded only in these tool results.",
        }
        response = client.generate(system_prompt, json.dumps(final_prompt, indent=2, default=str))
        parsed = _parse_json(response.get("content", ""))
        final_answer = str(parsed.get("final_answer") or response.get("content") or "").strip()
    trajectory = {
        "query_id": "real_llm_two_tools",
        "original_query": query,
        "strategy": REAL_LLM_TWO_TOOLS_BASELINE,
        "llm_turns": len(transcript),
        "llm_tool_calls": tool_calls,
        "steps": [
            {"kind": "llm_turn", **item}
            for item in transcript
        ],
        "final_answer": final_answer,
        "real_llm_used": True,
        "runtime": time.perf_counter() - start,
        "tool_call_count": len(tool_calls),
        "estimated_tokens": estimate_tokens({"query": query, "turns": transcript, "answer": final_answer}),
        "errors": [],
    }
    return redact_secrets(
        {
            "mode": REAL_LLM_TWO_TOOLS_BASELINE,
            "llm_provider": client.provider_name(),
            "llm_model": client.model_name(),
            "backend_used": False,
            "real_llm_used": True,
            "skipped": False,
            "final_answer": final_answer,
            "trajectory": trajectory,
            "tool_call_count": len(tool_calls),
        }
    )


def run_optimized_llm_controller_agent(
    query: str,
    *,
    config: Config | None = None,
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    client = llm_client or get_llm_client()
    route = route_prompt(query)
    checkpoints = CheckpointLogger()
    checkpoints.add_checkpoint(
        "checkpoint_llm_controller_decision",
        stage="llm controller",
        technique="prompt routing / controller decision",
        input_summary={"query": query},
        output=route.to_dict(),
        effect="decides whether the LLM can answer directly or should call the optimized backend tool",
        correctness_role="sends data questions to evidence tools",
        efficiency_role="allows conceptual prompts to avoid backend calls",
    )
    if route.mode == LLM_DIRECT:
        checkpoints.add_checkpoint(
            "checkpoint_llm_prompt",
            stage="llm prompt",
            technique="direct LLM response prompt",
            output={"tool_availability": "none", "route_mode": route.mode},
        )
        if not client.available():
            return _controller_fallback(query, client, route, checkpoints.to_list(), backend=None)
        response = client.generate(
            "Answer concise conceptual DASHSys questions. Do not claim local DB/API facts unless evidence is provided.",
            query,
        )
        final_answer = response.get("content", "").strip()
        checkpoints.add_checkpoint(
            "checkpoint_llm_final_response",
            stage="final response",
            technique="LLM direct answer",
            output={"final_answer": final_answer, "groundedness_caveat": "no DB/API evidence required"},
        )
        return {
            "mode": LLM_CONTROLLER_OPTIMIZED_AGENT,
            "llm_provider": client.provider_name(),
            "llm_model": client.model_name(),
            "backend_used": False,
            "real_llm_used": True,
            "final_answer": final_answer,
            "evidence_summary": {},
            "trajectory": {"checkpoints": checkpoints.to_list(), "final_answer": final_answer, "tool_call_count": 0},
        }

    backend = run_data_answer_tool(query, config=config)
    checkpoints.add_checkpoint(
        "checkpoint_llm_tool_call",
        stage="llm tool call",
        technique="optimized backend tool call",
        input_summary={"tool": "run_data_answer_tool", "query": query},
        output={
            "tool_call_count": backend.get("diagnostics", {}).get("tool_call_count"),
            "backend_answer": backend.get("final_answer"),
        },
        effect="uses optimized SQL/API backend as a high-level evidence tool",
        correctness_role="grounds final answer in validated backend evidence",
        efficiency_role="one high-level backend call instead of free-form tool probing",
    )
    if not client.available():
        return _controller_fallback(query, client, route, checkpoints.to_list(), backend=backend)
    prompt = {
        "query": query,
        "route": route.to_dict(),
        "backend_answer": backend.get("final_answer"),
        "diagnostics": backend.get("diagnostics", {}),
        "tool_results_summary": backend.get("tool_results_summary"),
        "instruction": "Write a concise final answer grounded only in backend evidence. Include dry-run/API-unavailable caveats when present.",
    }
    checkpoints.add_checkpoint(
        "checkpoint_llm_prompt",
        stage="llm prompt",
        technique="grounded final response prompt",
        output={"tool_availability": "run_data_answer_tool", "route_mode": route.mode},
    )
    response = client.generate(
        "You are the DASHSys LLM controller. Use backend evidence only; never invent IDs, counts, dates, statuses, or API confirmations.",
        json.dumps(prompt, indent=2, default=str),
    )
    proposed = response.get("content", "").strip() or backend.get("final_answer", "")
    verification = verify_answer_tool(query, proposed, {"tool_results": backend.get("trajectory", {}).get("steps", [])})
    final_answer = verification.get("safer_rewritten_answer") or proposed
    checkpoints.add_checkpoint(
        "checkpoint_llm_final_response",
        stage="final response",
        technique="grounded LLM final response",
        output={
            "final_answer": final_answer,
            "verifier_passed": verification.get("verifier_passed"),
            "groundedness_caveat": "backend evidence used",
        },
    )
    trajectory = dict(backend.get("trajectory", {}))
    trajectory["llm_controller_checkpoints"] = checkpoints.to_list()
    trajectory["final_answer"] = final_answer
    return {
        "mode": LLM_CONTROLLER_OPTIMIZED_AGENT,
        "llm_provider": client.provider_name(),
        "llm_model": client.model_name(),
        "backend_used": True,
        "real_llm_used": True,
        "final_answer": final_answer,
        "evidence_summary": backend.get("tool_results_summary", {}),
        "trajectory": trajectory,
    }


def _controller_fallback(
    query: str,
    client: LLMClient,
    route: Any,
    checkpoints: list[dict[str, Any]],
    *,
    backend: dict[str, Any] | None,
) -> dict[str, Any]:
    final_answer = (
        backend.get("final_answer")
        if backend
        else "OPENAI_API_KEY is not set; LLM direct response was skipped."
    )
    trajectory = backend.get("trajectory", {}) if backend else {}
    trajectory = dict(trajectory)
    trajectory["llm_controller_checkpoints"] = checkpoints
    trajectory["llm_skipped_reason"] = "OPENAI_API_KEY is not set"
    return {
        "mode": LLM_CONTROLLER_OPTIMIZED_AGENT,
        "llm_provider": client.provider_name(),
        "llm_model": client.model_name(),
        "backend_used": bool(backend),
        "real_llm_used": False,
        "skipped": True,
        "skipped_reason": "OPENAI_API_KEY is not set",
        "route": route.to_dict(),
        "final_answer": final_answer,
        "evidence_summary": backend.get("tool_results_summary", {}) if backend else {},
        "trajectory": trajectory,
    }


def _skipped_result(query: str, mode: str, client: LLMClient, reason: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "llm_provider": client.provider_name(),
        "llm_model": client.model_name(),
        "backend_used": False,
        "real_llm_used": False,
        "skipped": True,
        "skipped_reason": reason,
        "final_answer": "",
        "trajectory": {
            "original_query": query,
            "strategy": mode,
            "real_llm_used": False,
            "skipped_reason": reason,
            "steps": [],
            "final_answer": "",
            "tool_call_count": 0,
        },
        "tool_call_count": 0,
    }


def _execute_llm_tool_call(
    raw_call: dict[str, Any],
    db: DuckDBDatabase,
    api_client: AdobeAPIClient,
    sql_validator: SQLValidator,
    api_validator: APIValidator,
) -> dict[str, Any]:
    tool = raw_call.get("tool") or raw_call.get("name")
    args = raw_call.get("arguments") if isinstance(raw_call.get("arguments"), dict) else {}
    if tool == "execute_sql":
        sql = str(args.get("sql", ""))
        validation = sql_validator.validate(sql)
        result = db.execute_sql(sql) if validation.ok else {"ok": False, "rows": [], "row_count": 0, "error": "; ".join(validation.errors)}
        return {"tool": tool, "arguments": {"sql": sql}, "validation": validation.to_dict(), "result": compact_preview(result, 1000)}
    if tool == "call_api":
        method = str(args.get("method", "GET")).upper()
        url = str(args.get("url", ""))
        params = args.get("params") if isinstance(args.get("params"), dict) else {}
        headers = args.get("headers") if isinstance(args.get("headers"), dict) else {}
        validation = api_validator.validate(method, url, params, headers)
        result = api_client.call_api(method, url, params, headers) if validation.ok else {"ok": False, "error": "; ".join(validation.errors)}
        return {"tool": tool, "arguments": {"method": method, "url": url, "params": params}, "validation": validation.to_dict(), "result": compact_preview(result, 1000)}
    return {"tool": tool or "unknown", "validation": {"ok": False, "errors": ["Unknown tool."]}, "result": {"ok": False}}


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
