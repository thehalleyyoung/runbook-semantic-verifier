# 100 steps toward semantics-grounded runbook verification

This roadmap treats runbooks as executable operational programs: Markdown/wiki prose, embedded DSL blocks, source locations, service metadata, and incident assumptions all become semantic objects. Every item below pairs a formal-methods or program-semantics advance with an immediate operator-facing artifact such as a CI gate, audit report, remediation trace, benchmark row, or adoption workflow.

## Phase 1 — Preserved foundation with explicit semantic contracts

- [x] Preserve a repo-specific 100-step roadmap, now organized around executable semantics, measurable artifacts, datasets, and practical SRE adoption outcomes.
- [x] Expose a machine-readable JSON Schema through `frv schema`, giving the DSL a stable syntactic contract that editors, registries, and CI can validate before semantic checking.
- [x] Harden parser validation for numeric bounds (`max_depth`, waits, replicas, queues, alert suppression), making the state space finite enough for bounded semantics and immediately catching unsafe documentation values.
- [x] Reject cyclic step dependency graphs at parse time, enforcing an executable scheduling relation and failing impossible runbooks with actionable diagnostics.
- [x] Document the schema command and validation contract in the README and regression tests so users can adopt syntax checks without understanding the checker internals.
- [x] Publish `docs/schema/runbook.schema.json` as a checked-in canonical artifact, creating a reproducible interface between DSL syntax, generated docs, and CI integrations.
- [x] Add schema examples covering supported top-level fields, giving operators copyable fixtures and researchers concrete syntax for semantic examples.
- [x] Split action parameter validation into reusable typed field descriptors shared by parser, schema generation, docs, and exporters, reducing divergence between implementation and semantics.
- [x] Validate that every service `min_available` target is achievable from declared replicas, turning an availability invariant into an immediate preflight error.
- [x] Validate duplicate replica ids and generated scale-operation entity collisions, preserving a well-formed entity universe for semantic states and preventing ambiguous audit output.
- [x] Validate consistency between deployment entries and service deployment fields, exposing provenance mismatches that would otherwise weaken runbook-to-model refinement claims.
- [x] Add `frv validate` for parse/schema/entity/dependency checks without state-space exploration, giving teams a fast first CI gate for dangerous ops docs.
- [x] Add structured JSON diagnostics for parse errors with path, line, field, severity, and remediation text, making syntax obligations consumable by editors and pipelines.
- [x] Add a schema compatibility policy covering versioning, deprecations, and migrations, supporting longitudinal benchmarks and industry adoption without silent semantic drift.
- [x] Introduce an explicit action-semantics reference table generated from tests and implementation metadata, beginning the link between action rules and user-visible documentation.
- [x] Add first-class semantics for traffic shifting, load balancer draining, and weighted routing during regional failover, enabling practical checks of a common high-risk incident workflow.

## Phase 2 — Core formal objects connected to CLI evidence

- [ ] Define the mathematical objects for syntax, entity universe, stores, traces, hazards, observations, diagnostics, waivers, and benchmark labels, and map each object to CLI JSON fields.
- [ ] Specify a small-step operational semantics for dependency scheduling, action execution, waits, failures, nondeterministic operator choices, and bounded exploration budgets, then mirror rule names in traces.
- [ ] Define denotational state-transformer semantics for every action descriptor so parser metadata, schema text, checker transitions, and exporter comments share one vocabulary.
- [ ] Express safety checks as Hoare triples over preconditions, action effects, and postconditions, and surface failed triples as `frv check` findings with concrete runbook line numbers.
- [ ] Document weakest-precondition templates for missing guards such as backups, quorum, alerts, ownership, freeze windows, rollback paths, and customer notification prerequisites.
- [ ] Extend Markdown source mapping to multiline DSL blocks, nested preconditions, and effect diagnostics so formal counterexamples point to the prose operators must edit.
- [x] Add first-class semantics for cache flush, cache warmup, stale-read risk, and cold-start capacity, with safe and unsafe Markdown examples.
- [ ] Add first-class semantics for object-storage replication, bucket write freezes, restore-from-snapshot actions, and RPO/RTO obligations.
- [x] Add first-class semantics for message replay, dead-letter queues, deduplication keys, and consumer-group rebalancing, with duplicate-processing benchmarks.
- [x] Add first-class semantics for DNS changes, TTL wait windows, health-check convergence, and split-brain routing hazards, producing operator-readable traces.

## Phase 3 — Types, effects, contracts, and semantic refinement

- [ ] Introduce a lightweight type system for services, replicas, regions, traffic weights, queues, databases, credentials, alerts, durations, and ownership metadata, with schema-preserving migrations.
- [ ] Add action effect types for deletion, credential revocation, manual SQL, traffic drains, queue replay, customer-visible degradation, and irreversible state changes.
- [ ] Require effect annotations for idempotency, reversibility, retry safety, blast radius, and expected user impact, and warn when prose encourages unsafe retries.
- [ ] Define refinement from Markdown prose to executable DSL blocks, reporting unmapped operational claims as audit findings rather than treating them as verified.
- [ ] Add semantic diffing for runbook revisions, classifying changes as behavior-preserving, proof-obligation-strengthening, assumption-weakening, or safety-relevant.
- [ ] Add assume-guarantee contracts for service dependencies so one runbook can rely on another component's documented availability, durability, or recovery guarantees.
- [ ] Add rely/guarantee reasoning for concurrent operators and automation that may change replicas, routes, queues, alerts, or credentials during execution.
- [ ] Add temporal-logic invariant templates for blast radius, RPO/RTO, data durability, quorum, write availability, regional isolation, alert visibility, and rollback readiness.
- [ ] Add waiver syntax with owner, expiry, scope, rationale, linked invariant, and benchmark visibility so suppressed obligations remain auditable.
- [x] Generate property-coverage reports showing which services, databases, queues, alerts, credentials, owners, regions, and Markdown sections each invariant covers.

## Phase 4 — Verification algorithms with explainable counterexamples

- [ ] Specify bounded model checking as exploration of semantic transition systems with explicit depth, breadth, fairness, timeout, and inconclusive-result semantics.
- [ ] Add reproducible exploration strategies: breadth-first, depth-first, randomized bounded, shortest-counterexample, and seeded chaos-style schedules.
- [ ] Implement partial-order reduction for independent actions, with trace-equivalence tests showing reduced schedules preserve reported violations.
- [ ] Add dominance pruning and abstract interpretation for monotone hazards such as drained replicas, paused queues, suppressed alerts, frozen writes, and unrecovered credentials.
- [ ] Add symbolic execution for symbolic replica counts, region sets, traffic weights, queue depths, and wait intervals where concrete enumeration is too expensive.
- [ ] Add counterexample minimization that removes irrelevant independent steps, folds stuttering waits, preserves temporal violation witnesses, and reports the minimized proof obligation.
- [ ] Emit explanation traces with state deltas, causal dependencies, action rule names, provenance for every field, and source-line links to Markdown and DSL.
- [ ] Synthesize missing preconditions from weakest-precondition failures, producing candidate Markdown text and JSON patches for operator review.
- [ ] Add runtime-verification mode that checks observed execution logs or chatops events against modeled traces and reports deviations without claiming full infrastructure proof.
- [x] Add performance counters for states, transitions, branch factor, reductions, minimized trace length, symbolic splits, and proof-obligation outcomes in benchmark reports.

## Phase 5 — Formal exports and mechanizable semantics

- [ ] Add TLA+ exports with concrete state variables for services, queues, databases, alerts, credentials, routes, waits, ownership, and dependency scheduling.
- [ ] Add Alloy exports with signatures and assertions for bounded entity relations, dependency graphs, waivers, and invariant labels.
- [ ] Add Apalache/TLC invocation docs that separate generated starter specs, bounded checks, hand-strengthened proofs, and unproved operational assumptions.
- [ ] Add Coq/Lean-oriented mechanized-semantics notes for the small-step relation, selected action rules, state-transformer denotations, and trusted-code-base boundaries.
- [ ] Generate explicit proof obligations for invariants, refinement assumptions, exporter abstractions, checker optimizations, and runtime-verification monitors.
- [ ] Add round-trip tests ensuring exporter names, action comments, state variables, property identifiers, and native checker behavior stay synchronized.
- [ ] Add trace-equivalence checks between native counterexamples and exported-model counterexamples for representative failover, queue, data, and credential runbooks.
- [ ] Add formal-methods limitation notes for each exporter covering abstraction gaps, boundedness, fairness, environment assumptions, and trusted operational facts.
- [ ] Add exporter conformance fixtures proving that generated models preserve native action names, enabledness conditions, and safety-property labels for each benchmark family.
- [ ] Add a glossary connecting SRE, security, PL, and formal-methods terms so adoption material and paper text use consistent language.

## Phase 6 — Markdown/wiki audit and CI gates for operations docs

- [x] Expand prose lint rules for data deletion, manual SQL, backfills, credential handling, customer notification gaps, rollback ambiguity, and unmodeled escalation paths.
- [x] Make prose lint findings severity-aware (`info`, `warning`, `error`, `audit-only`, `responsible-disclosure`) with CI policies that teams can tune.
- [ ] Add prose suppressions requiring owner, expiry, reason, and link to a modeled invariant, waiver, or explicit limitation.
- [ ] Add Markdown autofix suggestions for missing executable blocks, stale owners, missing preconditions, ambiguous operator instructions, and unsafe copy-paste shell snippets.
- [x] Add wiki/repository scanning that discovers runbook-like Markdown files, ranks them by dangerous-effect vocabulary, and recommends which documents need executable models first.
- [ ] Add CI gates for high-risk operations docs that block newly introduced unsafe deletion, credential, traffic, or data-restoration instructions without owner-approved waivers.
- [ ] Add pull-request annotations that group findings by semantic obligation and source span so reviewers see why a prose change is blocked.
- [ ] Add stale-precondition detection by comparing runbook owners, service names, alert names, replica counts, and dependency names against configured inventories.
- [ ] Add incident-readiness reports summarizing unverified claims, missing rollback steps, expired waivers, stale preconditions, uncovered services, and highest-risk counterexamples.
- [ ] Add service-owner scorecards that aggregate verification status, audit severity, waiver debt, benchmark regressions, and freshness for each team.
- [x] Add SARIF, JUnit, Markdown, and JSON report outputs so GitHub code scanning, CI dashboards, and SRE review templates can consume the same semantic results.

## Phase 7 — Benchmarks, historical cases, and validity threats

- [x] Define a public benchmark schema with provenance, license, abstraction level, expected result, responsible-disclosure status, validity threats, and semantic feature coverage.
- [ ] Add historical outage reproductions as bounded semantic models that clearly distinguish public facts, reconstructed assumptions, and synthetic mutants.
- [ ] Add current operational case studies for failover, queue replay, data restore, credential rotation, DNS migration, and cache incidents using public or sanitized data.
- [ ] Add synthetic mutation operators for missing preconditions, reordered steps, stale owners, unsafe retries, insufficient waits, underprovisioned replicas, and invalid waivers.
- [ ] Report benchmark validity threats including label uncertainty, abstraction bias, public-data incompleteness, bounded search limits, and survivor bias in available runbooks.
- [ ] Add reproducible benchmark scripts that publish runtime, state counts, findings, minimization quality, false-positive reviews, and regression deltas.
- [ ] Add benchmark baselines comparing schema-only validation, prose linting, bounded checking, type/effect checking, semantic diffing, and combined workflows.
- [ ] Add a benchmark contribution guide with anonymization, licensing, redaction, disclosure review, and minimum metadata requirements.
- [ ] Add longitudinal evaluation over repository history to measure whether semantic gates would have caught unsafe changes before merge.
- [ ] Add oracle-review protocol where SRE reviewers label benchmark findings as true hazard, useful warning, false positive, or unsupported claim.
- [ ] Add adoption-oriented benchmark summaries translating formal findings into operator time saved, risk classes detected, and remediation actions taken.

## Phase 8 — Developer and SRE workflows that ship value early

- [x] Add `frv audit` workflow that scans Markdown/wiki runbooks, emits ranked findings, and links each prose issue to a semantic obligation or explicit limitation.
- [x] Add `frv explain` for a finding id, returning the relevant small-step rule, state delta, source lines, weakest-precondition hint, and remediation examples.
- [x] Add `frv diff old new` for semantic change review in pull requests, highlighting changed effects, assumptions, invariants, waivers, and reachable counterexamples.
- [x] Add `frv readiness` to produce incident-readiness reports for a service, region, or repository path using validation, audit, benchmark, and freshness signals.
- [x] Add `frv owner-scorecard` to generate team-facing summaries of verified runbooks, open hazards, stale assumptions, waiver debt, and remediation history.
- [ ] Add pre-commit and GitHub Actions templates for fast validation on every edit and deeper bounded checks on protected branches.
- [ ] Add remediation playbooks for common counterexamples: insufficient replicas, missing backup, skipped alert re-enable, premature DNS cutover, unsafe replay, and stale owner.
- [ ] Add editor-friendly JSON diagnostic examples and documentation so language servers or GitHub annotations can present semantic findings inline.
- [ ] Add configuration profiles for conservative production gates, advisory research mode, documentation-only audits, and benchmark reproduction.
- [ ] Add onboarding examples that take one risky Markdown runbook from prose audit to executable model, CI gate, counterexample fix, and readiness report.
- [ ] Add usability tests with SRE-style tasks measuring whether minimized traces and generated preconditions help users fix runbooks faster than raw model-checker output.
- [ ] Add migration guides that show teams how to start with Markdown audit, then validation, then bounded verification, without requiring full formal-methods expertise.

## Phase 9 — Responsible novelty, governance, and evidence quality

- [ ] Write a responsible-claims guide that distinguishes checked model safety, bounded counterexample absence, prose audit coverage, runtime conformance, and live infrastructure safety.
- [ ] Add governance for benchmark additions, waiver policies, severity definitions, disclosure handling, and compatibility-breaking semantic changes.
- [ ] Add artifact-evaluation packaging with pinned dependencies, exact commands, expected outputs, dataset metadata, and reproduction budgets.
- [ ] Add paper-ready tables for feature coverage, benchmark results, algorithm ablations, counterexample usefulness, and adoption workflows.
- [ ] Add related-work notes tying the implementation to operational semantics, abstract interpretation, model checking, runtime verification, program logics, and SRE tooling.
- [ ] Add negative results and limitations for cases where prose ambiguity, missing inventories, nondeterministic cloud behavior, or bounded search prevents strong claims.
- [ ] Add security and privacy guidance for handling incident runbooks, credentials, redactions, responsible disclosure, and generated counterexample traces.
- [ ] Add an evidence ledger connecting every headline claim to tests, benchmarks, case studies, user workflows, or explicit assumptions.
- [ ] Add release criteria requiring no unchecked schema drift, documented semantic changes, benchmark reruns, and updated migration notes.
- [ ] Publish a final artifact bundle and paper outline showing how the tool advances formal-methods practice while immediately improving operational runbook review.
