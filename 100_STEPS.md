# 100 steps toward research-grade formal runbook verification

This roadmap treats operational runbooks as programs with explicit semantics, proof obligations, datasets, and evaluation protocols. Each phase connects formal-methods work to practical artifacts: Markdown runbooks, CLI diagnostics, CI reports, benchmarks, case studies, and responsible disclosure.

## Phase 1 — Preserved foundation: executable DSL, validation, and schema contract

- [x] Preserve the repo-specific 100-step roadmap spanning verifier depth, research evidence, industry usability, and responsible adoption.
- [x] Expose a machine-readable JSON Schema for the runbook DSL through `frv schema` so editors, registries, and CI systems can validate models before checking.
- [x] Harden parser validation for numeric DSL bounds such as `max_depth`, wait durations, replica counts, queue depths, and alert suppression durations.
- [x] Reject cyclic step dependency graphs at parse time so impossible runbooks fail fast with actionable errors.
- [x] Document the schema command and strengthened validation contract in the README and cover it with regression tests.
- [x] Publish a checked-in canonical schema artifact under `docs/schema/runbook.schema.json` and verify it is generated from the implementation.
- [x] Add schema examples showing every supported top-level field with comments in prose and strict JSON fixtures for automation.
- [x] Split action parameter validation into reusable typed field descriptors shared by parser, schema generation, docs, and exporters.
- [x] Add semantic validation that every service `min_available` target is achievable by the declared replica set unless explicitly waived.
- [x] Add validation for duplicate replica ids within each service and duplicate entities across generated scale operations.
- [x] Add validation that deployment entries and service deployment fields agree or report a precise consistency warning.
- [x] Add a `frv validate` command that performs parse/schema/entity/dependency checks without running state-space exploration.
- [x] Add structured JSON diagnostics for parse errors with path, line, field, severity, and remediation text.
- [x] Add a schema compatibility policy documenting versioning, deprecations, and migration guarantees for industry users.
- [x] Introduce an explicit action semantics reference table generated from tests and implementation metadata.
- [x] Add first-class semantics for traffic shifting, load balancer draining, and weighted routing during regional failover.

## Phase 2 — Formal objects and operational semantics for real runbooks

- [ ] Define the core mathematical objects: runbook syntax, entity universe, stores, traces, hazards, observations, diagnostics, and benchmark labels, with each object linked to CLI JSON fields.
- [ ] Write a small-step operational semantics for actions, dependency scheduling, waits, failures, and nondeterministic operator choices, then mirror it in checker traces.
- [ ] Define denotational state transformers for each action descriptor so parser metadata, schema documentation, and checker transitions share one semantic vocabulary.
- [ ] Express runbook safety obligations as Hoare triples over preconditions, action effects, and postconditions, surfaced as actionable `frv check` diagnostics.
- [ ] Add weakest-precondition documentation for missing guards, including concrete CLI suggestions for steps that require alert, quorum, backup, or ownership preconditions.
- [ ] Extend Markdown source-line mapping to multiline step objects and nested precondition/effect diagnostics so formal counterexamples point back to prose.
- [ ] Add first-class semantics for cache flush, cache warmup, and stale-read risk during incident response, with safe and unsafe Markdown examples.
- [ ] Add first-class semantics for object storage replication, bucket write freezes, and restore-from-snapshot operations, with RPO/RTO invariants.
- [ ] Add first-class semantics for message replay, dead-letter queues, and consumer group rebalancing, with benchmark cases for duplicate processing.
- [ ] Add first-class semantics for DNS changes, TTL wait windows, and split-brain routing hazards, with CLI traces operators can review.

## Phase 3 — Types, effects, contracts, and refinement claims

- [ ] Introduce a lightweight type system for entities, regions, traffic weights, queues, databases, credentials, alerts, and time units, with schema-preserving migrations.
- [ ] Add an effect system for dangerous actions such as deletion, credential revocation, manual SQL, traffic drains, and customer-visible degradation.
- [ ] Require typed effect annotations for idempotency, reversibility, blast radius, and retry safety, and emit checker warnings for unsafe retries.
- [ ] Define refinement relations from prose Markdown to executable DSL blocks, reporting unmapped operational claims as audit findings rather than pretending they were verified.
- [ ] Add semantic diffing of two runbook versions to classify changes as behavior-preserving, proof-obligation-strengthening, or safety-relevant.
- [ ] Add assume-guarantee contracts for services and dependencies so one runbook can rely on another component's documented availability guarantees.
- [ ] Add rely/guarantee reasoning for concurrent operators and external automation that may change replicas, routes, or queues during execution.
- [ ] Add parameterized temporal logic invariant templates for blast radius, RPO/RTO, data durability, quorum, write availability, and regional isolation.
- [ ] Add waiver syntax with owner, expiry, scope, rationale, and benchmark visibility so suppressed proof obligations remain auditable.
- [ ] Generate property-coverage reports showing which services, databases, queues, alerts, credentials, and regions each invariant touches.

## Phase 4 — Algorithms for bounded verification and explainable counterexamples

- [ ] Specify the bounded model checker as exploration over semantic transition systems with explicit completeness limits, budgets, and inconclusive outcomes.
- [ ] Add configurable exploration strategies: breadth-first, depth-first, randomized bounded, and shortest-counterexample, all exposed through reproducible CLI flags.
- [ ] Add partial-order reduction for independent actions, with trace-equivalence tests proving reduced schedules preserve reported violations.
- [ ] Add dominance pruning and abstract interpretation for monotonic hazards such as drained replicas, paused queues, suppressed alerts, and irrevoked credentials.
- [ ] Add symbolic execution for symbolic replica counts, region sets, traffic weights, and queue depths where concrete enumeration is too expensive.
- [ ] Add counterexample minimization that removes irrelevant independent steps, folds stuttering waits, and preserves the violating temporal property.
- [ ] Add explanation traces with state deltas, causal dependencies, provenance of each field, and source-line links to Markdown and DSL.
- [ ] Add synthesis of missing preconditions from weakest-precondition failures, producing candidate Markdown and JSON patches for operator review.
- [ ] Add runtime verification mode that checks an observed execution log against the modeled runbook trace and reports deviations.
- [ ] Add performance counters for states, transitions, branch factor, reductions, minimized trace length, and proof-obligation outcomes in benchmark reports.

## Phase 5 — Formal exports, mechanized semantics, and proof obligations

- [ ] Add TLA+ exports with concrete state variables for services, queues, databases, alerts, credentials, routes, waits, and dependency scheduling.
- [ ] Add Alloy exports with signatures for entities and bounded assertions matching checker invariants and benchmark labels.
- [ ] Add Apalache/TLC invocation docs that clearly separate generated starter specs, bounded checks, hand-strengthened proofs, and unproved assumptions.
- [ ] Add Coq/Lean-oriented mechanized-semantics notes for the small-step relation, selected action rules, and trusted-code-base boundaries.
- [ ] Generate explicit proof obligations for each invariant, refinement assumption, exporter abstraction, and checker optimization.
- [ ] Add round-trip tests ensuring exporter action comments, property names, state variables, and checker behavior stay synchronized.
- [ ] Add trace-equivalence checks between native checker counterexamples and exported-model counterexamples for representative runbooks.
- [ ] Add formal-methods limitations notes for each exporter explaining abstraction gaps, boundedness, fairness assumptions, and trusted operational facts.
- [ ] Add a glossary of operational, PL, and formal-methods terms for SRE, security, and research readers.

## Phase 6 — Markdown audit, provenance, and responsible operational use

- [ ] Expand prose lint rules for data deletion, manual SQL, backfills, credential handling, customer notification gaps, and unmodeled rollback claims.
- [ ] Make prose lint findings severity-aware with warning, error, audit-only, and responsible-disclosure levels.
- [ ] Add prose lint suppressions that require owner, expiry, reason, and link to a modeled invariant or explicit limitation.
- [ ] Add Markdown autofix suggestions for missing executable `runbook-json` blocks, missing preconditions, and ambiguous operator instructions.
- [ ] Add a Markdown report section mapping prose warnings to exact DSL steps, unmodeled paragraphs, semantic diff results, and dataset provenance.
- [ ] Add causality/provenance tracking for diagnostics: source file, line, schema rule, semantic rule, benchmark label, and historical case-study source.
- [ ] Add report generation that emits Markdown, JSON, SARIF, and JUnit XML from the same check result.
- [ ] Add GitHub PR comment examples showing how operators should review verifier traces, waivers, and counterexample minimization output.
- [ ] Add a `SECURITY.md` workflow explaining how to report real operational vulnerabilities without exposing secrets or exploiting live systems.

## Phase 7 — Datasets, case studies, and benchmark validity over historical/current data

- [ ] Add a benchmark corpus manifest with stable IDs, provenance, expected outcomes, license notes, abstraction level, and validity-threat annotations.
- [ ] Add case-study methodology docs distinguishing exact public text, paraphrase, reconstruction, synthetic modeling, and private-derived anonymized models.
- [ ] Add public-cloud-inspired datasets for Kubernetes, Postgres, Kafka, Redis, object storage, CDN, DNS, and credential-rotation runbooks.
- [ ] Add at least three more current public case studies with reproducible commit/source citations and bounded claims about what was modeled.
- [ ] Add anonymization guidance for industry teams contributing private-derived runbook models without leaking topology, customer, or incident details.
- [ ] Add a dataset contribution checklist covering provenance, license, redaction, expected verifier behavior, and responsible disclosure review.
- [ ] Add per-property precision/recall-style evaluation against labeled synthetic mutants and historical/current case-study labels.
- [ ] Add benchmark trend reports comparing current results to checked-in baselines for safety outcomes, runtime, state counts, and minimized trace length.
- [ ] Add explicit benchmark validity-threat sections covering construct validity, ecological validity, label noise, survivorship bias, and abstraction error.

## Phase 8 — CI, packaging, reproducibility, and practitioner workflow

- [ ] Add a GitHub Actions workflow that runs tests, smoke checks, schema generation, benchmark suites, Markdown audit, and formal-export sanity checks.
- [ ] Add SARIF output for parse, prose, semantics, temporal invariant, and safety findings so GitHub code scanning can ingest results.
- [ ] Add JUnit XML output for CI systems that gate on unsafe runbook changes and inconclusive verification budgets.
- [ ] Add a pre-commit-friendly command that validates only changed runbooks quickly while deferring expensive benchmark checks to CI.
- [ ] Add `frv audit --format json` with recursive filtering by glob, expected safety label, case-study category, and waiver expiry.
- [ ] Add CLI exit-code documentation for safe, unsafe, parse error, schema mismatch, benchmark failure, runtime-verification mismatch, and inconclusive states.
- [ ] Add rich terminal summaries with counts by severity, property, semantic rule, source file, remediation class, and dataset split.
- [ ] Add a release checklist with tests, benchmark regeneration, schema compatibility, exporter snapshots, claims review, and changelog requirements.
- [ ] Add reproducibility scripts that regenerate schemas, reports, benchmark tables, and paper figures from checked-in data only.

## Phase 9 — Testing, robustness, and empirical evidence for claims

- [ ] Add mutation tests or table-driven adversarial tests for action semantics, effect annotations, invariants, and optimizer preservation.
- [ ] Add fuzz tests for parser robustness using only standard-library or optional test dependencies, with minimized failing inputs saved as fixtures.
- [ ] Add golden-file tests for CLI Markdown/JSON/SARIF/JUnit reports, semantic diffs, synthesized preconditions, and formal exports.
- [ ] Add tests for audit behavior on directories containing mixed valid, invalid, safe, unsafe, waived, and inconclusive runbooks.
- [ ] Add tests for line-number diagnostics in JSON and Markdown embedded runbooks, including nested multiline objects.
- [ ] Add performance tests for large dependency DAGs, high replica counts, broad independent step sets, and symbolic parameter ranges.
- [ ] Add regression tests showing partial-order reduction, abstract interpretation, and counterexample minimization preserve violation detection.
- [ ] Add empirical-study scripts for research questions, datasets, metrics, statistical summaries, confidence intervals, and replication packages.
- [ ] Add tables summarizing properties, action semantics, datasets, validity threats, empirical results, and limitations for direct paper reuse.

## Phase 10 — Research synthesis, governance, and adoption

- [ ] Write the paper-ready evaluation plan with research questions, hypotheses, datasets, metrics, threats to validity, and replication instructions.
- [ ] Draft bounded novelty claims: what the tool verifies, what it only audits, what remains heuristic, and what historical/current data can support.
- [ ] Add an industry adoption guide covering CI rollout, runbook authoring conventions, reviewer responsibilities, waiver governance, and incident-response limits.
- [ ] Add tutorials converting prose-only runbooks into executable DSL in small reviewable increments with before/after verifier output.
- [ ] Add examples that intentionally hit each parser, type, effect, invariant, and temporal-property error class with expected diagnostics.
- [ ] Add API documentation for Python library users embedding parser, checker, audit, exporter, benchmark, and empirical-study functionality.
- [ ] Add governance docs for accepting new action semantics, invariants, datasets, optimizations, and exporter claims without weakening soundness boundaries.
- [ ] Add an issue template for proposing new operational hazards with minimal reproducer runbooks, public/private provenance options, and disclosure guidance.
- [ ] Publish the final artifact bundle: tagged code, schemas, datasets, benchmark results, mechanized-semantics notes, paper outline, and reproducibility manifest.
