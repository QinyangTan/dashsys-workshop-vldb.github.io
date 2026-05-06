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
from .prompt_router import API_ONLY, LLM_DIRECT, route_prompt
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
        return _skipped_result(query, REAL_LLM_TWO_TOOLS_BASELINE, client, _llm_unavailable_reason(client))

    cfg = config or Config.from_env()
    db = DuckDBDatabase(cfg)
    schema_index = SchemaIndex.build(db)
    endpoint_catalog = EndpointCatalog(cfg)
    sql_validator = SQLValidator(schema_index)
    api_validator = APIValidator(endpoint_catalog, allow_unknown=cfg.allow_unknown_api_endpoints)
    api_client = AdobeAPIClient(cfg)
    full_context = build_full_schema_context(schema_index, endpoint_catalog)
    route = route_prompt(query)
    data_driven_prompt = route.mode != LLM_DIRECT

    tool_schemas = _baseline_tool_schemas()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _baseline_system_prompt(strict=False)},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "query": query,
                    "route_hint": route.to_dict(),
                    "schema_context": compact_preview(full_context, 9000),
                    "instruction": (
                        "Use execute_sql to inspect the local database for data-driven questions. "
                        "Use call_api only when live/platform/API evidence is required. "
                        "After tool results are available, answer concisely using only evidence."
                    ),
                },
                indent=2,
                default=str,
            ),
        },
    ]
    transcript: list[dict[str, Any]] = []
    llm_turns: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    final_answer = ""
    failure_reason = ""
    native_retry_used = False
    force_tool_retry = False
    real_llm_called = False
    start = time.perf_counter()

    for turn in range(max_turns):
        tool_choice: str | dict[str, Any] | None = "auto"
        if force_tool_retry:
            tool_choice = _forced_tool_choice(route.mode)
        response = _call_llm_messages(client, messages, tools=tool_schemas, tool_choice=tool_choice)
        force_tool_retry = False
        real_llm_called = True
        parsed = _parse_json(response.get("content", ""))
        requested = _extract_requested_tool_calls(response, parsed)
        llm_turns.append(
            {
                "turn": turn + 1,
                "tool_choice": tool_choice,
                "response_ok": response.get("ok"),
                "finish_reason": response.get("finish_reason"),
                "error": response.get("error") or response.get("reason") or "",
                "native_tool_call_count": len(response.get("tool_calls") or []),
                "json_tool_call_count": len(parsed.get("tool_calls") or []) if isinstance(parsed.get("tool_calls"), list) else 0,
                "final_answer_present": bool(parsed.get("final_answer")),
                "content_preview": compact_preview(response.get("content", ""), 700),
            }
        )
        if not response.get("ok"):
            failure_reason = _llm_failure_reason(response)
            transcript.append(
                {
                    "turn": turn + 1,
                    "llm_response": compact_preview(response, 1200),
                    "tool_results": [],
                    "failure_reason": failure_reason,
                }
            )
            break
        if not requested:
            candidate_answer = str(parsed.get("final_answer") or response.get("content") or "").strip()
            if candidate_answer and (not data_driven_prompt or any(call.get("executed") for call in tool_calls)):
                final_answer = candidate_answer
                transcript.append(
                    {
                        "turn": turn + 1,
                        "assistant_final": compact_preview(final_answer, 1000),
                        "tool_results": [],
                    }
                )
                break
            if data_driven_prompt and not any(call.get("executed") for call in tool_calls) and not native_retry_used:
                native_retry_used = True
                force_tool_retry = True
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "This is a data-driven prompt. Before answering, call exactly one tool now. "
                            "Prefer execute_sql unless the question is API-only. Do not return a final answer yet."
                        ),
                    }
                )
                transcript.append(
                    {
                        "turn": turn + 1,
                        "llm_response": compact_preview(parsed or response.get("content", ""), 1000),
                        "tool_results": [],
                        "retry_reason": "no native or JSON tool call before evidence",
                    }
                )
                continue
            failure_reason = (
                _no_tool_call_failure_reason(client)
                if data_driven_prompt and not any(call.get("executed") for call in tool_calls)
                else "no_final_answer_after_tool_results"
            )
            break

        remaining_tool_calls = max_tool_calls - len(tool_calls)
        requested_to_run = requested[:remaining_tool_calls]
        if not requested_to_run:
            messages.append(
                {
                    "role": "user",
                    "content": "The tool-call budget is exhausted. Produce a concise final answer using only the tool results above.",
                }
            )
            break
        native_calls_present = bool(response.get("tool_calls"))
        if native_calls_present:
            messages.append(_assistant_tool_message(requested_to_run, response))
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": response.get("content") or json.dumps({"tool_calls": requested_to_run, "final_answer": None}, default=str),
                }
            )
        turn_results = []
        for raw_call in requested_to_run:
            executed = _execute_llm_tool_call(raw_call, db, api_client, sql_validator, api_validator, turn=turn + 1)
            tool_calls.append(executed)
            turn_results.append(executed)
            if native_calls_present:
                messages.append(_tool_result_message(raw_call, executed))
        if not native_calls_present:
            messages.append(
                {
                    "role": "user",
                    "content": "Tool results:\n" + json.dumps(compact_preview(turn_results, 4000), indent=2, default=str),
                }
            )
        transcript.append(
            {
                "turn": turn + 1,
                "assistant_tool_calls": compact_preview(requested_to_run, 1500),
                "tool_results": turn_results,
            }
        )
        if len(tool_calls) >= max_tool_calls and not final_answer:
            messages.append(
                {
                    "role": "user",
                    "content": "The tool-call budget is exhausted. Produce a concise final answer using only the tool results above.",
                }
            )
            break
    if not final_answer:
        if any(call.get("executed") for call in tool_calls):
            messages.append(
                {
                    "role": "user",
                    "content": "Now produce the final answer. Do not call more tools. Use only the evidence in the tool results.",
                }
            )
            response = _call_llm_messages(client, messages, tools=tool_schemas, tool_choice="none")
            real_llm_called = True
            parsed = _parse_json(response.get("content", ""))
            final_answer = str(parsed.get("final_answer") or response.get("content") or "").strip()
            llm_turns.append(
                {
                    "turn": len(llm_turns) + 1,
                    "tool_choice": "none",
                    "response_ok": response.get("ok"),
                    "finish_reason": response.get("finish_reason"),
                    "error": response.get("error") or response.get("reason") or "",
                    "native_tool_call_count": len(response.get("tool_calls") or []),
                    "json_tool_call_count": len(parsed.get("tool_calls") or []) if isinstance(parsed.get("tool_calls"), list) else 0,
                    "final_answer_present": bool(final_answer),
                    "content_preview": compact_preview(response.get("content", ""), 700),
                }
            )
            if not response.get("ok") and not failure_reason:
                failure_reason = _llm_failure_reason(response)
        elif not failure_reason:
            failure_reason = _no_tool_call_failure_reason(client) if data_driven_prompt else "no_final_answer"
    validation_results = [call.get("validation", {}) for call in tool_calls]
    execution_previews = [call.get("result_preview", {}) for call in tool_calls]
    tool_calls_executed = any(call.get("executed") for call in tool_calls)
    if tool_calls and not tool_calls_executed:
        failure_reason = "no_valid_tool_calls_executed"
    if not final_answer and not failure_reason:
        failure_reason = "no_final_answer_after_tool_results"
    if data_driven_prompt:
        valid_agent_run = bool(real_llm_called and tool_calls_executed and final_answer and not failure_reason)
    else:
        valid_agent_run = bool(real_llm_called and final_answer and not failure_reason)
    skipped_or_failed = not valid_agent_run
    trajectory = {
        "query_id": "real_llm_two_tools",
        "original_query": query,
        "strategy": REAL_LLM_TWO_TOOLS_BASELINE,
        "prompt_route": route.to_dict(),
        "data_driven_prompt": data_driven_prompt,
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
        else f"{_llm_unavailable_reason(client)}; LLM direct response was skipped."
    )
    trajectory = backend.get("trajectory", {}) if backend else {}
    trajectory = dict(trajectory)
    trajectory["llm_controller_checkpoints"] = checkpoints
    skipped_reason = _llm_unavailable_reason(client)
    trajectory["llm_skipped_reason"] = skipped_reason
    return {
        "mode": LLM_CONTROLLER_OPTIMIZED_AGENT,
        "llm_provider": client.provider_name(),
        "llm_model": client.model_name(),
        "backend_used": bool(backend),
        "real_llm_used": False,
        "skipped": True,
        "skipped_reason": skipped_reason,
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
        "You are a naive tool-using DASHSys data agent. You have only two tools: execute_sql and call_api. "
        "For data questions, inspect the local database with execute_sql. Call API only when live, platform, "
        "or API-only evidence is required. You do not have DASHSys optimized templates, EvidenceBus, verifier, "
        "routing, or plan optimizer. Do not invent IDs, counts, statuses, timestamps, or API results. "
        "After tool results are available, answer concisely using only evidence."
    )
    if not strict:
        return base + " If the question is data-driven, normally call at least execute_sql unless it clearly requires only API."
    return (
        base
        + " STRICT FORMAT: call execute_sql or call_api now. If native tools are unavailable, return JSON only with exactly "
        + '{"tool_calls":[{"tool":"execute_sql","arguments":{"sql":"SELECT ..."}}],"final_answer":null} '
        + 'or {"tool_calls":[],"final_answer":"..."} after tool results. No markdown or prose outside JSON.'
    )


def _baseline_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "Execute a read-only SQL query against the local DuckDB snapshot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "Read-only DuckDB SQL query."}
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
                "description": "Call an Adobe API endpoint using method, URL/path, params, and headers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
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


def _call_llm_messages(
    client: LLMClient,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    if hasattr(client, "generate_messages"):
        return client.generate_messages(messages, tools=tools, tool_choice=tool_choice)
    system_prompt = messages[0].get("content", "") if messages and messages[0].get("role") == "system" else ""
    user_prompt = "\n\n".join(str(message.get("content", "")) for message in messages if message.get("role") != "system")
    return client.generate(system_prompt, user_prompt, tools=tools)


def _forced_tool_choice(route_mode: str) -> str | dict[str, Any]:
    if route_mode == API_ONLY:
        tool_name = "call_api"
    else:
        tool_name = "execute_sql"
    return {"type": "function", "function": {"name": tool_name}}


def _llm_failure_reason(response: dict[str, Any]) -> str:
    text = json.dumps(response.get("raw_preview") or response.get("error") or response.get("reason") or "", default=str)
    lowered = text.lower()
    if "insufficient_quota" in lowered or "exceeded your current quota" in lowered:
        return "llm_request_failed: insufficient_quota"
    if "invalid_api_key" in lowered or "incorrect api key" in lowered:
        return "llm_request_failed: invalid_api_key"
    if response.get("skipped"):
        return f"llm_request_skipped: {response.get('reason', 'unknown')}"
    return "llm_request_failed"


def _llm_unavailable_reason(client: LLMClient) -> str:
    try:
        probe = client.generate_messages([])
        reason = probe.get("reason")
        if reason:
            return str(reason)
    except Exception:
        pass
    return "LLM provider API key is not set"


def _no_tool_call_failure_reason(client: LLMClient) -> str:
    if client.provider_name() == "openrouter":
        return "model_did_not_return_tool_calls"
    return "no_valid_tool_call_after_native_retry"


def _assistant_tool_message(requested: list[dict[str, Any]], response: dict[str, Any]) -> dict[str, Any]:
    tool_calls = []
    for index, call in enumerate(requested):
        tool_name = call.get("tool") or call.get("name")
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        tool_calls.append(
            {
                "id": call.get("id") or f"call_{index + 1}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments, default=str),
                },
            }
        )
    return {"role": "assistant", "content": response.get("content") or None, "tool_calls": tool_calls}


def _tool_result_message(raw_call: dict[str, Any], executed: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "ok": bool(executed.get("executed")),
        "tool_name": executed.get("tool_name") or executed.get("tool"),
        "validation_ok": executed.get("validation_ok"),
        "result_preview": executed.get("result_preview"),
        "error": executed.get("error"),
    }
    return {
        "role": "tool",
        "tool_call_id": raw_call.get("id") or "call_1",
        "name": executed.get("tool_name") or executed.get("tool") or "unknown",
        "content": json.dumps(redact_secrets(payload), default=str),
    }


def _execute_llm_tool_call(
    raw_call: dict[str, Any],
    db: DuckDBDatabase,
    api_client: AdobeAPIClient,
    sql_validator: SQLValidator,
    api_validator: APIValidator,
    *,
    turn: int,
) -> dict[str, Any]:
    tool = raw_call.get("tool") or raw_call.get("name")
    args = raw_call.get("arguments") if isinstance(raw_call.get("arguments"), dict) else {}
    if tool == "execute_sql":
        sql = str(args.get("sql", ""))
        validation = sql_validator.validate(sql)
        result = db.execute_sql(sql) if validation.ok else {"ok": False, "rows": [], "row_count": 0, "error": "; ".join(validation.errors)}
        preview = {
            "ok": result.get("ok", False),
            "row_count": result.get("row_count", 0),
            "rows_preview": compact_preview(result.get("rows", []), 1000),
            "validation": validation.to_dict(),
            "error": result.get("error") or ("; ".join(validation.errors) if validation.errors else None),
        }
        return redact_secrets(
            {
                "turn": turn,
                "tool_name": tool,
                "tool": tool,
                "arguments": {"sql": sql},
                "validation_ok": validation.ok,
                "validation": validation.to_dict(),
                "executed": validation.ok and bool(result.get("ok", False)),
                "result_preview": preview,
                "error": preview["error"] or "",
            }
        )
    if tool == "call_api":
        method = str(args.get("method", "GET")).upper()
        url = str(args.get("url", ""))
        params = args.get("params") if isinstance(args.get("params"), dict) else {}
        headers = args.get("headers") if isinstance(args.get("headers"), dict) else {}
        validation = api_validator.validate(method, url, params, headers)
        result = api_client.call_api(method, url, params, headers) if validation.ok else {"ok": False, "error": "; ".join(validation.errors)}
        preview = {
            "ok": result.get("ok", False),
            "dry_run": result.get("dry_run", False),
            "status_code": result.get("status_code"),
            "result_preview": compact_preview(result.get("result_preview"), 1000),
            "validation": validation.to_dict(),
            "error": result.get("error") or ("; ".join(validation.errors) if validation.errors else None),
        }
        return redact_secrets(
            {
                "turn": turn,
                "tool_name": tool,
                "tool": tool,
                "arguments": {"method": method, "url": url, "params": params, "headers": redact_secrets(headers)},
                "validation_ok": validation.ok,
                "validation": validation.to_dict(),
                "executed": validation.ok,
                "result_preview": preview,
                "error": preview["error"] or "",
            }
        )
    return {
        "turn": turn,
        "tool_name": tool or "unknown",
        "tool": tool or "unknown",
        "arguments": redact_secrets(args),
        "validation_ok": False,
        "validation": {"ok": False, "errors": ["Unknown tool."]},
        "executed": False,
        "result_preview": {"ok": False, "error": "Unknown tool."},
        "error": "Unknown tool.",
    }


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
