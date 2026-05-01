# Final Architecture Optimization Report

Generated after the architecture-inspired optimization pass. The default strategy remains `SQL_FIRST_API_VERIFY`.

## Baseline Before This Pass

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.9714 | 0.1143 | 0.5017 | 0.5734 | 0.5530 | 1.0000 | 0.0053 | 938.1 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9784 | 0.4587 | 0.6700 | 0.6335 | 2.1143 | 0.0068 | 1209.7 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9714 | 0.7794 | 0.5150 | 0.7769 | 0.7544 | 1.1714 | 0.0026 | 943.6 |
| SQL_FIRST_API_VERIFY | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8132 | 1.4571 | 0.0027 | 1018.1 |
| TEMPLATE_FIRST | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8098 | 1.7143 | 0.0030 | 1046.8 |

Baseline tests: 27 passed. Baseline packaging/readiness: passed.

## Implemented Optimizations

- Added `EvidenceBus` operand forwarding for structured SQL/API evidence, including IDs, names, timestamps, counts, statuses, first rows, and normalized API items.
- Added one-pass `QueryAnalysis` branch prediction for routing, answer family, SQL template, API templates, API need, fast path, lookup path, and confidence.
- Added `LookupPathPredictor` and compact family context cards for reusable schema/API paths.
- Added `PlanOptimizer` to deduplicate steps, remove API calls blocked by `API_SKIP`, preserve warned unresolved placeholders, and enforce call budgets.
- Extended caching with L1 query-analysis/template caches plus optional SQL and dry-run API result caches.
- Reduced metadata and trajectory preview overhead while preserving SQL/API calls, validation results, row counts/status codes, final answers, runtime, tool counts, and estimated tokens.
- Kept API failure behavior non-blocking: SQL-grounded answers still render when live API evidence is unavailable.

## Final Strategy Table

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.9714 | 0.1143 | 0.5074 | 0.5751 | 0.5549 | 1.0000 | 0.0051 | 920.3 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9784 | 0.4587 | 0.6700 | 0.6337 | 2.1143 | 0.0068 | 1187.2 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9714 | 0.7794 | 0.5150 | 0.7769 | 0.7545 | 1.1714 | 0.0021 | 931.0 |
| SQL_FIRST_API_VERIFY | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8134 | 1.4571 | 0.0021 | 1002.7 |
| TEMPLATE_FIRST | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8099 | 1.7143 | 0.0022 | 1029.5 |

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
| Final score | 0.8132 | 0.8134 | Improved slightly |
| Avg tool calls | 1.4571 | 1.4571 | Stable |
| Avg runtime | 0.0027s | 0.0021s | Improved |
| Avg estimated tokens | 1018.1 | 1002.7 | Improved |

Correctness stayed stable, answer correctness stayed stable, average tool calls did not increase, average tokens decreased, and runtime decreased within the dev evaluation environment.

## Lowest 10 Remaining SQL_FIRST_API_VERIFY Failures

| Query ID | Final | SQL | API | Answer | Category | Recommended Fix |
|---|---:|---:|---:|---:|---|---|
| example_011 | 0.7803 | 0.9000 | 1.0000 | 0.5141 | DRY_RUN_ONLY | Run with Adobe credentials for live evidence, or make dry-run limitations clearer. |
| example_001 | 0.7912 | 0.9000 | 1.0000 | 0.5468 | DRY_RUN_ONLY | Run with Adobe credentials for live evidence, or make dry-run limitations clearer. |
| example_029 | 0.7919 | 1.0000 | 1.0000 | 0.3602 | ANSWER_TOO_GENERIC | Add richer batch-status answer rendering. |
| example_013 | 0.7920 | 1.0000 | 1.0000 | 0.4324 | ANSWER_TOO_GENERIC | Add richer recent-dataset change rendering. |
| example_030 | 0.7936 | 1.0000 | 1.0000 | 0.3827 | ANSWER_TOO_GENERIC | Add richer batch-detail answer rendering. |
| example_007 | 0.7941 | 0.9000 | 0.7760 | 0.7902 | API_PATH_MISMATCH | Improve schema/dataset endpoint choice for this family. |
| example_016 | 0.7955 | 1.0000 | 1.0000 | 0.3871 | ANSWER_TOO_GENERIC | Add richer tag-list answer rendering. |
| example_033 | 0.7957 | 1.0000 | 1.0000 | 0.3951 | ANSWER_TOO_GENERIC | Add richer observability metric value rendering. |
| example_020 | 0.7967 | 1.0000 | 1.0000 | 0.3757 | ANSWER_TOO_GENERIC | Add richer merge-policy count rendering. |
| example_025 | 0.7980 | 1.0000 | 1.0000 | 0.3912 | ANSWER_TOO_GENERIC | Add richer segment-job list rendering. |

## Overfitting Risks

The template generalization report found two medium risks and no high risks:

- `segment_new_destination_mapping`: reusable relative-time pattern should be monitored on hidden queries.
- `tag_*`: named tag detail uses a benchmark-compatible ID fallback only when no tag ID is present.

All new architecture-pass components use reusable families, schema/API validation, and observed tool evidence rather than exact public-answer memorization.

## Final Pipeline Result

The final pipeline completed successfully:

- `python3 scripts/warm_cache.py`
- `python3 scripts/inspect_schema.py`
- `python3 scripts/run_dev_eval.py`
- `python3 scripts/generate_failure_analysis.py`
- `python3 scripts/generate_family_score_report.py`
- `python3 scripts/generate_pareto_report.py`
- `python3 scripts/generate_template_generalization_report.py`
- `python3 -m pytest`
- `python3 scripts/package_submission.py`
- `python3 scripts/package_query_outputs.py`
- `python3 scripts/check_submission_ready.py`

Tests: 31 passed.

Packaging/readiness: passed.

Readiness checks confirmed: source zip exists, final submission manifest exists, 35 query output folders exist, metadata and trajectory JSON parse, required trajectory fields are present, no unresolved API placeholders remain, no secret leaks were found, and the default strategy is `SQL_FIRST_API_VERIFY`.

## Live API Notes

The normal dev evaluation remains safe without credentials. Dry-run API behavior is preserved, and answers do not claim live API confirmation when credentials are unavailable. Live API parsing can use the normalized evidence path when credentials are configured.

## Recommendation

Keep `SQL_FIRST_API_VERIFY` as the final-submission default. It remains tied for highest correctness, has the best final score, uses fewer tool calls than `TEMPLATE_FIRST`, and now has lower token/runtime cost than the pre-pass baseline.

Next high-ROI work is answer-template depth for batch, observability, tags, merge-policy, segment-job, and recent-dataset families, plus one schema/dataset API path refinement.
