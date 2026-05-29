from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checker import Checker
from .parser import load_runbook


@dataclass(frozen=True)
class UsabilityReport:
    cases: list[dict[str, Any]]

    @property
    def pass_(self) -> bool:
        return all(case["hinted_counterexamples"] > 0 for case in self.cases)

    def to_json_dict(self) -> dict[str, Any]:
        raw_total = sum(case["raw_trace_steps"] for case in self.cases)
        minimized_total = sum(case["minimized_trace_steps"] for case in self.cases)
        return {
            "pass": self.pass_,
            "summary": {
                "sre_tasks": len(self.cases),
                "raw_trace_steps": raw_total,
                "minimized_trace_steps": minimized_total,
                "trace_step_reduction": raw_total - minimized_total,
                "generated_precondition_hints": sum(case["generated_precondition_hints"] for case in self.cases),
                "generated_json_patches": sum(case["generated_json_patches"] for case in self.cases),
            },
            "cases": self.cases,
        }


def build_usability_report(paths: list[str | Path]) -> UsabilityReport:
    cases = []
    for path in paths:
        runbook = load_runbook(path)
        result = Checker(runbook).check()
        violations = result.violations
        raw_steps = sum(len(v.original_trace or v.trace) for v in violations)
        minimized_steps = sum(len(v.trace) for v in violations)
        cases.append({
            "path": str(path),
            "task": f"repair {runbook.name}",
            "counterexamples": len(violations),
            "hinted_counterexamples": sum(1 for v in violations if v.suggested_preconditions or v.json_patches),
            "raw_trace_steps": raw_steps,
            "minimized_trace_steps": minimized_steps,
            "trace_step_reduction": raw_steps - minimized_steps,
            "generated_precondition_hints": sum(len(v.suggested_preconditions) for v in violations),
            "generated_json_patches": sum(len(v.json_patches) for v in violations),
            "properties": sorted({v.property for v in violations}),
        })
    return UsabilityReport(cases)


def default_usability_paths(root: str | Path = ".") -> list[Path]:
    root = Path(root)
    return [
        root / "examples" / "unsafe_runbook.json",
        root / "case_studies" / "github_oct21_2018" / "github_oct21_reconstructed_runbook.md",
        root / "case_studies" / "current" / "grafana_tempo" / "tempo_runbook_current_impact.md",
    ]


def render_usability_json(report: UsabilityReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_usability_markdown(report: UsabilityReport) -> str:
    data = report.to_json_dict()
    lines = [
        "# SRE-style usability task report",
        "",
        f"- Pass: `{data['pass']}`",
        f"- Tasks: {data['summary']['sre_tasks']}",
        f"- Trace-step reduction from minimization: {data['summary']['trace_step_reduction']}",
        f"- Generated precondition hints: {data['summary']['generated_precondition_hints']}",
        f"- Generated JSON patches: {data['summary']['generated_json_patches']}",
        "",
        "This is an instrumented task proxy over checked-in fixtures, not a human-subjects claim: it measures whether each repair task receives minimized traces and generated precondition/patch hints instead of only raw model-checker output.",
        "",
        "| Task | CEX | Hinted CEX | Raw steps | Minimized steps | Hints | Patches | Properties |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in data["cases"]:
        lines.append(f"| {case['task']} | {case['counterexamples']} | {case['hinted_counterexamples']} | {case['raw_trace_steps']} | {case['minimized_trace_steps']} | {case['generated_precondition_hints']} | {case['generated_json_patches']} | `{json.dumps(case['properties'])}` |")
    return "\n".join(lines) + "\n"
