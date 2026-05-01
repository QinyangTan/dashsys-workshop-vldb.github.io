# Baseline Before Efficiency Pass

Generated after running the full baseline pipeline before this pass.

## Strategy Comparison

| Strategy | SQL | API | Answer | Correctness | Final | Tool calls | Runtime (s) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DETERMINISTIC_ROUTER_SELECTED_METADATA | 0.9171 | 0.7794 | 0.4596 | 0.7386 | 0.7153 | 1.1714 | 0.0023 | 1027.1 |
| LLM_FREE_AGENT_BASELINE | 0.5971 | 0.9734 | 0.4280 | 0.6593 | 0.6215 | 2.0857 | 0.0039 | 1397.5 |
| SQL_FIRST_API_VERIFY | 0.9171 | 0.9734 | 0.4637 | 0.7980 | 0.7698 | 1.5143 | 0.0024 | 1112.7 |
| SQL_ONLY_BASELINE | 0.9171 | 0.1143 | 0.4333 | 0.5311 | 0.5091 | 1.0000 | 0.0068 | 1135.0 |
| TEMPLATE_FIRST | 0.9171 | 0.9734 | 0.4685 | 0.7994 | 0.7675 | 1.7714 | 0.0026 | 1169.9 |

## SQL_FIRST_API_VERIFY Baseline

- Avg SQL correctness: 0.9171
- Avg API correctness: 0.9734
- Avg answer correctness: 0.4637
- Avg final score: 0.7698
- Avg tool calls: 1.5143
- Avg runtime: 0.0024s
- Avg estimated tokens: 1112.7

## Lowest 10 SQL_FIRST_API_VERIFY Failures

| Query ID | Final | SQL | API | Answer | Query |
|---|---:|---:|---:|---:|---|
| example_005 | 0.4515 | 0.0000 | 1.0000 | 0.6344 | Export a list of all destinations in the b2b-prod sandbox, sorted by most recently modified, including all columns associated with each destination, and include the 'modified' column for validation. |
| example_000 | 0.5054 | 0.0000 | 1.0000 | 0.7922 | When was the journey 'Birthday Message' published? |
| example_021 | 0.7141 | 1.0000 | 0.7200 | 0.4408 | Show the default merge policy for schema class '_xdm.context.profile'. |
| example_014 | 0.7380 | 0.9000 | 0.8240 | 0.5577 | Show me all entities created by download |
| example_004 | 0.7535 | 0.9000 | 1.0000 | 0.4255 | Show me the IDs of failed dataflow runs |
| example_024 | 0.7540 | 1.0000 | 1.0000 | 0.2455 | Which segment definitions were updated most recently? |
| example_003 | 0.7542 | 0.9000 | 1.0000 | 0.4906 | List all segment audiences connected to the destination named 'SMS Opt-In', showing audienceId, name, totalProfiles, createdTime, updatedTime, and used in other audience count for each audience. Remove any row limit from the results. |
| example_023 | 0.7577 | 1.0000 | 1.0000 | 0.2571 | List all segment definitions. |
| example_008 | 0.7598 | 0.9000 | 1.0000 | 0.4439 | show me the field for Person: Birthday Today 001 |
| example_018 | 0.7698 | 1.0000 | 1.0000 | 0.3041 | Show me the details of the tag named 'cool'. |
