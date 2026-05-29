# Incident readiness report: case_studies/current/grafana_tempo

- Status: `not_ready`
- Readiness score: 40/100
- Filters: service=`tempo-query` region=`prod`
- Runbooks considered: 1
- Safe runbooks: 0
- Parse errors: 0
- Semantic counterexamples: 2
- Unverified prose claims: 3
- Missing rollback/restore coverage: 0
- Stale preconditions: 0
- Benchmark expectation mismatches: 0

## Runbooks

| Path | Name | Safe | States | Transitions | Terminal traces | Max depth reached |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | Grafana Tempo current public runbook derived safety model | `False` | 3 | 2 | 1 | `False` |

## Highest-risk counterexamples

- `[no_queue_pause_without_drain_plan]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `delete-stale-tenant-indexes` trace `delete-stale-tenant-indexes`: queue tenant-index-fallback-scan has depth=18000 and consumers=1 before pause
- `[no_paused_queue_with_backlog]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `delete-stale-tenant-indexes` trace `delete-stale-tenant-indexes`: queue tenant-index-fallback-scan is paused with depth=18000 and consumers=1

## Unverified prose claims

| Rule | Severity | Obligation | Location | Excerpt | Recommendation |
| --- | --- | --- | --- | --- | --- |
| data-deletion-needs-restore-precondition | error | `restore_path_and_blast_radius_limited` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | > If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing. | Require a targeted scope, backup/restore validation, and capacity guard before destructive data operations. |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | > Use the "Forget" button to forget and remove any unhealthy distributors from the ring. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | > If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |

## Missing rollback/restore coverage

No high-risk executable step lacked a modeled rollback/restore action.

## Stale preconditions

No file exceeded the configured freshness window.

## Proof obligations

```json
{
  "checked": {
    "action_defined": 2,
    "precondition": 1,
    "promised_effect": 1,
    "safety_postcondition": 6
  },
  "failures": {
    "precondition": 1,
    "safety_postcondition": 1
  }
}
```

## Benchmark expectations

| Path | Pass | Expected labels | Errors |
| --- | --- | --- | --- |
| `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `True` | `{"expected_prose_rules": ["data-deletion-needs-restore-precondition", "destructive-delete-needs-targeting"], "expected_safe": false, "expected_violation_properties": ["no_paused_queue_with_backlog", "no_queue_pause_without_drain_plan"]}` | `[]` |

