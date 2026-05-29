# Markdown runbook lint report

- Findings: 4

| Rule | Severity | Obligation | Location | Excerpt | Recommendation |
| --- | --- | --- | --- | --- | --- |
| data-deletion-needs-restore-precondition | error | `restore_path_and_blast_radius_limited` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | > If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing. | Require a targeted scope, backup/restore validation, and capacity guard before destructive data operations. |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | > Use the "Forget" button to forget and remove any unhealthy distributors from the ring. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | > If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
| backfill-needs-queue-capacity | warning | `queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:26` | machine-checkable guardrails for deduplicated fallback replay, consumer-group | Add queue_depth_at_most, queue_has_consumers, and deduplicated replay preconditions, or document an explicit limitation. |
