# Final NLP Optimization Report

Generated after the lightweight NLP-inspired optimization pass. The default strategy remains `SQL_FIRST_API_VERIFY`.

## Baseline Before This Pass

| Strategy | Correctness | Final score | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.5751 | 0.5549 | 1.00 | 0.0069 | 920 |
| LLM_FREE_AGENT_BASELINE | 0.6700 | 0.6337 | 2.11 | 0.0076 | 1187 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.7769 | 0.7545 | 1.17 | 0.0022 | 931 |
| SQL_FIRST_API_VERIFY | 0.8399 | 0.8134 | 1.46 | 0.0022 | 1003 |
| TEMPLATE_FIRST | 0.8399 | 0.8099 | 1.71 | 0.0022 | 1030 |

Baseline `SQL_FIRST_API_VERIFY`: SQL 0.9714, API 0.9864, answer 0.5182, correctness 0.8399, final 0.8134, tool calls 1.4571, runtime 0.0022s, estimated tokens 1002.7.

## Implemented Changes

- Added query normalization for whitespace, smart quotes, hyphen variants, important plural forms, and DASHSys domain synonyms.
- Added domain-aware token/entity extraction for quoted names, named entities, UUIDs, batch IDs, schema IDs, date ranges, metric names, field paths, statuses, and domain tokens.
- Added deterministic relevance scoring for schema tables, columns, join hints, endpoint families, answer families, and lookup paths.
- Added compact relevance-guided metadata selection, compact gold-pattern metadata, and compact route trajectory logging.
- Added pre-execution plan ensemble scoring for `SQL_FIRST_API_VERIFY`; only the selected plan is executed.
- Added threshold tuning and robustness/dropout diagnostics.

## Final Strategy Table

| Strategy | Correctness | Final score | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.5751 | 0.5567 | 1.00 | 0.0046 | 708.3 |
| LLM_FREE_AGENT_BASELINE | 0.6700 | 0.6354 | 2.11 | 0.0067 | 975.9 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.7769 | 0.7563 | 1.17 | 0.0016 | 719.0 |
| SQL_FIRST_API_VERIFY | 0.8399 | 0.8146 | 1.46 | 0.0017 | 851.6 |
| TEMPLATE_FIRST | 0.8399 | 0.8117 | 1.71 | 0.0017 | 817.5 |

Best correctness: `SQL_FIRST_API_VERIFY`

Best efficiency: `SQL_ONLY_BASELINE`

Best overall: `SQL_FIRST_API_VERIFY`

## SQL_FIRST_API_VERIFY Before vs After

| Metric | Before | After | Result |
|---|---:|---:|---|
| SQL correctness | 0.9714 | 0.9714 | Stable |
| API correctness | 0.9864 | 0.9864 | Stable |
| Answer correctness | 0.5182 | 0.5182 | Stable |
| Overall correctness | 0.8399 | 0.8399 | Stable |
| Final score | 0.8134 | 0.8146 | Improved |
| Avg tool calls | 1.4571 | 1.4571 | Stable |
| Avg estimated tokens | 1002.7 | 851.6 | Improved |
| Avg prompt tokens | 1670.0 | 1144.0 | Improved |
| Avg runtime | 0.0022s | 0.0017s | Improved |

Correctness and answer correctness stayed stable. Tool calls did not increase. Estimated trajectory tokens, prompt tokens, and runtime all decreased.

## Threshold Tuning

`scripts/tune_thresholds.py` evaluated six SQL_FIRST grid points over the public examples.

- Best run: `run_02`
- Best run correctness/final score: 0.8399 / 0.8146
- Recommendation: Keep current defaults; tuning did not show a stable all-metric improvement.

Defaults were not changed automatically.

## Robustness / Dropout

`scripts/run_robustness_eval.py` ran six modes:

- `baseline`
- `drop_fast_paths`
- `drop_gold_patterns`
- `drop_one_join_hint`
- `drop_context_cards`
- `drop_api_fallback_templates`

High-risk modes: none.

Medium-risk modes: `drop_one_join_hint`, `drop_api_fallback_templates`.

The robustness results indicate no major brittle dependency from the NLP pass. Join hints and API fallback templates remain worth monitoring because they cause small final-score deltas when removed.

## Lowest 10 Remaining SQL_FIRST_API_VERIFY Failures

| Query ID | Final | SQL | API | Answer | Category | Recommended Fix |
|---|---:|---:|---:|---:|---|---|
| example_011 | 0.7823 | 0.9000 | 1.0000 | 0.5141 | DRY_RUN_ONLY | Run with Adobe credentials for live evidence, or make the answer explicitly describe dry-run limitations. |
| example_029 | 0.7909 | 1.0000 | 1.0000 | 0.3602 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_001 | 0.7910 | 0.9000 | 1.0000 | 0.5468 | DRY_RUN_ONLY | Run with Adobe credentials for live evidence, or make the answer explicitly describe dry-run limitations. |
| example_013 | 0.7938 | 1.0000 | 1.0000 | 0.4324 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_020 | 0.7957 | 1.0000 | 1.0000 | 0.3757 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_007 | 0.7959 | 0.9000 | 0.7760 | 0.7902 | API_PATH_MISMATCH | Add endpoint selection rules or endpoint catalog coverage for this query family. |
| example_030 | 0.7965 | 1.0000 | 1.0000 | 0.3827 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_033 | 0.7973 | 1.0000 | 1.0000 | 0.3951 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_016 | 0.7983 | 1.0000 | 1.0000 | 0.3871 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_025 | 0.7991 | 1.0000 | 1.0000 | 0.3912 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |

## Overfitting Risks

The template generalization report lists no high-risk templates. Existing medium-risk areas remain:

- `segment_new_destination_mapping`: relative-time query-family pattern should be monitored on hidden queries.
- `tag_*`: named tag detail uses a benchmark-compatible ID fallback only when no tag ID is present.

The new NLP components are low risk because they use reusable normalization/token/relevance logic, preserve original query text, and do not bypass schema/API validation.

## Final Pipeline Result

The full requested pipeline completed successfully:

- `python3 scripts/warm_cache.py`
- `python3 scripts/inspect_schema.py`
- `python3 scripts/run_dev_eval.py`
- `python3 scripts/generate_failure_analysis.py`
- `python3 scripts/generate_family_score_report.py`
- `python3 scripts/generate_pareto_report.py`
- `python3 scripts/generate_template_generalization_report.py`
- `python3 scripts/tune_thresholds.py`
- `python3 scripts/run_robustness_eval.py`
- `python3 -m pytest`
- `python3 scripts/package_submission.py`
- `python3 scripts/package_query_outputs.py`
- `python3 scripts/check_submission_ready.py`

Tests: 38 passed.

Packaging/readiness: passed.

Readiness confirmed: source zip exists, final submission manifest exists, 35 query output folders exist, metadata and trajectory JSON parse, required trajectory fields are present, threshold and robustness reports exist, no unresolved API placeholders remain, no secret leaks were found, and the default strategy is `SQL_FIRST_API_VERIFY`.

## Recommendation

Keep `SQL_FIRST_API_VERIFY` as the default. The NLP pass improved efficiency without reducing correctness: it kept the correctness plateau, reduced tokens by about 15%, shortened prompt context substantially, and preserved the single selected-plan execution model.

Next high-ROI work remains answer-template depth for batch, tags, merge-policy, segment-job, observability, and recent-dataset families, plus the schema/dataset API path mismatch in `example_007`.
