# Redis cache flush public-runbook-derived fixture

Source: OneUptime public blog/runbook template, "How to Create a Redis Runbook for Operations".
Source URL: <https://raw.githubusercontent.com/OneUptime/blog/master/posts/2026-03-31-redis-operations-runbook/README.md>
Retrieval date: `2026-05-29`
License note: public blog material; this fixture stores short attributed phrases plus an independently authored bounded model.

Public excerpt used as operational input:

> `03-common-tasks.md - Restart, backup, flush procedures`
>
> High memory alert: `redis-cli CONFIG SET maxmemory-policy allkeys-lru  # enable eviction`

Bounded modeling note: the public template usefully reminds operators to include flush procedures and capacity/scaling sections, but the excerpt does not itself encode write freeze, cache warmup threshold, or cold-start capacity obligations. This defensive fixture models a common unsafe cache-flush mutant so the verifier can check those obligations explicitly. It is not a claim about a live OneUptime deployment.

```runbook-json
{
  "name": "Redis public runbook derived cache flush mutant",
  "description": "Derived from a public Redis runbook template mentioning flush procedures and capacity; models an unsafe cache flush without write freeze or sufficient warmup capacity.",
  "metadata": {
    "owner": "public-redis-runbook-fixture",
    "labels": {
      "expected_safe": false,
      "expected_violation_properties": [
        "cache_flush_requires_write_freeze",
        "cache_warmup_before_traffic",
        "cache_warmup_within_capacity",
        "no_stale_reads_after_cache_flush"
      ],
      "expected_prose_rules": ["cache-flush-needs-warmup-capacity"]
    }
  },
  "allow_reordering": true,
  "max_depth": 2,
  "system": {
    "services": {
      "web-api": {"min_available": 0, "replicas": []}
    },
    "caches": {
      "redis-primary": {
        "service": "web-api",
        "entries": 100000,
        "warmup_entries": 80000,
        "capacity_entries": 120000,
        "warm": true,
        "write_frozen": false
      }
    }
  },
  "steps": [
    {"id": "flush-redis", "action": "flush_cache", "params": {"cache": "redis-primary"}},
    {"id": "underwarm-redis", "action": "warm_cache", "after": ["flush-redis"], "params": {"cache": "redis-primary", "entries": 40000}},
    {"id": "overwarm-redis", "action": "warm_cache", "after": ["flush-redis"], "params": {"cache": "redis-primary", "entries": 130000}}
  ]
}
```
