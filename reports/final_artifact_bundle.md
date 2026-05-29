# Final artifact bundle and paper outline

This bundle is a reproducibility map for the checked-in public artifacts. It does
not claim production safety for any third-party service; each result is bounded
by the runbook model, fixture provenance, configured search bound, and documented
validity threats.

## Artifact bundle

- Core verifier: `src/runbook_verify/`, `runbook.schema.json`, and `frv` CLI entry points.
- Public fixtures: `examples/`, `case_studies/github_oct21_2018/`, `case_studies/current/grafana_tempo/`, `case_studies/current/dnsswitch_dns/`, and `case_studies/current/redis_cache_flush/`.
- Benchmark suite: `benchmarks/builtin.json` with provenance, expected labels, semantic features, oracle-review metadata, and validity-threat categories.
- Generated evidence: `reports/builtin_benchmark.md`, `reports/current_impact.md`, `reports/formal_export_obligations_tempo.md`, `reports/formal_export_obligations_github_oct21.md`, `reports/trace_equivalence.md`, `reports/longitudinal_gate_evaluation.md`, `reports/paper_tables_builtin.md`, and related JSON/SARIF/JUnit outputs.
- Public claims and limitations: `README.md`, `docs/claims_evidence.md`, `docs/release_criteria.md`, `docs/security_privacy.md`, and `docs/glossary.md`.

## Reproduction commands

```bash
make verify
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli proof-obligations case_studies/current/grafana_tempo/tempo_runbook_current_impact.md --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli proof-obligations case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli paper-tables benchmarks/builtin.json --format markdown
```

## Paper outline

1. Motivation: incident runbooks encode safety-critical operational decisions but are usually reviewed as prose.
2. Method: a small YAML/Markdown DSL, schema validation, deterministic bounded small-step semantics, and traceable findings.
3. Semantics: typed effects, preconditions, invariants, temporal monitors, assume/guarantee contracts, rely/guarantee interference, and finite queue/cache abstractions.
4. Evidence surfaces: CLI checks, audits, semantic diffs, readiness reports, proof-obligation exports, TLA+/Alloy starter projections, and benchmark tables.
5. Evaluation: public historical reconstruction, current public runbook fixtures, synthetic mutants, benchmark baselines, longitudinal gate simulations, and oracle-review metadata.
6. Threats to validity: public-data incompleteness, abstraction bias, bounded search limits, label uncertainty, survivor bias, and lack of independent production telemetry.
7. Operational impact: actionable counterexamples, source-line explanations, waiver governance, and CI/reporting integrations for SRE review.
8. Formal-methods impact: a reproducible bridge between practical runbook review and mechanized/exported proof obligations without overstating unbounded production guarantees.
