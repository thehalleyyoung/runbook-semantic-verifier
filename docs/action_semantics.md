# Action semantics reference

This table is generated from the typed action descriptors used by parser validation, JSON Schema generation, and formal exporters.

| Action | Parameters | Semantics |
| --- | --- | --- |
| `confirm_quorum` | `database:string` | Marks database quorum/data-safety confirmation complete. |
| `drain_region` | `region:string, services?:string[]` | Drains replicas in a region, optionally limited to named services. |
| `drain_replica` | `service:string, replica:string` | Marks one service replica drained and unavailable. |
| `failover_database` | `database:string, target_region:string, data_loss_risk?:boolean` | Changes database primary region and records data-loss risk for invariants. |
| `finish_migration` | `database:string` | Clears the database migration-in-progress flag. |
| `mark_region_health` | `region:string, healthy:boolean` | Sets a region health flag used by failover checks. |
| `pause_queue` | `queue:string` | Pauses queue consumption/processing. |
| `restart_service` | `service:string` | Reasserts the modeled service without changing capacity. |
| `restore_replica` | `service:string, replica:string` | Marks one drained service replica available again. |
| `resume_queue` | `queue:string` | Resumes queue consumption/processing. |
| `rollback_deployment` | `service:string, to?:string` | Moves a service deployment pointer to a previous or named version. |
| `run_migration` | `database:string, in_progress?:boolean, compatible?:boolean` | Updates database migration progress and compatibility flags. |
| `scale_service` | `service:string, replicas:integer>=0, region?:string` | Resizes a service replica set using deterministic generated replica ids. |
| `suppress_alert` | `alert:string, expires_after_minutes:integer>=1` | Suppresses an alert until the bounded expiry minute. |
| `toggle_flag` | `flag:string, enabled:boolean` | Sets a feature flag to the requested boolean value. |
| `wait` | `minutes:integer>=0` | Advances the model clock by a non-negative number of minutes. |

## Condition descriptors

| Condition kind | Fields | Meaning |
| --- | --- | --- |
| `alert_active` | `alert:string, active:boolean` | Requires or asserts an alert activity value. |
| `alert_suppressed_for_at_most` | `alert:string, minutes:integer>=0` | Requires or asserts bounded alert suppression duration. |
| `database_primary_region` | `database:string, region:string` | Requires or asserts a database primary region. |
| `database_quorum_confirmed` | `database:string` | Requires or asserts confirmed database quorum. |
| `flag_enabled` | `flag:string, enabled:boolean` | Requires or asserts a feature flag value. |
| `queue_depth_at_most` | `queue:string, depth:integer>=0` | Requires or asserts bounded queue depth. |
| `queue_has_consumers` | `queue:string, count:integer>=0` | Requires or asserts minimum queue consumers. |
| `queue_resumed` | `queue:string` | Requires or asserts an unpaused queue. |
| `region_healthy` | `region:string` | Requires or asserts a healthy region. |
| `replica_not_drained` | `service:string, replica:string` | Requires or asserts a replica is not drained. |
| `service_available_at_least` | `service:string, count:integer>=0` | Requires or asserts minimum available service replicas. |
| `service_deployment_is` | `service:string, deployment:string` | Requires or asserts a service deployment version. |
