from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .checker import Checker
from .exporter import export_conformance_manifest
from .parser import load_runbook


@dataclass(frozen=True)
class TraceEquivalenceCase:
    path: str
    name: str
    native_counterexamples: int
    exported_counterexamples: int
    matched_counterexamples: int
    missing_from_export: list[dict[str, Any]]
    unexpected_exported: list[dict[str, Any]]
    pass_: bool

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pass"] = data.pop("pass_")
        return data


@dataclass(frozen=True)
class TraceEquivalenceReport:
    cases: list[TraceEquivalenceCase]

    @property
    def pass_(self) -> bool:
        return all(case.pass_ for case in self.cases)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "pass": self.pass_,
            "summary": {
                "cases": len(self.cases),
                "native_counterexamples": sum(c.native_counterexamples for c in self.cases),
                "exported_counterexamples": sum(c.exported_counterexamples for c in self.cases),
                "matched_counterexamples": sum(c.matched_counterexamples for c in self.cases),
                "missing_from_export": sum(len(c.missing_from_export) for c in self.cases),
                "unexpected_exported": sum(len(c.unexpected_exported) for c in self.cases),
            },
            "cases": [case.to_json_dict() for case in self.cases],
        }


def build_trace_equivalence(paths: list[str | Path]) -> TraceEquivalenceReport:
    cases: list[TraceEquivalenceCase] = []
    for path in paths:
        runbook = load_runbook(path)
        result = Checker(runbook).check()
        manifest = export_conformance_manifest(runbook)
        native = {_counterexample_key(v.property, v.trace) for v in result.violations}
        action_ids = set(manifest["action_sequence"])
        properties = set(manifest["property_identifiers"])
        exported = {
            key for key in native
            if key[0] in properties and all(step in action_ids for step in key[1])
        }
        missing = sorted(native - exported)
        unexpected = sorted(exported - native)
        cases.append(TraceEquivalenceCase(
            path=str(path),
            name=runbook.name,
            native_counterexamples=len(native),
            exported_counterexamples=len(exported),
            matched_counterexamples=len(native & exported),
            missing_from_export=[_key_dict(key) for key in missing],
            unexpected_exported=[_key_dict(key) for key in unexpected],
            pass_=not missing and not unexpected,
        ))
    return TraceEquivalenceReport(cases)


def default_trace_equivalence_paths(root: str | Path = ".") -> list[Path]:
    root = Path(root)
    return [
        root / "case_studies" / "github_oct21_2018" / "github_oct21_reconstructed_runbook.md",
        root / "case_studies" / "current" / "grafana_tempo" / "tempo_runbook_current_impact.md",
        root / "examples" / "object_storage_restore_unsafe.json",
        root / "examples" / "credential_rotation_runbook.json",
    ]


def render_trace_equivalence_json(report: TraceEquivalenceReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_trace_equivalence_markdown(report: TraceEquivalenceReport) -> str:
    data = report.to_json_dict()
    lines = [
        "# Native/exported trace-equivalence report",
        "",
        f"- Pass: `{data['pass']}`",
        f"- Cases: {data['summary']['cases']}",
        f"- Matched counterexamples: {data['summary']['matched_counterexamples']}",
        f"- Missing from export projection: {data['summary']['missing_from_export']}",
        "",
        "The exported-model side is the checker-derived conformance projection used by the TLA+/Alloy starters: action ids, enabledness edges, and property labels must preserve every native counterexample key. It does not claim TLC/Alloy discharged concrete arithmetic invariants.",
        "",
        "| Case | Pass | Native CEX | Exported CEX | Matched | Missing | Unexpected |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for case in data["cases"]:
        lines.append(
            f"| {Path(case['path']).name} | `{case['pass']}` | {case['native_counterexamples']} | {case['exported_counterexamples']} | {case['matched_counterexamples']} | `{json.dumps(case['missing_from_export'], sort_keys=True)}` | `{json.dumps(case['unexpected_exported'], sort_keys=True)}` |"
        )
    return "\n".join(lines) + "\n"


def _counterexample_key(property_name: str, trace: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    return (property_name, tuple(trace))


def _key_dict(key: tuple[str, tuple[str, ...]]) -> dict[str, Any]:
    return {"property": key[0], "trace": list(key[1])}
