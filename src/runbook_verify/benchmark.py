from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .checker import Checker
from .parser import RunbookParseError, load_document, load_runbook

RUNBOOK_SUFFIXES = {".json", ".yaml", ".yml", ".md"}


@dataclass(frozen=True)
class BenchmarkEntry:
    path: Path
    name: str | None = None


@dataclass
class RunbookBenchmarkResult:
    path: str
    name: str
    safe: bool
    pass_: bool
    states_explored: int
    traces_explored: int
    violations_by_property: dict[str, int]
    runtime_seconds: float
    expected_labels: dict[str, Any] | None = None
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

    @property
    def pass_(self) -> bool:
        return all(item.pass_ for item in self.runbooks)

    def to_json_dict(self) -> dict[str, Any]:
        aggregate: dict[str, Any] = {
            "runbooks": len(self.runbooks),
            "states_explored": sum(item.states_explored for item in self.runbooks),
            "traces_explored": sum(item.traces_explored for item in self.runbooks),
            "violations_by_property": {},
            "runtime_seconds": self.runtime_seconds,
            "pass": self.pass_,
        }
        for item in self.runbooks:
            for prop, count in item.violations_by_property.items():
                aggregate["violations_by_property"][prop] = aggregate["violations_by_property"].get(prop, 0) + count
        return {
            "name": self.name,
            "aggregate": aggregate,
            "runbooks": [item.to_json_dict() for item in self.runbooks],
        }


def run_benchmark(path: str | Path | None = None) -> BenchmarkSuiteResult:
    root = Path.cwd()
    if path is None:
        suite_name = "built-in benchmark"
        entries = [
            BenchmarkEntry(root / "examples" / "safe_runbook.json"),
            BenchmarkEntry(root / "examples" / "unsafe_runbook.json"),
            BenchmarkEntry(root / "examples" / "real_world" / "kubernetes_region_failover.md"),
            BenchmarkEntry(root / "case_studies" / "github_oct21_2018" / "github_oct21_reconstructed_runbook.md"),
        ]
    else:
        config_path = Path(path)
        if not config_path.exists():
            raise BenchmarkConfigError(f"benchmark path does not exist: {config_path}")
        if config_path.is_dir():
            suite_name = str(config_path)
            entries = [BenchmarkEntry(p) for p in _runbook_files(config_path)]
        elif config_path.suffix.lower() == ".json":
            suite_name, entries = _load_config(config_path)
        elif config_path.suffix.lower() in RUNBOOK_SUFFIXES:
            suite_name = str(config_path)
            entries = [BenchmarkEntry(config_path)]
        else:
            raise BenchmarkConfigError(f"unsupported benchmark input {config_path}; use a directory, config .json, or runbook file")

    if not entries:
        raise BenchmarkConfigError("benchmark has no runbook entries")

    started = time.perf_counter()
    runbooks = [_run_one(entry) for entry in entries]
    return BenchmarkSuiteResult(suite_name, runbooks, time.perf_counter() - started)


def render_json(result: BenchmarkSuiteResult) -> str:
    return json.dumps(result.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_markdown(result: BenchmarkSuiteResult) -> str:
    data = result.to_json_dict()
    aggregate = data["aggregate"]
    lines = [
        f"# Benchmark: {result.name}",
        "",
        f"- Pass: `{aggregate['pass']}`",
        f"- Runbooks: {aggregate['runbooks']}",
        f"- States explored: {aggregate['states_explored']}",
        f"- Traces explored: {aggregate['traces_explored']}",
        f"- Runtime seconds: {aggregate['runtime_seconds']:.6f}",
        f"- Violations by property: `{json.dumps(aggregate['violations_by_property'], sort_keys=True)}`",
        "",
        "| Runbook | Pass | Safe | States | Traces | Runtime (s) | Violations | Expected labels |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in data["runbooks"]:
        lines.append(
            "| {name} | `{pass_}` | `{safe}` | {states} | {traces} | {runtime:.6f} | `{violations}` | `{expected}` |".format(
                name=item["name"].replace("|", "\\|"),
                pass_=item["pass"],
                safe=item["safe"],
                states=item["states_explored"],
                traces=item["traces_explored"],
                runtime=item["runtime_seconds"],
                violations=json.dumps(item["violations_by_property"], sort_keys=True),
                expected=json.dumps(item["expected_labels"], sort_keys=True) if item["expected_labels"] else "",
            )
        )
    return "\n".join(lines) + "\n"


class BenchmarkConfigError(ValueError):
    pass


def _load_config(path: Path) -> tuple[str, list[BenchmarkEntry]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkConfigError(f"invalid benchmark config JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise BenchmarkConfigError("benchmark config must be a JSON object")
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
        entries.extend(BenchmarkEntry(p, raw_entry.get("name")) for p in _expand_entry_path(entry_path))
    return suite_name, entries


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
    expected_labels: dict[str, Any] | None = None
    name = entry.name or entry.path.name
    try:
        doc = load_document(entry.path)
        expected_labels = _expected_labels(doc)
        runbook = load_runbook(entry.path)
        name = entry.name or runbook.name
        result = Checker(runbook).check()
        violations = _violations_by_property(result)
        passed, errors = _matches_expected(result.safe, violations, expected_labels)
        return RunbookBenchmarkResult(
            path=str(entry.path),
            name=name,
            safe=result.safe,
            pass_=passed,
            states_explored=result.states_explored,
            traces_explored=result.traces_explored,
            violations_by_property=violations,
            runtime_seconds=time.perf_counter() - started,
            expected_labels=expected_labels,
            errors=errors,
        )
    except (RunbookParseError, BenchmarkConfigError, OSError, KeyError, TypeError, ValueError) as exc:
        return RunbookBenchmarkResult(
            path=str(entry.path),
            name=name,
            safe=False,
            pass_=False,
            states_explored=0,
            traces_explored=0,
            violations_by_property={},
            runtime_seconds=time.perf_counter() - started,
            expected_labels=expected_labels,
            errors=[str(exc)],
        )


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
    return expected or None


def _matches_expected(safe: bool, violations: dict[str, int], expected: dict[str, Any] | None) -> tuple[bool, list[str]]:
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
    return not errors, errors
