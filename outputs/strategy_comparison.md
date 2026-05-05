# Strategy Comparison

| Strategy | Correctness | Final score | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.5763 | 0.5578 | 1.00 | 0.0113 | 708 |
| LLM_FREE_AGENT_BASELINE | 0.6707 | 0.6361 | 2.11 | 0.0179 | 976 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.7777 | 0.7570 | 1.17 | 0.0100 | 719 |
| SQL_FIRST_API_VERIFY | 0.8407 | 0.8154 | 1.46 | 0.0104 | 852 |
| TEMPLATE_FIRST | 0.8407 | 0.8124 | 1.71 | 0.0105 | 818 |

- Best correctness: `SQL_FIRST_API_VERIFY`
- Best efficiency: `SQL_ONLY_BASELINE`
- Best overall: `SQL_FIRST_API_VERIFY`

## Token Context

| Strategy | Metadata tokens | Prompt tokens | Preprocess (s) | Planning (s) | Execution (s) | Answer (s) |
|---|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 819 | 1463 | 0.00490 | 0.00010 | 0.00130 | 0.00090 |
| LLM_FREE_AGENT_BASELINE | 5782 | 7759 | 0.00760 | 0.00010 | 0.00130 | 0.00130 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 823 | 1467 | 0.00250 | 0.00010 | 0.00040 | 0.00050 |
| SQL_FIRST_API_VERIFY | 819 | 1463 | 0.00240 | 0.00030 | 0.00040 | 0.00050 |
| TEMPLATE_FIRST | 817 | 1461 | 0.00250 | 0.00010 | 0.00050 | 0.00050 |

## Recommended Next Focus
- Improve entity extraction and join-template coverage.
- Add endpoint-specific param selection from observed gold API patterns.
