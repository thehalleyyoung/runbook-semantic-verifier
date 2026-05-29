# Markdown runbook lint report

- Findings: 2

| Rule | Severity | Location | Excerpt | Recommendation |
| --- | --- | --- | --- | --- |
| destructive-delete-needs-targeting | warning | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | > Use the "Forget" button to forget and remove any unhealthy distributors from the ring. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
| destructive-delete-needs-targeting | warning | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | > If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
