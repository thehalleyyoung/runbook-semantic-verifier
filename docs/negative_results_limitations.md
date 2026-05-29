# Negative results and limitations

These are explicit cases where the artifact should not be read as stronger than
its evidence.

## Prose ambiguity

Markdown audit can flag dangerous wording and require executable blocks, but it
cannot infer exact intent from ambiguous prose. A sentence such as "drain traffic
carefully" needs a modeled route, capacity preconditions, and waits before FRV can
verify it. Unmapped operational claims remain audit findings or coverage gaps.

## Missing or stale inventories

Readiness and owner-scorecard commands can compare models with a supplied JSON
inventory. They cannot discover whether that inventory is complete, current, or
synchronized with live cloud resources. Inventory disagreements are refinement
findings over checked inputs, not live discovery.

## Nondeterministic cloud behavior

Provider APIs, eventual consistency, DNS caches, queue redelivery, failover
controllers, and human operators can behave outside the DSL's abstractions. The
model captures selected hazards such as TTL waits, queue dedupe, quorum, capacity,
write freezes, and alert expiry; it does not prove arbitrary distributed-system
correctness.

## Bounded search

Absence of violations means no modeled property failed within `max_depth`, state
budget, timeout, entity universe, and selected exploration strategy. It is useful
for review gates and regression tests, but it is not a temporal proof over all
possible executions.

## Public case-study reconstruction

The GitHub Oct. 21 fixture is reconstructed from public post-incident facts; the
Grafana Tempo, DNS, and Redis examples are bounded public-documentation-derived
models or mutants. They are evaluation artifacts, not claims about private
runbooks or live deployments.

## Synthetic mutation bias

`frv mutate` generates useful calibration mutants for missing preconditions,
reordered dependencies, stale owners, unsafe retries, insufficient waits,
underprovisioned replicas, and invalid waivers. Mutants are deliberately seeded
hazards; they measure whether the artifact catches known patterns, not the rate
of real production mistakes.
