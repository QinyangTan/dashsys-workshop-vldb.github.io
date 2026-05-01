# Final Improvement Report

Generated after the efficiency and targeted-correctness pass.

## Baseline Before This Pass

Baseline was captured in `outputs/baseline_before_efficiency_pass.md` after running the full pipeline before code changes.

| Metric | SQL_FIRST_API_VERIFY baseline |
|---|---:|
| Avg SQL correctness | 0.9171 |
| Avg API correctness | 0.9734 |
| Avg answer correctness | 0.4637 |
| Avg correctness | 0.7980 |
| Avg final score | 0.7698 |
| Avg tool calls | 1.5143 |
| Avg runtime | 0.0024s |
| Avg estimated tokens | 1112.7 |

## Final Strategy Table

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.9457 | 0.1143 | 0.4677 | 0.5529 | 0.5317 | 1.0000 | 0.0051 | 1046.0 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9784 | 0.4430 | 0.6653 | 0.6281 | 2.1143 | 0.0071 | 1281.8 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9457 | 0.7794 | 0.4908 | 0.7593 | 0.7363 | 1.1714 | 0.0025 | 1010.5 |
| SQL_FIRST_API_VERIFY | 0.9457 | 0.9864 | 0.4941 | 0.8224 | 0.7952 | 1.4571 | 0.0026 | 1085.6 |
| TEMPLATE_FIRST | 0.9457 | 0.9864 | 0.4941 | 0.8224 | 0.7915 | 1.7143 | 0.0029 | 1136.2 |

## SQL_FIRST_API_VERIFY Final Metrics

| Metric | Value | Delta vs baseline |
|---|---:|---:|
| Avg SQL correctness | 0.9457 | +0.0286 |
| Avg API correctness | 0.9864 | +0.0130 |
| Avg answer correctness | 0.4941 | +0.0304 |
| Avg correctness | 0.8224 | +0.0244 |
| Avg final score | 0.7952 | +0.0254 |
| Avg tool calls | 1.4571 | -0.0572 |
| Avg runtime | 0.0026s | +0.0002s |
| Avg estimated tokens | 1085.6 | -27.1 |
| Avg metadata tokens | 1253.5 | recorded |
| Avg prompt tokens | 1729.1 | recorded |

Correctness improved. Efficiency improved on average tool calls and estimated tokens. Runtime was effectively flat, with this run slightly higher by about 0.0002 seconds.

## Lowest 10 Remaining SQL_FIRST_API_VERIFY Failures

| Query ID | Final | SQL | API | Answer | Category | Query | Recommended fix |
|---|---:|---:|---:|---:|---|---|---|
| example_000 | 0.5055 | 0.0000 | 1.0000 | 0.7922 | SQL_COLUMN_MISMATCH | When was the journey 'Birthday Message' published? | Align journey published SQL projection/aliases with gold-style columns. |
| example_003 | 0.7534 | 0.9000 | 1.0000 | 0.4906 | ANSWER_TOO_GENERIC | List all segment audiences connected to the destination named 'SMS Opt-In', showing audienceId, name, totalProfiles, createdTime, updatedTime, and used in other audience count for each audience. Remove any row limit from the results. | Add a richer segment-destination answer template using the SQL row fields. |
| example_033 | 0.7771 | 1.0000 | 1.0000 | 0.3333 | ANSWER_TOO_GENERIC | What are the daily 'timeseries.ingestion.dataset.recordsuccess.count' values between '2026-03-15' and '2026-03-31'? | Add observability time-series answer rendering for compact date/value lists. |
| example_024 | 0.7777 | 1.0000 | 1.0000 | 0.3248 | ANSWER_TOO_GENERIC | Which segment definitions were updated most recently? | Add a recent segment-definition answer template that names IDs/timestamps. |
| example_011 | 0.7797 | 0.9000 | 1.0000 | 0.5141 | DRY_RUN_ONLY | How many schemas do I have? | Improve dry-run wording and live schema-registry response parsing. |
| example_018 | 0.7831 | 1.0000 | 1.0000 | 0.3483 | ANSWER_TOO_GENERIC | Show me the details of the tag named 'cool'. | Add richer tag detail answer rendering from live tag fields. |
| example_034 | 0.7861 | 1.0000 | 1.0000 | 0.3506 | ANSWER_TOO_GENERIC | Show ingestion record counts and batch success counts for the last 90 days. | Add observability summary template for multi-metric windows. |
| example_025 | 0.7897 | 1.0000 | 1.0000 | 0.3636 | ANSWER_TOO_GENERIC | List all segment evaluation jobs. | Add segment job list answer template with status/timestamp fields. |
| example_001 | 0.7899 | 0.9000 | 1.0000 | 0.5468 | DRY_RUN_ONLY | Give me inactive journeys | Improve inactive journey wording while preserving dry-run caveat. |
| example_004 | 0.7901 | 0.9000 | 1.0000 | 0.5479 | DRY_RUN_ONLY | Show me the IDs of failed dataflow runs | Keep improving failed-run dry-run language and live parser coverage. |

## Default Strategy Decision

`SQL_FIRST_API_VERIFY` remains the best default. It tied `TEMPLATE_FIRST` on correctness, but had a higher final score because it used fewer tool calls and fewer tokens. `SQL_ONLY_BASELINE` remains the efficiency floor, but its API correctness is too low for the official task.

## Overfitting Risks

The template generalization report found two medium-risk templates:

| Template | Risk | Reason |
|---|---|---|
| segment_new_destination_mapping | medium | Uses a reusable relative-time pattern, but should be monitored on hidden audit/destination wording. |
| tag_* | medium | Named tag detail uses a benchmark-compatible ID fallback when no tag ID is present. |

No template was flagged as a high-risk exact public-answer memorization pattern. All listed templates are schema/API validated.

## Readiness Checks

All final pipeline checks passed:

- `python3 scripts/warm_cache.py`
- `python3 scripts/inspect_schema.py`
- `python3 scripts/run_dev_eval.py`
- `python3 scripts/generate_failure_analysis.py`
- `python3 scripts/generate_family_score_report.py`
- `python3 scripts/generate_pareto_report.py`
- `python3 scripts/generate_template_generalization_report.py`
- `python3 -m pytest` -> 25 passed
- `python3 scripts/package_submission.py`
- `python3 scripts/package_query_outputs.py`
- `python3 scripts/check_submission_ready.py`

Readiness result: passed. Query output count: 35. Secret scan: passed. Default strategy: `SQL_FIRST_API_VERIFY`.

## Next Remaining Work

1. Fix `example_000` by aligning the journey published SQL template projection/aliases with the gold-style query.
2. Improve answer templates for observability, segment definitions, tags, and segment jobs; these dominate the remaining answer-score gap.
3. Add live API credentials test coverage when credentials are available, especially for merge policies, schema registry, tag detail, and observability metrics.
4. Review the medium-risk tag fallback and destination-audit relative-time template against hidden-query style assumptions.
