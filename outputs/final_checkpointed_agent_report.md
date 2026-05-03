# Final Checkpointed Agent Report

## Summary

Implemented an LLM-agent-compatible checkpoint layer around the existing deterministic backend. `SQL_FIRST_API_VERIFY` remains the default strategy, and the backend still executes one selected plan per query.

## Before vs After

| Metric | Before checkpoint pass | After checkpoint pass |
| --- | ---: | ---: |
| Correctness | 0.8407 | 0.8407 |
| Final score | 0.8154 | 0.8154 |
| Tool calls | 1.4571 | 1.4571 |
| Estimated tokens | 851.6 | 851.8 |
| Runtime | not provided in prompt baseline | 0.0102s |
| Answer correctness | not changed target baseline | 0.5208 |

No extra SQL/API calls were added. The small estimated-token difference is within rounding of the prior baseline and checkpoints are excluded from the eval token estimate because they are trajectory artifacts, not prompt/final-answer content.

## Final Strategy Table

| Strategy | Correctness | Final | SQL | API | Answer | Tool calls | Tokens | Runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.7777 | 0.7570 | 0.9714 | 0.7794 | 0.5176 | 1.1714 | 719.1 | 0.0099s |
| LLM_FREE_AGENT_BASELINE | 0.6707 | 0.6361 | 0.5971 | 0.9784 | 0.4610 | 2.1143 | 975.9 | 0.0176s |
| SQL_FIRST_API_VERIFY | 0.8407 | 0.8154 | 0.9714 | 0.9864 | 0.5208 | 1.4571 | 851.8 | 0.0102s |
| SQL_ONLY_BASELINE | 0.5763 | 0.5578 | 0.9714 | 0.1143 | 0.5114 | 1.0000 | 708.5 | 0.0112s |
| TEMPLATE_FIRST | 0.8407 | 0.8124 | 0.9714 | 0.9864 | 0.5208 | 1.7143 | 817.6 | 0.0103s |

Best overall remains `SQL_FIRST_API_VERIFY`.

## Checkpoint Coverage

- Required checkpoint IDs: 18
- Checkpoints per newly packaged trajectory: min 19, max 19
- All required checkpoint types observed in report: yes
- `checkpoint_simple_prompt_gate` is included in full executor trajectories in addition to the required 18 data-flow checkpoints.
- Checkpoint report: `outputs/checkpoint_report.md` and `outputs/checkpoint_report.json`.

## Trajectory Size

- Average SQL_FIRST eval trajectory size after checkpoints: 26.2 KB.
- Minimum/maximum SQL_FIRST eval trajectory size: 22.5 KB / 32.5 KB.
- Pre-pass trajectory size was not separately recorded before overwriting eval outputs, so no fabricated before-size is reported.

## SDK Adapter

- Optional OpenAI Agents SDK adapter is implemented and covered by tests; it no-ops when the SDK is absent.
- Checkpoint spans use compact, redacted checkpoint payloads when `agents.custom_span` is available.

## Validation

- `python3 scripts/run_dev_eval.py`: completed, 35 public examples.
- `python3 -m pytest`: 53 passed.
- `python3 scripts/package_submission.py`: passed.
- `python3 scripts/package_query_outputs.py`: passed; 38 query folders packaged.
- `python3 scripts/check_submission_ready.py`: passed (check_submission_ready.py returned ok=true).
- Packaged trajectory checkpoint count check: all packaged trajectories have at least 19 checkpoints.
- Secret scan: passed in packaging/readiness outputs.

## Lowest 10 Remaining SQL_FIRST_API_VERIFY Cases

| Query ID | Final | SQL | API | Answer | Query |
| --- | ---: | ---: | ---: | ---: | --- |
| example_011 | 0.7823 | 0.9000 | 1.0000 | 0.5141 | How many schemas do I have? |
| example_001 | 0.7910 | 0.9000 | 1.0000 | 0.5468 | Give me inactive journeys |
| example_013 | 0.7938 | 1.0000 | 1.0000 | 0.4324 | Show recent changes in datasets. |
| example_029 | 0.7945 | 1.0000 | 1.0000 | 0.3725 | How many batches have status 'success'? |
| example_007 | 0.7959 | 0.9000 | 0.7760 | 0.7902 | List all datasets that use the schema 'hkg_adls_profile_count_history'. |
| example_030 | 0.7963 | 1.0000 | 1.0000 | 0.3823 | Show the details of batch 01KP69BPA5ZKFB7HCDYPE4GN6F. |
| example_033 | 0.7973 | 1.0000 | 1.0000 | 0.3951 | What are the daily 'timeseries.ingestion.dataset.recordsuccess.count' values between '2026-03-15' and '2026-03-31'? |
| example_025 | 0.7991 | 1.0000 | 1.0000 | 0.3912 | List all segment evaluation jobs. |
| example_020 | 0.8008 | 1.0000 | 1.0000 | 0.3929 | How many merge policies are configured in this sandbox? |
| example_031 | 0.8010 | 1.0000 | 1.0000 | 0.3985 | Which files are available for download in batch 69de8a0e0cc6102b5d11f01e? |

## Remaining Risks

- Adobe API execution is still mostly dry-run unless credentials are available; live response behavior needs validation.
- Some API-only families still depend on planned API correctness and live parsers rather than observed live payloads.
- Checkpoints make trajectory files larger, although prompt/final-answer token estimates and tool calls stayed stable.
- Old non-eval debug outputs had to be refreshed so packaged trajectories include checkpoints; future stale debug runs should be regenerated or excluded before packaging.

## Outcome

The checkpoint layer is present, compact, JSON-serializable, redacted, and LLM-agent-compatible. Correctness/final score stayed stable, tool calls did not increase, `SQL_FIRST_API_VERIFY` remains the default, tests passed, and packaging/readiness passed.
