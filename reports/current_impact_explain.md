# Finding explanation: finding-001

- Type: `semantic`
- Rule: `no_duplicate_processing_risk`
- Small-step rule: `PostInvariant.NoDuplicateReplayProcessing`
- Obligation: `no_duplicate_processing_risk`
- Location: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:105`
- Message: queue tenant-index-fallback-scan has replayed messages without modeled deduplication
- Weakest-precondition hint: A replay step may not leave the queue in a duplicate-risk state unless deduplication/idempotency was modeled.
- Remediation: Stop replay or add deduplication/idempotency guards before messages can be processed twice.

## Trace

delete-stale-tenant-indexes-trigger-fallback

## Small-step trace

1. `Schedule.SequenceNext(delete-stale-tenant-indexes-trigger-fallback)`
2. `Action.Execute(delete-stale-tenant-indexes-trigger-fallback)`
3. `PostInvariant.NoDuplicateReplayProcessing(delete-stale-tenant-indexes-trigger-fallback)`

## State delta

| Field | Before | After |
| --- | --- | --- |
| `queues.tenant-index-fallback-scan.depth` | `18000` | `36000` |
| `queues.tenant-index-fallback-scan.duplicate_risk` | `False` | `True` |

## Remediation examples

- Replay from the dead-letter queue with a stable dedupe key.
- Drain or quarantine duplicate-risk messages before resuming consumers.
