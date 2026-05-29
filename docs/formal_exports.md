# Formal exports: TLA+, Alloy, and proof obligations

`frv export` emits starter models that preserve the executable runbook's step ids,
dependency graph, action signatures, denotational comments, modeled entity names,
waiver ids, and safety-property labels. The native Python checker remains the
authoritative executable semantics for this prototype.

```bash
PYTHONPATH=src python3 -m runbook_verify.cli export examples/safe_runbook.json --format tla
PYTHONPATH=src python3 -m runbook_verify.cli export examples/safe_runbook.json --format alloy
PYTHONPATH=src python3 -m runbook_verify.cli proof-obligations examples/safe_runbook.json --format markdown
```

## TLA+ starter specs

The generated TLA+ module includes concrete state-variable names for runbook
execution (`done`, `clock`, `dependencies`) and modeled operational entities:
services, replicas, regions, databases, queues, caches, alerts, feature flags,
deployments, traffic routes, DNS records, credentials, owners, and waivers. It
also emits dependency-scheduling predicates (`Predecessors`, `CanRun`, `Run`), a
`Wait` clock abstraction, property identifiers, and invariant-template names.

Suggested TLC workflow:

1. Save the export to a `.tla` file.
2. Add or hand-strengthen concrete invariant bodies for the properties you want
   TLC to check beyond label preservation.
3. Configure model constants so `Steps = StepSet` and the finite entity sets match
   the emitted values.
4. Run TLC over `Spec` and `Safety`, recording any counterexamples separately from
   native `frv check` results.

Suggested Apalache workflow:

1. Keep the generated module as a seed model.
2. Replace template invariants (`TRUE`) with Apalache-friendly state predicates.
3. Bound the number of transitions to the runbook's `max_depth` or a reviewed
   operational bound.
4. Treat Apalache findings as model-strengthening feedback unless they reproduce a
   native `frv` property label and trace.

## Alloy starter specs

The generated Alloy module includes signatures for `Step`, `ActionLabel`,
`PropertyLabel`, operational entity classes, waiver labels, dependency relations,
and bounded assertions for preserving native enabledness and property labels. Use
it to inspect small dependency/entity relation instances or to hand-strengthen
relations that the native checker currently handles arithmetically.

## Proof obligations

`frv proof-obligations` makes invariant, refinement-precondition, promised-effect,
temporal-monitor, exporter-abstraction, and checker-optimization obligations
explicit. These reports are review artifacts: they document which assumptions are
checked by the parser/checker, which are only exported as labels, and which would
need external runtime logs or hand-written formal proofs.

## Limitations and trusted assumptions

- Generated exports are starter specs, not complete proofs of production systems.
- The TLA+ invariant bodies preserve names and obligations but are templates until
  a reviewer strengthens them with concrete state predicates.
- The Alloy model preserves bounded relations and labels; queue/cache/DNS/service
  arithmetic remains checked by `frv` unless encoded by hand.
- Fairness, operator availability, clock skew, service discovery, telemetry
  freshness, and infrastructure behavior outside the runbook DSL are environment
  assumptions.
- Public case-study models distinguish public facts and reconstructed assumptions;
  exports do not prove private incident behavior.
- Runtime-verification obligations require observed execution logs or chatops
  events, which this command does not collect.
