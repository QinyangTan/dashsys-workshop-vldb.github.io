# Baseline Before Architecture Optimization

Generated before the architecture-inspired optimization pass.

## Pipeline

The full baseline pipeline completed successfully:

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

Tests: 27 passed. Packaging/readiness: passed.

## Strategy Comparison

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.9714 | 0.1143 | 0.5017 | 0.5734 | 0.5530 | 1.0000 | 0.0053 | 938.1 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9784 | 0.4587 | 0.6700 | 0.6335 | 2.1143 | 0.0068 | 1209.7 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9714 | 0.7794 | 0.5150 | 0.7769 | 0.7544 | 1.1714 | 0.0026 | 943.6 |
| SQL_FIRST_API_VERIFY | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8132 | 1.4571 | 0.0027 | 1018.1 |
| TEMPLATE_FIRST | 0.9714 | 0.9864 | 0.5182 | 0.8399 | 0.8098 | 1.7143 | 0.0030 | 1046.8 |

## SQL_FIRST_API_VERIFY Baseline

- Avg SQL correctness: 0.9714
- Avg API correctness: 0.9864
- Avg answer correctness: 0.5182
- Avg correctness: 0.8399
- Avg final score: 0.8132
- Avg tool calls: 1.4571
- Avg runtime: 0.0027s
- Avg estimated tokens: 1018.1
