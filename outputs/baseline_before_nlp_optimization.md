# Baseline Before NLP Optimization

Generated before implementing the NLP-inspired optimization pass.

## Pipeline

The baseline pipeline completed successfully:

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

Tests: 31 passed. Packaging/readiness: passed.

## Strategy Table

| Strategy | Correctness | Final score | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.5751 | 0.5549 | 1.00 | 0.0069 | 920 |
| LLM_FREE_AGENT_BASELINE | 0.6700 | 0.6337 | 2.11 | 0.0076 | 1187 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.7769 | 0.7545 | 1.17 | 0.0022 | 931 |
| SQL_FIRST_API_VERIFY | 0.8399 | 0.8134 | 1.46 | 0.0022 | 1003 |
| TEMPLATE_FIRST | 0.8399 | 0.8099 | 1.71 | 0.0022 | 1030 |

Best correctness: `SQL_FIRST_API_VERIFY`

Best efficiency: `SQL_ONLY_BASELINE`

Best overall: `SQL_FIRST_API_VERIFY`

## SQL_FIRST_API_VERIFY Baseline

- Avg SQL correctness: 0.9714
- Avg API correctness: 0.9864
- Avg answer correctness: 0.5182
- Avg correctness: 0.8399
- Avg final score: 0.8134
- Avg tool calls: 1.4571
- Avg runtime: 0.0022s
- Avg estimated tokens: 1002.7

## Lowest 10 SQL_FIRST_API_VERIFY Failures

| Query ID | Final | SQL | API | Answer | Category | Recommended Fix |
|---|---:|---:|---:|---:|---|---|
| example_011 | 0.7803 | 0.9000 | 1.0000 | 0.5141 | DRY_RUN_ONLY | Run with Adobe credentials for live evidence, or make the answer explicitly describe dry-run limitations. |
| example_001 | 0.7912 | 0.9000 | 1.0000 | 0.5468 | DRY_RUN_ONLY | Run with Adobe credentials for live evidence, or make the answer explicitly describe dry-run limitations. |
| example_029 | 0.7919 | 1.0000 | 1.0000 | 0.3602 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_013 | 0.7920 | 1.0000 | 1.0000 | 0.4324 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_030 | 0.7936 | 1.0000 | 1.0000 | 0.3827 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_007 | 0.7941 | 0.9000 | 0.7760 | 0.7902 | API_PATH_MISMATCH | Add endpoint selection rules or endpoint catalog coverage for this query family. |
| example_016 | 0.7955 | 1.0000 | 1.0000 | 0.3871 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_033 | 0.7957 | 1.0000 | 1.0000 | 0.3951 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_020 | 0.7967 | 1.0000 | 1.0000 | 0.3757 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
| example_025 | 0.7980 | 1.0000 | 1.0000 | 0.3912 | ANSWER_TOO_GENERIC | Add a query-family answer template that names concrete SQL/API evidence. |
