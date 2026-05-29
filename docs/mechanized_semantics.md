# Mechanized-semantics notes

These notes sketch how the current Python artifact could be ported to Coq or Lean
without claiming that such a mechanization already exists.

## Core objects

- `SystemState`: finite maps for regions, services/replicas, databases, queues,
  caches, alerts, feature flags, deployments, traffic routes, DNS records, and
  credentials.
- `Runbook`: a finite list of steps plus dependency edges, reordering policy,
  safety configuration, waivers, metadata, and a depth bound.
- `Step`: an action label, typed parameters, declared `requires` conditions,
  declared `effects`, and source span metadata.

## Small-step relation

A mechanized relation can mirror `checker.py` as:

```text
enabled(rb, trace, step) := step not in trace and all dependencies(step) in trace
step(rb, state, trace) -> (state', trace ++ [step])
```

Action-specific rules then refine the transition by invoking the denotational
state transformer currently documented in `docs/action_semantics.md` and generated
from `contracts.py` descriptors.

## Selected action rules

- `scale_service` updates a service's finite replica set and must preserve
  `service_min_available` after growth or shrinkage.
- `failover_database` updates `primary_region` and relies on separate quorum and
  region-health facts.
- `replay_messages` updates queue depth/dead-letter depth and may set duplicate
  risk unless dedupe/idempotency preconditions are present.
- `update_dns_record` creates a TTL window over prior and target regions; finalize
  rules must respect modeled TTL elapsed facts.
- `revoke_credential` and `rotate_credential` update credential activity and age
  facts used by dependent preconditions.

## Trusted-code-base boundary

A future mechanized proof would need to trust or separately verify: JSON/Markdown
parsing, source-span extraction, benchmark metadata, report rendering, and any
translation from production telemetry into DSL states. The current checker and
exporters are tested Python implementations, not machine-checked kernels.
