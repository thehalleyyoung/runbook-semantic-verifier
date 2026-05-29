# Owner scorecard: case_studies/current/grafana_tempo

- Status: `not_ready`
- Owners: 1
- Runbooks: 1
- Verified runbooks: 0
- Open hazards: 7
- Effect annotation warnings: 0
- Stale assumptions: 0
- Waiver debt: 0

The scorecard groups executable runbooks by owner metadata and treats each runbook as a bounded operational program. Failed preconditions, safety postconditions, and prose-obligation gaps are counted as owner-visible remediation debt, not as live infrastructure proof.

| Owner | Status | Score | Runbooks | Verified | Open hazards | Semantic CEX | Effect warnings | Prose findings | Stale | Waiver debt | Services | Recent remediation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `grafana-tempo-public-fixture` | `not_ready` | 0 | 1 | 0 | 7 | 6 | 0 | 4 | 0 | 0 | `tempo-query` | 2026-05-29 open: Derived fixture recorded queue fallback replay, consumer-group stability, and destructive-deletion precondition findings from public documentation excerpts. |

## Owner details

### `grafana-tempo-public-fixture`

- Status: `not_ready` score=0/100
- Regions: `prod`
- Proof obligations checked: `{"action_defined": 2, "precondition": 2, "promised_effect": 0, "safety_postcondition": 14}`
- Proof obligation failures: `{"precondition": 2, "safety_postcondition": 4}`

Top hazards:
- `semantic` `no_replay_without_dedupe` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan replay count=18000 lacks dedupe_key, idempotency proof, or dedupe window
- `semantic` `no_duplicate_processing_risk` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan has replayed messages without modeled deduplication
- `semantic` `no_rebalance_to_zero_consumers` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan has depth=36000 before rebalance to 0 consumers
- `semantic` `no_duplicate_processing_risk` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan has replayed messages without modeled deduplication
- `semantic` `queue_backlog_requires_consumers` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan has depth=36000 with no active consumers
- `semantic` `no_unstable_consumer_group_with_backlog` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan has depth=36000 while consumer group rebalance is not stable
- `prose` `data-deletion-needs-restore-precondition` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Prose describes data deletion without executable restore/blast-radius preconditions. Missing condition(s): service_available_at_least.
- `prose` `destructive-delete-needs-targeting` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Prose describes destructive removal/forgetting without executable blast-radius checks. Missing condition(s): service_available_at_least.
- `prose` `backfill-needs-queue-capacity` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Prose mentions backfill/replay work without executable queue/backlog capacity guards. Missing condition(s): queue_depth_at_most, queue_has_consumers, queue_replay_deduplicated.
- `prose` `prose-suppression-applied` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Suppressed destructive-delete-needs-targeting at line 19 with owner=grafana-tempo-public-fixture, expires=2099-12-31, reason=public excerpt is retained as audit evidence while the fixture models this as an explicit limitation, not a verified blast-radius proof, link=limitation:ring-forget-targeting.

