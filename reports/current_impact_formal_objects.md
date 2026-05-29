# Formal object map: case_studies/current/grafana_tempo

- Object schema version: `1.0`
- Executable runbooks: 1
- Parse diagnostics: 0
- Prose observations: 4
- Hazard counterexamples: 6
- Waivers/limitations observed: 1

## Object-to-CLI map

| Object | Mathematical role | Primary CLI JSON fields |
| --- | --- | --- |
| `syntax` | The parsed DSL/Markdown program, including steps, dependency edges, and bounded exploration settings. | `runbooks[].syntax, runbooks[].steps` |
| `entity_universe` | Finite typed identifiers for infrastructure objects referenced by actions and properties. | `runbooks[].entity_universe, coverage.entities, readiness.modeled_entities` |
| `store` | Immutable infrastructure state transformed by small-step action semantics. | `runbooks[].store, runbooks[].traces.states_explored` |
| `trace` | A dependency-respecting action sequence explored within the runbook's max_depth budget. | `runbooks[].traces, runbooks[].hazards.counterexamples[].trace` |
| `hazard` | A failed safety, precondition, effect, or action-definedness obligation with a witness trace. | `runbooks[].hazards, readiness.highest_risk_counterexamples, benchmark.results[].observed_violation_properties` |
| `observation` | A source-addressed prose signal that is not automatically verified by the executable model. | `observations[], audit.markdown_findings[], lint-markdown findings[]` |
| `diagnostic` | A parser/schema/entity rejection or warning with source and remediation metadata. | `diagnostics.parse, validate diagnostics, audit parse_errors` |
| `waiver` | An auditable suppression or limitation record that preserves owner, expiry, reason, and linked obligation evidence. | `observations[rule=prose-suppression-applied], lint-markdown findings[]` |
| `benchmark_label` | Expected safety/prose observations used as regression or public-case evidence labels. | `runbooks[].benchmark_labels, benchmark.results[].expected, readiness.benchmark_expectations` |

## Executable runbooks

| Path | Program | Steps | Entities | Safe | Counterexamples | Trace budget |
| --- | --- | ---: | ---: | --- | ---: | --- |
| `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | Grafana Tempo current public runbook derived safety model | 2 | 5 | `False` | 6 | max_depth=2, terminal=1 |

## Hazard obligations by runbook

### case_studies/current/grafana_tempo/tempo_runbook_current_impact.md
- `[no_replay_without_dedupe]` step `delete-stale-tenant-indexes-trigger-fallback` trace `delete-stale-tenant-indexes-trigger-fallback`: queue tenant-index-fallback-scan replay count=18000 lacks dedupe_key, idempotency proof, or dedupe window
- `[no_duplicate_processing_risk]` step `delete-stale-tenant-indexes-trigger-fallback` trace `delete-stale-tenant-indexes-trigger-fallback`: queue tenant-index-fallback-scan has replayed messages without modeled deduplication
- `[no_rebalance_to_zero_consumers]` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has depth=36000 before rebalance to 0 consumers
- `[no_duplicate_processing_risk]` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has replayed messages without modeled deduplication
- `[queue_backlog_requires_consumers]` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has depth=36000 with no active consumers
- `[no_unstable_consumer_group_with_backlog]` step `rebalance-fallback-consumers` trace `delete-stale-tenant-indexes-trigger-fallback -> rebalance-fallback-consumers`: queue tenant-index-fallback-scan has depth=36000 while consumer group rebalance is not stable

## Prose observations and waivers

| Object | Rule | Severity | Location | Obligation |
| --- | --- | --- | --- | --- |
| `observation` | data-deletion-needs-restore-precondition | error | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21` | `restore_path_and_blast_radius_limited` |
| `observation` | destructive-delete-needs-targeting | warning | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21` | `blast_radius_limited_or_explicit_limitation` |
| `observation` | backfill-needs-queue-capacity | warning | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:27` | `queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk` |
| `waiver` | prose-suppression-applied | audit-only | `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18` | `limitation:ring-forget-targeting` |

