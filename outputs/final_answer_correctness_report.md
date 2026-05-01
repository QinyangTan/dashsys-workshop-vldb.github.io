# Final Answer-Correctness Optimization Report

## Baseline Before This Pass

User-provided baseline for `SQL_FIRST_API_VERIFY`:

| Metric | Before |
| --- | ---: |
| Correctness | 0.8399 |
| Answer correctness | 0.5182 |
| Final score | 0.8146 |
| Avg tool calls | 1.4571 |
| Avg estimated tokens | 851.6 |

## Final Result

`SQL_FIRST_API_VERIFY` remains the default and the best overall strategy.

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQL_ONLY_BASELINE | 0.9714 | 0.1143 | 0.5114 | 0.5763 | 0.5578 | 1.0000 | 708.3 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9784 | 0.4610 | 0.6707 | 0.6361 | 2.1143 | 975.9 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9714 | 0.7794 | 0.5176 | 0.7777 | 0.7570 | 1.1714 | 718.9 |
| SQL_FIRST_API_VERIFY | 0.9714 | 0.9864 | 0.5208 | 0.8407 | 0.8154 | 1.4571 | 851.6 |
| TEMPLATE_FIRST | 0.9714 | 0.9864 | 0.5208 | 0.8407 | 0.8125 | 1.7143 | 817.4 |

## Before vs After

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Answer correctness | 0.5182 | 0.5208 | +0.0026 |
| Overall correctness | 0.8399 | 0.8407 | +0.0008 |
| Final score | 0.8146 | 0.8154 | +0.0008 |
| Avg tool calls | 1.4571 | 1.4571 | +0.0000 |
| Avg estimated tokens | 851.6 | 851.6 | flat |

## Implemented

- Added a verification-first answer layer: `answer_slots.py`, `answer_intent.py`, `answer_claims.py`, `answer_verifier.py`, `answer_style_miner.py`, `answer_reranker.py`, and `answer_diagnostics.py`.
- Wired `synthesize_answer_with_diagnostics` into `AgentExecutor.run`.
- Added compact `answer_diagnostics` trajectory steps without adding them to the estimated LLM/token budget.
- Improved dry-run-safe answer templates for tags, batches, merge policies, segment definitions/jobs, and live-like batch/tag payloads.
- Kept all SQL/API execution unchanged: no extra tool calls, no extra LLM calls, no default strategy change.

## Verifier Diagnostics

For `SQL_FIRST_API_VERIFY`, all 35 evaluated answers passed verifier checks after reranking.

| Category | Count |
| --- | ---: |
| verifier_passed | 35 |
| verifier_failed | 0 |
| unsupported_claims | 0 |

## Lowest 10 Remaining Answer Failures

| Query ID | Answer score | Final score | Current issue |
| --- | ---: | ---: | --- |
| example_029 | 0.3725 | 0.7946 | Batch count requires live API evidence in dry-run mode. |
| example_030 | 0.3823 | 0.7964 | Batch detail answer is necessarily generic without live API payload. |
| example_025 | 0.3912 | 0.7991 | Segment evaluation job list is API-only in dry-run mode. |
| example_020 | 0.3929 | 0.8009 | Merge-policy count is API-only in dry-run mode. |
| example_033 | 0.3951 | 0.7973 | Observability daily values require live API evidence. |
| example_031 | 0.3985 | 0.8010 | Batch files require live API payload. |
| example_019 | 0.4029 | 0.8029 | Merge-policy list is API-only in dry-run mode. |
| example_028 | 0.4037 | 0.8030 | Recent batch list is API-only in dry-run mode. |
| example_024 | 0.4050 | 0.8031 | Recent segment definitions require live API payload. |
| example_015 | 0.4154 | 0.8078 | Tag count is API-only in dry-run mode. |

## Validation

- `python3 scripts/run_dev_eval.py`: passed.
- `python3 scripts/generate_failure_analysis.py`: passed.
- `python3 -m pytest`: 46 passed.
- `python3 scripts/package_submission.py`: passed.
- `python3 scripts/package_query_outputs.py`: passed.
- `python3 scripts/check_submission_ready.py`: passed.

## Default Strategy

`SQL_FIRST_API_VERIFY` remains the default and best overall strategy. The pass improved answer correctness and final score without increasing tool calls or the rounded estimated token average.
