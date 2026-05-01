# Strategy Comparison

| Strategy | Correctness | Final score | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 0.5751 | 0.5567 | 1.00 | 0.0046 | 708 |
| LLM_FREE_AGENT_BASELINE | 0.6700 | 0.6354 | 2.11 | 0.0067 | 976 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.7769 | 0.7563 | 1.17 | 0.0016 | 719 |
| SQL_FIRST_API_VERIFY | 0.8399 | 0.8146 | 1.46 | 0.0017 | 852 |
| TEMPLATE_FIRST | 0.8399 | 0.8117 | 1.71 | 0.0017 | 817 |

- Best correctness: `SQL_FIRST_API_VERIFY`
- Best efficiency: `SQL_ONLY_BASELINE`
- Best overall: `SQL_FIRST_API_VERIFY`

## Token Context

| Strategy | Metadata tokens | Prompt tokens | Preprocess (s) | Planning (s) | Execution (s) | Answer (s) |
|---|---:|---:|---:|---:|---:|---:|
| SQL_ONLY_BASELINE | 819 | 1144 | 0.00200 | 0.00000 | 0.00130 | 0.00000 |
| LLM_FREE_AGENT_BASELINE | 5782 | 7440 | 0.00230 | 0.00010 | 0.00120 | 0.00000 |
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 823 | 1148 | 0.00160 | 0.00000 | 0.00040 | 0.00000 |
| SQL_FIRST_API_VERIFY | 819 | 1144 | 0.00150 | 0.00030 | 0.00040 | 0.00000 |
| TEMPLATE_FIRST | 817 | 1142 | 0.00150 | 0.00010 | 0.00050 | 0.00000 |

## Recommended Next Focus
- Improve entity extraction and join-template coverage.
- Add endpoint-specific param selection from observed gold API patterns.
