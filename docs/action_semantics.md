# Action semantics reference

This table is generated from the typed action descriptors used by parser validation, JSON Schema generation, and formal exporters.

| Action | Parameters | Semantics |
| --- | --- | --- |
| `confirm_quorum` | `database:string` | Marks database quorum/data-safety confirmation complete. |
| `drain_dead_letter_queue` | `queue:string, count:integer>=0` | Removes messages from a queue's dead-letter backlog after modeled triage. |
| `drain_load_balancer` | `route:string, region:string` | Marks a route's regional load balancer drained; traffic must already be shifted away. |
| `drain_region` | `region:string, services?:string[]` | Drains replicas in a region, optionally limited to named services. |
| `drain_replica` | `service:string, replica:string` | Marks one service replica drained and unavailable. |
| `failover_database` | `database:string, target_region:string, data_loss_risk?:boolean` | Changes database primary region and records data-loss risk for invariants. |
| `failover_traffic` | `route:string, target_region:string` | Moves all modeled route traffic to one target region and zeroes the other route weights. |
| `finalize_dns_record` | `record:string` | Clears a DNS record's prior target after the TTL wait obligation has elapsed. |
| `finish_migration` | `database:string` | Clears the database migration-in-progress flag. |
| `mark_dns_health_check` | `record:string, region:string, converged:boolean` | Records whether DNS health checks have converged for a record's regional endpoint. |
| `mark_region_health` | `region:string, healthy:boolean` | Sets a region health flag used by failover checks. |
| `pause_queue` | `queue:string` | Pauses queue consumption/processing. |
| `rebalance_consumers` | `queue:string, consumers:integer>=0, stable?:boolean` | Changes consumer-group capacity and records whether the group has reached a stable post-rebalance assignment. |
| `replay_messages` | `queue:string, count:integer>=0, from_dead_letter?:boolean, dedupe_key?:string, idempotent?:boolean` | Replays messages into a queue, optionally from the dead-letter queue, and records duplicate-processing risk unless a dedupe key, idempotency proof, or dedupe window is present. |
| `restart_service` | `service:string` | Reasserts the modeled service without changing capacity. |
| `restore_load_balancer` | `route:string, region:string` | Marks a route's regional load balancer active again. |
| `restore_replica` | `service:string, replica:string` | Marks one drained service replica available again. |
| `resume_queue` | `queue:string` | Resumes queue consumption/processing. |
| `rollback_deployment` | `service:string, to?:string` | Moves a service deployment pointer to a previous or named version. |
| `run_migration` | `database:string, in_progress?:boolean, compatible?:boolean` | Updates database migration progress and compatibility flags. |
| `scale_service` | `service:string, replicas:integer>=0, region?:string` | Resizes a service replica set using deterministic generated replica ids. |
| `shift_traffic` | `route:string, region:string, percent:integer>=0<=100` | Sets weighted routing for a route in one region; two-region routes automatically assign the remainder to the peer region. |
| `suppress_alert` | `alert:string, expires_after_minutes:integer>=1` | Suppresses an alert until the bounded expiry minute. |
| `toggle_flag` | `flag:string, enabled:boolean` | Sets a feature flag to the requested boolean value. |
| `update_dns_record` | `record:string, target_region:string` | Changes a DNS record target region and starts the modeled TTL propagation window. |
| `wait` | `minutes:integer>=0` | Advances the model clock by a non-negative number of minutes. |

## Condition descriptors

| Condition kind | Fields | Meaning |
| --- | --- | --- |
| `alert_active` | `alert:string, active:boolean` | Requires or asserts an alert activity value. |
| `alert_suppressed_for_at_most` | `alert:string, minutes:integer>=0` | Requires or asserts bounded alert suppression duration. |
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
