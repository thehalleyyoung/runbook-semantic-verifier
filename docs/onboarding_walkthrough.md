# Onboarding walkthrough: prose audit to readiness report

This walkthrough uses only checked-in public or repository-authored fixtures. It demonstrates the adoption path without claiming live infrastructure safety.

## 1. Start with risky Markdown prose

Run a prose-first audit over the Grafana Tempo-derived public fixture:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format markdown --expect-findings
```

Expected evidence: destructive/data-deletion/backfill prose obligations, queue replay counterexamples, and one explicit limitation suppression.

## 2. Add or inspect the executable model

The fixture embeds one `runbook-json` block. Validate and check it directly:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli validate case_studies/current/grafana_tempo/tempo_runbook_current_impact.md
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/current/grafana_tempo/tempo_runbook_current_impact.md --expect-violations
```

The reported queue hazards are bounded model findings. They mean the modeled replay lacks dedupe/consumer-group proof obligations; they do not assert a live Tempo vulnerability.

## 3. Use CI policy before merging prose changes

```bash
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate case_studies/current/grafana_tempo --format markdown --expect-blocks
PYTHONPATH=src python3 -m runbook_verify.cli annotate case_studies/current/grafana_tempo --format markdown --fail-on none
```

The gate identifies blocking high-risk prose unless an auditable owner/expiry/reason limitation exists. The annotation view is suitable for review comments.

## 4. Fix the modeled counterexample or document the limitation

For an executable fix, add required `requires` conditions, positive consumers, or dedupe/idempotency evidence to the runbook model and compare old/new behavior:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli diff OLD_RUNBOOK.md NEW_RUNBOOK.md --format markdown
```

For a prose-only public excerpt that cannot be fully modeled, add an auditable `frv-suppress` comment with owner, expiry, reason, and a limitation or invariant link. Suppression keeps the claim visible to coverage, readiness, and scorecards.

## 5. Produce readiness and owner views

```bash
PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --service tempo-query --region prod --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli owner-scorecard case_studies/current/grafana_tempo --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli coverage case_studies/current/grafana_tempo --format markdown
```

Use readiness to decide whether the runbook is incident-ready, owner scorecards to assign remediation debt, and coverage to show which modeled entities and source sections each invariant reaches.
