# Final LLM NL-to-SQL, Strict Scoring, and Candidate Context Report

Date: May 5, 2026

## 1. Summary

Implemented the final LLM-paired DASHSys pass while preserving `SQL_FIRST_API_VERIFY` as the deterministic default and fallback.

Added:

- Optional OpenAI-backed `LLMClient` with safe no-key fallback.
- Prompt Router with `LLM_DIRECT`, `LOCAL_DB_ONLY`, `SQL_PLUS_API`, and `API_ONLY`.
- Candidate/full schema context retrieval for LLM SQL.
- Optional LLM SQL generation, validation, repair, and fallback.
- True real LLM two-tools baseline interface with bounded multi-turn tool execution.
- Optimized LLM controller interface using the existing backend as a high-level evidence tool.
- Strict evaluation mode.
- Candidate context report.
- Baseline comparison report.
- Prompt-to-answer Mermaid/Markdown/HTML visualization.
- Real trajectory checkpoint export script for OpenAI Agents SDK spans.

No public-example final answers or exact query strings were hardcoded.

## 2. LLM Availability

- `OPENAI_API_KEY` available: `false`
- Real LLM baseline status: skipped with reason `OPENAI_API_KEY is not set`
- Deterministic fallback status: functional
- Adobe live API credentials: not required; dry-run behavior remains supported

## 3. Prompt Router

Sample routing behavior:

| Prompt | Expected route | Behavior |
| --- | --- | --- |
| Explain how checkpoints work | `LLM_DIRECT` | Routes to direct LLM mode; no SQL/API needed |
| List all journeys | `LOCAL_DB_ONLY` | Uses local snapshot with `API_SKIP` policy |
| Is the 'Birthday Message' journey published? | `SQL_PLUS_API` | SQL grounds journey, API may verify live state |
| How many merge policies are configured? | `API_ONLY` | API/platform family |
| What overall pattern do you see? | data pipeline if ambiguous | Avoids unsupported facts |

Every trajectory now includes `checkpoint_00_prompt_router`.

## 4. Candidate Context

Candidate context is schema/API retrieval only. It does not use gold SQL/API/answer patterns and does not decide the answer.

Candidate context summary:

| Metric | Value |
| --- | ---: |
| Avg candidate context tokens | 888.5714 |
| Avg full schema context tokens | 4682 |
| Compression ratio | 0.1898 |
| Table recall@3 | 0.4333 |
| Table recall@5 | 0.5111 |
| API recall@3 | 0.4677 |
| API recall@5 | 0.5484 |

Report files:

- `outputs/candidate_context_report.md`
- `outputs/candidate_context_report.json`

## 5. LLM SQL Design

Implemented optional strategies:

- `CANDIDATE_GUIDED_LLM_SQL`
- `FULL_SCHEMA_LLM_SQL`
- `LLM_SQL_FIRST_API_VERIFY`

Behavior:

- Candidate-guided SQL uses retrieved tables/columns/joins/APIs as context only.
- If candidate confidence is low or validation fails, full-schema fallback is available.
- If LLM SQL is unavailable or invalid, execution falls back to `SQL_FIRST_API_VERIFY`.
- Generated and repaired SQL are validated before execution.

With no `OPENAI_API_KEY`, LLM SQL generation is skipped and deterministic fallback is used.

## 6. Real LLM Tool Baselines

Implemented:

- `REAL_LLM_TWO_TOOLS_BASELINE`: real LLM with only `execute_sql` and `call_api`, max 4 turns and max 4 tool calls.
- `LLM_CONTROLLER_OPTIMIZED_AGENT`: real LLM controller using prompt routing and `run_data_answer_tool`.

Current status:

- Real LLM baseline: skipped because `OPENAI_API_KEY` is not set.
- Optimized controller: falls back to backend answer for evidence prompts, or reports direct LLM skip for conceptual prompts.

## 7. Normal Scorer Results

`SQL_FIRST_API_VERIFY` remains the best overall deterministic strategy.

| Metric | Value |
| --- | ---: |
| SQL correctness | 0.9714 |
| API correctness | 0.9864 |
| Answer correctness | 0.5208 |
| Overall correctness | 0.8407 |
| Final score | 0.8154 |
| Tool calls | 1.4571 |
| Tokens | 851.7714 |
| Runtime | 0.0104 |

## 8. Strict Scorer Results

Strict mode removes free credit for missing gold dimensions and caps fuzzy answer matching.

| Metric | Value |
| --- | ---: |
| SQL correctness | 0.9333 |
| API correctness | 0.9791 |
| Answer correctness | 0.3076 |
| Overall correctness | 0.6743 |
| Final score | 0.6490 |
| Tool calls | 1.4571 |
| Tokens | 851.7714 |
| Runtime | 0.0104 |

Strict scoring exposes that answer correctness is still the weakest dimension.

## 9. Baseline Comparison

Baseline comparison outputs:

- `outputs/baseline_comparison_report.md`
- `outputs/baseline_comparison_report.json`
- `outputs/llm_baseline_comparison.md`

The report clearly separates:

- real LLM baseline, skipped when no key exists
- deterministic LLM approximation baseline
- SQL-only baseline
- current optimized backend
- optional LLM SQL paths
- optimized LLM controller

## 10. Visualization And Trace Export

Generated dataflow files:

- `outputs/demo_dataflow/dataflow.mmd`
- `outputs/demo_dataflow/dataflow.md`
- `outputs/demo_dataflow/dataflow.html`
- `outputs/demo_dataflow/dataflow.svg`

Trace export result:

- Script: `scripts/export_trajectory_to_openai_trace.py`
- Behavior without key/SDK: safe no-op
- Real trajectory checkpoint count in demo: 20

## 11. Validation

Commands completed successfully:

- `python3 scripts/warm_cache.py`
- `python3 scripts/inspect_schema.py`
- `python3 scripts/run_dev_eval.py`
- `python3 scripts/run_dev_eval.py --strict`
- `python3 scripts/run_llm_baseline_eval.py`
- `python3 scripts/generate_candidate_context_report.py`
- `python3 scripts/generate_baseline_comparison_report.py`
- `python3 scripts/generate_failure_analysis.py`
- `python3 scripts/generate_family_score_report.py`
- `python3 scripts/generate_pareto_report.py`
- `python3 scripts/generate_template_generalization_report.py`
- `python3 scripts/generate_checkpoint_report.py`
- `python3 -m pytest`
- `python3 scripts/package_submission.py`
- `python3 scripts/package_query_outputs.py`
- `python3 scripts/check_submission_ready.py`

Test result: `73 passed`

Packaging result: passed

Readiness result: passed

Default strategy remains `SQL_FIRST_API_VERIFY`.

## 12. Remaining Risks

- Real LLM SQL behavior still needs live testing with `OPENAI_API_KEY`.
- Live Adobe API behavior still needs credentials.
- Strict scoring shows answer correctness remains moderate.
- Candidate context is intentionally conservative; recall can improve without using gold patterns.
- Some old output folders contain malformed stale trajectories, so packaging now skips invalid trajectory outputs.
