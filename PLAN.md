# Research and product plan: semantics-grounded runbook verification

## Thesis

Operational runbooks are programs over infrastructure state, even when they are written as Markdown or wiki prose. A useful verifier should therefore provide explicit program semantics, bounded and honest verification claims, and practical SRE workflows that catch unsafe operations documentation before incidents. The project thesis is that small-step semantics, state-transformer meanings, program logics, and model-checking techniques can be packaged as CI gates, audit reports, counterexample traces, and service-owner scorecards rather than as academic artifacts alone.

## Immediate product and research value

- **For SRE teams:** fast validation, Markdown/wiki audits, CI gates for dangerous docs, stale-precondition detection, incident-readiness reports, and remediation-oriented counterexamples.
- **For reviewers:** semantic diffs that identify changed effects, weakened assumptions, expired waivers, and newly reachable hazards in pull requests.
- **For researchers:** a concrete runbook language, executable semantics, benchmark suite, historical/current case studies, and documented validity threats for studying incident-response verification.
- **For adoption:** every formal feature must produce a user-visible artifact: a clearer diagnostic, minimized trace, generated precondition, benchmark row, code-scanning annotation, or explicit limitation.

## Formal objects and semantics

- **Syntax:** Markdown prose, fenced `runbook-json` DSL blocks, action descriptors, dependencies, preconditions, effects, invariants, waivers, owners, inventories, and benchmark metadata.
- **State:** services, replicas, regions, routes, traffic weights, queues, databases, caches, object stores, credentials, alerts, timers, ownership, provenance, and environment assumptions.
- **Small-step semantics:** a transition relation over configurations `(runbook, store, schedule, trace, budget)` for enabled steps, dependency ordering, waits, nondeterministic operator choices, failures, and external interference.
- **Denotational semantics:** each action has a state-transformer meaning used by parser metadata, schema documentation, checker transitions, formal exports, and explanation traces.
- **Program logics:** local action obligations are expressed as Hoare triples; missing guards are explained as weakest-precondition failures; run-level properties use temporal invariants over traces.
- **Types and effects:** entity and unit types prevent malformed models; action effect types record idempotency, reversibility, blast radius, retry safety, data loss risk, and customer-visible impact.
- **Contracts:** assume-guarantee and rely/guarantee rules model service dependencies, concurrent operators, automation, and cloud/environment assumptions.
- **Refinement:** prose-to-DSL checks classify claims as modeled, unmodeled, contradicted, waived, or out-of-scope, avoiding false claims that all Markdown text was verified.
- **Mechanization boundary:** TLA+/Alloy exports and Coq/Lean notes should identify trusted code, boundedness, fairness assumptions, abstraction gaps, and proof obligations.

## Algorithms

1. Parse Markdown and DSL while preserving source locations and provenance for every semantic object.
2. Type-check entities and effect-check actions before exploration, emitting fast CI diagnostics.
3. Run bounded model checking with explicit depth, schedule, fairness, timeout, and inconclusive-result semantics.
4. Apply partial-order reduction, dominance pruning, abstract interpretation, and symbolic execution where they preserve reported violations.
5. Minimize counterexamples by removing independent steps, folding stuttering waits, and retaining the temporal witness.
6. Synthesize candidate missing preconditions from weakest-precondition failures and present reviewable Markdown/JSON patches.
7. Compute semantic diffs between runbook revisions and classify changes by behavioral and proof-obligation impact.
8. Compare observed execution logs with modeled traces for runtime verification without claiming live-system proof.
9. Export selected models to TLA+, Alloy, and mechanization notes with synchronized property names and limitations.

## CLI and user workflows

- `frv validate`: fast schema, parser, entity, dependency, and type checks for pre-commit use.
- `frv check`: bounded verification with minimized counterexample traces and remediation hints.
- `frv scan`: repository/wiki triage that discovers runbook-like Markdown, ranks dangerous-effect vocabulary against semantic obligations, and recommends which docs need executable models first.
- `frv audit`: Markdown/wiki scan for dangerous operations prose, stale assumptions, missing executable blocks, and unsafe suppressions.
- `frv diff old new`: implemented semantic pull-request review for changed effects, assumptions, verification settings, proof-obligation deltas, and reachable counterexample deltas.
- `frv explain FINDING`: show the rule, state delta, source lines, weakest-precondition hint, and suggested fix for one diagnostic.
- `frv readiness`: implemented service or repository incident-readiness report covering validation, bounded-checking status, audit severity, stale preconditions, rollback/restore coverage, proof obligations, and uncovered service/region paths.
- `frv owner-scorecard`: implemented team-facing scorecard for verified runbooks, open hazards, stale assumptions, waiver debt, proof-obligation failures, and remediation history grouped by owner metadata.
- `frv coverage`: implemented property-coverage report mapping invariant/proof-obligation templates to modeled services, databases, queues, caches, alerts, DNS records, credentials, owners, regions, source steps, and Markdown sections; unverified prose obligations remain explicit coverage gaps.
- CI outputs should include JSON, Markdown, SARIF, and JUnit so the same semantic result powers terminals, GitHub annotations, dashboards, and reports.

## Benchmark and dataset plan

Use three strata of evidence:

1. **Regression examples:** small checked-in DSL/Markdown models for every semantic rule, diagnostic, exporter, and CLI workflow.
2. **Historical/current case studies:** public or sanitized reproductions of failover, queue replay, data restore, credential rotation, DNS migration, cache, and alerting incidents.
3. **Synthetic mutants:** controlled variants that remove guards, reorder steps, weaken waits, stale owners, underprovision replicas, misuse waivers, or introduce unsafe retries.

Every benchmark entry should record provenance, license/redaction status, abstraction level, expected outcome, semantic features covered, responsible-disclosure review, and validity threats. Reports should include runtime, state counts, reduction impact, minimized trace length, finding severity, false-positive review notes, and remediation category.

## Historical and current knowledge claims

The repository can responsibly claim evidence about bounded models of runbooks, public/sanitized case reconstructions, and synthetic mutants. It should not claim proof of live infrastructure safety. Historical outage reproductions must distinguish public facts from reconstructed assumptions. Current case studies must identify inventory freshness, redaction effects, and whether results are advisory, CI-blocking, or benchmark-only.

## Evaluation questions

- Which hazards are found by schema validation, prose audit, type/effect checks, bounded verification, semantic diffing, and combined workflows?
- Do weakest-precondition hints and minimized traces help operators remediate faster than raw counterexamples?
- Which partial-order, abstract-interpretation, symbolic, and minimization techniques reduce cost without hiding benchmark violations?
- How often do Markdown refinement checks expose unmodeled or contradicted operational claims?
- Are incident-readiness reports and owner scorecards stable enough to guide SRE prioritization?
- What false positives, false negatives, validity threats, and abstraction gaps limit the claims?

## Milestones

1. Document formal objects, small-step rules, state transformers, Hoare obligations, and responsible claim boundaries.
2. Extend types/effects, temporal invariants, source-preserving diagnostics, and semantic diffing.
3. Improve bounded checking with reduction, abstraction, symbolic execution, counterexample minimization, and precondition synthesis.
4. Ship Markdown/wiki audit, CI gate templates, incident-readiness reports, owner scorecards, and SARIF/JUnit outputs.
5. Build benchmark strata, historical/current case studies, synthetic mutants, validity-threat documentation, and reproducible reports.
6. Harden formal exports, mechanization notes, proof-obligation tracking, artifact packaging, governance, and release criteria.

## Paper outline

1. Motivation: runbooks as operational programs and why prose-only review fails.
2. Language and semantic objects: syntax, state, traces, effects, waivers, and provenance.
3. Semantics and logics: small-step rules, state transformers, Hoare/weakest-precondition obligations, temporal invariants, and contracts.
4. Algorithms: bounded checking, reductions, abstract interpretation, symbolic execution, counterexample minimization, semantic diffing, and runtime verification.
5. User workflows: validation, audit, CI gates, explanations, readiness reports, and scorecards.
6. Benchmarks and datasets: regression examples, historical/current cases, synthetic mutants, metadata, and validity threats.
7. Evaluation: hazards found, cost, trace usefulness, remediation impact, ablations, and adoption signals.
8. Responsible claims and limitations: boundedness, abstraction gaps, public-data limits, disclosure, and live-system non-claims.
9. Related work: operational semantics, model checking, abstract interpretation, program logics, runtime verification, configuration verification, and SRE tooling.
10. Conclusion and artifact availability.

## Responsible novelty claims

Strong claims should be phrased as: this project provides an executable semantics and practical workflow for finding bounded classes of runbook documentation hazards, plus a benchmark methodology for evaluating those checks. Novelty should focus on connecting PL/formal-methods semantics to Markdown operations docs, semantic refinement of prose to executable models, and SRE-facing counterexample/remediation workflows. Avoid claiming complete incident prevention, infrastructure correctness, or verification of undocumented environment behavior.
