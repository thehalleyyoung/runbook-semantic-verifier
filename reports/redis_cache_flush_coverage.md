# Property coverage report: case_studies/current/redis_cache_flush

- Executable runbooks: 1
- Properties mapped: 6
- Services covered: 1/1
- Databases covered: 0/0
- Queues covered: 0/0
- Caches covered: 1/1
- Alerts covered: 0/0
- DNS records covered: 0/0
- Credentials covered: 0/0 (credential state is not implemented in the current DSL)
- Regions covered: 0/0
- Owners: `public-redis-runbook-fixture`
- Unverified prose obligations: 2
- Coverage gaps: 2

## Invariant coverage

| Property | Runbook | Owners | Services | Databases | Queues | Caches | Alerts | DNS records | Credentials | Regions | Steps/sections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cache_flush_requires_write_freeze` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md` | `public-redis-runbook-fixture` | `web-api` |  |  | `redis-primary` |  |  |  |  | `flush-redis` (L51, Redis cache flush public-runbook-derived fixture)<br>`underwarm-redis` (L52, Redis cache flush public-runbook-derived fixture)<br>`overwarm-redis` (L53, Redis cache flush public-runbook-derived fixture) |
| `cache_warmup_before_traffic` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md` | `public-redis-runbook-fixture` | `web-api` |  |  | `redis-primary` |  |  |  |  | `flush-redis` (L51, Redis cache flush public-runbook-derived fixture)<br>`underwarm-redis` (L52, Redis cache flush public-runbook-derived fixture)<br>`overwarm-redis` (L53, Redis cache flush public-runbook-derived fixture) |
| `cache_warmup_within_capacity` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md` | `public-redis-runbook-fixture` | `web-api` |  |  | `redis-primary` |  |  |  |  | `flush-redis` (L51, Redis cache flush public-runbook-derived fixture)<br>`underwarm-redis` (L52, Redis cache flush public-runbook-derived fixture)<br>`overwarm-redis` (L53, Redis cache flush public-runbook-derived fixture) |
| `no_draining_all_replicas` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md` | `public-redis-runbook-fixture` | `web-api` |  |  |  |  |  |  |  |  |
| `no_stale_reads_after_cache_flush` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md` | `public-redis-runbook-fixture` | `web-api` |  |  | `redis-primary` |  |  |  |  | `flush-redis` (L51, Redis cache flush public-runbook-derived fixture)<br>`underwarm-redis` (L52, Redis cache flush public-runbook-derived fixture)<br>`overwarm-redis` (L53, Redis cache flush public-runbook-derived fixture) |
| `service_min_available` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md` | `public-redis-runbook-fixture` | `web-api` |  |  |  |  |  |  |  |  |

## Unverified prose obligations

| Rule | Severity | Obligation | Location | Section |
| --- | --- | --- | --- | --- |
| cache-flush-needs-warmup-capacity | warning | `cache_flush_requires_write_freeze; cache_warmup_before_traffic; cache_warmup_within_capacity` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md:1` | Redis cache flush public-runbook-derived fixture |
| cache-flush-needs-warmup-capacity | warning | `cache_flush_requires_write_freeze; cache_warmup_before_traffic; cache_warmup_within_capacity` | `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md:14` | Redis cache flush public-runbook-derived fixture |

## Coverage gaps

- `prose_obligation` `cache-flush-needs-warmup-capacity` in `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md`: Markdown section has unverified obligation cache_flush_requires_write_freeze; cache_warmup_before_traffic; cache_warmup_within_capacity
- `prose_obligation` `cache-flush-needs-warmup-capacity` in `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md`: Markdown section has unverified obligation cache_flush_requires_write_freeze; cache_warmup_before_traffic; cache_warmup_within_capacity
