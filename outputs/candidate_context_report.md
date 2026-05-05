# Candidate Context Report

Candidate context is schema/API retrieval only. It does not use public gold patterns or decide final SQL.

## Summary

| Metric | Value |
| --- | ---: |
| avg_candidate_context_tokens | 888.5714 |
| avg_full_schema_context_tokens | 4682 |
| compression_ratio | 0.1898 |
| table_recall_at_3 | 0.4333 |
| table_recall_at_5 | 0.5111 |
| api_recall_at_3 | 0.4677 |
| api_recall_at_5 | 0.5484 |

## Per Example

| Query ID | Tables | APIs | Confidence | Used gold patterns |
| --- | --- | --- | ---: | --- |
| `example_000` | dim_campaign | journey_list, schema_registry_schema, unified_tag_detail | 0.8667 | False |
| `example_001` | dim_campaign | journey_list | 0.8667 | False |
| `example_002` | dim_campaign | journey_list, catalog_batches, catalog_datasets, export_batch_failed, export_batch_files | 0.8667 | False |
| `example_003` | dim_segment, hkg_br_segment_target, dim_collection, dim_target, hkg_br_base_segment_used_by_dependent_segment | audit_events, audit_events_short, merge_policies, segment_jobs, ups_audiences | 0.85 | False |
| `example_004` | dim_connector, dim_target | flowservice_runs, audit_events, export_batch_failed, flowservice_flows | 0.6667 | False |
| `example_005` | dim_connector, dim_target, hkg_br_base_segment_used_by_dependent_segment | export_batch_files, export_batch_failed, flowservice_flows, audit_events, catalog_datasets | 0.6667 | False |
| `example_006` | dim_blueprint, dim_collection, hkg_br_blueprint_collection | export_batch_files, audit_events, audit_events_short, catalog_batch_detail, catalog_batches | 0.6667 | False |
| `example_007` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | catalog_batches, catalog_datasets, export_batch_failed, export_batch_files, schema_registry_schemas | 0.0833 | False |
| `example_008` | dim_collection, dim_segment, hkg_br_collection_property, hkg_br_segment_property | audit_events, audit_events_short, export_batch_failed, export_batch_files, schema_registry_schema | 0.6667 | False |
| `example_009` | dim_blueprint, dim_collection, hkg_br_blueprint_collection | audit_events, audit_events_short, catalog_batch_detail, export_batch_failed, export_batch_files | 0.6667 | False |
| `example_010` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | audit_events, audit_events_short, catalog_batches, export_batch_failed, export_batch_files | 0.0833 | False |
| `example_011` | dim_blueprint, dim_collection, hkg_br_blueprint_collection | audit_events, audit_events_short, catalog_batch_detail, catalog_batches, catalog_datasets | 0.6667 | False |
| `example_012` | dim_connector, dim_target | export_batch_files, flowservice_flows, merge_policies, segment_jobs, ups_audiences | 0.6667 | False |
| `example_013` | dim_blueprint, dim_collection, hkg_br_blueprint_collection | audit_events, export_batch_files, audit_events_short, catalog_batch_detail, catalog_batches | 0.6667 | False |
| `example_014` | dim_collection, dim_segment, dim_target, hkg_br_segment_target, hkg_br_base_segment_used_by_dependent_segment | audit_events, audit_events_short, catalog_batch_detail, export_batch_files | 0.6667 | False |
| `example_015` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | unified_tag_categories, export_batch_files, unified_tag_detail | 0.0833 | False |
| `example_016` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | unified_tag_categories, export_batch_files, catalog_batches, catalog_datasets, export_batch_failed | 0.0833 | False |
| `example_017` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | unified_tag_categories, unified_tag_detail | 0.0833 | False |
| `example_018` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | unified_tag_categories, unified_tag_detail, catalog_batch_detail, schema_registry_schema | 0.0833 | False |
| `example_019` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | merge_policies, export_batch_files, catalog_batches, catalog_datasets, export_batch_failed | 0.0833 | False |
| `example_020` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | merge_policies, export_batch_files | 0.0833 | False |
| `example_021` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | audit_events, audit_events_short, export_batch_failed, export_batch_files, merge_policies | 0.0833 | False |
| `example_022` | dim_segment, hkg_br_segment_target, dim_target, br_campaign_segment, hkg_br_base_segment_used_by_dependent_segment | segment_definitions, export_batch_files, merge_policies, segment_jobs, ups_audiences | 0.85 | False |
| `example_023` | dim_segment, hkg_br_segment_target, dim_target, br_campaign_segment, hkg_br_base_segment_used_by_dependent_segment | segment_definitions, merge_policies, segment_jobs, ups_audiences, catalog_batches | 0.85 | False |
| `example_024` | dim_segment, hkg_br_segment_target, dim_target, br_campaign_segment, hkg_br_base_segment_used_by_dependent_segment | segment_definitions, merge_policies, segment_jobs, ups_audiences | 0.85 | False |
| `example_025` | dim_segment, hkg_br_segment_target, dim_target, br_campaign_segment, hkg_br_base_segment_used_by_dependent_segment | segment_jobs, merge_policies, ups_audiences, catalog_batches, catalog_datasets | 0.85 | False |
| `example_026` | dim_segment, hkg_br_segment_target, dim_target, br_campaign_segment, hkg_br_base_segment_used_by_dependent_segment | segment_jobs, merge_policies, segment_definitions, ups_audiences | 0.85 | False |
| `example_027` | dim_segment, hkg_br_segment_target, dim_target, br_campaign_segment, hkg_br_base_segment_used_by_dependent_segment | segment_jobs, audit_events, audit_events_short, catalog_batches, export_batch_failed | 0.85 | False |
| `example_028` | dim_collection, dim_segment, dim_target, hkg_br_segment_target | audit_events, audit_events_short, export_batch_failed, export_batch_files, catalog_batch_detail | 0.6667 | False |
| `example_029` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | export_batch_failed, audit_events, audit_events_short, catalog_batch_detail, catalog_batches | 0.0833 | False |
| `example_030` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | catalog_batch_detail, export_batch_failed, export_batch_files, schema_registry_schema, unified_tag_detail | 0.0833 | False |
| `example_031` | dim_collection, dim_segment, dim_target, hkg_br_segment_target | audit_events, audit_events_short, export_batch_files, export_batch_failed, catalog_batch_detail | 0.6667 | False |
| `example_032` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | export_batch_failed, export_batch_files, audit_events, audit_events_short, catalog_batch_detail | 0.0833 | False |
| `example_033` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | observability_metrics, catalog_batches, catalog_datasets, audit_events, audit_events_short | 0.0833 | False |
| `example_034` | br_campaign_segment, dim_property, dim_target, hkg_br_base_segment_used_by_dependent_segment, hkg_br_blueprint_collection | ups_audiences, audit_events, audit_events_short, catalog_datasets, export_batch_failed | 0.0833 | False |
