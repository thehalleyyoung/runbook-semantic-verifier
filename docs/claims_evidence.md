# Claims and evidence

## What this repo now demonstrates

This repository contains a small, executable verifier for operational runbooks,
a Markdown prose linter, a benchmark harness, a public historical case-study
fixture with a semantic remediation diff, and a current public-documentation
case study. The CLI also includes incident-readiness, owner-scorecard, and
property-coverage reports. The historical fixture reconstructs the GitHub
October 21, 2018 MySQL failover incident from public postmortem facts. The
current case study analyzes short attributed excerpts from Grafana Tempo's
public runbook and checks a derived executable safety model.

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
  when the file lacks matching executable actions/preconditions/effects.
- The benchmark records states explored, terminal traces explored, violations by
  property, prose findings by rule, expected labels when present, runtime, and
  pass/fail.
- The semantic diff reports model-level changes, assumption weakenings,
  proof-obligation deltas, and introduced/resolved/persisting counterexample
  traces between two bounded executable runbook models.
- The readiness report aggregates validation, bounded checker, Markdown audit,
  service/region coverage, rollback/restore coverage, source-freshness, and
  proof-obligation signals for a repository path or scoped service/region.
- The owner scorecard groups bounded semantic counterexamples, blocking prose
  obligations, stale assumptions, declared waiver debt, proof-obligation
  failures, and remediation history by checked-in owner metadata.
- The coverage report maps each current invariant/proof-obligation template to
  modeled services, databases, queues, alerts, credentials (none in the current
  DSL), owners, regions, source steps, and Markdown sections; unverified prose
  obligations are reported as coverage gaps, not as verified properties.

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
- Checked-in evidence:
  - `case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md`
  - `reports/github_oct21_semantic_diff.json`
  - `reports/github_oct21_semantic_diff.md`
  - `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md`
  - `reports/current_impact.json`
  - `reports/current_impact.md`
  - `reports/current_impact_lint.json`
  - `reports/current_impact_lint.md`
  - `reports/current_impact_readiness.json`
  - `reports/current_impact_readiness.md`
  - `reports/current_impact_owner_scorecard.json`
  - `reports/current_impact_owner_scorecard.md`
  - `reports/current_impact_coverage.json`
  - `reports/current_impact_coverage.md`

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
PYTHONPATH=src python3 -m runbook_verify.cli lint-markdown case_studies/current/grafana_tempo --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --service tempo-query --region prod --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli owner-scorecard case_studies/current/grafana_tempo --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli coverage case_studies/current/grafana_tempo --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli diff case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md --format markdown
```

Expected result: tests pass; benchmark `aggregate.pass` is `true`; the GitHub
case-study runbook reports `precondition` and
`quorum_before_data_loss_action` violations; the current-impact benchmark reports
`destructive-delete-needs-targeting`, `no_queue_pause_without_drain_plan`, and
`no_paused_queue_with_backlog`; the GitHub semantic diff reports zero introduced
counterexamples and resolves the modeled `precondition` and
`quorum_before_data_loss_action` traces. The current-impact readiness report is
`not_ready` with two bounded queue counterexamples, three unverified prose
claims, no stale preconditions as of 2026-05-29, and aggregated
proof-obligation counters.
The current-impact owner scorecard reports one checked-in fixture owner,
`grafana-tempo-public-fixture`, with zero verified runbooks, two bounded queue
counterexamples, one blocking prose obligation, no stale assumptions, and no
waiver debt as of 2026-05-29.
The current-impact coverage report maps five invariant/proof-obligation
templates to the fixture's `tempo-query` service, `tenant-index-fallback-scan`
queue, `prod` region, owner metadata, and executable Markdown section, and
keeps three destructive-data prose obligations as explicit coverage gaps.
