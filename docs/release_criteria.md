# Release criteria

Use this checklist before tagging a release, publishing a paper artifact, or merging changes that alter semantics, schemas, benchmark expectations, or public claims.

## Required checks

- `make verify` passes.
- `PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown` passes and expected benchmark labels remain justified.
- Parser/schema docs, action semantics, README, and claims evidence are updated for any changed field, action, safety property, or output schema.
- `100_STEPS.md` remains local/ignored and still contains exactly 100 checkbox items.

## Schema and semantic drift

- No unchecked parser/schema drift: descriptor changes are reflected in schema, docs, examples, and tests.
- No silent safety-property renames: benchmark expected labels and remediation playbooks are updated together.
- Exporter/report changes include round-trip or renderer tests when public output changes.

## Benchmark and evidence refresh

- Regenerate affected checked-in reports under `reports/` when CLI output changes.
- Update validity threats if a fixture's abstraction, source, or expected result changes.
- Keep responsible-disclosure status and public-source attribution current.

## Migration notes

- Document compatibility-breaking changes in `docs/migration_guide.md` or a release note.
- Explain how adopters can move from baseline audit to validation/checking under the new behavior.
- Provide a rollback or pinning recommendation if output changes may break downstream CI gates.

## Claim review

- Re-read `docs/responsible_claims.md` and `docs/security_privacy.md`.
- Confirm README status counts and claims match actual implemented features.
- Do not claim live infrastructure safety, independent SRE validation, or measured operator time savings unless new evidence explicitly supports it.
