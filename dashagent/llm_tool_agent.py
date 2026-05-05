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

    system_prompt = _baseline_system_prompt(strict=False)
    tool_schemas = _baseline_tool_schemas()
    transcript: list[dict[str, Any]] = []
    llm_turns: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    final_answer = ""
    failure_reason = ""
    invalid_format_retries = 0
    real_llm_called = False
    start = time.perf_counter()

    for turn in range(max_turns):
        strict_retry = invalid_format_retries > 0
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
            "instruction": (
                "Return at least one tool call before any final answer. "
                "After tool results are available, return final_answer grounded only in those results."
            ),
        }
        response = client.generate(
            _baseline_system_prompt(strict=strict_retry),
            json.dumps(user_payload, indent=2, default=str),
            tools=tool_schemas,
        )
        real_llm_called = True
        parsed = _parse_json(response.get("content", ""))
        requested = _extract_requested_tool_calls(response, parsed)
        llm_turns.append(
            {
                "turn": turn + 1,
                "strict_retry": strict_retry,
                "response_ok": response.get("ok"),
                "native_tool_call_count": len(response.get("tool_calls") or []),
                "json_tool_call_count": len(parsed.get("tool_calls") or []) if isinstance(parsed.get("tool_calls"), list) else 0,
                "final_answer_present": bool(parsed.get("final_answer")),
                "content_preview": compact_preview(response.get("content", ""), 700),
            }
        )
        if parsed.get("final_answer") and not requested:
            if tool_calls:
                final_answer = str(parsed["final_answer"]).strip()
                break
            if invalid_format_retries < 1:
                invalid_format_retries += 1
                transcript.append(
                    {
                        "turn": turn + 1,
                        "llm_response": compact_preview(parsed, 1000),
                        "tool_results": [],
                        "retry_reason": "final answer was returned before any tool call",
                    }
                )
                continue
            failure_reason = "final_answer_before_tool_results"
            break
        if not requested:
            if invalid_format_retries < 1:
                invalid_format_retries += 1
                transcript.append(
                    {
                        "turn": turn + 1,
                        "llm_response": compact_preview(parsed or response.get("content", ""), 1000),
                        "tool_results": [],
                        "retry_reason": "invalid tool-call JSON/native format",
                    }
                )
                continue
            failure_reason = "invalid_tool_call_format_after_retry"
            break
        turn_results = []
        for raw_call in requested:
            if len(tool_calls) >= max_tool_calls:
                break
            executed = _execute_llm_tool_call(raw_call, db, api_client, sql_validator, api_validator)
            tool_calls.append(executed)
            turn_results.append(executed)
        transcript.append({"turn": turn + 1, "llm_response": compact_preview(parsed, 1000), "tool_results": turn_results})
        if len(tool_calls) >= max_tool_calls and not final_answer:
            break
    if not final_answer:
        if tool_calls:
            final_prompt = {
                "query": query,
                "tool_results": compact_preview(tool_calls, 6000),
                "instruction": "Return strict JSON only: {\"tool_calls\": [], \"final_answer\": \"...\"}. Ground the answer only in these tool results.",
            }
            response = client.generate(_baseline_system_prompt(strict=True), json.dumps(final_prompt, indent=2, default=str))
            real_llm_called = True
            parsed = _parse_json(response.get("content", ""))
            final_answer = str(parsed.get("final_answer") or response.get("content") or "").strip()
            llm_turns.append(
                {
                    "turn": len(llm_turns) + 1,
                    "strict_retry": True,
                    "response_ok": response.get("ok"),
                    "native_tool_call_count": len(response.get("tool_calls") or []),
                    "json_tool_call_count": len(parsed.get("tool_calls") or []) if isinstance(parsed.get("tool_calls"), list) else 0,
                    "final_answer_present": bool(final_answer),
                    "content_preview": compact_preview(response.get("content", ""), 700),
                }
            )
        elif not failure_reason:
            failure_reason = "no_tool_calls_executed"
    validation_results = [call.get("validation", {}) for call in tool_calls]
    execution_previews = [call.get("result", {}) for call in tool_calls]
    tool_calls_executed = any(call.get("executed") for call in tool_calls)
    if final_answer and tool_calls and not tool_calls_executed and not failure_reason:
        failure_reason = "no_valid_tool_calls_executed"
    if not final_answer and not failure_reason:
        failure_reason = "no_final_answer_after_tool_results"
    valid_agent_run = bool(real_llm_called and tool_calls_executed and final_answer and not failure_reason)
    skipped_or_failed = not valid_agent_run
    trajectory = {
        "query_id": "real_llm_two_tools",
        "original_query": query,
        "strategy": REAL_LLM_TWO_TOOLS_BASELINE,
        "llm_turns": llm_turns,
        "llm_turn_count": len(llm_turns),
        "llm_tool_calls": tool_calls,
        "validation_results": validation_results,
        "execution_previews": execution_previews,
        "steps": [
            {"kind": "llm_turn", **item}
            for item in transcript
        ],
        "final_answer": final_answer,
        "real_llm_used": True,
        "real_llm_called": real_llm_called,
        "tool_calls_executed": tool_calls_executed,
        "valid_agent_run": valid_agent_run,
        "skipped_or_failed": skipped_or_failed,
        "failure_reason": failure_reason,
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
            "real_llm_called": real_llm_called,
            "skipped": False,
            "tool_calls_executed": tool_calls_executed,
            "valid_agent_run": valid_agent_run,
            "skipped_or_failed": skipped_or_failed,
            "failure_reason": failure_reason,
            "llm_turns": llm_turns,
            "llm_tool_calls": tool_calls,
            "validation_results": validation_results,
            "execution_previews": execution_previews,
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
        "real_llm_called": False,
        "skipped": True,
        "tool_calls_executed": False,
        "valid_agent_run": False,
        "skipped_or_failed": True,
        "failure_reason": reason,
        "llm_turns": [],
        "llm_tool_calls": [],
        "validation_results": [],
        "execution_previews": [],
        "skipped_reason": reason,
        "final_answer": "",
        "trajectory": {
            "original_query": query,
            "strategy": mode,
            "real_llm_used": False,
            "real_llm_called": False,
            "llm_turns": [],
            "llm_turn_count": 0,
            "llm_tool_calls": [],
            "validation_results": [],
            "execution_previews": [],
            "skipped_reason": reason,
            "steps": [],
            "final_answer": "",
            "tool_call_count": 0,
            "tool_calls_executed": False,
            "valid_agent_run": False,
            "skipped_or_failed": True,
            "failure_reason": reason,
        },
        "tool_call_count": 0,
    }


def _baseline_system_prompt(*, strict: bool) -> str:
    base = (
        "You are a naive DASHSys LLM agent. You may use exactly two tools: execute_sql and call_api. "
        "You do not have DASHSys optimized templates, EvidenceBus, verifier, routing, or plan optimizer. "
        "Use tools to gather evidence before answering. Do not invent IDs, counts, statuses, or timestamps."
    )
    if not strict:
        return base + " Prefer native tool calls when available; otherwise return strict JSON with tool_calls and final_answer."
    return (
        base
        + " STRICT FORMAT: return either native tool calls, or JSON only with exactly "
        + '{"tool_calls":[{"tool":"execute_sql","arguments":{"sql":"SELECT ..."}}],"final_answer":null} '
        + 'or {"tool_calls":[],"final_answer":"..."} after tool results. No markdown or prose outside JSON.'
    )


def _baseline_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "Execute one read-only DuckDB SQL query over the local snapshot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "Read-only SELECT SQL using provided tables and columns."}
                    },
                    "required": ["sql"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "call_api",
                "description": "Call one allowed Adobe API endpoint, or dry-run when credentials are unavailable.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST"]},
                        "url": {"type": "string"},
                        "params": {"type": "object"},
                        "headers": {"type": "object"},
                    },
                    "required": ["method", "url"],
                    "additionalProperties": False,
                },
            },
        },
    ]


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
        return {"tool": tool, "arguments": {"sql": sql}, "validation": validation.to_dict(), "executed": validation.ok, "result": compact_preview(result, 1000)}
    if tool == "call_api":
        method = str(args.get("method", "GET")).upper()
        url = str(args.get("url", ""))
        params = args.get("params") if isinstance(args.get("params"), dict) else {}
        headers = args.get("headers") if isinstance(args.get("headers"), dict) else {}
        validation = api_validator.validate(method, url, params, headers)
        result = api_client.call_api(method, url, params, headers) if validation.ok else {"ok": False, "error": "; ".join(validation.errors)}
        return {"tool": tool, "arguments": {"method": method, "url": url, "params": params}, "validation": validation.to_dict(), "executed": validation.ok, "result": compact_preview(result, 1000)}
    return {"tool": tool or "unknown", "validation": {"ok": False, "errors": ["Unknown tool."]}, "executed": False, "result": {"ok": False}}


def _extract_requested_tool_calls(response: dict[str, Any], parsed: dict[str, Any]) -> list[dict[str, Any]]:
    native_calls = response.get("tool_calls")
    if isinstance(native_calls, list) and native_calls:
        return [_normalize_tool_call(call) for call in native_calls]
    json_calls = parsed.get("tool_calls")
    if isinstance(json_calls, list):
        return [_normalize_tool_call(call) for call in json_calls]
    json_call = parsed.get("tool_call")
    if isinstance(json_call, dict):
        return [_normalize_tool_call(json_call)]
    return []


def _normalize_tool_call(raw_call: dict[str, Any]) -> dict[str, Any]:
    tool = raw_call.get("tool") or raw_call.get("name")
    args = raw_call.get("arguments") if isinstance(raw_call.get("arguments"), dict) else {}
    if isinstance(raw_call.get("arguments"), str):
        try:
            parsed_args = json.loads(raw_call["arguments"])
            if isinstance(parsed_args, dict):
                args = parsed_args
        except Exception:
            args = {"_raw": raw_call["arguments"]}
    return {"tool": tool, "name": tool, "arguments": args, "id": raw_call.get("id")}


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
