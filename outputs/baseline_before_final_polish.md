# Baseline Before Final Polish

Generated before making final-polish code changes.

## Pipeline

The following commands completed successfully:

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

Tests: 25 passed. Packaging/readiness: passed.

## Strategy Comparison

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.9457 | 0.1143 | 0.4677 | 0.5529 | 0.5317 | 1.0000 | 0.0049 | 1046.0 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9784 | 0.4430 | 0.6653 | 0.6281 | 2.1143 | 0.0068 | 1281.8 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9457 | 0.7794 | 0.4908 | 0.7593 | 0.7363 | 1.1714 | 0.0024 | 1010.5 |
| SQL_FIRST_API_VERIFY | 0.9457 | 0.9864 | 0.4941 | 0.8224 | 0.7952 | 1.4571 | 0.0025 | 1085.6 |
| TEMPLATE_FIRST | 0.9457 | 0.9864 | 0.4941 | 0.8224 | 0.7915 | 1.7143 | 0.0028 | 1136.2 |

## SQL_FIRST_API_VERIFY Baseline

- Avg SQL correctness: 0.9457
- Avg API correctness: 0.9864
- Avg answer correctness: 0.4941
- Avg correctness: 0.8224
- Avg final score: 0.7952
- Avg tool calls: 1.4571
- Avg runtime: 0.0025s
- Avg estimated tokens: 1085.6

## Lowest 10 SQL_FIRST_API_VERIFY Failures

| Query ID | Final | SQL | API | Answer | Category | Query |
|---|---:|---:|---:|---:|---|---|
| example_000 | 0.5055 | 0.0000 | 1.0000 | 0.7922 | SQL_COLUMN_MISMATCH | When was the journey 'Birthday Message' published? |
| example_003 | 0.7534 | 0.9000 | 1.0000 | 0.4906 | ANSWER_TOO_GENERIC | List all segment audiences connected to the destination named 'SMS Opt-In', showing audienceId, name, totalProfiles, createdTime, updatedTime, and used in other audience count for each audience. Remove any row limit from the results. |
| example_033 | 0.7771 | 1.0000 | 1.0000 | 0.3333 | ANSWER_TOO_GENERIC | What are the daily 'timeseries.ingestion.dataset.recordsuccess.count' values between '2026-03-15' and '2026-03-31'? |
| example_024 | 0.7777 | 1.0000 | 1.0000 | 0.3248 | ANSWER_TOO_GENERIC | Which segment definitions were updated most recently? |
| example_011 | 0.7797 | 0.9000 | 1.0000 | 0.5141 | DRY_RUN_ONLY | How many schemas do I have? |
| example_018 | 0.7831 | 1.0000 | 1.0000 | 0.3483 | ANSWER_TOO_GENERIC | Show me the details of the tag named 'cool'. |
| example_034 | 0.7861 | 1.0000 | 1.0000 | 0.3506 | ANSWER_TOO_GENERIC | Show ingestion record counts and batch success counts for the last 90 days. |
| example_025 | 0.7897 | 1.0000 | 1.0000 | 0.3636 | ANSWER_TOO_GENERIC | List all segment evaluation jobs. |
| example_001 | 0.7899 | 0.9000 | 1.0000 | 0.5468 | DRY_RUN_ONLY | Give me inactive journeys |
| example_004 | 0.7901 | 0.9000 | 1.0000 | 0.5479 | DRY_RUN_ONLY | Show me the IDs of failed dataflow runs |
