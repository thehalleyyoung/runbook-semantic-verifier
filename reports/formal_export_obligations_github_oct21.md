# Proof obligations: GitHub Oct21 2018 MySQL failover reconstruction with quorum guard

These obligations make explicit what the native checker, exported starter models, and future runtime monitors are expected to preserve. They are bounded artifact obligations, not claims about live infrastructure.

| ID | Kind | Subject | Claim | Checked by |
| --- | --- | --- | --- | --- |
| `invariant:bounded_alert_suppression` | invariant | `bounded_alert_suppression` | alert suppression remains bounded | native bounded checker; exported as TLA+/Alloy label |
| `invariant:cache_flush_requires_write_freeze` | invariant | `cache_flush_requires_write_freeze` | destructive flush cannot race writers | native bounded checker; exported as TLA+/Alloy label |
| `invariant:cache_warmup_before_traffic` | invariant | `cache_warmup_before_traffic` | cold cache is not exposed to traffic | native bounded checker; exported as TLA+/Alloy label |
| `invariant:cache_warmup_within_capacity` | invariant | `cache_warmup_within_capacity` | cache entries stay within capacity | native bounded checker; exported as TLA+/Alloy label |
| `invariant:credential_active` | invariant | `credential_active` | credential remains active unless explicitly revoked | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dead_letter_drain_has_messages` | invariant | `dead_letter_drain_has_messages` | DLQ depth never goes negative | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dead_letter_replay_has_messages` | invariant | `dead_letter_replay_has_messages` | DLQ depth never goes negative | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dns_health_check_converged_before_cutover` | invariant | `dns_health_check_converged_before_cutover` | DNS cutover follows health convergence | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dns_no_split_brain_during_ttl` | invariant | `dns_no_split_brain_during_ttl` | stateful split-brain window is absent | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dns_requires_regional_capacity` | invariant | `dns_requires_regional_capacity` | DNS target can serve the service | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dns_target_region_healthy` | invariant | `dns_target_region_healthy` | DNS points only to healthy regions | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dns_ttl_elapsed_before_finalize` | invariant | `dns_ttl_elapsed_before_finalize` | finalization happens after TTL | native bounded checker; exported as TLA+/Alloy label |
| `invariant:dns_ttl_elapsed_before_recursion` | invariant | `dns_ttl_elapsed_before_recursion` | recursive cutovers do not overlap stateful TTL windows | native bounded checker; exported as TLA+/Alloy label |
| `invariant:effect` | invariant | `effect` | all declared step.effects conditions hold | native bounded checker; exported as TLA+/Alloy label |
| `invariant:effect_annotation_required` | invariant | `effect_annotation_required` | effect annotations make retry/reversal/blast-radius assumptions auditable | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_draining_all_replicas` | invariant | `no_draining_all_replicas` | not all replicas of any non-empty service are drained | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_draining_load_balancer_with_traffic` | invariant | `no_draining_load_balancer_with_traffic` | drained LB receives no traffic | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_duplicate_processing_risk` | invariant | `no_duplicate_processing_risk` | duplicate_risk remains false | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_failover_to_unhealthy_region` | invariant | `no_failover_to_unhealthy_region` | database primary region remains healthy | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_paused_queue_with_backlog` | invariant | `no_paused_queue_with_backlog` | no reachable paused backlog without processing capacity | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_queue_pause_without_drain_plan` | invariant | `no_queue_pause_without_drain_plan` | paused queues do not strand backlog | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_rebalance_to_zero_consumers` | invariant | `no_rebalance_to_zero_consumers` | backlog is not assigned zero consumers | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_replay_without_dedupe` | invariant | `no_replay_without_dedupe` | replay does not introduce duplicate-processing risk | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_rollback_during_incompatible_migration` | invariant | `no_rollback_during_incompatible_migration` | rollback does not occur during incompatible migration | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_stale_reads_after_cache_flush` | invariant | `no_stale_reads_after_cache_flush` | no stale-read-risk state remains | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_traffic_to_drained_load_balancer` | invariant | `no_traffic_to_drained_load_balancer` | positive traffic only reaches active load balancers | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_traffic_to_unhealthy_region` | invariant | `no_traffic_to_unhealthy_region` | positive traffic only reaches healthy regions | native bounded checker; exported as TLA+/Alloy label |
| `invariant:no_unstable_consumer_group_with_backlog` | invariant | `no_unstable_consumer_group_with_backlog` | backlog is processed only by a stable consumer group | native bounded checker; exported as TLA+/Alloy label |
| `invariant:object_bucket_replication_min_regions` | invariant | `object_bucket_replication_min_regions` | bucket durability requirement is preserved | native bounded checker; exported as TLA+/Alloy label |
| `invariant:object_bucket_replication_regions_healthy` | invariant | `object_bucket_replication_regions_healthy` | all bucket replica regions are healthy | native bounded checker; exported as TLA+/Alloy label |
| `invariant:object_replication_target_region_healthy` | invariant | `object_replication_target_region_healthy` | bucket replicas are only added in healthy regions | native bounded checker; exported as TLA+/Alloy label |
| `invariant:object_restore_requires_snapshot` | invariant | `object_restore_requires_snapshot` | restore has a concrete snapshot source | native bounded checker; exported as TLA+/Alloy label |
| `invariant:object_restore_requires_write_freeze` | invariant | `object_restore_requires_write_freeze` | restore is not racing concurrent bucket writes | native bounded checker; exported as TLA+/Alloy label |
| `invariant:object_restore_within_rpo` | invariant | `object_restore_within_rpo` | recovery point objective is met | native bounded checker; exported as TLA+/Alloy label |
| `invariant:object_restore_within_rto` | invariant | `object_restore_within_rto` | recovery time objective is met | native bounded checker; exported as TLA+/Alloy label |
| `invariant:precondition` | invariant | `precondition` | declared requires obligations are true before action | native bounded checker; exported as TLA+/Alloy label |
| `invariant:queue_backlog_requires_consumers` | invariant | `queue_backlog_requires_consumers` | backlog has at least one consumer | native bounded checker; exported as TLA+/Alloy label |
| `invariant:quorum_before_data_loss_action` | invariant | `quorum_before_data_loss_action` | data-loss-risk failover has quorum evidence | native bounded checker; exported as TLA+/Alloy label |
| `invariant:service_min_available` | invariant | `service_min_available` | available(service) >= min_available(service) | native bounded checker; exported as TLA+/Alloy label |
| `invariant:traffic_requires_regional_capacity` | invariant | `traffic_requires_regional_capacity` | positive traffic has regional capacity | native bounded checker; exported as TLA+/Alloy label |
| `invariant:traffic_weights_sum_to_100` | invariant | `traffic_weights_sum_to_100` | sum(weights)=100 | native bounded checker; exported as TLA+/Alloy label |
| `invariant:unsafe_retry_annotation` | invariant | `unsafe_retry_annotation` | retry policy matches modeled effect risk | native bounded checker; exported as TLA+/Alloy label |
| `precondition:orchestrator-failover-to-west:1` | refinement-precondition | `orchestrator-failover-to-west` | {"database": "mysql-metadata", "kind": "database_quorum_confirmed"} | native checker before action execution |
| `exporter:tla-abstraction` | exporter-abstraction | `TLA+` | Export preserves step ids, dependencies, state-variable names, property identifiers, and action denotation comments. | round-trip exporter tests |
| `exporter:alloy-abstraction` | exporter-abstraction | `Alloy` | Export preserves step signatures, dependency graph, waiver labels, entity signatures, and safety-property labels. | round-trip exporter tests |
| `checker:optimization-soundness` | checker-optimization | `bounded exploration` | Current exporter conformance assumes no partial-order or dominance pruning changes native counterexample labels. | benchmark performance counters and regression tests |
| `checker:finite-abstraction-soundness` | checker-abstraction | `bounded queue/cache abstraction` | Queue depths and cache entry counts are modeled as non-negative counters with explicit capacity/depth obligations, so unbounded live resources are represented by finite thresholds chosen by each fixture. | native bounded checker, schema bounds, and benchmark fixtures |
