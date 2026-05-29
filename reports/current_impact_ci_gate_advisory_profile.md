# CI gate report: case_studies/current/grafana_tempo

- Profile: `advisory-research`
- Status: **FAIL**
- Baseline: `none; all high-risk findings are treated as new`
- Blocking findings: 2
- Owner-approved waived findings: 1
- Existing baseline findings: 0
- Categories: `{"data_restoration_guard": 1, "unsafe_deletion_guard": 2}`

| ID | Status | Baseline | Category | Severity | Rule | Location | Obligation | Message | Recommendation | Waiver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ci-gate-001 | block | new | data_restoration_guard | error | data-deletion-needs-restore-precondition | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21` | `restore_path_and_blast_radius_limited` | Prose describes data deletion without executable restore/blast-radius preconditions. Missing condition(s): service_available_at_least. | Require a targeted scope, backup/restore validation, and capacity guard before destructive data operations. |  |
| ci-gate-002 | block | new | unsafe_deletion_guard | warning | destructive-delete-needs-targeting | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21` | `blast_radius_limited_or_explicit_limitation` | Prose describes destructive removal/forgetting without executable blast-radius checks. Missing condition(s): service_available_at_least. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |  |
| ci-gate-003 | waived | new | unsafe_deletion_guard | audit-only | destructive-delete-needs-targeting | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:19` | `limitation:ring-forget-targeting` | Owner-approved waiver suppresses high-risk rule destructive-delete-needs-targeting. Suppressed destructive-delete-needs-targeting at line 19 with owner=grafana-tempo-public-fixture, expires=2099-12-31, reason=public excerpt is retained as audit evidence while the fixture models this as an explicit limitation, not a verified blast-radius proof, link=limitation:ring-forget-targeting. | Review suppression owner, expiry, reason, and invariant/waiver/limitation link during runbook review. | owner=grafana-tempo-public-fixture; expires=2099-12-31; reason=public excerpt is retained as audit evidence while the fixture models this as an explicit limitation, not a verified blast-radius proof; link=limitation:ring-forget-targeting |
