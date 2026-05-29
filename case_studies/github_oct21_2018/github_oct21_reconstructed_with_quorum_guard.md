# GitHub October 21, 2018 incident: reconstructed runbook with explicit quorum guard

This fixture is **not an original GitHub runbook**. It is a transparent
reconstruction for benchmarking, derived from public facts in GitHub's official
post-incident analysis:

- Source: <https://github.blog/news-insights/company-news/oct21-post-incident-analysis/>
- Incident date: 2018-10-21 through 2018-10-22.
- Public facts used: a 43-second network partition; Orchestrator/Raft nodes in
  US West and US East public cloud established quorum and failed MySQL clusters
  over to US West; brief unreplicated writes remained in US East; GitHub paused
  webhooks/GitHub Pages and chose data integrity over availability; recovery
  involved backup restore, synchronization, controlled failover/fallback, and
  queue draining.

The executable model below is a bounded remediation variant of the sibling
reconstruction: it makes the data-safety/quorum confirmation step occur before
the modeled failover. This is a verifier fixture derived from the same public
facts, not a claim about GitHub's exact internal runbook.

```runbook-json
{
  "name": "GitHub Oct21 2018 MySQL failover reconstruction with quorum guard",
  "description": "Reconstructed executable benchmark fixture from GitHub's public October 21, 2018 post-incident analysis. It models the bounded remediation where quorum/data-safety confirmation happens before the failover action.",
  "metadata": {
    "case_study": "github-oct21-2018",
    "date": "2018-10-21",
    "sources": [
      {
        "title": "GitHub October 21 post-incident analysis",
        "url": "https://github.blog/news-insights/company-news/oct21-post-incident-analysis/"
      }
    ],
    "provenance": "reconstructed executable runbook, not exact original runbook text",
    "reconstructed_from_public_facts": [
      "43-second connectivity loss between US East Coast network hub and primary US East data center",
      "Orchestrator nodes established quorum outside the primary data center and failed clusters over to US West",
      "unreplicated writes remained in US East and new writes landed in US West, preventing a safe immediate failback",
      "webhook delivery and GitHub Pages builds were paused to protect data integrity",
      "recovery plan restored backups, synchronized replicas, fell back to a stable topology, and resumed queued jobs"
    ],
    "labels": {
      "expected_safe": true,
      "expected_violation_properties": []
    }
  },
  "allow_reordering": false,
  "max_depth": 5,
  "safety": { "max_alert_suppression_minutes": 120 },
  "system": {
    "regions": {
      "us-east": { "healthy": true },
      "us-west": { "healthy": true },
      "public-cloud-east": { "healthy": true }
    },
    "services": {
      "github-web": {
        "min_available": 1,
        "replicas": [
          { "id": "web-east-1", "region": "us-east", "healthy": true },
          { "id": "web-east-2", "region": "us-east", "healthy": true }
        ]
      }
    },
    "databases": {
      "mysql-metadata": {
        "primary_region": "us-east",
        "healthy_regions": ["us-east", "us-west"],
        "quorum_confirmed": false,
        "migration_in_progress": false,
        "migration_compatible": true
      }
    },
    "queues": {
      "webhooks": { "depth": 1000000, "consumers": 4, "paused": false },
      "pages-builds": { "depth": 50000, "consumers": 2, "paused": false }
    },
    "alerts": {
      "replication-topology-unexpected": { "active": true }
    }
  },
  "steps": [
    {
      "id": "confirm-reconciled-topology",
      "action": "confirm_quorum",
      "params": { "database": "mysql-metadata" }
    },
    {
      "id": "orchestrator-failover-to-west",
      "action": "failover_database",
      "params": {
        "database": "mysql-metadata",
        "target_region": "us-west",
        "data_loss_risk": true
      },
      "requires": [
        { "kind": "database_quorum_confirmed", "database": "mysql-metadata" }
      ]
    },
    {
      "id": "lock-deployments",
      "action": "toggle_flag",
      "params": { "flag": "deployments_locked", "enabled": true }
    },
    {
      "id": "pause-webhooks",
      "action": "pause_queue",
      "params": { "queue": "webhooks" }
    },
    {
      "id": "pause-pages-builds",
      "action": "pause_queue",
      "params": { "queue": "pages-builds" }
    }
  ]
}
```
