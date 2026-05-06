# LLM Baseline Comparison

| System | Rows | Valid runs | Failed runs | Avg answer score on valid runs | Avg tool calls on valid runs |
| --- | ---: | ---: | ---: | ---: | ---: |
| REAL_LLM_TWO_TOOLS_BASELINE | 35 | 31 | 4 | 0.4151 | 1.55 |
| LLM_CONTROLLER_OPTIMIZED_AGENT | 35 | 35 | 0 | 0.4710 | 1.46 |

## Failed Real LLM Tool Loops

These rows are real LLM calls, but they are not counted as successful real tool-using baseline runs.

| Query ID | Tool calls executed? | Failure reason |
| --- | --- | --- |
| `example_009` | False | no_valid_tool_calls_executed |
| `example_011` | False | no_valid_tool_calls_executed |
| `example_031` | False | no_valid_tool_calls_executed |
| `example_033` | False | no_valid_tool_calls_executed |
