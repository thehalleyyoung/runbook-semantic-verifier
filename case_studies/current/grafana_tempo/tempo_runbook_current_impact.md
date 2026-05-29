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

> Use the "Forget" button to forget and remove any unhealthy distributors from the ring.

> If you can isolate the impacted tenants, attempt to take targeted action instead of making sweeping changes. Your easiest lever to pull is to simply delete stale tenant indexes as all components will fallback to bucket listing.

## Defensive interpretation

The public runbook appropriately warns operators to isolate tenants before broad
changes. The executable model below asks whether a derived procedure has enough
machine-checkable guardrails for capacity and fallback/backlog safety. The result
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
        "summary": "Derived fixture recorded queue fallback backlog and destructive-deletion precondition findings from public documentation excerpts."
      }
    ],
    "labels": {
      "expected_safe": false,
      "expected_violation_properties": [
        "no_queue_pause_without_drain_plan",
        "no_paused_queue_with_backlog"
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
      "tenant-index-fallback-scan": { "depth": 18000, "consumers": 1, "paused": false }
    },
    "alerts": {},
    "feature_flags": {},
    "deployments": {}
  },
  "steps": [
    {
      "id": "delete-stale-tenant-indexes",
      "action": "pause_queue",
      "params": { "queue": "tenant-index-fallback-scan" },
      "requires": []
    },
    {
      "id": "resume-fallback-scans",
      "action": "resume_queue",
      "after": ["delete-stale-tenant-indexes"],
      "params": { "queue": "tenant-index-fallback-scan" },
      "effects": [{ "kind": "queue_resumed", "queue": "tenant-index-fallback-scan" }]
    }
  ]
}
```
