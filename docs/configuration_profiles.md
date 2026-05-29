# Configuration profiles

`frv profiles` lists named policy profiles that make CLI behavior reproducible
across local review, CI, and artifact-evaluation runs. Profiles set default exit
policies only when a command does not pass an explicit `--fail-on`; they do not
change parser validation, action semantics, bounded exploration, or reported
findings.

```bash
PYTHONPATH=src python3 -m runbook_verify.cli profiles --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli profiles --format json
```

## Profiles

- `conservative-production`: fail protected branches on warning-or-higher
  audit/lint findings, CI gate blockers, and not-ready readiness/owner reports.
- `advisory-research`: emit the same audit, CI-gate, readiness, and owner
  evidence without failing on findings. Parse errors and benchmark expectation
  mismatches still fail.
- `documentation-only-audit`: non-blocking Markdown/wiki triage for teams that
  have not yet embedded executable `runbook-json` models.
- `benchmark-reproduction`: record the profile in benchmark JSON/Markdown and
  keep checked-in expected-label pass/fail behavior for public artifact
  reproduction.

## Public-fixture validation

The Grafana Tempo-derived public fixture intentionally contains high-risk prose.
The conservative default blocks the CI gate, while `advisory-research` keeps the
same blocking-finding count but exits successfully for non-blocking review:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate \
  case_studies/current/grafana_tempo --format json

PYTHONPATH=src python3 -m runbook_verify.cli ci-gate \
  case_studies/current/grafana_tempo --format markdown \
  --profile advisory-research
```

Checked-in evidence:

- `reports/current_impact_ci_gate_advisory_profile.md`
- `reports/builtin_benchmark_profile.md`
