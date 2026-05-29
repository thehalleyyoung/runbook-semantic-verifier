# Benchmark contribution guide

Public benchmark entries must make evidence limits reviewable before a result is treated as verifier evidence.

Minimum metadata:

- provenance kind and source URL/commit/date when public material is used;
- license status and notes explaining copied text vs independently authored model text;
- abstraction level (`toy`, `real-world-style`, `reconstructed-public-facts`, `derived-public-runbook`, or `sanitized-production`);
- expected safety result, expected violation properties, and expected prose-lint rules;
- responsible-disclosure status and why the fixture is safe to publish;
- validity threats plus categories for label uncertainty, abstraction bias, public-data incompleteness, bounded-search limits, survivor bias, or synthetic-mutant bias;
- semantic features covered by the fixture;
- optional oracle-review metadata and adoption summary.

Contribution workflow:

1. Add or update the runbook fixture without secrets, customer data, private incident details, or large copyrighted excerpts.
2. Add the entry to a benchmark config and run `PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown`.
3. If the fixture is a remediation or regression pair, add a `semantic_diff_baselines` entry with expected introduced/resolved counterexample counts.
4. Regenerate benchmark evidence with `make benchmark-reproduce`.
5. Document any unsupported claims in `validity_threats`; do not convert live-infrastructure assumptions into verifier claims.

Sanitization and disclosure requirements:

- Redact hostnames, credentials, customer identifiers, and internal topology that is not already public.
- Prefer short attributed excerpts plus independently authored executable models for public runbooks.
- Mark restricted or review-required material as not publishable until disclosure review is complete.
- Keep expected labels auditable: reviewers should be able to classify each finding as a true hazard, useful warning, false positive, or unsupported claim.
