# Governance for benchmarks, waivers, severities, and semantic changes

## Benchmark additions

A new benchmark entry must include provenance, license, abstraction level, expected result labels, responsible-disclosure status, validity threats, semantic features, and reproduction commands. Public-current or public-historical cases must distinguish source facts from independently authored model assumptions.

Review checklist:

1. Source material is public, sanitized, or original.
2. License and attribution are recorded.
3. Expected labels are justified by the modeled artifact.
4. Validity threats include boundedness and data-completeness limits where relevant.
5. `PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown` passes.

## Waiver and suppression policy

- Prose suppressions require owner, expiry, reason, and a linked invariant, waiver, or limitation.
- Expired suppressions should block production-oriented readiness reviews.
- Suppressions remain visible in audit, coverage, readiness, owner scorecards, and benchmark summaries.

## Severity definitions

- `responsible-disclosure`: potentially sensitive public-safety/security issue; handle privately before broad publication.
- `error`: high-risk executable or prose obligation suitable for CI blocking.
- `warning`: meaningful review finding that may be advisory in early adoption.
- `audit-only`: evidence that should remain visible but not block by default, such as an approved limitation.
- `info`: reserved for future low-risk guidance.

## Disclosure handling

If a benchmark or report could reveal a non-public vulnerability, do not publish the details in this repository. Replace it with a sanitized fixture, mark responsible-disclosure status, and keep enough metadata to explain why evidence is withheld.

## Compatibility-breaking semantic changes

Changes to parser validation, action semantics, safety properties, report schemas, benchmark expected labels, or profile exit policies require:

1. README and public docs updates.
2. Benchmark rerun and regenerated checked-in reports when outputs change.
3. Migration notes for changed fields or meanings.
4. Release-criteria review before commit.
