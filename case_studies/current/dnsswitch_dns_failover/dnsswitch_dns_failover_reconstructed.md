# DNS cutover TTL and health-check convergence case study

Public provenance: `Hotpirsch/dnsswitch` README, retrieved 2026-05-29,
describes DNS health checks and routing and the role of TTLs in how
quickly clients pick up DNS changes. This checked-in fixture is an
independently authored bounded model of that class of operation, not a claim
about the project's live infrastructure or a maintainer-authored runbook.

The intentionally unsafe variant below models an operator cutting a stateful
service DNS record from `east` to `west` before the west endpoint has converged
health checks, before west service capacity exists, and before any TTL split
brain window can be made safe or waited out.

```runbook-json
{
  "name": "Reconstructed public DNS failover with missing TTL guards",
  "description": "Bounded model derived from public DNS cutover guidance; unsafe by construction.",
  "metadata": {
    "owners": ["edge-sre"],
    "source_url": "https://github.com/Hotpirsch/dnsswitch",
    "retrieved": "2026-05-29",
    "labels": {
      "expected_safe": false,
      "expected_violation_properties": [
        "dns_health_check_converged_before_cutover",
        "dns_no_split_brain_during_ttl",
        "dns_requires_regional_capacity",
        "dns_ttl_elapsed_before_finalize"
      ]
    }
  },
  "allow_reordering": true,
  "max_depth": 2,
  "system": {
    "regions": {
      "east": { "healthy": true },
      "west": { "healthy": true }
    },
    "services": {
      "checkout": {
        "min_available": 1,
        "replicas": [
          { "id": "checkout-east-0", "region": "east", "healthy": true }
        ]
      }
    },
    "dns_records": {
      "checkout.example.com": {
        "service": "checkout",
        "region": "east",
        "ttl_minutes": 5,
        "health_check_converged_regions": ["east"],
        "allow_split_brain": false
      }
    }
  },
  "steps": [
    {
      "id": "cutover-dns-west",
      "action": "update_dns_record",
      "params": { "record": "checkout.example.com", "target_region": "west" }
    },
    {
      "id": "finalize-before-ttl",
      "action": "finalize_dns_record",
      "after": ["cutover-dns-west"],
      "params": { "record": "checkout.example.com" }
    }
  ]
}
```
