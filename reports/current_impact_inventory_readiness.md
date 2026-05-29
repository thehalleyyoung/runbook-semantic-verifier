# Incident readiness report: case_studies/current/grafana_tempo

- Status: `not_ready`
- Readiness score: 0/100
- Filters: service=`tempo-query` region=`prod`
- Inventory: `case_studies/current/grafana_tempo/tempo_inventory_current_impact.json`
- Runbooks considered: 1
- Safe runbooks: 0
- Parse errors: 0
- Semantic counterexamples: 6
- Unverified prose claims: 4
- Missing rollback/restore coverage: 0
- Stale preconditions: 3
- Blocking stale preconditions: 1
- Benchmark expectation mismatches: 0

## Runbooks

| Path | Name | Safe | States | Transitions | Terminal traces | Max depth reached |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | Grafana Tempo current public runbook derived safety model | `False` | 3 | 2 | 1 | `False` |

## Highest-risk counterexamples

- `[no_replay_without_dedupe]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `delete-stale-tenant-indexes-trigger-fallback` trace `delete-stale-tenant-indexes-trigger-fallback`: queue tenant-index-fallback-scan replay count=18000 lacks dedupe_key, idempotency proof, or dedupe window
- `[no_duplicate_processing_risk]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `delete-stale-tenant-indexes-trigger-fallback` trace `delete-stale-tenant-indexes-trigger-fallback`: queue tenant-index-fallback-scan has replayed messages without modeled deduplication
- `[no_rebalance_to_zero_consumers]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has depth=36000 before rebalance to 0 consumers
- `[no_duplicate_processing_risk]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has replayed messages without modeled deduplication
- `[queue_backlog_requires_consumers]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has depth=36000 with no active consumers
- `[no_unstable_consumer_group_with_backlog]` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has depth=36000 while consumer group rebalance is not stable

## Unverified prose claims

| Rule | Severity | Obligation | Location | Excerpt | Recommendation |
| --- | --- | --- | --- | --- | --- |
| data-deletion-needs-restore-precondition | error | `restore_path_and_blast_radius_limited` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21` | > If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing. | Require a targeted scope, backup/restore validation, and capacity guard before destructive data operations. |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21` | > If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |
| backfill-needs-queue-capacity | warning | `queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:27` | machine-checkable guardrails for deduplicated fallback replay, consumer-group | Add queue_depth_at_most, queue_has_consumers, and deduplicated replay preconditions, or document an explicit limitation. |
| prose-suppression-applied | audit-only | `limitation:ring-forget-targeting` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | frv-suppress rule=destructive-delete-needs-targeting | Review suppression owner, expiry, reason, and invariant/waiver/limitation link during runbook review. |

## Missing rollback/restore coverage

No high-risk executable step lacked a modeled rollback/restore action.

## Stale preconditions

- `error` `replica_count_mismatch` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: service 'tempo-query' models 2 replica(s) but inventory expects 3 (obligation `inventory_refinement_precondition`)
- `warning` `missing_service_alert` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: service 'tempo-query' omits inventory alert(s): tempo-query-consumer-group-unstable, tempo-query-fallback-backlog (obligation `inventory_refinement_precondition`)
- `warning` `missing_dependency` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: service 'tempo-query' omits inventory dependency name(s): tempo-ring (obligation `inventory_refinement_precondition`)

## Proof obligations

```json
{
  "checked": {
    "action_defined": 2,
    "precondition": 2,
    "promised_effect": 0,
    "safety_postcondition": 14
  },
  "failures": {
    "precondition": 2,
    "safety_postcondition": 4
  }
}
```

## Benchmark expectations

| Path | Pass | Expected labels | Errors |
| --- | --- | --- | --- |
| `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `True` | `{"expected_prose_rules": ["data-deletion-needs-restore-precondition", "destructive-delete-needs-targeting"], "expected_safe": false, "expected_violation_properties": ["no_duplicate_processing_risk", "no_rebalance_to_zero_consumers", "no_replay_without_dedupe", "no_unstable_consumer_group_with_backlog", "queue_backlog_requires_consumers"]}` | `[]` |

