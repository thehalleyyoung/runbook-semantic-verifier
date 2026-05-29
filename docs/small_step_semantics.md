# Small-step operational semantics

The checker treats a runbook as a bounded transition system.  A configuration is
`(state, done, trace, rules)`, where `state` is the immutable modeled system
state, `done` is the set of executed step ids, `trace` is the operator-visible
step sequence, and `rules` is the mirrored small-step rule trace emitted in
reports.

## Scheduling

- `Schedule.SequenceNext(step)`: when `allow_reordering: false`, the next source
  order step may run only if all of its `after` dependencies are already done.
- `Schedule.DependencyReady(step)`: when `allow_reordering: true`, any not-yet-run
  step whose `after` dependencies are done may run.
- `Schedule.OperatorChoice(step)`: if more than one dependency-ready step exists,
  the checker explores each operator choice as a nondeterministic branch.

The bounded search is breadth-first and deduplicates configurations by state
fingerprint plus `done`, so the first counterexample for a property is already a
short dependency-respecting trace in this abstraction.

## Guards, execution, waits, and failures

- `StepEnabled.Requires(step)` and `StepEnabled.RequiresDefined(step)` check
  declared `requires` conditions before action execution.
- `ActionGuard.*(step)` rules check operation-specific safety guards such as
  database quorum, queue replay deduplication, cache write freezes, load-balancer
  drain traffic, and DNS TTL/health/capacity preconditions.
- `Action.Execute(step)` applies normal action semantics from
  `docs/action_semantics.md`.
- `Action.Wait(step)` is the distinguished execution rule for `wait`; it advances
  only the modeled clock by `params.minutes`.
- `Action.Failure(step)` records an action whose parameters are syntactically
  valid but fail against the current model state during execution.

## Post-state obligations

After a successful action, `PostInvariant.*`, `RouteInvariant.*`, and
`Postcondition.*` rules check global invariants and declared `effects`.  These
rules are bounded obligations over the reached state, not claims about live
production systems outside the DSL model.

## Exploration budgets

- `Explore.BudgetReached` records a terminal frontier when `max_depth` is reached
  before all steps are done.
- `Explore.Terminal` records a terminal completed trace.

`CheckResult.performance_counters()["semantic_rule_counts"]`, `frv check`, audit
JSON/Markdown/SARIF, benchmark output, and `frv explain` expose these rule names.
Semantic findings also include a `semantic_trace`, for example:

```text
Schedule.DependencyReady(cutover) -> ActionGuard.DNSHealthCheckConverged(cutover)
```

This trace is a rule-level witness for why the bounded checker reported a
counterexample.
