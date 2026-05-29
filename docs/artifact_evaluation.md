# Artifact-evaluation package

This file gives reviewers a bounded, reproducible evaluation plan using checked-in fixtures and the Python standard library.

## Environment

- Python: pin artifact-comparison runs to Python 3.11; Python 3.10 or newer is supported for normal use.
- Dependencies: none for JSON/Markdown fixtures; optional `PyYAML` is only needed for YAML inputs and should be pinned by adopting repositories if they enable YAML runbooks.
- Repository root: run all commands from the project root.
- Reproduction budget: the full `make verify` and benchmark commands are expected to complete in seconds on a laptop-scale environment.

## Required commands

```bash
make verify
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format markdown --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --service tempo-query --region prod --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli diff case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md --format markdown
```

## Expected outputs

- `make verify` exits successfully while intentionally expecting violations in unsafe fixtures.
- The built-in benchmark reports `Pass: True`, 11 runbooks, validity-threat categories, workflow baselines, and semantic-diff baselines.
- The Tempo audit reports bounded queue counterexamples, prose obligations, and one auditable limitation suppression.
- The readiness report is `not_ready` for the derived Tempo fixture and lists open hazards/waiver debt; this is expected evidence, not a test failure.
- The GitHub Oct. 21 semantic diff reports quorum-guard remediation evidence for the reconstructed public model.

## Dataset metadata

- Synthetic examples are original MIT-licensed regression fixtures.
- The GitHub Oct. 21 fixture is reconstructed from public post-incident facts, not private runbook text.
- Grafana Tempo, dnsswitch, and Redis case studies are derived from public documentation with bounded, independently authored models.
- Responsible-claims and validity-threat details live in `docs/claims_evidence.md` and `benchmarks/builtin.json`.

## Optional regenerated artifacts

Use `python3 scripts/reproduce_benchmarks.py` to refresh checked-in benchmark reports. When a report changes, review whether the semantic change is expected and update README, claims evidence, and release criteria notes accordingly.
