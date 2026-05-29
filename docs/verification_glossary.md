# Verification glossary

| Term | Meaning in this repository |
| --- | --- |
| Runbook | Operator procedure represented as prose plus an executable `runbook-json` model. |
| Step | One modeled operator action with typed parameters, dependencies, preconditions, and effects. |
| Dependency scheduling | The finite partial order induced by each step's `after` list. |
| Trace | A dependency-respecting sequence of executed steps explored by the checker. |
| Safety property / invariant | A named bounded condition such as `service_min_available` or `queue_backlog_requires_consumers`. |
| Counterexample | A concrete bounded trace that violates a safety property in the DSL model. |
| Waiver | Owner-reviewed, expiring metadata that explains why a finding is accepted or advisory. |
| Weakest precondition | The modeled condition that would prevent a particular property violation for an action. |
| Hoare triple | Report text connecting a precondition, action, and postcondition obligation. |
| Denotational state transformer | The documented state update associated with an action label. |
| Small-step semantics | The checker rules that advance one action at a time through a finite trace. |
| TLA+ export | A starter temporal model preserving step, dependency, variable, and property names. |
| Alloy export | A starter bounded-relational model preserving signatures, dependency edges, waiver labels, and property labels. |
| Proof obligation | An explicit review item for invariants, refinements, exporter abstractions, checker assumptions, or future runtime monitors. |
| Runtime monitor | A future consumer of execution logs/chatops events that could compare observed steps with modeled traces. |
| Public historical fixture | A model reconstructed only from public incident facts, not private operational data. |
| Public current fixture | A bounded model derived from current public documentation with source/licensing notes. |
| Validity threat | A documented limit on how strongly benchmark results generalize. |
