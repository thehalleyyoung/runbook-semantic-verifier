from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .checker import Checker
from .markdown_lint import MarkdownFinding, lint_markdown_file
from .parser import RunbookParseError, is_runbook_document, load_document, parse_runbook

RUNBOOK_SUFFIXES = {".json", ".yaml", ".yml", ".md"}


def build_formal_objects_report(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    if not root.exists():
        raise FormalObjectsError(f"formal-objects path does not exist: {root}")
    runbook_paths = _runbook_files(root)
    markdown_paths = _markdown_files(root)
    runbooks: list[dict[str, Any]] = []
    parse_diagnostics: list[dict[str, Any]] = []
    for file in runbook_paths:
        if file.suffix.lower() == ".md" and not _has_embedded_runbook(file):
            continue
        try:
            doc = load_document(file)
            if not is_runbook_document(doc):
                continue
            runbook = parse_runbook(doc, source_path=file)
        except RunbookParseError as exc:
            diagnostic = exc.with_context(path=str(file)).to_dict()
            parse_diagnostics.append(diagnostic)
            continue
        result = Checker(runbook).check()
        metadata = doc.get("metadata", {}) if isinstance(doc.get("metadata", {}), dict) else {}
        runbooks.append({
            "path": str(file),
            "syntax": {
                "object": "runbook_program",
                "mathematical_role": "A finite operational program with a declared initial store, dependency relation, bounded schedule budget, and guarded/effectful statements.",
                "cli_json_fields": ["runbooks[].syntax", "runbooks[].steps", "runbooks[].benchmark_labels"],
                "dsl_fields": sorted(key for key in doc if not str(key).startswith("__")),
                "name": runbook.name,
                "step_count": len(runbook.steps),
                "allow_reordering": runbook.allow_reordering,
                "max_depth": runbook.max_depth,
            },
            "entity_universe": _entity_universe(runbook.state),
            "store": {
                "object": "store",
                "mathematical_role": "The immutable infrastructure state over which action transformers execute.",
                "cli_json_fields": ["runbooks[].store", "runbooks[].entity_universe", "readiness.modeled_entities"],
                "clock_minute": runbook.state.clock_minute,
                "fingerprint_components": [
                    "regions",
                    "services",
                    "databases",
                    "queues",
                    "caches",
                    "alerts",
                    "feature_flags",
                    "deployments",
                    "traffic_routes",
                    "dns_records",
                ],
                "fingerprint_size": len(runbook.state.fingerprint()),
            },
            "steps": [
                {
                    "id": step.id,
                    "action": step.action,
                    "after": list(step.after),
                    "requires": list(step.requires),
                    "effects": list(step.effects),
                    "source": {"path": step.source_path, "line": step.source_line},
                    "cli_json_fields": ["audit.findings[].trace", "audit.findings[].semantic_trace", "check violations trace", "readiness.highest_risk_counterexamples[].trace"],
                }
                for step in runbook.steps
            ],
            "traces": {
                "object": "bounded_trace_set",
                "mathematical_role": "All dependency-respecting executions explored up to max_depth, with concrete counterexample prefixes when an obligation fails.",
                "cli_json_fields": ["runbooks[].traces", "benchmark.results[].performance", "readiness.highest_risk_counterexamples"],
                "states_explored": result.states_explored,
                "transitions_explored": result.transitions_explored,
                "terminal_traces": result.traces_explored,
                "max_depth_reached": result.max_depth_reached,
                "branch_points": result.branch_points,
                "avg_branch_factor": result.avg_branch_factor,
            },
            "hazards": {
                "object": "hazard_obligations",
                "mathematical_role": "Failed safety postconditions, preconditions, and action-definedness obligations witnessed by a trace.",
                "cli_json_fields": ["runbooks[].hazards", "audit.findings", "readiness.highest_risk_counterexamples", "benchmark.results[].observed_violation_properties"],
                "safe": result.safe,
                "properties": sorted({violation.property for violation in result.violations}),
                "counterexamples": [
                    {
                        "property": violation.property,
                        "step": violation.step,
                        "trace": list(violation.trace),
                        "small_step_rule": violation.small_step_rule,
                        "semantic_trace": list(violation.semantic_trace),
                        "message": violation.message,
                        "remediation": violation.remediation,
                    }
                    for violation in result.violations
                ],
                "proof_obligations_checked": dict(sorted(result.proof_obligations_checked.items())),
                "proof_obligation_failures": dict(sorted(result.proof_obligation_failures.items())),
            },
            "benchmark_labels": {
                "object": "benchmark_label",
                "mathematical_role": "Expected observations used as an external oracle for regression and public-case evidence, not as proof assumptions.",
                "cli_json_fields": ["runbooks[].benchmark_labels", "benchmark.results[].expected", "readiness.benchmark_expectations"],
                "labels": metadata.get("labels", {}),
                "owner": metadata.get("owner"),
                "owners": metadata.get("owners", []),
            },
        })
    prose_findings = [finding for file in markdown_paths for finding in lint_markdown_file(file)]
    observations = [_observation_record(finding) for finding in prose_findings]
    return {
        "path": str(root),
        "object_schema_version": "1.0",
        "summary": {
            "runbooks": len(runbooks),
            "parse_diagnostics": len(parse_diagnostics),
            "observations": len(observations),
            "hazard_counterexamples": sum(len(item["hazards"]["counterexamples"]) for item in runbooks),
            "waivers": sum(1 for item in observations if item["object"] == "waiver"),
        },
        "mathematical_objects": _object_definitions(),
        "runbooks": runbooks,
        "observations": observations,
        "diagnostics": {
            "object": "diagnostic",
            "mathematical_role": "A source-addressed rejection or warning emitted before or outside state-space exploration.",
            "cli_json_fields": ["diagnostics.parse", "validate diagnostics", "audit parse_errors"],
            "parse": parse_diagnostics,
        },
    }


def render_formal_objects_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_formal_objects_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Formal object map: {report['path']}",
        "",
        f"- Object schema version: `{report['object_schema_version']}`",
        f"- Executable runbooks: {report['summary']['runbooks']}",
        f"- Parse diagnostics: {report['summary']['parse_diagnostics']}",
        f"- Prose observations: {report['summary']['observations']}",
        f"- Hazard counterexamples: {report['summary']['hazard_counterexamples']}",
        f"- Waivers/limitations observed: {report['summary']['waivers']}",
        "",
        "## Object-to-CLI map",
        "",
        "| Object | Mathematical role | Primary CLI JSON fields |",
        "| --- | --- | --- |",
    ]
    for item in report["mathematical_objects"]:
        lines.append(f"| `{item['object']}` | {item['mathematical_role']} | `{', '.join(item['cli_json_fields'])}` |")
    lines.extend(["", "## Executable runbooks", ""])
    if report["runbooks"]:
        lines.extend(["| Path | Program | Steps | Entities | Safe | Counterexamples | Trace budget |", "| --- | --- | ---: | ---: | --- | ---: | --- |"])
        for item in report["runbooks"]:
            entity_count = sum(len(v) for v in item["entity_universe"]["names"].values())
            lines.append(
                f"| `{item['path']}` | {item['syntax']['name']} | {item['syntax']['step_count']} | {entity_count} | "
                f"`{item['hazards']['safe']}` | {len(item['hazards']['counterexamples'])} | max_depth={item['syntax']['max_depth']}, terminal={item['traces']['terminal_traces']} |"
            )
    else:
        lines.append("No executable runbooks were found.")
    lines.extend(["", "## Hazard obligations by runbook", ""])
    for item in report["runbooks"]:
        lines.append(f"### {item['path']}")
        if item["hazards"]["counterexamples"]:
            for violation in item["hazards"]["counterexamples"]:
                trace = " -> ".join(violation["trace"])
                lines.append(f"- `[{violation['property']}]` step `{violation['step']}` trace `{trace}`: {violation['message']}")
        else:
            lines.append("- No counterexamples within the configured bound.")
        lines.append("")
    lines.extend(["## Prose observations and waivers", ""])
    if report["observations"]:
        lines.extend(["| Object | Rule | Severity | Location | Obligation |", "| --- | --- | --- | --- | --- |"])
        for item in report["observations"]:
            lines.append(f"| `{item['object']}` | {item['rule']} | {item['severity']} | `{item['path']}:{item['line']}` | `{item['semantic_obligation']}` |")
    else:
        lines.append("No prose observations were found.")
    lines.append("")
    return "\n".join(lines) + "\n"


class FormalObjectsError(ValueError):
    pass


def _runbook_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() in RUNBOOK_SUFFIXES)


def _markdown_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*.md"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() == ".md")


def _has_embedded_runbook(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "```runbook-json" in text or "```json" in text


def _entity_universe(state: Any) -> dict[str, Any]:
    service_replicas = {
        name: [replica.id for replica in service.replicas]
        for name, service in state.services.items()
    }
    names = {
        "regions": sorted(state.regions),
        "services": sorted(state.services),
        "replicas": sorted(replica for replicas in service_replicas.values() for replica in replicas),
        "databases": sorted(state.databases),
        "queues": sorted(state.queues),
        "caches": sorted(state.caches),
        "alerts": sorted(state.alerts),
        "feature_flags": sorted(state.flags),
        "deployments": sorted(state.deployments),
        "traffic_routes": sorted(state.traffic_routes),
        "dns_records": sorted(state.dns_records),
    }
    return {
        "object": "entity_universe",
        "mathematical_role": "The finite typed names over which stores, action parameters, preconditions, and findings are interpreted.",
        "cli_json_fields": ["runbooks[].entity_universe", "coverage.entities", "readiness.modeled_entities"],
        "names": names,
        "service_replicas": service_replicas,
    }


def _observation_record(finding: MarkdownFinding) -> dict[str, Any]:
    return {
        "object": "waiver" if finding.rule == "prose-suppression-applied" else "observation",
        "rule": finding.rule,
        "severity": finding.severity,
        "path": finding.path,
        "line": finding.line,
        "excerpt": finding.excerpt,
        "message": finding.message,
        "recommendation": finding.recommendation,
        "semantic_obligation": finding.semantic_obligation,
        "autofix_suggestions": [asdict(suggestion) for suggestion in finding.autofix_suggestions],
        "cli_json_fields": ["observations[]", "audit.markdown_findings[]", "lint-markdown findings[]"],
    }


def _object_definitions() -> list[dict[str, Any]]:
    return [
        {
            "object": "syntax",
            "mathematical_role": "The parsed DSL/Markdown program, including steps, dependency edges, and bounded exploration settings.",
            "cli_json_fields": ["runbooks[].syntax", "runbooks[].steps"],
        },
        {
            "object": "entity_universe",
            "mathematical_role": "Finite typed identifiers for infrastructure objects referenced by actions and properties.",
            "cli_json_fields": ["runbooks[].entity_universe", "coverage.entities", "readiness.modeled_entities"],
        },
        {
            "object": "store",
            "mathematical_role": "Immutable infrastructure state transformed by small-step action semantics.",
            "cli_json_fields": ["runbooks[].store", "runbooks[].traces.states_explored"],
        },
        {
            "object": "trace",
            "mathematical_role": "A dependency-respecting action sequence plus mirrored small-step rule names explored within the runbook's max_depth budget.",
            "cli_json_fields": ["runbooks[].traces", "runbooks[].hazards.counterexamples[].trace", "runbooks[].hazards.counterexamples[].semantic_trace"],
        },
        {
            "object": "hazard",
            "mathematical_role": "A failed safety, precondition, effect, or action-definedness obligation with a witness trace.",
            "cli_json_fields": ["runbooks[].hazards", "readiness.highest_risk_counterexamples", "benchmark.results[].observed_violation_properties"],
        },
        {
            "object": "observation",
            "mathematical_role": "A source-addressed prose signal that is not automatically verified by the executable model.",
            "cli_json_fields": ["observations[]", "audit.markdown_findings[]", "lint-markdown findings[]"],
        },
        {
            "object": "diagnostic",
            "mathematical_role": "A parser/schema/entity rejection or warning with source and remediation metadata.",
            "cli_json_fields": ["diagnostics.parse", "validate diagnostics", "audit parse_errors"],
        },
        {
            "object": "waiver",
            "mathematical_role": "An auditable suppression or limitation record that preserves owner, expiry, reason, and linked obligation evidence.",
            "cli_json_fields": ["observations[rule=prose-suppression-applied]", "lint-markdown findings[]"],
        },
        {
            "object": "benchmark_label",
            "mathematical_role": "Expected safety/prose observations used as regression or public-case evidence labels.",
            "cli_json_fields": ["runbooks[].benchmark_labels", "benchmark.results[].expected", "readiness.benchmark_expectations"],
        },
    ]
