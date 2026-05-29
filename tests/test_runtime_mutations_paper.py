from __future__ import annotations

from pathlib import Path

from runbook_verify.mutations import MUTATION_OPERATORS, run_mutations
from runbook_verify.paper_tables import build_paper_tables, render_paper_tables_markdown
from runbook_verify.runtime_verification import render_runtime_markdown, verify_runtime_log

ROOT = Path(__file__).resolve().parents[1]
GITHUB_CASE = ROOT / "case_studies" / "github_oct21_2018" / "github_oct21_reconstructed_runbook.md"
RUNTIME_LOG = ROOT / "examples" / "runtime_logs" / "github_oct21_observed_unsafe.json"
BENCHMARK = ROOT / "benchmarks" / "builtin.json"


def test_runtime_verify_reports_modeled_deviation_for_observed_failover() -> None:
    report = verify_runtime_log(GITHUB_CASE, RUNTIME_LOG)
    assert not report.conformant
    assert report.events_checked == 2
    assert any(deviation.rule == "runtime_precondition_violation" for deviation in report.deviations)
    assert any(deviation.modeled_property == "precondition" for deviation in report.deviations)
    markdown = render_runtime_markdown(report)
    assert "Runtime verification" in markdown
    assert "database_quorum_confirmed" in markdown


def test_mutation_operators_cover_expected_benchmark_calibration_set() -> None:
    report = run_mutations(GITHUB_CASE)
    operators = {mutation.operator for mutation in report.mutations}
    assert operators == set(MUTATION_OPERATORS)
    assert any(mutation.operator == "missing_preconditions" and mutation.applied for mutation in report.mutations)
    assert any(mutation.operator == "unsafe_retries" and mutation.annotation_warnings_by_property for mutation in report.mutations)
    assert any(mutation.operator == "invalid_waivers" and mutation.applied for mutation in report.mutations)


def test_paper_tables_include_feature_and_benchmark_sections() -> None:
    tables = build_paper_tables(BENCHMARK)
    markdown = render_paper_tables_markdown(tables)
    assert tables["benchmark"]["aggregate"]["runbooks"] >= 1
    assert "Runtime conformance" in markdown
    assert "Algorithm ablation proxy" in markdown
    assert "Counterexample usefulness" in markdown
