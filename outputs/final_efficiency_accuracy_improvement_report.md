# DASHSys Efficiency And Accuracy Improvement Report

## 1. What Changed

This pass keeps `SQL_FIRST_API_VERIFY` as the packaged deterministic default and adds a clean raw-vs-guided real LLM baseline split.

- `RAW_REAL_LLM_TWO_TOOLS_BASELINE`: real LLM plus only `execute_sql` and `call_api`, with minimal affordance and normal validation.
- `GUIDED_REAL_LLM_TWO_TOOLS_BASELINE`: the same two tools, plus schema affordance, endpoint repair, virtual schema guidance, actionable validation feedback, duplicate-call tracking, and uncertainty-safe answer wording.
- `REAL_LLM_TWO_TOOLS_BASELINE` remains the backward-compatible raw-baseline concept.
- Candidate context now records adaptive modes: `candidate`, `expanded_candidate`, `hybrid`, or `full_schema`.
- Reports now distinguish tool invocation, validation, execution attempt, execution success, dry-run-only API calls, and evidence availability.

## 2. Raw Baseline vs Guided Baseline

Latest provider-backed run used OpenRouter through the OpenAI-compatible tool-calling path.

| Metric | Raw baseline | Guided baseline |
| --- | ---: | ---: |
| Rows | 35 | 35 |
| Valid runs | 34 | 35 |
| Failed runs | 1 | 0 |
| Average invalid tool calls | 0.5429 | 0.0286 |
| Endpoint repairs | 0 | 33 |
| Schema hint injections | 0 | 0 |
| Average prompt/context tokens | 1318.3429 | 2057.3429 |
| Average runtime | 4.0898 | 4.1965 |

Guided uses more prompt/context tokens because it includes explicit schema/API affordance. The cost is visible and modest in runtime for this run, while tool validity improved: invalid tool calls dropped sharply and all guided rows completed as valid runs.

## 3. Tool Execution vs Evidence Success

The tool loop now records:

- `tool_invoked`
- `tool_validation_ok`
- `tool_execution_attempted`
- `tool_execution_ok`
- `evidence_available`
- `dry_run_only`
- `successful_evidence_count`

Dry-run API calls count as tool invocations and execution attempts, but do not count as evidence when Adobe credentials are unavailable. SQL returning rows or meaningful aggregate rows counts as evidence. Zero-row SQL is treated as uncertain unless supported by strong schema context.

## 4. Empty-Result Uncertainty

Raw sample:

`When was the journey 'Birthday Message' published?`

The raw baseline produced a zero-row/uncertain path and the answer was rewritten to:

`The executed query did not find evidence for Birthday Message. This is not a hard proof that it does not exist, because the query/schema choice may be incomplete.`

This prevents unsupported hard negatives such as "not found" or "does not exist" when the executed query may be incomplete.

## 5. Endpoint Repair Examples

Guided sample:

`Which files are available for download in batch 69de8a0e0cc6102b5d11f01e?`

The guided baseline repaired batch-file aliases to the catalog endpoint family:

- from `/data/core/ups/batch/{id}/files`
- to `/data/foundation/export/batches/{batch_id}/files`

The final answer still reported that Adobe credentials were unavailable, so the API was dry-run only and not counted as live evidence.

## 6. Schema Feedback Examples

Guided SQL validation now suggests safe tables for invalid generic names:

- invalid `journey` suggests `dim_campaign`
- `information_schema`, `sqlite_master`, and `duckdb_tables` are not executed as DB internals
- guided virtual schema guidance exposes `__schema_tables`, `__schema_columns`, and `DESCRIBE <allowed_table>`

The raw baseline is isolated from these features by tests, preserving the clean naive comparison.

## 7. Curated Join Hint Audit

`outputs/candidate_context_report.json` now includes `curated_join_hint_audit`.

- Join hint count: 35
- `used_gold_patterns`: false
- Sources are classified as schema-level relationship, naming convention, bridge-table heuristic, or manual general rule.
- No join hint is derived from gold SQL, exact public query strings, or public answer patterns.

## 8. Candidate Context Mode Distribution

| Metric | Value |
| --- | ---: |
| Candidate context tokens | 896.4857 |
| Full schema context tokens | 4682 |
| Compression ratio | 0.1915 |
| Table recall@3 | 0.7444 |
| Table recall@5 | 0.8222 |
| API recall@3 | 0.4677 |
| API recall@5 | 0.5484 |
| Low-confidence count | 14 |
| Zero-margin count | 32 |
| Recommended fallback rate | 0.9143 |

Context mode distribution:

| Mode | Count |
| --- | ---: |
| candidate | 3 |
| hybrid | 32 |

This means candidate retrieval remains useful for compression, but weak or tied contexts are not over-trusted; most examples recommend hybrid/full-schema fallback.

## 9. Before/After Regression Table

| Gate | Before / reference | After | Result |
| --- | ---: | ---: | --- |
| `SQL_FIRST_API_VERIFY` strict final score | 0.649 reference from strict rerun | 0.649 | pass |
| `SQL_FIRST_API_VERIFY` strict correctness | 0.6743 | 0.6743 | pass |
| Packaged preferred strategy | `SQL_FIRST_API_VERIFY` | `SQL_FIRST_API_VERIFY` | pass |
| `no_secret_scan.ok` | true | true | pass |
| Strict missing-gold behavior | unscored, not free 1.0 | preserved | pass |
| Raw baseline available | required | available | pass |
| Guided baseline separate | required | reported separately | pass |

`SQL_FIRST_API_VERIFY` token count and runtime stayed materially stable in strict mode: 851.7714 estimated tokens and 0.0103 average runtime.

## 10. Failure-Category Before/After Table

| Category | Raw | Guided | Result |
| --- | ---: | ---: | --- |
| unknown_table_count | 16 | 0 | improved |
| unknown_column_count | 3 | 0 | improved |
| schema_introspection_failure_count | 5 | 0 | improved |
| duplicate_invalid_call_count | 0 | 0 | stable |
| dry_run_only_api_count | 21 | 36 | expected: guided reaches more catalog API paths, but dry-run remains non-evidence without Adobe credentials |
| unsupported_negative_answer_count | 4 | 0 | improved |
| max_turns_exceeded_count | 1 | 0 | improved |
| no_final_answer_count | 1 | 0 | improved |
| unknown_endpoint_count | 0 | 1 | explained: one guided run reached an endpoint validation path that raw did not attempt in this stochastic provider run; it was not counted as successful live evidence |

Guided reduced the main invalid-call categories. The one unknown-endpoint category is reported rather than hidden.

## 11. Efficiency Gates

| Metric | Raw | Guided | Tradeoff |
| --- | ---: | ---: | --- |
| Avg prompt/context tokens | 1318.3429 | 2057.3429 | Guided costs more context |
| Avg runtime | 4.0898 | 4.1965 | Guided slightly slower |
| Valid run rate | 0.9714 | 1.0 | Guided improved reliability |
| Avg invalid calls | 0.5429 | 0.0286 | Guided reduced waste |

The guided baseline is more expensive, but the report exposes the tradeoff directly. The deterministic packaged path is unchanged.

## 12. Strict Eval, Packaging, Readiness

- `python3 scripts/run_dev_eval.py --strict`: passed.
- `python3 -m pytest`: 102 passed.
- `python3 scripts/package_submission.py`: passed.
- `python3 scripts/package_query_outputs.py`: passed.
- `python3 scripts/check_submission_ready.py`: passed.
- `outputs/final_submission_manifest.json` reports `preferred_strategy: SQL_FIRST_API_VERIFY` and `no_secret_scan.ok: true`.

## 13. Remaining Risks

- Live Adobe API credentials are still unavailable, so API calls remain dry-run in local evaluation.
- Real LLM baseline behavior varies by provider/model and can still choose weak SQL/API paths.
- Guided baseline improves tool reliability but should not replace the raw baseline for fair naive comparison.
- Candidate context has strong compression but low/zero-margin cases are common, so hybrid/full-schema fallback remains important.
