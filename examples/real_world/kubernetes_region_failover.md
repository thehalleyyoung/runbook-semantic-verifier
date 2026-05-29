# Kubernetes Region Failover Runbook Case Study

This case-study fixture is written as a Markdown runbook because many real operational procedures live in wikis or incident-management systems rather than DSL files. The fenced model below is the executable artifact used by `frv audit`.

The modeled bug is realistic: an operator suppresses the high-latency alert for too long, drains both API replicas before replacement capacity exists, and performs a data-loss-risk failover before quorum has been confirmed.

```runbook-json
{
  "name": "kubernetes region failover - missing quorum and capacity checks",
  "description": "Real-world-style Markdown runbook with an executable model embedded for audit.",
  "allow_reordering": true,
  "max_depth": 4,
  "safety": {"max_alert_suppression_minutes": 120},
  "system": {
    "regions": {
      "us-east": {"healthy": true},
      "us-west": {"healthy": true}
    },
    "services": {
      "api": {
        "min_available": 1,
        "replicas": [
          {"id": "api-east-1", "region": "us-east", "healthy": true},
          {"id": "api-east-2", "region": "us-east", "healthy": true}
        ]
      }
    },
    "databases": {
      "orders": {
        "primary_region": "us-east",
        "healthy_regions": ["us-east", "us-west"],
        "quorum_confirmed": false
      }
    },
    "alerts": {
      "api-high-latency": {"active": true}
    }
  },
  "steps": [
    {
      "id": "suppress-latency-alert",
      "action": "suppress_alert",
      "params": {"alert": "api-high-latency", "expires_after_minutes": 360}
    },
    {
      "id": "drain-api-east",
      "action": "drain_region",
      "params": {"region": "us-east", "services": ["api"]}
    },
    {
      "id": "failover-orders-west",
      "action": "failover_database",
      "params": {"database": "orders", "target_region": "us-west", "data_loss_risk": true}
    }
  ]
}
```
