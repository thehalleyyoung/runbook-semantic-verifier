from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .benchmark import BenchmarkConfigError, BenchmarkSuiteResult, run_benchmark

FEATURE_ROWS = [
    ("Executable DSL", "schema, parser, typed descriptors", "frv validate/schema"),
    ("Bounded checking", "dependency-aware transition exploration", "frv check"),
    ("Counterexample explanation", "small-step trace, Hoare triple, weakest-precondition hint, source line", "frv check --format json / frv explain"),
    ("Runtime conformance", "observed step logs checked against model dependencies and preconditions", "frv runtime-verify"),
    ("Mutation calibration", "synthetic missing-guard/reorder/stale-owner/retry/wait/capacity/waiver mutants", "frv mutate"),
    ("Benchmark governance", "provenance, licensing, validity threats, oracle labels", "frv benchmark"),
]


def build_paper_tables(path: str | Path | None = None) -> dict[str, Any]:
    suite = run_benchmark(path)
    data = suite.to_json_dict()
    aggregate = data["aggregate"]
    return {
        "benchmark": data,
        "feature_coverage": [
            {"feature": feature, "evidence": evidence, "surface": surface}
            for feature, evidence, surface in FEATURE_ROWS
        ],
        "algorithm_ablation_proxy": _algorithm_proxy(aggregate),
        "counterexample_usefulness": _counterexample_usefulness(data),
        "adoption_workflows": _adoption_workflows(aggregate),
    }


def render_paper_tables_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_paper_tables_markdown(report: dict[str, Any]) -> str:
    bench = report["benchmark"]
    aggregate = bench["aggregate"]
    lines = [
        f"# Paper-ready artifact tables: {bench['name']}",
        "",
        "## Feature coverage",
        "",
        "| Feature | Evidence in artifact | CLI/report surface |",
        "| --- | --- | --- |",
    ]
    for row in report["feature_coverage"]:
        lines.append(f"| {row['feature']} | {row['evidence']} | `{row['surface']}` |")
    lines.extend([
        "",
        "## Benchmark results",
        "",
        "| Runbooks | Pass | States | Traces | Runtime seconds | Violations | Prose findings | Validity threats |",
        "| ---: | --- | ---: | ---: | ---: | --- | --- | --- |",
        f"| {aggregate['runbooks']} | `{aggregate['pass']}` | {aggregate['states_explored']} | {aggregate['traces_explored']} | {aggregate['runtime_seconds']:.6f} | `{json.dumps(aggregate['violations_by_property'], sort_keys=True)}` | `{json.dumps(aggregate['prose_findings_by_rule'], sort_keys=True)}` | `{json.dumps(aggregate['validity_threat_categories'], sort_keys=True)}` |",
        "",
        "## Algorithm ablation proxy",
        "",
        "| Counter | Value | Interpretation |",
        "| --- | ---: | --- |",
    ])
    for row in report["algorithm_ablation_proxy"]:
        lines.append(f"| `{row['counter']}` | {row['value']} | {row['interpretation']} |")
    lines.extend(["", "## Counterexample usefulness", "", "| Metric | Value |", "| --- | --- |"])
    for key, value in report["counterexample_usefulness"].items():
        lines.append(f"| {key} | `{json.dumps(value, sort_keys=True)}` |")
    lines.extend(["", "## Adoption workflows", "", "| Workflow | Passing suites | Failing suites |", "| --- | ---: | ---: |"])
    for name, counts in report["adoption_workflows"].items():
        lines.append(f"| `{name}` | {counts.get('pass', 0)} | {counts.get('fail', 0)} |")
    return "\n".join(lines) + "\n"


def _algorithm_proxy(aggregate: dict[str, Any]) -> list[dict[str, Any]]:
    perf = aggregate.get("performance_counters", {})
    rows = []
    interpretations = {
        "states_explored": "bounded transition states visited",
        "transitions_explored": "candidate operator actions evaluated",
        "max_branch_factor": "largest enabled-step set",
        "reductions_applied": "implemented reduction/pruning counter",
        "minimized_counterexample_trace_length": "shortest minimized witness length",
        "symbolic_splits": "symbolic case split counter",
    }
    for key, interpretation in interpretations.items():
        rows.append({"counter": key, "value": perf.get(key), "interpretation": interpretation})
    return rows


def _counterexample_usefulness(data: dict[str, Any]) -> dict[str, Any]:
    traces = []
    warnings = 0
    for item in data["runbooks"]:
        perf = item.get("performance_counters", {})
        if isinstance(perf.get("minimized_counterexample_trace_length"), int):
            traces.append(perf["minimized_counterexample_trace_length"])
        warnings += int(perf.get("annotation_warnings", 0) or 0)
    return {
        "runbooks_with_minimized_counterexamples": len(traces),
        "shortest_minimized_trace": min(traces) if traces else None,
        "effect_annotation_warnings": warnings,
        "oracle_review_labels": data["aggregate"].get("adoption_summary", {}).get("oracle_review_labels", {}),
    }


def _adoption_workflows(aggregate: dict[str, Any]) -> dict[str, Any]:
    return aggregate.get("workflow_baselines", {})
