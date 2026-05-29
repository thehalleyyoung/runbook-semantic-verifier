# Oracle-review protocol

Benchmark findings can be reviewed by SRE/security operators without claiming stronger formal proof. The allowed labels are:

- `true_hazard`: the modeled trace represents a real operational hazard for the scoped fixture.
- `useful_warning`: the trace is not known to be a live hazard but would prompt a useful runbook edit, precondition, rollback step, or explicit limitation.
- `false_positive`: the trace is ruled out by trusted operational facts missing from the model.
- `unsupported_claim`: public or sanitized evidence is insufficient to decide.

Review packet:

1. Benchmark config entry with provenance, license, abstraction level, disclosure status, validity threats, and semantic features.
2. JSON/Markdown benchmark output including bounded states, traces, workflow baselines, and expected labels.
3. `frv explain` output for representative counterexamples when available.
4. Any semantic diff baseline if the benchmark claims a remediation or regression delta.

Protocol rules:

- Reviewers label findings, not live services.
- A `false_positive` label must cite the missing trusted fact and should become either a modeled precondition/effect, inventory fact, waiver, or limitation.
- `unsupported_claim` is acceptable evidence quality debt; it must not be rewritten as a safety claim.
- Expired, anonymous, or scope-free reviews are ignored by release evidence.
