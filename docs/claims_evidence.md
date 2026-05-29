# Claims and evidence

## What this repo now demonstrates

This repository contains a small, executable verifier for operational runbooks,
a benchmark harness, and a public historical case-study fixture. The historical
fixture reconstructs the GitHub October 21, 2018 MySQL failover incident from
public postmortem facts and checks it as an executable safety model.

## Bounded novelty claim

We are not aware of an existing open-source benchmark that converts public
outage narratives into executable runbook safety models and reproduces the
safety failure with model checking. This is a bounded novelty claim about this
artifact and its public, reproducible benchmark; it is not a universal proof
that no such private or unpublished system exists.

## What is proven

- For each input model, the checker exhaustively explores dependency-respecting
  step orders up to the runbook's `max_depth`.
- Within that finite bound and this DSL's action semantics, reported violations
  are concrete traces that breach named safety properties.
- The benchmark records states explored, terminal traces explored, violations by
  property, expected labels when present, runtime, and pass/fail.

## What is not proven

- This is not a full temporal model checker for arbitrary distributed systems.
- The historical fixture is reconstructed from public facts, not exact original
  runbook text.
- The abstractions do not prove what GitHub's private systems did internally.
- Absence of violations means no modeled property failed within the configured
  bound; it is not proof of operational safety in production.

## Historical source

- GitHub, "October 21 post-incident analysis":
  <https://github.blog/news-insights/company-news/oct21-post-incident-analysis/>

## Reproducibility protocol

From the repository root:

```bash
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format json
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations
```

Expected result: tests pass; benchmark `aggregate.pass` is `true`; the GitHub
case-study runbook reports `precondition` and
`quorum_before_data_loss_action` violations.
