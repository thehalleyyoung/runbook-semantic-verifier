# Owner scorecard: case_studies/current/grafana_tempo

- Status: `not_ready`
- Owners: 1
- Runbooks: 1
- Verified runbooks: 0
- Open hazards: 3
- Stale assumptions: 0
- Waiver debt: 0

The scorecard groups executable runbooks by owner metadata and treats each runbook as a bounded operational program. Failed preconditions, safety postconditions, and prose-obligation gaps are counted as owner-visible remediation debt, not as live infrastructure proof.

| Owner | Status | Score | Runbooks | Verified | Open hazards | Semantic CEX | Prose findings | Stale | Waiver debt | Services | Recent remediation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `grafana-tempo-public-fixture` | `not_ready` | 50 | 1 | 0 | 3 | 2 | 3 | 0 | 0 | `tempo-query` | 2026-05-29 open: Derived fixture recorded queue fallback backlog and destructive-deletion precondition findings from public documentation excerpts. |

## Owner details

### `grafana-tempo-public-fixture`

- Status: `not_ready` score=50/100
- Regions: `prod`
- Proof obligations checked: `{"action_defined": 2, "precondition": 1, "promised_effect": 1, "safety_postcondition": 6}`
- Proof obligation failures: `{"precondition": 1, "safety_postcondition": 1}`

Top hazards:
- `semantic` `no_queue_pause_without_drain_plan` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan has depth=18000 and consumers=1 before pause
- `semantic` `no_paused_queue_with_backlog` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: queue tenant-index-fallback-scan is paused with depth=18000 and consumers=1
- `prose` `data-deletion-needs-restore-precondition` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Prose describes data deletion without executable restore/blast-radius preconditions. Missing condition(s): service_available_at_least.
- `prose` `destructive-delete-needs-targeting` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Prose describes destructive removal/forgetting without executable blast-radius checks. Missing condition(s): service_available_at_least.
- `prose` `destructive-delete-needs-targeting` `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`: Prose describes destructive removal/forgetting without executable blast-radius checks. Missing condition(s): service_available_at_least.

