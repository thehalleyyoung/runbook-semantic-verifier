# Runbook audit: case_studies/current/grafana_tempo

- Runbooks checked: 1
- Safe runbooks: 0
- Findings: 5
- Findings by severity: `{"error": 3, "warning": 2}`
- Findings by rule: `{"data-deletion-needs-restore-precondition": 1, "destructive-delete-needs-targeting": 2, "no_paused_queue_with_backlog": 1, "no_queue_pause_without_drain_plan": 1}`

| Runbook | Safe | States | Traces | Violations |
| --- | --- | ---: | ---: | ---: |
| `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `False` | 3 | 1 | 2 |

| ID | Rank | Type | Severity | Rule | Obligation | Location | Message | Recommendation |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| `finding-001` | 3 | semantic | error | no_paused_queue_with_backlog | `no_paused_queue_with_backlog` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:` | queue tenant-index-fallback-scan is paused with depth=18000 and consumers=1 | Resume the queue or prove backlog is drained and alternate consumers are active. |
| `finding-002` | 3 | semantic | error | no_queue_pause_without_drain_plan | `no_queue_pause_without_drain_plan` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:` | queue tenant-index-fallback-scan has depth=18000 and consumers=1 before pause | Drain backlog or add queue_depth_at_most and queue_has_consumers preconditions before pausing. |
| `finding-003` | 3 | prose | error | data-deletion-needs-restore-precondition | `restore_path_and_blast_radius_limited` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | Prose describes data deletion without executable restore/blast-radius preconditions. Missing condition(s): service_available_at_least. | Require a targeted scope, backup/restore validation, and capacity guard before destructive data operations. |
| `finding-004` | 2 | prose | warning | destructive-delete-needs-targeting | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | Prose describes destructive removal/forgetting without executable blast-radius checks. Missing condition(s): service_available_at_least. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
| `finding-005` | 2 | prose | warning | destructive-delete-needs-targeting | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | Prose describes destructive removal/forgetting without executable blast-radius checks. Missing condition(s): service_available_at_least. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
