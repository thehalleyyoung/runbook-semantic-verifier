# Finding explanation: finding-001

- Type: `semantic`
- Rule: `no_paused_queue_with_backlog`
- Small-step rule: `PostInvariant.QueueBacklogProgress`
- Obligation: `no_paused_queue_with_backlog`
- Location: `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md:77`
- Message: queue tenant-index-fallback-scan is paused with depth=18000 and consumers=1
- Weakest-precondition hint: A terminal paused queue is safe only when backlog is bounded or alternate consumers remain active.
- Remediation: Resume the queue or prove backlog is drained and alternate consumers are active.

## Trace

delete-stale-tenant-indexes

## State delta

| Field | Before | After |
| --- | --- | --- |
| `queues.tenant-index-fallback-scan.paused` | `False` | `True` |

## Remediation examples

- Resume the queue after the maintenance step.
- Drain backlog before pausing consumers.
