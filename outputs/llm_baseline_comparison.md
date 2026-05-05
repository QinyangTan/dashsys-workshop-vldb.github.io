# LLM Baseline Comparison

| System | Rows | Valid runs | Failed runs | Avg answer score on valid runs | Avg tool calls on valid runs |
| --- | ---: | ---: | ---: | ---: | ---: |
| REAL_LLM_TWO_TOOLS_BASELINE | 35 | 0 | 35 | 0.0000 | 0.00 |
| LLM_CONTROLLER_OPTIMIZED_AGENT | 35 | 35 | 0 | 0.4666 | 1.46 |

## Failed Real LLM Tool Loops

These rows are real LLM calls, but they are not counted as successful real tool-using baseline runs.

| Query ID | Tool calls executed? | Failure reason |
| --- | --- | --- |
| `example_000` | False | invalid_tool_call_format_after_retry |
| `example_001` | False | invalid_tool_call_format_after_retry |
| `example_002` | False | invalid_tool_call_format_after_retry |
| `example_003` | False | invalid_tool_call_format_after_retry |
| `example_004` | False | invalid_tool_call_format_after_retry |
| `example_005` | False | invalid_tool_call_format_after_retry |
| `example_006` | False | invalid_tool_call_format_after_retry |
| `example_007` | False | invalid_tool_call_format_after_retry |
| `example_008` | False | invalid_tool_call_format_after_retry |
| `example_009` | False | invalid_tool_call_format_after_retry |
| `example_010` | False | invalid_tool_call_format_after_retry |
| `example_011` | False | invalid_tool_call_format_after_retry |
| `example_012` | False | invalid_tool_call_format_after_retry |
| `example_013` | False | invalid_tool_call_format_after_retry |
| `example_014` | False | invalid_tool_call_format_after_retry |
| `example_015` | False | invalid_tool_call_format_after_retry |
| `example_016` | False | invalid_tool_call_format_after_retry |
| `example_017` | False | invalid_tool_call_format_after_retry |
| `example_018` | False | invalid_tool_call_format_after_retry |
| `example_019` | False | invalid_tool_call_format_after_retry |
