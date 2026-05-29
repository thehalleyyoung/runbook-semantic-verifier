# Migration guide for adopting semantic runbook checks

This guide stages adoption so teams can get useful review signals before committing to full formal-methods workflows.

## Stage 0: Inventory and baseline

- Run `frv scan PATH --format markdown` to rank Markdown/wiki runbooks by high-risk operations vocabulary.
- Record a baseline audit with `frv audit PATH --format json --fail-on none` so existing debt is visible but not yet blocking.
- Document owner, alert, dependency, and replica-count inventories if readiness refinement will be used.

## Stage 1: Syntax and schema validation

- Add `runbook-json` blocks to the highest-priority docs.
- Run `frv validate RUNBOOK.md` in pre-commit or CI.
- Treat parse/schema/entity-reference errors as merge blockers because the model is not executable.

## Stage 2: Advisory bounded checking

- Run `frv check RUNBOOK.md --format json` or `frv audit PATH --format markdown --fail-on none`.
- Use `frv explain PATH finding-NNN --format markdown` to connect each counterexample to source lines, small-step rules, and weakest-precondition hints.
- Label unsupported public-document assumptions rather than presenting them as verified.

## Stage 3: CI gates for new risk

- Use `frv ci-gate CHANGED_PATH --baseline MAIN_PATH` to block newly introduced unsafe deletion, credential, traffic, data-restore, cache, SQL, or replay prose.
- Copy `docs/templates/github-actions-frv.yml` and adapt paths to your repository.
- Use `frv annotate` to publish grouped review comments from the same findings.

## Stage 4: Readiness and ownership

- Run `frv readiness PATH --service SERVICE --region REGION --inventory inventory.json --fail-on none` during incident-prep reviews.
- Run `frv owner-scorecard PATH --owner TEAM --fail-on none` for team-level debt triage.
- Track expired suppressions and stale inventory assumptions as remediation work, not proof failures about live systems.

## Stage 5: Benchmarks and release gates

- Add benchmark entries with provenance, license, abstraction level, responsible-disclosure status, validity threats, expected labels, and reproduction commands.
- Regenerate benchmark evidence with `PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown`.
- Use `docs/release_criteria.md` before publishing semantic or benchmark changes.
