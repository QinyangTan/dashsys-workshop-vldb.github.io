# Final Real LLM Tool Baseline Fix Report

## What Was Wrong Before

`REAL_LLM_TWO_TOOLS_BASELINE` called the real LLM, but it did not maintain a native OpenAI tool-calling conversation. It asked for JSON-like tool calls and carried prior tool results in prompt text, so OpenAI responses with assistant `tool_calls` were not followed by matching `role="tool"` messages with `tool_call_id`.

That made the baseline fail as a true naive LLM + two tools agent.

## Implemented Fix

- Added `LLMClient.generate_messages(...)`.
- Implemented OpenAI Chat Completions message calls with registered native tools.
- Kept `generate(...)` as a compatibility wrapper.
- Reworked `REAL_LLM_TWO_TOOLS_BASELINE` into a multi-turn message loop:
  1. Send system and user messages with broad schema/API affordances.
  2. Register exactly `execute_sql` and `call_api`.
  3. Read native OpenAI `tool_calls`.
  4. Append the assistant tool-call message.
  5. Validate and execute each tool call.
  6. Append one `role="tool"` result message per `tool_call_id`.
  7. Continue until a grounded final answer is produced.
- Kept strict JSON parsing as a fallback only.
- Added retry behavior for data prompts that return no tool call.
- Failed tool-loop runs are marked invalid and not scored as successful baselines.

## Key Availability

- `OPENAI_API_KEY` available in this environment: `false`
- Real baseline local run status: skipped safely because `OPENAI_API_KEY` is not set.
- No fake real-LLM result was recorded.

## Native Tool Calling

Native OpenAI tool calling is implemented in `dashagent/llm_client.py` and `dashagent/llm_tool_agent.py`.

Registered baseline tools:

- `execute_sql(sql)`
- `call_api(method, url, params, headers)`

Tool calls record:

- LLM turn
- tool name
- redacted arguments
- validation status
- execution status
- compact result preview
- error, if any

## JSON Fallback

The JSON fallback still exists, but only as a fallback path when native `tool_calls` are unavailable or malformed.

## Current Baseline Counts

- Successful `REAL_LLM_TWO_TOOLS_BASELINE` runs: 0
- Failed `REAL_LLM_TWO_TOOLS_BASELINE` runs: 0
- Skipped no-key baseline runs: yes

Because no `OPENAI_API_KEY` is available locally, there is no real successful tool-loop example to include from this environment. When a key is present, the same loop will require at least one valid executed tool call before a public data-driven run is marked valid.

## Validation Results

- `python3 -m pytest`: passed, 83 tests.
- `python3 scripts/run_llm_baseline_eval.py`: passed, skipped real LLM baseline due to missing key.
- `python3 scripts/generate_baseline_comparison_report.py`: passed.
- `python3 scripts/run_dev_eval.py --strict`: passed.
- `python3 scripts/package_submission.py`: passed.
- `python3 scripts/package_query_outputs.py`: passed.
- `python3 scripts/check_submission_ready.py`: passed.

## Readiness

- Default deterministic strategy remains `SQL_FIRST_API_VERIFY`.
- Strict eval was not weakened.
- Failed real LLM tool loops are separated from successful real baselines.
- No-key behavior is safe and explicit.
- Packaging and readiness checks pass.

## Remaining Risk

The only remaining verification step is to run the real baseline with `OPENAI_API_KEY` available and confirm at least one data-driven query executes `execute_sql` or `call_api` through OpenAI native tool calls.
