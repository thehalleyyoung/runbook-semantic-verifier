# Current-impact case study: Grafana Tempo public runbook excerpt

This defensive case study analyzes public operational documentation, not a live
service. Findings are phrased as potential runbook safety gaps and should be
validated by maintainers before operational use.

## Source metadata

- Source: Grafana Tempo `operations/tempo-mixin/runbook.md`
- URL: <https://raw.githubusercontent.com/grafana/tempo/main/operations/tempo-mixin/runbook.md>
- Repository commit observed: `ef18cc176e44dea795543f50cb2341f5ea9e7827`
- Commit date observed: 2026-05-29T15:35:05Z
- Retrieval date: 2026-05-29
- License note: source repository publishes AGPL-3.0 license text; this file uses short attributed excerpts plus an independently authored executable safety model.

## Public prose excerpts analyzed

<!-- frv-suppress rule=destructive-delete-needs-targeting owner=grafana-tempo-public-fixture expires=2099-12-31 reason="public excerpt is retained as audit evidence while the fixture models this as an explicit limitation, not a verified blast-radius proof" link=limitation:ring-forget-targeting -->
> Use the "Forget" button to forget and remove any unhealthy distributors from the ring.

> If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing.

## Defensive interpretation

The public runbook appropriately warns operators to isolate tenants before broad
changes. The executable model below asks whether a derived procedure has enough
machine-checkable guardrails for deduplicated fallback replay, consumer-group
stability, and backlog safety. The result
is a reproducible finding about missing executable preconditions in this artifact,
not an undisclosed vulnerability claim about Grafana Tempo.

```runbook-json
{
  "name": "Grafana Tempo current public runbook derived safety model",
  "description": "Defensive model derived from public Tempo runbook prose about ring forget and stale tenant index deletion.",
  "metadata": {
    "source": {
      "url": "https://raw.githubusercontent.com/grafana/tempo/main/operations/tempo-mixin/runbook.md",
      "commit": "ef18cc176e44dea795543f50cb2341f5ea9e7827",
      "retrieved": "2026-05-29",
      "license_note": "AGPL-3.0 repository; short attributed excerpts plus independent model."
    },
    "owners": [
      {
        "id": "grafana-tempo-public-fixture",
        "role": "case-study-model-owner"
      }
    ],
    "service_owners": {
      "tempo-query": ["grafana-tempo-public-fixture"]
    },
    "remediation_history": [
      {
        "date": "2026-05-29",
        "status": "open",
        "summary": "Derived fixture recorded queue fallback replay, consumer-group stability, and destructive-deletion precondition findings from public documentation excerpts."
      }
    ],
    "labels": {
      "expected_safe": false,
      "expected_violation_properties": [
        "no_replay_without_dedupe",
        "no_duplicate_processing_risk",
        "no_rebalance_to_zero_consumers",
        "queue_backlog_requires_consumers",
        "no_unstable_consumer_group_with_backlog"
      ],
      "expected_prose_rules": [
        "data-deletion-needs-restore-precondition",
        "destructive-delete-needs-targeting"
      ]
    }
  },
  "allow_reordering": false,
  "max_depth": 2,
  "safety": { "max_alert_suppression_minutes": 120 },
  "system": {
    "regions": { "prod": { "healthy": true } },
    "services": {
      "tempo-query": {
        "min_available": 2,
        "replicas": [
          { "id": "query-1", "region": "prod", "healthy": true },
          { "id": "query-2", "region": "prod", "healthy": true }
        ]
      }
    },
    "databases": {},
    "queues": {
      "tenant-index-fallback-scan": {
        "depth": 18000,
        "consumers": 1,
        "paused": false,
        "dead_letter_depth": 2500,
        "dedupe_window_minutes": 0,
        "consumer_group_stable": true
      }
    },
    "alerts": {},
    "feature_flags": {},
    "deployments": {}
  },
  "steps": [
    {
      "id": "delete-stale-tenant-indexes-trigger-fallback",
      "action": "replay_messages",
      "params": {
        "queue": "tenant-index-fallback-scan",
        "count": 18000
      },
      "requires": [],
      "effect_annotations": {
        "effect_types": ["queue_replay"],
        "idempotency": "unknown",
        "reversibility": "unknown",
        "retry_safety": "unknown",
        "blast_radius": "tenant-index fallback scan backlog in this bounded public fixture",
        "expected_user_impact": "potential duplicate work and query degradation unless dedupe and consumer stability preconditions are added",
        "reviewed_by": ["grafana-tempo-public-fixture"]
      }
    },
    {
      "id": "rebalance-fallback-consumers",
      "action": "rebalance_consumers",
      "after": ["delete-stale-tenant-indexes-trigger-fallback"],
      "params": {
        "queue": "tenant-index-fallback-scan",
        "consumers": 0
      }
    }
  ]
}
```
