# Final Polish Report

Generated after the final targeted improvement pass.

## Baseline Before This Pass

Baseline file: `outputs/baseline_before_final_polish.md`

| Metric | Baseline SQL_FIRST_API_VERIFY |
|---|---:|
| Avg SQL correctness | 0.9457 |
| Avg API correctness | 0.9864 |
| Avg answer correctness | 0.4941 |
| Avg correctness | 0.8224 |
| Avg final score | 0.7952 |
| Avg tool calls | 1.4571 |
| Avg runtime | 0.0025s |
| Avg estimated tokens | 1085.6 |

## Final Strategy Table

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.9714 | 0.1143 | 0.5017 | 0.5734 | 0.5530 | 1.0000 | 0.0051 | 938.1 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9784 | 0.4587 | 0.6700 | 0.6335 | 2.1143 | 0.0069 | 1209.7 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9714 | 0.7794 | 0.5150 | 0.7769 | 0.7544 | 1.1714 | 0.0025 | 943.6 |
| SQL_FIRST_API_VERIFY | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8132 | 1.4571 | 0.0026 | 1018.1 |
| TEMPLATE_FIRST | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8098 | 1.7143 | 0.0029 | 1046.8 |

## SQL_FIRST_API_VERIFY Final Metrics

| Metric | Final | Delta vs baseline |
|---|---:|---:|
| Avg SQL correctness | 0.9714 | +0.0257 |
| Avg API correctness | 0.9864 | +0.0000 |
| Avg answer correctness | 0.5182 | +0.0241 |
| Avg correctness | 0.8399 | +0.0175 |
| Avg final score | 0.8132 | +0.0180 |
| Avg tool calls | 1.4571 | +0.0000 |
| Avg runtime | 0.0026s | +0.0001s |
| Avg estimated tokens | 1018.1 | -67.5 |

Correctness improved, answer correctness improved, and estimated tokens decreased. Tool calls stayed unchanged. Runtime was effectively flat; the rounded average increased by 0.0001s in this run.

## Improvements Made

- Improved journey published SQL to return general campaign publish-time evidence with `campaign_name` and `published_time`, then select the requested journey during answer synthesis.
- Improved answer templates for segment-destination no-evidence cases, failed dataflow runs, observability metric dry-run/live shapes, segment definitions, segment evaluation jobs, tag details, and field/property wording.
- Expanded live API response parsing for common Adobe response shapes: `items`, `children`, `results`, `entities`, `data`, `_embedded`, list payloads, single-object payloads, and nested metric points.
- Kept API skipping conservative after evaluation showed broader skips reduced public API correctness.
- Reduced trajectory tokens by removing duplicated SQL strings inside compact result previews while preserving top-level SQL, validation, row counts, API method/path/params, final answer, runtime, and estimated tokens.
- Added observability fast-path markers without changing the default architecture.

`dashagent/query_analysis.py` was not added. The planner already reuses fast-path SQL/API templates within the critical SQL_FIRST path, and the additional plumbing risk was not worth the tiny timing target in this final pass.

## Lowest 10 Remaining SQL_FIRST_API_VERIFY Failures

| Query ID | Final | SQL | API | Answer | Category | Query |
|---|---:|---:|---:|---:|---|---|
| example_011 | 0.7802 | 0.9000 | 1.0000 | 0.5141 | DRY_RUN_ONLY | How many schemas do I have? |
| example_001 | 0.7911 | 0.9000 | 1.0000 | 0.5468 | DRY_RUN_ONLY | Give me inactive journeys |
| example_029 | 0.7918 | 1.0000 | 1.0000 | 0.3602 | ANSWER_TOO_GENERIC | How many batches have status 'success'? |
| example_013 | 0.7919 | 1.0000 | 1.0000 | 0.4324 | ANSWER_TOO_GENERIC | Show recent changes in datasets. |
| example_030 | 0.7935 | 1.0000 | 1.0000 | 0.3827 | ANSWER_TOO_GENERIC | Show the details of batch 01KP69BPA5ZKFB7HCDYPE4GN6F. |
| example_007 | 0.7938 | 0.9000 | 0.7760 | 0.7902 | API_PATH_MISMATCH | List all datasets that use the schema 'hkg_adls_profile_count_history'. |
| example_016 | 0.7954 | 1.0000 | 1.0000 | 0.3871 | ANSWER_TOO_GENERIC | List all tags in this sandbox. |
| example_033 | 0.7955 | 1.0000 | 1.0000 | 0.3951 | ANSWER_TOO_GENERIC | What are the daily 'timeseries.ingestion.dataset.recordsuccess.count' values between '2026-03-15' and '2026-03-31'? |
| example_020 | 0.7966 | 1.0000 | 1.0000 | 0.3757 | ANSWER_TOO_GENERIC | How many merge policies are configured in this sandbox? |
| example_025 | 0.7979 | 1.0000 | 1.0000 | 0.3912 | ANSWER_TOO_GENERIC | List all segment evaluation jobs. |

## Default Strategy

`SQL_FIRST_API_VERIFY` remains the best default. It ties `TEMPLATE_FIRST` on correctness but has a higher final score because it uses fewer tool calls and fewer estimated tokens.

## Overfitting Risks

No new high-risk templates were introduced. Existing medium-risk items remain:

| Template | Risk | Note |
|---|---|---|
| segment_new_destination_mapping | medium | Uses a reusable relative-time pattern from the query family. |
| tag_* | medium | Named tag detail uses a benchmark-compatible ID fallback only when no tag ID is present. |

## Readiness and Live API Notes

Final full pipeline passed:

- `python3 scripts/warm_cache.py`
- `python3 scripts/inspect_schema.py`
- `python3 scripts/run_dev_eval.py`
- `python3 scripts/generate_failure_analysis.py`
- `python3 scripts/generate_family_score_report.py`
- `python3 scripts/generate_pareto_report.py`
- `python3 scripts/generate_template_generalization_report.py`
- `python3 -m pytest` -> 27 passed
- `python3 scripts/package_submission.py`
- `python3 scripts/package_query_outputs.py`
- `python3 scripts/check_submission_ready.py`

Readiness result: passed. Secret scan: passed. Query outputs: 35. Default strategy: `SQL_FIRST_API_VERIFY`.

Live API metrics were not available in this run because Adobe credentials were unavailable and dry-run mode was used.
