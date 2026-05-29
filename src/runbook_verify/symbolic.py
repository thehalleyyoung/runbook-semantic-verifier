from __future__ import annotations

import copy
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checker import Checker
from .parser import load_document, parse_runbook


@dataclass(frozen=True)
class SymbolicReport:
    path: str
    pass_: bool
    variants: list[dict[str, Any]]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "pass": self.pass_,
            "summary": {
                "variants": len(self.variants),
                "safe_variants": sum(1 for item in self.variants if item["safe"]),
                "unsafe_variants": sum(1 for item in self.variants if not item["safe"]),
                "symbolic_splits": max(0, len(self.variants) - 1),
            },
            "variants": self.variants,
        }


def run_symbolic_check(path: str | Path) -> SymbolicReport:
    doc = load_document(path)
    symbolic = doc.get("symbolic", {})
    choices = symbolic.get("choices", {}) if isinstance(symbolic, dict) else {}
    variants = []
    if not isinstance(choices, dict) or not choices:
        runbook = parse_runbook(doc, source_path=path)
        result = Checker(runbook).check()
        variants.append(_variant_result({}, result))
    else:
        keys = sorted(str(key) for key in choices)
        value_lists = [_choice_list(choices[key], key) for key in keys]
        for values in itertools.product(*value_lists):
            bindings = dict(zip(keys, values, strict=True))
            variant_doc = copy.deepcopy(doc)
            variant_doc.pop("symbolic", None)
            for selector, value in bindings.items():
                _set_selector(variant_doc, selector, value)
            runbook = parse_runbook(variant_doc, source_path=path)
            result = Checker(runbook).check()
            result.symbolic_splits = max(0, len(keys))
            variants.append(_variant_result(bindings, result))
    return SymbolicReport(str(path), all(item["pass"] for item in variants), variants)


def render_symbolic_json(report: SymbolicReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_symbolic_markdown(report: SymbolicReport) -> str:
    data = report.to_json_dict()
    lines = [
        "# Symbolic bounded check",
        "",
        f"- Path: `{report.path}`",
        f"- Pass: `{data['pass']}`",
        f"- Variants: {data['summary']['variants']}",
        f"- Symbolic splits: {data['summary']['symbolic_splits']}",
        "",
        "| Bindings | Pass | Safe | States | Violations |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for item in data["variants"]:
        lines.append(f"| `{json.dumps(item['bindings'], sort_keys=True)}` | `{item['pass']}` | `{item['safe']}` | {item['states_explored']} | `{json.dumps(item['violations_by_property'], sort_keys=True)}` |")
    return "\n".join(lines) + "\n"


def _choice_list(raw: Any, key: str) -> list[Any]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"symbolic choice {key!r} must be a non-empty list")
    return raw


def _set_selector(doc: dict[str, Any], selector: str, value: Any) -> None:
    parts = selector.split(".")
    current: Any = doc
    for part in parts[:-1]:
        if part.startswith("steps[") and part.endswith("]"):
            step_id = part[6:-1]
            current = next(step for step in current["steps"] if str(step.get("id")) == step_id)
        else:
            current = current[part]
    current[parts[-1]] = value


def _variant_result(bindings: dict[str, Any], result: Any) -> dict[str, Any]:
    violations: dict[str, int] = {}
    for violation in result.violations:
        violations[violation.property] = violations.get(violation.property, 0) + 1
    return {
        "bindings": bindings,
        "safe": result.safe,
        "pass": True,
        "states_explored": result.states_explored,
        "violations_by_property": violations,
        "performance_counters": result.performance_counters(),
    }
