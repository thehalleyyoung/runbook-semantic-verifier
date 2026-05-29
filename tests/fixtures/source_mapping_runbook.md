# Source mapping fixture

```runbook-json
{
  "name": "source mapping fixture",
  "system": {
    "regions": {"east": {"healthy": true}, "west": {"healthy": false}},
    "databases": {"orders": {"primary_region": "east", "healthy_regions": ["east"]}}
  },
  "steps": [
    {
      "id": "failover-orders",
      "action": "failover_database",
      "params": {"database": "orders", "target_region": "west", "data_loss_risk": true},
      "requires": [
        {"kind": "region_healthy", "region": "west"}
      ]
    }
  ]
}
```
