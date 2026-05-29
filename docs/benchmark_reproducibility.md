# Benchmark reproducibility and baselines

Use `make benchmark-reproduce` to regenerate checked-in benchmark outputs and `reports/benchmark_reproduction_manifest.json`. The script runs only repository-local fixtures and writes under `reports/`.

The benchmark report now compares workflow baselines:

- schema-only validation: parser/schema/entity/dependency acceptance;
- prose linting: Markdown-only dangerous-operation findings;
- bounded checking: executable semantic counterexamples;
- type/effect checking: failed precondition/effect proof obligations surfaced by the checker;
- semantic diffing: configured old/new runbook pairs such as the GitHub Oct. 21 quorum-guard remediation;
- combined workflow: expected-label pass/fail across the available signals.

Validity threats are reported as categorized counts so benchmark summaries preserve label uncertainty, abstraction bias, public-data incompleteness, bounded-search limits, survivor bias, and synthetic-mutant bias. Adoption summaries translate findings into risk classes and review/remediation actions; they are operator-triage evidence, not measured incident time saved unless explicitly stated.
