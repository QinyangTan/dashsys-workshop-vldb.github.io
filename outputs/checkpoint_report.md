# Checkpoint Report

Trajectory files inspected: 216

## Required Checkpoints

| Checkpoint | Technique | Correctness role | Efficiency role | Present in | Avg duration ms |
| --- | --- | --- | --- | ---: | ---: |
| `checkpoint_00_prompt_router` | prompt routing policy | chooses direct vs SQL/API evidence path | skips tools for safe conceptual prompts | 213 | 0.0 |
| `checkpoint_01_raw_query` | raw user query capture | preserves the original query | starts a reproducible trace | 216 | 0.0 |
| `checkpoint_02_query_normalization` | data cleaning / query normalization | improves matching robustness | reduces reparsing | 216 | 0.0 |
| `checkpoint_03_query_tokens` | domain-aware tokenization/entity extraction | extracts names/IDs/dates/metrics | shares token structure | 216 | 0.0 |
| `checkpoint_04_relevance_scoring` | attention-style relevance scoring | keeps useful schema/API context | reduces metadata tokens | 216 | 0.0 |
| `checkpoint_05_query_analysis` | branch prediction / QueryAnalysis | aligns route/domain/family/template decisions | avoids repeated analysis | 216 | 0.0 |
| `checkpoint_06_lookup_path` | TLB-style lookup path prediction | guides joins and API families | filters irrelevant paths | 216 | 0.0 |
| `checkpoint_07_context_card` | huge-page-style compact context card | packs required context | reduces prompt size | 216 | 0.0 |
| `checkpoint_08_candidate_plans` | pre-execution plan ensemble | chooses validated plan before execution | executes only one candidate | 216 | 0.0 |
| `checkpoint_09_plan_optimization` | compiler-style plan optimization | drops duplicates/placeholders | enforces compact plan | 216 | 0.0 |
| `checkpoint_10_evidence_policy` | API_REQUIRED/API_OPTIONAL/API_SKIP policy | keeps required API evidence | skips unnecessary API calls | 216 | 0.0 |
| `checkpoint_11_call_budget` | tool-call budgeting | bounds SQL/API plan | controls calls/tokens/runtime | 216 | 0.0 |
| `checkpoint_12_validation` | SQL/API safety validation | blocks unsafe calls | avoids wasted invalid execution | 216 | 0.0 |
| `checkpoint_13_tool_execution` | SQL/API tool execution | records SQL/API evidence | makes tool cost explicit | 216 | 0.0 |
| `checkpoint_14_evidence_bus` | operand forwarding / EvidenceBus | forwards exact evidence | avoids repeated lookup | 216 | 0.0 |
| `checkpoint_15_answer_slots` | structured answer slot extraction | builds factual answer fields | keeps evidence compact | 216 | 0.0 |
| `checkpoint_16_answer_verification` | claim verification / groundedness checking | blocks unsupported claims | rewrites without extra calls | 216 | 0.0 |
| `checkpoint_17_answer_reranking` | deterministic answer reranking | selects safest candidate | uses same evidence only | 216 | 0.0 |
| `checkpoint_18_final_answer` | concise grounded final response | returns evidence-grounded answer | keeps final response short | 216 | 0.0 |

## Representative Data Flow Examples

### simple_local_sql_query

- Query ID: `example_000`
- Query: When was the journey 'Birthday Message' published?
- Tool calls: 1
- First checkpoints: checkpoint_01_raw_query, checkpoint_00_prompt_router, checkpoint_simple_prompt_gate, checkpoint_02_query_normalization, checkpoint_03_query_tokens, checkpoint_04_relevance_scoring
- Final answer preview: The journey "Birthday Message" has not been published. The database shows a null published_time for this journey, and API evidence was not requested.

### sql_plus_api_verification_query

- Query ID: `debug_example_005`
- Query: Export a list of all destinations in the b2b-prod sandbox, sorted by most recently modified, including all columns associated with each destination, and include the 'modified' column for validation.
- Tool calls: 2
- First checkpoints: checkpoint_01_raw_query, checkpoint_simple_prompt_gate, checkpoint_02_query_normalization, checkpoint_03_query_tokens, checkpoint_04_relevance_scoring, checkpoint_05_query_analysis
- Final answer preview: Based on the evidence provided, 1 destination was found. The most recent is "Activate segments to S3 Feed" (amazon-s3 target) with a modification timestamp of 2026-04-14 16:15:03.000 UTC. Live API evidence is needed to validate the requeste

### api_only_or_dry_run_query

- Query ID: `example_015`
- Query: How many tags exist in this sandbox?
- Tool calls: 1
- First checkpoints: checkpoint_01_raw_query, checkpoint_00_prompt_router, checkpoint_simple_prompt_gate, checkpoint_02_query_normalization, checkpoint_03_query_tokens, checkpoint_04_relevance_scoring
- Final answer preview: The tag count cannot be determined from the available evidence. Live API verification was not executed because Adobe credentials are unavailable.

## Missing Checkpoints

- `debug_example_005` missing: checkpoint_00_prompt_router
- `debug_example_005b` missing: checkpoint_00_prompt_router
- `list_all_journeys` missing: checkpoint_00_prompt_router
