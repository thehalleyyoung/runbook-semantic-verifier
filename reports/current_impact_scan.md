# Repository runbook scan: case_studies/current/grafana_tempo

- Markdown files ranked: 1
- Files with executable models: 1
- Files needing first executable model: 0
- Highest score: 56
- Priority counts: `{"critical": 1}`
- Dangerous-effect rules: `{"backfill-needs-queue-capacity": 1, "data-deletion-needs-restore-precondition": 1, "destructive-delete-needs-targeting": 2}`

## Ranking semantics

Each rule maps prose evidence to a semantic obligation already used by lint/audit/check workflows; high scores identify documents where Markdown prose should be refined into executable DSL models first.

| Priority | Score | Executable model | Path | Matched dangerous-effect rules | Uncovered obligations | Recommendation |
| --- | ---: | --- | --- | --- | --- | --- |
| critical | 56 | `True` | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | `{"backfill-needs-queue-capacity": 1, "data-deletion-needs-restore-precondition": 1, "destructive-delete-needs-targeting": 2}` | `{"blast_radius_limited_or_explicit_limitation": 2, "queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk": 1, "restore_path_and_blast_radius_limited": 1}` | Model or explicitly limit uncovered semantic obligations: blast_radius_limited_or_explicit_limitation, queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk, restore_path_and_blast_radius_limited. Review whether prose dangerous-effect matches refine to the existing executable model and coverage reports. |
