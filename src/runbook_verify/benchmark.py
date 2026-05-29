from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .checker import Checker
from .markdown_lint import lint_markdown_file
from .parser import RunbookParseError, load_document, load_runbook
from .profiles import get_profile
from .semantic_diff import diff_runbooks

RUNBOOK_SUFFIXES = {".json", ".yaml", ".yml", ".md"}


@dataclass(frozen=True)
class BenchmarkEntry:
    path: Path
    name: str | None = None
    benchmark_metadata: dict[str, Any] | None = None
    expected_labels: dict[str, Any] | None = None


@dataclass(frozen=True)
class DiffBenchmarkEntry:
    old_path: Path
    new_path: Path
    name: str
    expected: dict[str, Any] | None = None


@dataclass
class RunbookBenchmarkResult:
    path: str
    name: str
    safe: bool
    pass_: bool
    states_explored: int
    traces_explored: int
    violations_by_property: dict[str, int]
    prose_findings_by_rule: dict[str, int]
    runtime_seconds: float
    performance_counters: dict[str, Any] = field(default_factory=dict)
    workflow_baselines: dict[str, Any] = field(default_factory=dict)
    expected_labels: dict[str, Any] | None = None
    benchmark_metadata: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pass"] = data.pop("pass_")
        return data


@dataclass
class DiffBenchmarkResult:
    name: str
    old_path: str
    new_path: str
    pass_: bool
    summary: dict[str, Any]
    expected: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pass"] = data.pop("pass_")
        return data


@dataclass
class BenchmarkSuiteResult:
    name: str
    runbooks: list[RunbookBenchmarkResult]
    runtime_seconds: float
    diff_baselines: list[DiffBenchmarkResult] = field(default_factory=list)
    profile: dict[str, str] | None = None

    @property
    def pass_(self) -> bool:
        return all(item.pass_ for item in self.runbooks) and all(item.pass_ for item in self.diff_baselines)

    def to_json_dict(self) -> dict[str, Any]:
        aggregate: dict[str, Any] = {
            "runbooks": len(self.runbooks),
            "states_explored": sum(item.states_explored for item in self.runbooks),
            "traces_explored": sum(item.traces_explored for item in self.runbooks),
            "violations_by_property": {},
            "prose_findings_by_rule": {},
            "runtime_seconds": self.runtime_seconds,
            "performance_counters": _aggregate_performance_counters(self.runbooks),
            "validity_threat_categories": _aggregate_validity_threats(self.runbooks),
            "workflow_baselines": _aggregate_workflow_baselines(self.runbooks, self.diff_baselines),
            "adoption_summary": _aggregate_adoption_summary(self.runbooks),
            "pass": self.pass_,
        }
        for item in self.runbooks:
            for prop, count in item.violations_by_property.items():
                aggregate["violations_by_property"][prop] = aggregate["violations_by_property"].get(prop, 0) + count
            for rule, count in item.prose_findings_by_rule.items():
                aggregate["prose_findings_by_rule"][rule] = aggregate["prose_findings_by_rule"].get(rule, 0) + count
        return {
            "name": self.name,
            "profile": self.profile,
            "aggregate": aggregate,
            "runbooks": [item.to_json_dict() for item in self.runbooks],
            "semantic_diff_baselines": [item.to_json_dict() for item in self.diff_baselines],
        }


def run_benchmark(path: str | Path | None = None, profile_name: str | None = None) -> BenchmarkSuiteResult:
    root = Path.cwd()
    if path is None:
        builtin_config = root / "benchmarks" / "builtin.json"
        if builtin_config.exists():
            suite_name, entries, diff_entries = _load_config(builtin_config)
        else:
            suite_name = "built-in benchmark"
            diff_entries = []
            entries = [
                BenchmarkEntry(root / "examples" / "safe_runbook.json"),
                BenchmarkEntry(root / "examples" / "unsafe_runbook.json"),
                BenchmarkEntry(root / "examples" / "real_world" / "kubernetes_region_failover.md"),
                BenchmarkEntry(root / "case_studies" / "github_oct21_2018" / "github_oct21_reconstructed_runbook.md"),
                BenchmarkEntry(root / "case_studies" / "current" / "grafana_tempo" / "tempo_runbook_current_impact.md"),
            ]
    else:
        config_path = Path(path)
        if not config_path.exists():
            raise BenchmarkConfigError(f"benchmark path does not exist: {config_path}")
        if config_path.is_dir():
            suite_name = str(config_path)
            diff_entries = []
            entries = [BenchmarkEntry(p) for p in _runbook_files(config_path)]
        elif config_path.suffix.lower() == ".json" and _looks_like_benchmark_config(config_path):
            suite_name, entries, diff_entries = _load_config(config_path)
        elif config_path.suffix.lower() in RUNBOOK_SUFFIXES:
            suite_name = str(config_path)
            diff_entries = []
            entries = [BenchmarkEntry(config_path)]
        else:
            raise BenchmarkConfigError(f"unsupported benchmark input {config_path}; use a directory, config .json, or runbook file")

    if not entries:
        raise BenchmarkConfigError("benchmark has no runbook entries")

    started = time.perf_counter()
    runbooks = [_run_one(entry) for entry in entries]
    diff_results = [_run_diff_baseline(entry) for entry in diff_entries]
    profile = get_profile(profile_name)
    return BenchmarkSuiteResult(suite_name, runbooks, time.perf_counter() - started, diff_results, profile.to_json_dict() if profile else None)


def render_json(result: BenchmarkSuiteResult) -> str:
    return json.dumps(result.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_markdown(result: BenchmarkSuiteResult) -> str:
    data = result.to_json_dict()
    aggregate = data["aggregate"]
    lines = [
        f"# Benchmark: {result.name}",
        "",
        f"- Profile: `{data['profile']['name']}` ({data['profile']['benchmark_mode']})" if data["profile"] else "- Profile: `none`",
        f"- Pass: `{aggregate['pass']}`",
        f"- Runbooks: {aggregate['runbooks']}",
        f"- States explored: {aggregate['states_explored']}",
        f"- Traces explored: {aggregate['traces_explored']}",
        f"- Runtime seconds: {aggregate['runtime_seconds']:.6f}",
        f"- Performance counters: `{json.dumps(aggregate['performance_counters'], sort_keys=True)}`",
        f"- Validity threat categories: `{json.dumps(aggregate['validity_threat_categories'], sort_keys=True)}`",
        f"- Workflow baselines: `{json.dumps(aggregate['workflow_baselines'], sort_keys=True)}`",
        f"- Adoption summary: `{json.dumps(aggregate['adoption_summary'], sort_keys=True)}`",
        f"- Violations by property: `{json.dumps(aggregate['violations_by_property'], sort_keys=True)}`",
        f"- Prose findings by rule: `{json.dumps(aggregate['prose_findings_by_rule'], sort_keys=True)}`",
        "",
        "| Runbook | Pass | Safe | States | Transitions | Max branch | Min CEX trace | Runtime (s) | Violations | Prose findings | Expected labels | Benchmark metadata |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for item in data["runbooks"]:
        lines.append(
            "| {name} | `{pass_}` | `{safe}` | {states} | {transitions} | {max_branch} | {min_trace} | {runtime:.6f} | `{violations}` | `{prose}` | `{expected}` | `{metadata}` |".format(
                name=item["name"].replace("|", "\\|"),
                pass_=item["pass"],
                safe=item["safe"],
                states=item["states_explored"],
                transitions=item["performance_counters"].get("transitions_explored", 0),
                max_branch=item["performance_counters"].get("max_branch_factor", 0),
                min_trace=item["performance_counters"].get("minimized_counterexample_trace_length") or "",
                runtime=item["runtime_seconds"],
                violations=json.dumps(item["violations_by_property"], sort_keys=True),
                prose=json.dumps(item["prose_findings_by_rule"], sort_keys=True),
                expected=json.dumps(item["expected_labels"], sort_keys=True) if item["expected_labels"] else "",
                metadata=json.dumps(item["benchmark_metadata"], sort_keys=True) if item["benchmark_metadata"] else "",
            )
        )
    lines.extend(["", "## Semantic diff baselines", ""])
    if data["semantic_diff_baselines"]:
        lines.extend(["| Name | Pass | Old | New | Expected | Summary | Errors |", "| --- | --- | --- | --- | --- | --- | --- |"])
        for item in data["semantic_diff_baselines"]:
            lines.append(
                "| {name} | `{pass_}` | `{old}` | `{new}` | `{expected}` | `{summary}` | `{errors}` |".format(
                    name=item["name"].replace("|", "\\|"),
                    pass_=item["pass"],
                    old=item["old_path"],
                    new=item["new_path"],
                    expected=json.dumps(item["expected"], sort_keys=True) if item["expected"] else "",
                    summary=json.dumps(item["summary"], sort_keys=True),
                    errors=json.dumps(item["errors"], sort_keys=True),
                )
            )
    else:
        lines.append("No semantic-diff baseline pairs configured for this suite.")
    return "\n".join(lines) + "\n"


class BenchmarkConfigError(ValueError):
    pass


def _aggregate_performance_counters(items: list[RunbookBenchmarkResult]) -> dict[str, Any]:
    counters: dict[str, Any] = {
        "states_explored": 0,
        "terminal_traces": 0,
        "transitions_explored": 0,
        "branch_points": 0,
        "branch_factor_total": 0,
        "avg_branch_factor": 0.0,
        "max_branch_factor": 0,
        "reductions_applied": 0,
        "symbolic_splits": 0,
        "minimized_counterexample_trace_length": None,
        "max_depth_reached": False,
        "proof_obligations_checked": {},
        "proof_obligation_failures": {},
        "semantic_rule_counts": {},
    }
    min_trace: int | None = None
    for item in items:
        perf = item.performance_counters or {}
        counters["states_explored"] += int(perf.get("states_explored", item.states_explored))
        counters["terminal_traces"] += int(perf.get("terminal_traces", item.traces_explored))
        counters["transitions_explored"] += int(perf.get("transitions_explored", 0))
        counters["branch_points"] += int(perf.get("branch_points", 0))
        counters["branch_factor_total"] += int(perf.get("branch_factor_total", 0))
        counters["max_branch_factor"] = max(counters["max_branch_factor"], int(perf.get("max_branch_factor", 0)))
        counters["reductions_applied"] += int(perf.get("reductions_applied", 0))
        counters["symbolic_splits"] += int(perf.get("symbolic_splits", 0))
        counters["max_depth_reached"] = bool(counters["max_depth_reached"] or perf.get("max_depth_reached", False))
        trace_len = perf.get("minimized_counterexample_trace_length")
        if isinstance(trace_len, int):
            min_trace = trace_len if min_trace is None else min(min_trace, trace_len)
        _merge_counter_map(counters["proof_obligations_checked"], perf.get("proof_obligations_checked", {}))
        _merge_counter_map(counters["proof_obligation_failures"], perf.get("proof_obligation_failures", {}))
        _merge_counter_map(counters["semantic_rule_counts"], perf.get("semantic_rule_counts", {}))
    points = counters["branch_points"]
    counters["avg_branch_factor"] = counters["branch_factor_total"] / points if points else 0.0
    counters["minimized_counterexample_trace_length"] = min_trace
    counters["proof_obligations_checked"] = dict(sorted(counters["proof_obligations_checked"].items()))
    counters["proof_obligation_failures"] = dict(sorted(counters["proof_obligation_failures"].items()))
    counters["semantic_rule_counts"] = dict(sorted(counters["semantic_rule_counts"].items()))
    return counters


def _aggregate_validity_threats(items: list[RunbookBenchmarkResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        metadata = item.benchmark_metadata or {}
        for category in metadata.get("validity_threat_categories", []):
            counts[str(category)] = counts.get(str(category), 0) + 1
    return dict(sorted(counts.items()))


def _aggregate_workflow_baselines(items: list[RunbookBenchmarkResult], diffs: list[DiffBenchmarkResult]) -> dict[str, Any]:
    workflow_names = [
        "schema_only_validation",
        "prose_linting",
        "bounded_checking",
        "type_effect_checking",
        "combined_workflow",
    ]
    aggregate: dict[str, Any] = {name: {"pass": 0, "fail": 0} for name in workflow_names}
    for item in items:
        for name in workflow_names:
            record = item.workflow_baselines.get(name, {})
            passed = bool(record.get("pass", False))
            aggregate[name]["pass" if passed else "fail"] += 1
    aggregate["semantic_diffing"] = {
        "pass": sum(1 for item in diffs if item.pass_),
        "fail": sum(1 for item in diffs if not item.pass_),
        "configured_pairs": len(diffs),
    }
    return aggregate


def _aggregate_adoption_summary(items: list[RunbookBenchmarkResult]) -> dict[str, Any]:
    risk_classes: set[str] = set()
    actions: set[str] = set()
    review_labels: dict[str, int] = {}
    for item in items:
        metadata = item.benchmark_metadata or {}
        adoption = metadata.get("adoption_summary", {})
        if isinstance(adoption, dict):
            risk_classes.update(str(value) for value in adoption.get("risk_classes_detected", []) if value)
            actions.update(str(value) for value in adoption.get("remediation_actions", []) if value)
        oracle = metadata.get("oracle_review", {})
        if isinstance(oracle, dict):
            for label in oracle.get("allowed_labels", []):
                review_labels[str(label)] = review_labels.get(str(label), 0) + 1
    return {
        "risk_classes_detected": sorted(risk_classes),
        "remediation_actions": sorted(actions),
        "oracle_review_labels": dict(sorted(review_labels.items())),
    }


def _merge_counter_map(target: dict[str, int], source: object) -> None:
    if not isinstance(source, dict):
        return
    for key, value in source.items():
        target[str(key)] = target.get(str(key), 0) + int(value)


def _load_config(path: Path) -> tuple[str, list[BenchmarkEntry], list[DiffBenchmarkEntry]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkConfigError(f"invalid benchmark config JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise BenchmarkConfigError("benchmark config must be a JSON object")
    _validate_public_benchmark_config(raw)
    suite_name = str(raw.get("name", path.stem))
    raw_entries = raw.get("runbooks")
    if not isinstance(raw_entries, list):
        raise BenchmarkConfigError("benchmark config field 'runbooks' must be a list")
    entries: list[BenchmarkEntry] = []
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            raise BenchmarkConfigError(f"benchmark runbooks[{index}] must be an object")
        raw_path = raw_entry.get("path")
        if not isinstance(raw_path, str):
            raise BenchmarkConfigError(f"benchmark runbooks[{index}].path must be a string")
        entry_path = (path.parent / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path)
        metadata = _benchmark_metadata(raw_entry)
        expected = _expected_labels_from_benchmark_metadata(raw_entry)
        entries.extend(BenchmarkEntry(p, raw_entry.get("name"), metadata, expected) for p in _expand_entry_path(entry_path))
    diff_entries = _diff_benchmark_entries(path, raw.get("semantic_diff_baselines", []))
    return suite_name, entries, diff_entries


def _looks_like_benchmark_config(path: Path) -> bool:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(raw, dict) and isinstance(raw.get("runbooks"), list)


def _validate_public_benchmark_config(raw: dict[str, Any]) -> None:
    version = raw.get("benchmark_schema_version")
    if version != "1.0":
        raise BenchmarkConfigError("benchmark config field 'benchmark_schema_version' must be '1.0'")
    if not isinstance(raw.get("name"), str) or not raw["name"].strip():
        raise BenchmarkConfigError("benchmark config field 'name' must be a non-empty string")


def _benchmark_metadata(raw_entry: dict[str, Any]) -> dict[str, Any]:
    required = [
        "provenance",
        "license",
        "abstraction_level",
        "expected_result",
        "responsible_disclosure",
        "validity_threats",
        "semantic_features",
    ]
    for field_name in required:
        if field_name not in raw_entry:
            raise BenchmarkConfigError(f"benchmark runbook {raw_entry.get('path', '<unknown>')} is missing required public benchmark field '{field_name}'")
    provenance = _require_object(raw_entry["provenance"], "provenance")
    license_info = _require_object(raw_entry["license"], "license")
    expected_result = _require_object(raw_entry["expected_result"], "expected_result")
    disclosure = _require_object(raw_entry["responsible_disclosure"], "responsible_disclosure")
    abstraction_level = _require_enum(
        raw_entry["abstraction_level"],
        "abstraction_level",
        {"toy", "real-world-style", "reconstructed-public-facts", "derived-public-runbook", "sanitized-production"},
    )
    _require_enum(
        str(provenance.get("kind", "")),
        "provenance.kind",
        {"synthetic", "real-world-style", "public-historical", "public-current", "sanitized"},
    )
    _require_enum(
        str(license_info.get("status", "")),
        "license.status",
        {"original", "public-license", "excerpted", "sanitized", "unknown"},
    )
    _require_enum(
        str(disclosure.get("status", "")),
        "responsible_disclosure.status",
        {"not-applicable", "public-information", "sanitized", "review-required", "restricted"},
    )
    _require_bool(expected_result.get("safe"), "expected_result.safe")
    metadata = {
        "provenance": provenance,
        "license": license_info,
        "abstraction_level": abstraction_level,
        "expected_result": {
            "safe": bool(expected_result["safe"]),
            "violation_properties": _string_list(expected_result.get("violation_properties", []), "expected_result.violation_properties"),
            "prose_rules": _string_list(expected_result.get("prose_rules", []), "expected_result.prose_rules"),
        },
        "responsible_disclosure": disclosure,
        "validity_threats": _non_empty_string_list(raw_entry["validity_threats"], "validity_threats"),
        "validity_threat_categories": _validity_threat_categories(raw_entry),
        "semantic_features": _non_empty_string_list(raw_entry["semantic_features"], "semantic_features"),
        "oracle_review": _oracle_review(raw_entry),
        "adoption_summary": _adoption_summary(raw_entry),
        "reproduction": _reproduction(raw_entry),
    }
    return metadata


def _diff_benchmark_entries(config_path: Path, raw: Any) -> list[DiffBenchmarkEntry]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise BenchmarkConfigError("benchmark config field 'semantic_diff_baselines' must be a list")
    entries = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise BenchmarkConfigError(f"benchmark semantic_diff_baselines[{index}] must be an object")
        name = item.get("name")
        old_path = item.get("old_path")
        new_path = item.get("new_path")
        if not isinstance(name, str) or not name.strip():
            raise BenchmarkConfigError(f"benchmark semantic_diff_baselines[{index}].name must be a non-empty string")
        if not isinstance(old_path, str) or not isinstance(new_path, str):
            raise BenchmarkConfigError(f"benchmark semantic_diff_baselines[{index}] old_path and new_path must be strings")
        expected = item.get("expected", {})
        if not isinstance(expected, dict):
            raise BenchmarkConfigError(f"benchmark semantic_diff_baselines[{index}].expected must be an object")
        old_resolved = (config_path.parent / old_path).resolve() if not Path(old_path).is_absolute() else Path(old_path)
        new_resolved = (config_path.parent / new_path).resolve() if not Path(new_path).is_absolute() else Path(new_path)
        if not old_resolved.exists() or not new_resolved.exists():
            raise BenchmarkConfigError(f"benchmark semantic_diff_baselines[{index}] paths must exist")
        entries.append(DiffBenchmarkEntry(old_resolved, new_resolved, name, expected or None))
    return entries


VALIDITY_THREAT_CATEGORIES = {
    "label_uncertainty",
    "abstraction_bias",
    "public_data_incompleteness",
    "bounded_search_limits",
    "survivor_bias",
    "synthetic_mutant_bias",
}


def _validity_threat_categories(raw_entry: dict[str, Any]) -> list[str]:
    raw_categories = raw_entry.get("validity_threat_categories")
    if raw_categories is not None:
        categories = _non_empty_string_list(raw_categories, "validity_threat_categories")
        unknown = sorted(set(categories) - VALIDITY_THREAT_CATEGORIES)
        if unknown:
            raise BenchmarkConfigError(f"benchmark field 'validity_threat_categories' has unknown categories: {', '.join(unknown)}")
        return sorted(set(categories))
    threats = " ".join(_non_empty_string_list(raw_entry["validity_threats"], "validity_threats")).lower()
    categories = set()
    if "synthetic" in threats or "mutant" in threats:
        categories.add("synthetic_mutant_bias")
    if "public" in threats or "incomplete" in threats or "reconstructed" in threats:
        categories.add("public_data_incompleteness")
    if "abstract" in threats or "derived" in threats or "model" in threats:
        categories.add("abstraction_bias")
    if "bounded" in threats or "small" in threats:
        categories.add("bounded_search_limits")
    return sorted(categories or {"label_uncertainty"})


def _oracle_review(raw_entry: dict[str, Any]) -> dict[str, Any]:
    default = {
        "status": "not-reviewed",
        "allowed_labels": ["true_hazard", "useful_warning", "false_positive", "unsupported_claim"],
        "notes": "No independent SRE oracle review is claimed for this fixture.",
    }
    raw = raw_entry.get("oracle_review")
    if raw is None:
        return default
    review = _require_object(raw, "oracle_review")
    labels = _non_empty_string_list(review.get("allowed_labels", default["allowed_labels"]), "oracle_review.allowed_labels")
    allowed = set(default["allowed_labels"])
    unknown = sorted(set(labels) - allowed)
    if unknown:
        raise BenchmarkConfigError(f"benchmark field 'oracle_review.allowed_labels' has unknown labels: {', '.join(unknown)}")
    return {
        "status": str(review.get("status", default["status"])),
        "allowed_labels": labels,
        "reviewer_role": str(review.get("reviewer_role", "")),
        "notes": str(review.get("notes", default["notes"])),
    }


def _adoption_summary(raw_entry: dict[str, Any]) -> dict[str, Any]:
    raw = raw_entry.get("adoption_summary")
    if raw is None:
        expected = _require_object(raw_entry["expected_result"], "expected_result")
        return {
            "risk_classes_detected": sorted(set(_string_list(expected.get("violation_properties", []), "expected_result.violation_properties") + _string_list(expected.get("prose_rules", []), "expected_result.prose_rules"))),
            "remediation_actions": ["review modeled counterexamples and add missing preconditions, rollback, dedupe, capacity, or limitation evidence"],
            "operator_time_saved": "not-measured; reported as review-prioritization evidence only",
        }
    summary = _require_object(raw, "adoption_summary")
    return {
        "risk_classes_detected": _string_list(summary.get("risk_classes_detected", []), "adoption_summary.risk_classes_detected"),
        "remediation_actions": _string_list(summary.get("remediation_actions", []), "adoption_summary.remediation_actions"),
        "operator_time_saved": str(summary.get("operator_time_saved", "not-measured")),
    }


def _reproduction(raw_entry: dict[str, Any]) -> dict[str, Any]:
    raw = raw_entry.get("reproduction")
    if raw is None:
        return {
            "commands": ["PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown"],
            "expected_outputs": ["benchmark pass=true with bounded states, counterexamples, prose findings, validity threats, and workflow baselines"],
            "budget": "standard-library Python; intended to run in seconds on a laptop",
        }
    repro = _require_object(raw, "reproduction")
    return {
        "commands": _non_empty_string_list(repro.get("commands", []), "reproduction.commands"),
        "expected_outputs": _non_empty_string_list(repro.get("expected_outputs", []), "reproduction.expected_outputs"),
        "budget": str(repro.get("budget", "")),
    }


def _expected_labels_from_benchmark_metadata(raw_entry: dict[str, Any]) -> dict[str, Any]:
    expected = _require_object(raw_entry["expected_result"], "expected_result")
    labels: dict[str, Any] = {"expected_safe": bool(expected["safe"])}
    labels["expected_violation_properties"] = sorted(_string_list(expected.get("violation_properties", []), "expected_result.violation_properties"))
    labels["expected_prose_rules"] = sorted(_string_list(expected.get("prose_rules", []), "expected_result.prose_rules"))
    return labels


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BenchmarkConfigError(f"benchmark field '{field_name}' must be an object")
    return value


def _require_bool(value: Any, field_name: str) -> None:
    if not isinstance(value, bool):
        raise BenchmarkConfigError(f"benchmark field '{field_name}' must be a boolean")


def _require_enum(value: str, field_name: str, choices: set[str]) -> str:
    if value not in choices:
        raise BenchmarkConfigError(f"benchmark field '{field_name}' must be one of: {', '.join(sorted(choices))}")
    return value


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise BenchmarkConfigError(f"benchmark field '{field_name}' must be a list of non-empty strings")
    return list(value)


def _non_empty_string_list(value: Any, field_name: str) -> list[str]:
    items = _string_list(value, field_name)
    if not items:
        raise BenchmarkConfigError(f"benchmark field '{field_name}' must contain at least one item")
    return items


def _expand_entry_path(path: Path) -> list[Path]:
    if not path.exists():
        raise BenchmarkConfigError(f"benchmark runbook path does not exist: {path}")
    if path.is_dir():
        return _runbook_files(path)
    if path.suffix.lower() not in RUNBOOK_SUFFIXES:
        raise BenchmarkConfigError(f"unsupported runbook file extension: {path}")
    return [path]


def _runbook_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in RUNBOOK_SUFFIXES)


def _run_one(entry: BenchmarkEntry) -> RunbookBenchmarkResult:
    started = time.perf_counter()
    expected_labels: dict[str, Any] | None = entry.expected_labels
    name = entry.name or entry.path.name
    try:
        doc = load_document(entry.path)
        expected_labels = entry.expected_labels or _expected_labels(doc)
        runbook = load_runbook(entry.path)
        name = entry.name or runbook.name
        result = Checker(runbook).check()
        violations = _violations_by_property(result)
        prose_findings = _prose_findings_by_rule(entry.path)
        passed, errors = _matches_expected(result.safe, violations, prose_findings, expected_labels)
        performance = result.performance_counters()
        return RunbookBenchmarkResult(
            path=str(entry.path),
            name=name,
            safe=result.safe,
            pass_=passed,
            states_explored=result.states_explored,
            traces_explored=result.traces_explored,
            violations_by_property=violations,
            prose_findings_by_rule=prose_findings,
            runtime_seconds=time.perf_counter() - started,
            performance_counters=performance,
            workflow_baselines=_workflow_baselines(True, result.safe, violations, prose_findings, performance, passed, []),
            expected_labels=expected_labels,
            benchmark_metadata=entry.benchmark_metadata,
            errors=errors,
        )
    except (RunbookParseError, BenchmarkConfigError, OSError, KeyError, TypeError, ValueError) as exc:
        errors = [str(exc)]
        return RunbookBenchmarkResult(
            path=str(entry.path),
            name=name,
            safe=False,
            pass_=False,
            states_explored=0,
            traces_explored=0,
            violations_by_property={},
            prose_findings_by_rule={},
            runtime_seconds=time.perf_counter() - started,
            performance_counters={},
            workflow_baselines=_workflow_baselines(False, False, {}, {}, {}, False, errors),
            expected_labels=expected_labels,
            benchmark_metadata=entry.benchmark_metadata,
            errors=errors,
        )


def _run_diff_baseline(entry: DiffBenchmarkEntry) -> DiffBenchmarkResult:
    try:
        result = diff_runbooks(entry.old_path, entry.new_path)
        summary = dict(result.summary)
        expected_errors = _diff_expected_errors(summary, entry.expected)
        return DiffBenchmarkResult(
            name=entry.name,
            old_path=str(entry.old_path),
            new_path=str(entry.new_path),
            pass_=result.pass_ and not expected_errors,
            summary=summary,
            expected=entry.expected,
            errors=expected_errors,
        )
    except (RunbookParseError, OSError, KeyError, TypeError, ValueError) as exc:
        return DiffBenchmarkResult(
            name=entry.name,
            old_path=str(entry.old_path),
            new_path=str(entry.new_path),
            pass_=False,
            summary={},
            expected=entry.expected,
            errors=[str(exc)],
        )


def _diff_expected_errors(summary: dict[str, Any], expected: dict[str, Any] | None) -> list[str]:
    if not expected:
        return []
    errors = []
    for key in ("introduced_counterexamples", "resolved_counterexamples", "assumption_weakenings", "safety_relevant_changes"):
        if key in expected and summary.get(key) != expected[key]:
            errors.append(f"expected {key}={expected[key]} but observed {summary.get(key)}")
    return errors


def _workflow_baselines(schema_pass: bool, safe: bool, violations: dict[str, int], prose_findings: dict[str, int], performance: dict[str, Any], combined_pass: bool, errors: list[str]) -> dict[str, Any]:
    proof_failures = performance.get("proof_obligation_failures", {}) if isinstance(performance, dict) else {}
    return {
        "schema_only_validation": {"pass": schema_pass, "errors": list(errors)},
        "prose_linting": {"pass": not prose_findings, "finding_count": sum(prose_findings.values()), "findings_by_rule": prose_findings},
        "bounded_checking": {"pass": safe, "counterexamples": sum(violations.values()), "violations_by_property": violations},
        "type_effect_checking": {"pass": not proof_failures, "proof_obligation_failures": proof_failures},
        "combined_workflow": {"pass": combined_pass, "uses": ["schema_only_validation", "prose_linting", "bounded_checking", "type_effect_checking", "semantic_diffing_when_configured"]},
    }


def _violations_by_property(result: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for violation in result.violations:
        counts[violation.property] = counts.get(violation.property, 0) + 1
    return dict(sorted(counts.items()))


def _expected_labels(doc: dict[str, Any]) -> dict[str, Any] | None:
    metadata = doc.get("metadata", {})
    if not isinstance(metadata, dict):
        return None
    labels = metadata.get("labels", {})
    if not isinstance(labels, dict) or not labels:
        return None
    expected: dict[str, Any] = {}
    if "expected_safe" in labels:
        expected["expected_safe"] = bool(labels["expected_safe"])
    props = labels.get("expected_violation_properties")
    if isinstance(props, list):
        expected["expected_violation_properties"] = sorted(str(prop) for prop in props)
    prose_rules = labels.get("expected_prose_rules")
    if isinstance(prose_rules, list):
        expected["expected_prose_rules"] = sorted(str(rule) for rule in prose_rules)
    return expected or None


def _matches_expected(safe: bool, violations: dict[str, int], prose_findings: dict[str, int], expected: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if expected is None:
        return True, []
    errors = []
    if "expected_safe" in expected and safe is not bool(expected["expected_safe"]):
        errors.append(f"expected_safe={expected['expected_safe']} but observed safe={safe}")
    expected_props = set(expected.get("expected_violation_properties", []))
    observed_props = set(violations)
    missing = sorted(expected_props - observed_props)
    if missing:
        errors.append(f"missing expected violation properties: {', '.join(missing)}")
    expected_prose = set(expected.get("expected_prose_rules", []))
    observed_prose = set(prose_findings)
    missing_prose = sorted(expected_prose - observed_prose)
    if missing_prose:
        errors.append(f"missing expected prose rules: {', '.join(missing_prose)}")
    return not errors, errors


def _prose_findings_by_rule(path: Path) -> dict[str, int]:
    if path.suffix.lower() != ".md":
        return {}
    counts: dict[str, int] = {}
    for finding in lint_markdown_file(path):
        counts[finding.rule] = counts.get(finding.rule, 0) + 1
    return dict(sorted(counts.items()))
