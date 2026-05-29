# Property coverage report: case_studies/current/grafana_tempo

- Executable runbooks: 1
- Properties mapped: 5
- Services covered: 1/1
- Databases covered: 0/0
- Queues covered: 1/1
- Alerts covered: 0/0
- Credentials covered: 0/0 (credential state is not implemented in the current DSL)
- Regions covered: 1/1
- Owners: `grafana-tempo-public-fixture`
- Unverified prose obligations: 3
- Coverage gaps: 3

## Invariant coverage

| Property | Runbook | Owners | Services | Databases | Queues | Alerts | Credentials | Regions | Steps/sections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `declared_effect` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  | `resume-fallback-scans` (L99, Defensive interpretation) |
| `no_draining_all_replicas` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` | `tempo-query` |  |  |  |  | `prod` |  |
| `no_paused_queue_with_backlog` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  | `delete-stale-tenant-indexes` (L93, Defensive interpretation)<br>`resume-fallback-scans` (L99, Defensive interpretation) |
| `no_queue_pause_without_drain_plan` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` |  |  | `tenant-index-fallback-scan` |  |  |  | `delete-stale-tenant-indexes` (L93, Defensive interpretation)<br>`resume-fallback-scans` (L99, Defensive interpretation) |
| `service_min_available` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `grafana-tempo-public-fixture` | `tempo-query` |  |  |  |  | `prod` |  |

## Unverified prose obligations

| Rule | Severity | Obligation | Location | Section |
| --- | --- | --- | --- | --- |
| data-deletion-needs-restore-precondition | error | `restore_path_and_blast_radius_limited` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | Public prose excerpts analyzed |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | Public prose excerpts analyzed |
| destructive-delete-needs-targeting | warning | `blast_radius_limited_or_explicit_limitation` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:20` | Public prose excerpts analyzed |

## Coverage gaps

- `prose_obligation` `data-deletion-needs-restore-precondition` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Markdown section has unverified obligation restore_path_and_blast_radius_limited
- `prose_obligation` `destructive-delete-needs-targeting` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Markdown section has unverified obligation blast_radius_limited_or_explicit_limitation
- `prose_obligation` `destructive-delete-needs-targeting` in `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Markdown section has unverified obligation blast_radius_limited_or_explicit_limitation
