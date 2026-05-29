# Paper-ready artifact tables: built-in formal runbook verification benchmark

## Feature coverage

| Feature | Evidence in artifact | CLI/report surface |
| --- | --- | --- |
| Executable DSL | schema, parser, typed descriptors | `frv validate/schema` |
| Bounded checking | dependency-aware transition exploration | `frv check` |
| Counterexample explanation | small-step trace, Hoare triple, weakest-precondition hint, source line | `frv check --format json / frv explain` |
| Runtime conformance | observed step logs checked against model dependencies and preconditions | `frv runtime-verify` |
| Mutation calibration | synthetic missing-guard/reorder/stale-owner/retry/wait/capacity/waiver mutants | `frv mutate` |
| Benchmark governance | provenance, licensing, validity threats, oracle labels | `frv benchmark` |

## Benchmark results

| Runbooks | Pass | States | Traces | Runtime seconds | Violations | Prose findings | Validity threats |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 14 | `True` | 119 | 16 | 0.057162 | `{"bounded_alert_suppression": 20, "cache_flush_requires_write_freeze": 2, "cache_warmup_before_traffic": 6, "cache_warmup_within_capacity": 4, "dns_health_check_converged_before_cutover": 1, "dns_no_split_brain_during_ttl": 1, "dns_requires_regional_capacity": 3, "dns_ttl_elapsed_before_finalize": 1, "no_draining_all_replicas": 36, "no_duplicate_processing_risk": 4, "no_failover_to_unhealthy_region": 16, "no_rebalance_to_zero_consumers": 2, "no_replay_without_dedupe": 2, "no_rollback_during_incompatible_migration": 16, "no_stale_reads_after_cache_flush": 2, "no_unstable_consumer_group_with_backlog": 2, "object_bucket_replication_min_regions": 1, "object_bucket_replication_regions_healthy": 3, "object_replication_target_region_healthy": 2, "object_restore_requires_snapshot": 2, "object_restore_requires_write_freeze": 2, "object_restore_within_rpo": 2, "object_restore_within_rto": 2, "precondition": 1, "queue_backlog_requires_consumers": 2, "quorum_before_data_loss_action": 21, "service_min_available": 56}` | `{"backfill-needs-queue-capacity": 1, "cache-flush-needs-warmup-capacity": 2, "data-deletion-needs-restore-precondition": 1, "destructive-delete-needs-targeting": 1, "failover-needs-health-and-quorum": 3, "prose-suppression-applied": 1}` | `{"abstraction_bias": 4, "bounded_search_limits": 8, "public_data_incompleteness": 5, "synthetic_mutant_bias": 9}` |

## Algorithm ablation proxy

| Counter | Value | Interpretation |
| --- | ---: | --- |
| `states_explored` | 119 | bounded transition states visited |
| `transitions_explored` | 209 | candidate operator actions evaluated |
| `max_branch_factor` | 5 | largest enabled-step set |
| `reductions_applied` | 0 | implemented reduction/pruning counter |
| `minimized_counterexample_trace_length` | 1 | shortest minimized witness length |
| `symbolic_splits` | 0 | symbolic case split counter |

## Counterexample usefulness

| Metric | Value |
| --- | --- |
| runbooks_with_minimized_counterexamples | `9` |
| shortest_minimized_trace | `1` |
| effect_annotation_warnings | `105` |
| oracle_review_labels | `{"false_positive": 14, "true_hazard": 14, "unsupported_claim": 14, "useful_warning": 14}` |

## Adoption workflows

| Workflow | Passing suites | Failing suites |
| --- | ---: | ---: |
| `schema_only_validation` | 14 | 0 |
| `prose_linting` | 10 | 4 |
| `bounded_checking` | 5 | 9 |
| `type_effect_checking` | 5 | 9 |
| `combined_workflow` | 14 | 0 |
| `semantic_diffing` | 1 | 0 |
