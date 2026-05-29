# Claims and evidence

## What this repo now demonstrates

This repository contains a small, executable verifier for operational runbooks,
a Markdown prose linter, a benchmark harness, a public historical case-study
fixture with a semantic remediation diff, and a current public-documentation
case study. The CLI also includes repository/wiki runbook-priority scanning,
small-step semantic rule traces, formal object maps, incident-readiness, owner-scorecard, property-coverage reports, and auditable
prose suppressions with owner/expiry/reason/limitation metadata. Markdown
findings also include manual autofix suggestions for missing executable models,
missing preconditions/effects, stale owner placeholders, ambiguous operator
instructions, and unsafe copy-paste shell snippets. `frv ci-gate` turns those
findings into a baseline-aware CI policy for newly introduced high-risk deletion,
credential, traffic/capacity, failover, SQL, cache, and data-restoration prose.
`frv annotate` emits pull-request annotations grouped by semantic obligation and
source span, including small-step rule names for executable counterexamples and
prose-audit rule names for Markdown findings. Named configuration profiles make
conservative production, advisory research,
documentation-only, and benchmark-reproduction exit policies reproducible without
changing parser validation, action semantics, bounded exploration, or reported
findings. Readiness reports can also compare scoped runbooks against a configured
JSON inventory of current service names, owner identifiers, alert identifiers,
dependency names, and replica counts, reporting stale assumptions as
`inventory_refinement_precondition` obligations.
The DSL also models queue
replay/DLQ/consumer-group semantics, DNS cutovers with TTL and health-check
convergence obligations, and cache flush/warmup/cold-start/capacity semantics.
Action descriptors now carry generated denotational state-transformer text, and
semantic findings carry Hoare triples, weakest-precondition hints, source lines,
causal dependencies, and state deltas in `frv check --format json`.
The historical fixture reconstructs the GitHub
October 21, 2018 MySQL failover incident from public postmortem facts. The
current case studies analyze short attributed excerpts from Grafana Tempo's
public runbook, a bounded DNS failover pattern derived from public `dnsswitch`
guidance, and a bounded Redis cache-flush mutant derived from a public Redis
runbook template.
Benchmark evidence now includes categorized validity threats, workflow-baseline
comparisons, semantic-diff remediation baselines, oracle-review label metadata,
reproducible report-generation commands, and adoption-oriented risk/action
summaries.

## Bounded novelty claim

We are not aware, as of 2026-05-29, of an existing open-source benchmark that
combines (1) public outage narratives, (2) current public runbook prose, (3)
executable runbook safety models, (4) static prose checks for dangerous
unmodeled operations, and (5) checked-in JSON/Markdown findings with exact source
metadata. This is a bounded novelty claim about this artifact and the search
protocol below; it is not a universal proof that no private, unpublished, or
differently named system exists.

## What is proven

- For each input model, the checker exhaustively explores dependency-respecting
  step orders up to the runbook's `max_depth`.
- Within that finite bound and this DSL's action semantics, reported violations
  are concrete traces that breach named safety properties.
- The parser rejects unsupported actions, unknown parameters, unknown condition
  kinds, duplicate step ids, missing dependencies, and references to unknown
  modeled entities before state-space exploration.
- The Markdown linter deterministically flags selected dangerous prose patterns
  when the file lacks matching executable actions/preconditions/effects, and
  refuses to silently hide prose findings unless a suppression has owner,
  expiry, reason, and invariant/waiver/limitation metadata.
- Markdown lint/audit JSON includes `autofix_suggestions` for reviewable edits.
  These suggestions point to executable blocks, Hoare-style precondition/effect
  snippets, owner metadata, measurable operator guards, or scoped shell command
  templates; they are not applied automatically and do not prove the suggested
  repair is operationally correct without review.
- The benchmark records states explored, terminal traces explored, violations by
  property, prose findings by rule, semantic rule counters, expected labels when
  present, categorized validity threats, workflow-baseline comparisons
  (schema-only validation, prose linting, bounded checking, type/effect checking,
  configured semantic diffing, and combined workflow), adoption summaries,
  runtime, and pass/fail.
- Benchmark semantic-diff baselines execute the same `frv diff` logic used for PR
  review and compare expected introduced/resolved counterexample counts. The
  built-in suite currently uses this for the bounded GitHub Oct. 21
  quorum-guard remediation pair.
- Oracle-review metadata defines the allowed review labels (`true_hazard`,
  `useful_warning`, `false_positive`, and `unsupported_claim`) but does not claim
  an independent review unless a benchmark entry explicitly records one.
- The semantic diff reports model-level changes, assumption weakenings,
  proof-obligation deltas, and introduced/resolved/persisting counterexample
  traces between two bounded executable runbook models.
- The formal-object report maps syntax, entity universe, immutable store,
  bounded trace set, hazards, prose observations, diagnostics, waivers, and
  benchmark labels to concrete CLI JSON fields. This is an evidence ledger for
  what the tool reasons about; it does not add proof beyond parser, linter, and
  checker results.
- The readiness report aggregates validation, bounded checker, Markdown audit,
  service/region coverage, rollback/restore coverage, source-freshness, and
  proof-obligation signals for a repository path or scoped service/region. With
  `--inventory`, it additionally checks that modeled services, owner names,
  alerts, dependencies, and replica counts refine a configured inventory fixture.
- The owner scorecard groups bounded semantic counterexamples, blocking prose
  obligations, stale assumptions, declared waiver debt, proof-obligation
  failures, and remediation history by checked-in owner metadata.
- The repository scan ranks Markdown runbook-like files by dangerous-effect
  vocabulary, uncovered semantic obligations, and whether executable models are
  present, so teams can prioritize prose-to-DSL refinement before stronger
  checking claims.
- The CI gate compares high-risk Markdown findings against an optional baseline
  and blocks only new unsafe operations prose unless the finding is represented
  by an auditable owner/expiry/reason waiver or explicit limitation. It is a
  document-review gate, not proof that waived operations are safe.
- Pull-request annotations are deterministic projections of the audit/check
  findings. They group findings by semantic obligation and exact modeled source
  span, then render GitHub Actions commands, JSON, or Markdown; they do not add
  new proof beyond the underlying bounded checker and prose audit.
- Small-step traces map each executable counterexample to the scheduling,
  operator-choice, action/wait, failure, postcondition, and bounded-exploration
  rule names documented in `docs/small_step_semantics.md`; they are explanatory
  witnesses for the bounded DSL execution, not a stronger proof system.
- Hoare triples and weakest-precondition templates are generated from
  `src/runbook_verify/contracts.py` and documented in
  `docs/weakest_preconditions.md`. They explain the bounded proof obligation
  that failed for a DSL trace; they are not machine-checked program-logic proofs
  over production infrastructure.
- `frv check --format json` emits explanation records with `semantic_trace`,
  `state_delta`, `causal_dependencies`, `source`, `hoare_triple`, and
  `weakest_precondition_hint` for editor/review integration. The data is derived
  from the same bounded checker result.
- Configuration profiles set CLI default exit policies for audit, lint, CI gate,
  readiness, owner-scorecard, and benchmark reproduction workflows. Explicit
  `--fail-on` values override profile defaults, and profiles do not suppress or
  rewrite findings.
- The coverage report maps each current invariant/proof-obligation template to
  modeled services, databases, queues, alerts, DNS records, credentials (none in the current
  DSL), owners, regions, source steps, and Markdown sections; unverified prose
  obligations are reported as coverage gaps, not as verified properties.
- Queue replay, DLQ draining, deduplication guards, and consumer-group
  rebalancing are checked as bounded small-step transitions with concrete
  duplicate-processing and backlog counterexamples.
- Cache write freezes, destructive flushes, warmup thresholds, capacity limits,
  and stale-read risk are checked as bounded small-step transitions with
  concrete cold-start and over-capacity counterexamples.
- Inventory-refinement findings are configuration checks over provided inventory
  data, not live discovery. A mismatch means the artifact and configured
  inventory disagree; it does not prove the external service catalog is complete
  or current.

## Auditable prose suppression evidence

- Command:
  `PYTHONPATH=src python3 -m runbook_verify.cli lint-markdown case_studies/current/grafana_tempo --format markdown --expect-findings`
- Expected result: `reports/current_impact_lint.md` includes
  `prose-suppression-applied` for the public Tempo ring-forget excerpt, with
  owner, expiry, reason, and `limitation:ring-forget-targeting` metadata.
  It also includes Markdown autofix-suggestion summaries for the unsuppressed
  destructive-data/backfill findings; `reports/current_impact_lint.json` carries
  the full suggestion payloads.
  Invalid suppressions are tested in `tests/test_markdown_lint.py` and produce
  `invalid-prose-suppression` without hiding the original finding.
- Claim supported: the Markdown audit can represent an explicit
  waiver/limitation contract for a prose-derived semantic obligation without
  silently suppressing evidence.
- Bound: suppression metadata is syntactically checked and reported; downstream
  organizations still decide whether a linked invariant, waiver, or limitation
  is acceptable policy.

## What is not proven

- This is not a full temporal model checker for arbitrary distributed systems.
- The historical fixture is reconstructed from public facts, not exact original
  runbook text.
- The GitHub quorum-guard remediation fixture is a bounded counterfactual model
  for verifier evaluation, not a claim about GitHub's internal procedures.
- The abstractions do not prove what GitHub's private systems did internally.
- Absence of violations means no modeled property failed within the configured
  bound; it is not proof of operational safety in production.
- The Grafana Tempo case study is a defensive documentation analysis. It reports
  potential operational safety gaps in public prose/modeling, not an undisclosed
  vulnerability in Grafana Labs, Tempo, or any live service.
- The `dnsswitch` DNS case study is a defensive bounded reconstruction of a
  documented failover pattern, not a claim about a live deployment.
- The Redis cache-flush case study is a defensive bounded mutant derived from a
  public runbook template, not a claim about a live deployment.
- Adoption summaries are reviewer triage metadata. They do not prove operator
  time saved unless a benchmark entry separately records measured user-study or
  oracle-review evidence.
- The prior-art search cannot prove universal nonexistence; it only documents
  the public search performed for this repository.

## Historical source

- GitHub, "October 21 post-incident analysis":
  <https://github.blog/news-insights/company-news/oct21-post-incident-analysis/>

## Current public source

- Grafana Tempo `operations/tempo-mixin/runbook.md`:
  <https://raw.githubusercontent.com/grafana/tempo/main/operations/tempo-mixin/runbook.md>
- Commit observed with GitHub API on 2026-05-29:
  `ef18cc176e44dea795543f50cb2341f5ea9e7827`
- Source repository license text observed: AGPL-3.0.
- Hotpirsch `dnsswitch` public DNS failover guidance:
  <https://github.com/Hotpirsch/dnsswitch>
- OneUptime public Redis operations runbook template:
  <https://raw.githubusercontent.com/OneUptime/blog/master/posts/2026-03-31-redis-operations-runbook/README.md>
- Checked-in evidence:
  - `case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md`
  - `reports/github_oct21_semantic_diff.json`
  - `reports/github_oct21_semantic_diff.md`
  - `reports/github_oct21_check_explanations.json`
  - `reports/github_oct21_check_explanations.md`
  - `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`
  - `reports/current_impact.json`
  - `reports/current_impact.md`
  - `reports/current_impact_lint.json`
  - `reports/current_impact_lint.md`
  - `reports/current_impact_ci_gate.json`
  - `reports/current_impact_ci_gate.md`
  - `reports/current_impact_ci_gate_advisory_profile.md`
  - `reports/current_impact_annotations.json`
  - `reports/current_impact_annotations.md`
  - `reports/current_impact_annotations.github.txt`
  - `reports/current_impact_scan.json`
  - `reports/current_impact_scan.md`
  - `reports/current_impact_formal_objects.json`
  - `reports/current_impact_formal_objects.md`
  - `reports/current_impact_readiness.json`
  - `reports/current_impact_readiness.md`
  - `case_studies/current/grafana_tempo/tempo_inventory_current_impact.json`
  - `reports/current_impact_inventory_readiness.json`
  - `reports/current_impact_inventory_readiness.md`
  - `reports/current_impact_owner_scorecard.json`
  - `reports/current_impact_owner_scorecard.md`
  - `reports/current_impact_coverage.json`
  - `reports/current_impact_coverage.md`
  - `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md`
  - `reports/dnsswitch_dns_audit.json`
  - `reports/dnsswitch_dns_audit.md`
  - `reports/dnsswitch_dns_coverage.md`
  - `case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md`
  - `reports/redis_cache_flush_audit.json`
  - `reports/redis_cache_flush_audit.md`
  - `reports/redis_cache_flush_coverage.json`
  - `reports/redis_cache_flush_coverage.md`
  - `reports/builtin_benchmark.md`
  - `reports/builtin_benchmark_profile.md`
  - `reports/benchmark_reproduction_manifest.json`
  - `reports/current_impact_benchmark.md`
  - `docs/benchmark_contribution.md`
  - `docs/benchmark_reproducibility.md`
  - `docs/oracle_review_protocol.md`

## Prior-art search protocol for bounded novelty

The bounded claim above was checked using public web/GitHub search phrases such
as:

- `"runbook" "model checking" "benchmark"`
- `"incident runbook" "formal verification"`
- `"runbook-json" "safety" "benchmark"`
- `"public runbook" "prose linter" "precondition"`
- `"outage narrative" "executable runbook"`

No result found during this session matched this repository's combination of
public-source executable runbook models, deterministic safety checker, prose
linter, benchmark labels, generated reports, and precise source metadata. This
is evidence for the bounded claim only.

## Reproducibility protocol

From the repository root:

```bash
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/current_impact.json --format json
make benchmark-reproduce
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli lint-markdown case_studies/current/grafana_tempo --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate case_studies/current/grafana_tempo --format markdown --expect-blocks
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate case_studies/current/grafana_tempo --format markdown --profile advisory-research
PYTHONPATH=src python3 -m runbook_verify.cli annotate case_studies/current/grafana_tempo --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --service tempo-query --region prod --inventory case_studies/current/grafana_tempo/tempo_inventory_current_impact.json --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli profiles --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli scan case_studies/current/grafana_tempo --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --service tempo-query --region prod --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli owner-scorecard case_studies/current/grafana_tempo --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli coverage case_studies/current/grafana_tempo --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/redis_cache_flush --format markdown --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli coverage case_studies/current/redis_cache_flush --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli diff case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown --profile benchmark-reproduction
```

Expected result: tests pass; benchmark `aggregate.pass` is `true` and includes
`aggregate.performance_counters.semantic_rule_counts`; the GitHub
case-study runbook reports `precondition` and
`quorum_before_data_loss_action` violations; the current-impact benchmark reports
`destructive-delete-needs-targeting`, `data-deletion-needs-restore-precondition`,
`backfill-needs-queue-capacity`, `no_replay_without_dedupe`,
`no_duplicate_processing_risk`, `no_rebalance_to_zero_consumers`,
`queue_backlog_requires_consumers`, and `no_unstable_consumer_group_with_backlog`;
the GitHub semantic diff reports zero introduced counterexamples and resolves the
modeled `precondition` and `quorum_before_data_loss_action` traces. The
current-impact readiness report is `not_ready` with six bounded queue
counterexamples, three unsuppressed prose claims, one audited explicit-limitation
suppression, no stale preconditions as of 2026-05-29, and aggregated
proof-obligation counters.
The current-impact owner scorecard reports one checked-in fixture owner,
`grafana-tempo-public-fixture`, with zero verified runbooks, six bounded queue
counterexamples, destructive-data/backfill prose obligations, one audited prose
suppression, no stale assumptions, and no waiver debt as of 2026-05-29.
The current-impact repository scan ranks the Grafana Tempo-derived fixture as
`critical` with score 52 from destructive-delete, data-deletion, and
backfill/replay dangerous-effect vocabulary plus uncovered blast-radius,
restore-path, queue, consumer, deduplication, and explicit-limitation
obligations. The
current-impact CI gate reports two blocking high-risk prose findings for the
unsuppressed destructive/data-deletion line and one owner-approved waiver for the
ring-forget excerpt retained as an explicit limitation. Under
`--profile advisory-research`, the same Tempo-derived CI-gate findings are
reported but the command exits successfully for non-blocking review.
The
current-impact coverage report maps eleven invariant/proof-obligation
templates to the fixture's `tempo-query` service, `tenant-index-fallback-scan`
queue, `prod` region, owner metadata, and executable Markdown section, and
keeps three destructive-data/backfill prose obligations plus one explicit
suppression as coverage gaps.
The DNS case-study check reports bounded `dns_health_check_converged_before_cutover`,
`dns_requires_regional_capacity`, `dns_no_split_brain_during_ttl`, and
`dns_ttl_elapsed_before_finalize` counterexamples.
The Redis cache-flush case-study audit reports bounded
`cache_flush_requires_write_freeze`, `cache_warmup_before_traffic`,
`cache_warmup_within_capacity`, and `no_stale_reads_after_cache_flush`
counterexamples plus cache-flush prose obligations for write-freeze, warmup, and
capacity.
