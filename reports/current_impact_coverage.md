# Property coverage report: case_studies/current/grafana_tempo

- Executable runbooks: 1
- Properties mapped: 11
- Services covered: 1/1
- Databases covered: 0/0
- Queues covered: 1/1
- Alerts covered: 0/0
- DNS records covered: 0/0
- Credentials covered: 0/0 (credential state is not implemented in the current DSL)
- Regions covered: 1/1
- Owners: `grafana-tempo-public-fixture`
- Unverified prose obligations: 4
- Coverage gaps: 4

## Invariant coverage

| Property | Runbook | Owners | Services | Databases | Queues | Alerts | DNS records | Credentials | Regions | Steps/sections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dead_letter_drain_has_messages` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `dead_letter_replay_has_messages` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `no_draining_all_replicas` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` | `tempo-query` |  |  |  |  |  | `prod` |  |
| `no_duplicate_processing_risk` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `no_paused_queue_with_backlog` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `no_queue_pause_without_drain_plan` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `no_rebalance_to_zero_consumers` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `no_replay_without_dedupe` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `no_unstable_consumer_group_with_backlog` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `queue_backlog_requires_consumers` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  |  | `delete-stale-tenant-indexes-trigger-fallback` (L104, Defensive interpretation)<br>`rebalance-fallback-consumers` (L113, Defensive interpretation) |
| `service_min_available` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` | `tempo-query` |  |  |  |  |  | `prod` |  |

## Unverified prose obligations

| Rule | Severity | Obligation | Location | Section |
| --- | --- | --- | --- | --- |
| data-deletion-needs-restore-precondition | error | `restore_path_and_blast_radius_limited` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | Public prose excerpts analyzed |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | Public prose excerpts analyzed |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | Public prose excerpts analyzed |
| backfill-needs-queue-capacity | warning | `queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:26` | Defensive interpretation |

## Coverage gaps

- `prose_obligation` `data-deletion-needs-restore-precondition` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Markdown section has unverified obligation restore_path_and_blast_radius_limited
- `prose_obligation` `destructive-delete-needs-targeting` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Markdown section has unverified obligation blast_radius_limited_or_explicit_limitation
- `prose_obligation` `destructive-delete-needs-targeting` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Markdown section has unverified obligation blast_radius_limited_or_explicit_limitation
- `prose_obligation` `backfill-needs-queue-capacity` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Markdown section has unverified obligation queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk
