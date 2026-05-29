# Related-work notes

These notes position the artifact without claiming exhaustive novelty. They are
intended for reviewers who want to map implementation surfaces to established
research and SRE practice.

## Operational semantics and program models

FRV treats a runbook as a small operational program: parsed syntax, a finite
entity universe, immutable stores, enabled-step scheduling, action transitions,
wait transitions, failures, traces, and hazards. The implementation evidence is
`src/runbook_verify/checker.py`, `src/runbook_verify/actions.py`,
`docs/small_step_semantics.md`, and `frv formal-objects`. The connection is a
bounded executable semantics for incident procedures, not a new universal
language semantics.

## Model checking and bounded exploration

The checker enumerates dependency-respecting traces up to model budgets and emits
counterexample witnesses. This is closest to bounded explicit-state model
checking used as an engineering gate. State budgets, timeout metadata,
seeded/randomized schedules, and benchmark performance counters make the bound
explicit. The repo also exports TLA+/Alloy starter models, but those exports are
labels and scaffolding unless reviewers strengthen predicates and run native
model checkers.

## Program logics and weakest preconditions

Findings include Hoare-style triples and weakest-precondition hints to make
operator remediation concrete: add quorum checks, freeze writes, wait for TTLs,
ensure dedupe keys, restore capacity, or re-enable alerts. These hints are
explanatory obligations generated from explicit action descriptors; they are not
machine-checked Coq/Lean proofs of cloud behavior.

## Abstract interpretation and reductions

The artifact currently records counters for reductions, symbolic splits, and
minimized traces. The implemented counterexample minimizer greedily replays
subsequences and preserves the same property/step witness when dependency order
permits. Dominance pruning, full abstract interpretation, and symbolic execution
remain future algorithmic work rather than claimed results.

## Runtime verification

`frv runtime-verify` checks observed JSON/chatops event prefixes against modeled
runbook step ids, dependencies, preconditions, action semantics, and
postconditions. This follows runtime-verification practice by monitoring
conformance of observed traces to a model, while explicitly avoiding live-safety
claims about unobserved infrastructure state.

## SRE tooling and documentation governance

FRV complements runbook linters, CI checks, repository scanners, service catalogs,
and incident-readiness dashboards. Its specific contribution is to connect those
surfaces to executable safety semantics, source-linked counterexamples,
benchmark metadata, waivers, owner scorecards, and reproducible public fixtures.
It does not replace on-call review, game days, chaos tests, post-incident review,
or provider-specific validation.
