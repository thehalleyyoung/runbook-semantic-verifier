# Pull-request annotation report: case_studies/current/grafana_tempo

- Status: **PASS**
- Fail-on: `none`
- Annotation groups: 10
- Annotations: 10
- Blocking annotations: 0
- Findings by severity: `{"audit-only": 1, "error": 7, "warning": 2}`
- Findings by obligation: `{"blast_radius_limited_or_explicit_limitation": 1, "limitation:ring-forget-targeting": 1, "no_duplicate_processing_risk": 2, "no_rebalance_to_zero_consumers": 1, "no_replay_without_dedupe": 1, "no_unstable_consumer_group_with_backlog": 1, "queue_backlog_requires_consumers": 1, "queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk": 1, "restore_path_and_blast_radius_limited": 1}`

## annotation-group-001: `no_duplicate_processing_risk`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:105`
- Highest severity: `error`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-001-01 | finding-001 | error | semantic | no_duplicate_processing_risk | `PostInvariant.NoDuplicateReplayProcessing` | queue tenant-index-fallback-scan has replayed messages without modeled deduplication | Stop replay or add deduplication/idempotency guards before messages can be processed twice. |

## annotation-group-002: `no_duplicate_processing_risk`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:114`
- Highest severity: `error`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-002-01 | finding-002 | error | semantic | no_duplicate_processing_risk | `PostInvariant.NoDuplicateReplayProcessing` | queue tenant-index-fallback-scan has replayed messages without modeled deduplication | Stop replay or add deduplication/idempotency guards before messages can be processed twice. |

## annotation-group-003: `no_rebalance_to_zero_consumers`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:114`
- Highest severity: `error`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-003-01 | finding-003 | error | semantic | no_rebalance_to_zero_consumers | `ActionGuard.ConsumerRebalanceProgress` | queue tenant-index-fallback-scan has depth=36000 before rebalance to 0 consumers | Rebalance to a positive consumer count while backlog exists, or drain the queue first. |

## annotation-group-004: `no_replay_without_dedupe`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:105`
- Highest severity: `error`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-004-01 | finding-004 | error | semantic | no_replay_without_dedupe | `ActionGuard.MessageReplayDeduplication` | queue tenant-index-fallback-scan replay count=18000 lacks dedupe_key, idempotency proof, or dedupe window | Add a dedupe_key, prove the handler idempotent, or model a positive dedupe_window_minutes before replay. |

## annotation-group-005: `no_unstable_consumer_group_with_backlog`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:114`
- Highest severity: `error`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-005-01 | finding-005 | error | semantic | no_unstable_consumer_group_with_backlog | `PostInvariant.ConsumerGroupStableForBacklog` | queue tenant-index-fallback-scan has depth=36000 while consumer group rebalance is not stable | Wait for consumer-group stability before leaving replay/backlog processing exposed. |

## annotation-group-006: `queue_backlog_requires_consumers`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:114`
- Highest severity: `error`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-006-01 | finding-006 | error | semantic | queue_backlog_requires_consumers | `PostInvariant.QueueBacklogHasConsumers` | queue tenant-index-fallback-scan has depth=36000 with no active consumers | Keep at least one active consumer or drain backlog before rebalancing to zero consumers. |

## annotation-group-007: `restore_path_and_blast_radius_limited`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21`
- Highest severity: `error`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-007-01 | finding-007 | error | prose | data-deletion-needs-restore-precondition | `ProseAudit.data-deletion-needs-restore-precondition` | Prose describes data deletion without executable restore/blast-radius preconditions. Missing condition(s): service_available_at_least. | Require a targeted scope, backup/restore validation, and capacity guard before destructive data operations. |

## annotation-group-008: `blast_radius_limited_or_explicit_limitation`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:21`
- Highest severity: `warning`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-008-01 | finding-008 | warning | prose | destructive-delete-needs-targeting | `ProseAudit.destructive-delete-needs-targeting` | Prose describes destructive removal/forgetting without executable blast-radius checks. Missing condition(s): service_available_at_least. | Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions. |

## annotation-group-009: `queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:27`
- Highest severity: `warning`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-009-01 | finding-009 | warning | prose | backfill-needs-queue-capacity | `ProseAudit.backfill-needs-queue-capacity` | Prose mentions backfill/replay work without executable queue/backlog capacity guards. Missing condition(s): queue_depth_at_most, queue_has_consumers, queue_replay_deduplicated. | Add queue_depth_at_most, queue_has_consumers, and deduplicated replay preconditions, or document an explicit limitation. |

## annotation-group-010: `limitation:ring-forget-targeting`

- Source span: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:18`
- Highest severity: `audit-only`

| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| annotation-010-01 | finding-010 | notice | prose | prose-suppression-applied | `ProseAudit.prose-suppression-applied` | Suppressed destructive-delete-needs-targeting at line 19 with owner=grafana-tempo-public-fixture, expires=2099-12-31, reason=public excerpt is retained as audit evidence while the fixture models this as an explicit limitation, not a verified blast-radius proof, link=limitation:ring-forget-targeting. | Review suppression owner, expiry, reason, and invariant/waiver/limitation link during runbook review. |

