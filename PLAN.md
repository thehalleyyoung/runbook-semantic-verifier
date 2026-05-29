# Research plan: formal runbook verification

## Thesis

Operational runbooks can be treated as small programs over infrastructure state. A practical checker can combine executable Markdown models, bounded verification, semantic linting, and reproducible benchmarks to find real classes of incident-response hazards while making only bounded, explicit claims.

## Formal objects

- **Syntax:** embedded Markdown `runbook-json`, JSON/YAML DSL, action descriptors, preconditions, effects, invariants, waivers, and datasets.
- **State:** services, replicas, regions, routes, queues, databases, object stores, caches, credentials, alerts, timers, and provenance labels.
- **Semantics:** small-step transition relation for schedules and actions; denotational state transformers for descriptor documentation; traces with observations, causality, and source locations.
- **Properties:** Hoare triples for local actions, temporal logic invariants for traces, refinement obligations from prose to DSL, and explicit proof obligations for exporters and optimizations.

## Core algorithms

1. Parse, type-check, and effect-check runbooks with source-preserving diagnostics.
2. Explore bounded transition systems with budgets, partial-order reduction, dominance pruning, abstract interpretation, and symbolic execution where useful.
3. Minimize counterexamples and synthesize candidate missing preconditions from weakest-precondition failures.
4. Compare runbook versions with semantic diffing and trace equivalence.
5. Export selected models to TLA+, Alloy, and mechanized-semantics notes while documenting trusted assumptions.
6. Run Markdown audit, runtime-verification checks, benchmark suites, and CI reports from one result model.

## Evaluation questions

- Which safety, liveness, and operational-readiness defects are found in historical/current public runbooks and reconstructed case studies?
- How often do typed effects, temporal invariants, and prose-to-DSL refinement checks expose hazards missed by schema validation alone?
- What reduction and minimization techniques improve runtime and trace usability without losing benchmark violations?
- How stable are results across benchmark versions, synthetic mutants, and anonymized industry-style datasets?
- What claims are justified, and which remain limited by abstraction, labels, public data availability, and bounded exploration?

## Datasets and evidence

Use three strata: checked-in examples for regression tests, public or reconstructed historical/current case studies with citations, and synthetic mutants with known labels. Every dataset entry should record provenance, license/redaction status, abstraction level, expected outcome, validity threats, and responsible-disclosure review.

## Novelty claims, bounded responsibly

Potential contributions are: a runbook-specific operational semantics, a practical Markdown-to-model refinement workflow, benchmark methodology for incident-response verification, and evidence about which formal checks help operators. Claims must not imply proof of live infrastructure safety; the tool verifies bounded models under stated assumptions.

## Practical integration path

Expose the research through `frv validate`, `frv check`, `frv audit`, `frv benchmark`, formal exporters, SARIF/JUnit output, pre-commit checks, and GitHub Actions. Each formal concept should produce an operator-facing artifact: a clearer diagnostic, a minimized trace, a generated precondition, a benchmark row, or a documented limitation.

## Milestones

1. Formalize syntax, state, small-step semantics, and proof obligations in docs and tests.
2. Add types/effects, temporal invariants, semantic diffing, and source-preserving diagnostics.
3. Improve bounded checking with reduction, abstraction, symbolic cases, and minimization.
4. Build datasets, benchmark validity notes, reproducible reports, and empirical scripts.
5. Harden CI, exports, packaging, governance, disclosure, and adoption docs.
6. Assemble paper outline, tables, artifact bundle, and replication instructions.

## Paper outline

1. Motivation: runbooks as operational programs.
2. Language and semantics.
3. Verification, audit, and counterexample algorithms.
4. Dataset and benchmark methodology.
5. Empirical results over examples, historical/current cases, and synthetic mutants.
6. Practical integration and responsible disclosure.
7. Threats to validity and limits of bounded formalization.
8. Related work in PL, model checking, runtime verification, and SRE tooling.
9. Conclusion and artifact availability.
