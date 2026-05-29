# Action semantics reference

This table is generated from the typed action descriptors used by parser
validation, JSON Schema generation, and formal exporters. See
`docs/small_step_semantics.md` for the operational scheduling, wait, failure,
and bounded-exploration rules that wrap these action transitions and appear in
checker traces.

| Action | Parameters | Operational summary | Denotational state transformer |
| --- | --- | --- | --- |
| `confirm_quorum` | `database:string` | Marks database quorum/data-safety confirmation complete. | Sets databases[database].quorum_confirmed := true. |
| `drain_dead_letter_queue` | `queue:string, count:integer>=0` | Removes messages from a queue's dead-letter backlog after modeled triage. | Subtracts count from queues[queue].dead_letter_depth after validating the modeled backlog bound. |
| `drain_load_balancer` | `route:string, region:string` | Marks a route's regional load balancer drained; traffic must already be shifted away. | Adds region to traffic_routes[route].drained_regions. |
| `drain_region` | `region:string, services?:string[]` | Drains replicas in a region, optionally limited to named services. | For each selected service replica in params.region, sets drained := true; replicas in other regions are framed. |
| `drain_replica` | `service:string, replica:string` | Marks one service replica drained and unavailable. | Sets services[service].replicas[replica].drained := true; all other state fields are framed. |
| `failover_database` | `database:string, target_region:string, data_loss_risk?:boolean` | Changes database primary region and records data-loss risk for invariants. | Sets databases[database].primary_region := target_region; quorum and health facts are not created by the action. |
| `failover_traffic` | `route:string, target_region:string` | Moves all modeled route traffic to one target region and zeroes the other route weights. | Sets traffic_routes[route].weights[target_region] := 100 and all other modeled route weights to 0. |
| `finalize_dns_record` | `record:string` | Clears a DNS record's prior target after the TTL wait obligation has elapsed. | Sets dns_records[record].previous_region := None after the TTL proof obligation has elapsed. |
| `finish_migration` | `database:string` | Clears the database migration-in-progress flag. | Sets databases[database].migration_in_progress := false. |
| `flush_cache` | `cache:string` | Evicts all modeled cache entries, making the cache cold and recording stale-read risk unless writes are frozen. | Sets caches[cache].entries := 0, warm := false, and stale_read_risk := not write_frozen. |
| `freeze_cache_writes` | `cache:string` | Freezes writes that could repopulate or serve stale values during a cache flush. | Sets caches[cache].write_frozen := true. |
| `mark_dns_health_check` | `record:string, region:string, converged:boolean` | Records whether DNS health checks have converged for a record's regional endpoint. | Adds or removes region from dns_records[record].health_check_converged_regions according to converged. |
| `mark_region_health` | `region:string, healthy:boolean` | Sets a region health flag used by failover checks. | Sets regions[region].healthy := healthy. |
| `pause_queue` | `queue:string` | Pauses queue consumption/processing. | Sets queues[queue].paused := true. |
| `rebalance_consumers` | `queue:string, consumers:integer>=0, stable?:boolean` | Changes consumer-group capacity and records whether the group has reached a stable post-rebalance assignment. | Sets queues[queue].consumers := consumers and consumer_group_stable := stable (default false). |
| `replay_messages` | `queue:string, count:integer>=0, from_dead_letter?:boolean, dedupe_key?:string, idempotent?:boolean` | Replays messages into a queue, optionally from the dead-letter queue, and records duplicate-processing risk unless a dedupe key, idempotency proof, or dedupe window is present. | Adds count to queues[queue].depth, optionally subtracts count from dead_letter_depth, and sets duplicate_risk unless dedupe/idempotency is modeled. |
| `restart_service` | `service:string` | Reasserts the modeled service without changing capacity. | Identity transformer on service capacity and deployment; validates the referenced service exists. |
| `restore_load_balancer` | `route:string, region:string` | Marks a route's regional load balancer active again. | Removes region from traffic_routes[route].drained_regions. |
| `restore_replica` | `service:string, replica:string` | Marks one drained service replica available again. | Sets services[service].replicas[replica].drained := false; all other state fields are framed. |
| `resume_cache_writes` | `cache:string` | Re-enables writes to a cache after warmup/verification. | Sets caches[cache].write_frozen := false. |
| `resume_queue` | `queue:string` | Resumes queue consumption/processing. | Sets queues[queue].paused := false. |
| `rollback_deployment` | `service:string, to?:string` | Moves a service deployment pointer to a previous or named version. | Sets services[service].deployment and deployments[service].current to params.to or 'previous'. |
| `run_migration` | `database:string, in_progress?:boolean, compatible?:boolean` | Updates database migration progress and compatibility flags. | Sets database migration_in_progress and migration_compatible from parameters, defaulting to preserve compatibility. |
| `scale_service` | `service:string, replicas:integer>=0, region?:string` | Resizes a service replica set using deterministic generated replica ids. | Resizes services[service].replicas to params.replicas, generating healthy undrained replicas in params.region when growing. |
| `shift_traffic` | `route:string, region:string, percent:integer>=0<=100` | Sets weighted routing for a route in one region; two-region routes automatically assign the remainder to the peer region. | Sets traffic_routes[route].weights[region] := percent and, for two-region routes, assigns the peer region 100 - percent. |
| `suppress_alert` | `alert:string, expires_after_minutes:integer>=1` | Suppresses an alert until the bounded expiry minute. | Sets alerts[alert].suppressed_until_minute := clock_minute + expires_after_minutes. |
| `toggle_flag` | `flag:string, enabled:boolean` | Sets a feature flag to the requested boolean value. | Sets feature_flags[flag].enabled := enabled, creating the modeled flag if absent. |
| `update_dns_record` | `record:string, target_region:string` | Changes a DNS record target region and starts the modeled TTL propagation window. | Sets dns_records[record].region := target_region, previous_region := old region, and last_changed_minute := clock_minute. |
| `wait` | `minutes:integer>=0` | Advances the model clock by a non-negative number of minutes. | Advances clock_minute by params.minutes; all modeled entities are framed. |
| `warm_cache` | `cache:string, entries:integer>=0` | Warms a cache with a bounded number of entries and clears modeled stale-read risk when the warmup threshold is met. | Sets caches[cache].entries := entries, warm according to warmup threshold, and clears stale_read_risk. |

## Condition descriptors

| Condition kind | Fields | Meaning |
| --- | --- | --- |
| `alert_active` | `alert:string, active:boolean` | Requires or asserts an alert activity value. |
| `alert_suppressed_for_at_most` | `alert:string, minutes:integer>=0` | Requires or asserts bounded alert suppression duration. |
| `cache_capacity_at_least` | `cache:string, entries:integer>=0` | Requires or asserts enough cache capacity for the requested warmup. |
| `cache_entries_at_least` | `cache:string, entries:integer>=0` | Requires or asserts a minimum number of warmed cache entries. |
| `cache_no_stale_read_risk` | `cache:string` | Requires or asserts no modeled stale-read risk remains after flush and warmup. |
| `cache_warm` | `cache:string` | Requires or asserts that cache warmup has reached the modeled threshold. |
| `cache_writes_frozen` | `cache:string` | Requires or asserts that cache writes are frozen before a destructive flush. |
| `consumer_group_stable` | `queue:string` | Requires or asserts that consumer-group rebalancing has converged. |
| `database_primary_region` | `database:string, region:string` | Requires or asserts a database primary region. |
| `database_quorum_confirmed` | `database:string` | Requires or asserts confirmed database quorum. |
| `dns_health_check_converged` | `record:string, region:string` | Requires or asserts health-check convergence before DNS cutover. |
| `dns_no_split_brain` | `record:string` | Requires or asserts no active DNS split-brain window for stateful records. |
| `dns_points_to` | `record:string, region:string` | Requires or asserts that a DNS record points at a region. |
| `dns_ttl_elapsed` | `record:string` | Requires or asserts that the record's TTL propagation window has elapsed. |
| `flag_enabled` | `flag:string, enabled:boolean` | Requires or asserts a feature flag value. |
| `load_balancer_active` | `route:string, region:string` | Requires or asserts that a route's regional load balancer is not drained. |
| `queue_dead_letter_depth_at_most` | `queue:string, depth:integer>=0` | Requires or asserts bounded dead-letter queue backlog. |
| `queue_dedupe_window_at_least` | `queue:string, minutes:integer>=0` | Requires or asserts that the queue has a deduplication window long enough for replay. |
| `queue_depth_at_most` | `queue:string, depth:integer>=0` | Requires or asserts bounded queue depth. |
| `queue_has_consumers` | `queue:string, count:integer>=0` | Requires or asserts minimum queue consumers. |
| `queue_replay_deduplicated` | `queue:string` | Requires or asserts that replay has no modeled duplicate-processing risk. |
| `queue_resumed` | `queue:string` | Requires or asserts an unpaused queue. |
| `region_healthy` | `region:string` | Requires or asserts a healthy region. |
| `replica_not_drained` | `service:string, replica:string` | Requires or asserts a replica is not drained. |
| `service_available_at_least` | `service:string, count:integer>=0` | Requires or asserts minimum available service replicas. |
| `service_deployment_is` | `service:string, deployment:string` | Requires or asserts a service deployment version. |
| `traffic_weight_at_least` | `route:string, region:string, percent:integer>=0<=100` | Requires or asserts a minimum weighted-routing percentage for a route region. |
| `traffic_weight_at_most` | `route:string, region:string, percent:integer>=0<=100` | Requires or asserts a maximum weighted-routing percentage for a route region. |
| `traffic_weight_is` | `route:string, region:string, percent:integer>=0<=100` | Requires or asserts an exact weighted-routing percentage for a route region. |
