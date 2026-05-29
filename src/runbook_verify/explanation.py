from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .actions import ActionError, apply_action
from .checker import Checker, Violation
from .markdown_lint import SEVERITY_RANK, lint_markdown_tree
from .model import Runbook, SystemState
from .parser import RunbookParseError, is_runbook_document, load_document, parse_runbook

from .semantics import RULE_EXPLANATIONS

def _explain_parse_finding(finding: dict[str, Any]) -> dict[str, Any]:
    source = _source_excerpt(str(finding["path"]), finding.get("line"))
    return {
        "id": finding["id"],
        "type": "parse",
        "rule": finding["rule"],
        "severity": finding["severity"],
        "semantic_obligation": finding["semantic_obligation"],
        "small_step_rule": "Parser.WellFormedExecutableModel",
        "message": finding["message"],
        "trace": [],
        "source": source,
        "state_delta": [],
        "weakest_precondition_hint": "The executable model must parse and pass schema/entity checks before operational semantics can be applied.",
        "remediation": finding["recommendation"],
        "remediation_examples": [finding["recommendation"]],
    }


class ExplainError(ValueError):
    pass


def explain_finding(path: str | Path, finding_id: str) -> dict[str, Any]:
    findings = collect_explain_findings(path)
    for item in findings:
        if item["finding"]["id"] == finding_id:
            if item["runbook"] is not None:
                return _explain_semantic_finding(item["finding"], item["runbook"])
            if item["finding"]["type"] == "parse":
                return _explain_parse_finding(item["finding"])
            return _explain_prose_finding(item["finding"])
    known = ", ".join(str(item["finding"]["id"]) for item in findings[:10])
    raise ExplainError(f"unknown finding id {finding_id!r}; known ids include: {known or '(none)'}")


def collect_explain_findings(path: str | Path) -> list[dict[str, Any]]:
    root = Path(path)
    if not root.exists():
        raise ExplainError(f"explain path does not exist: {root}")
    findings: list[dict[str, Any]] = []
    for prose in lint_markdown_tree(root):
        data = prose.__dict__.copy()
        data["type"] = "prose"
        data["rank"] = SEVERITY_RANK[data["severity"]]
        findings.append({"finding": data, "runbook": None})
    for file in _executable_runbook_files(root):
        try:
            doc = load_document(file)
            if not is_runbook_document(doc):
                continue
            runbook = parse_runbook(doc, source_path=file)
        except RunbookParseError as exc:
            contextual = exc.with_context(path=str(file))
            findings.append({
                "finding": {
                    "type": "parse",
                    "severity": "error",
                    "rank": SEVERITY_RANK["error"],
                    "path": str(file),
                    "line": contextual.diagnostic.line,
                    "rule": "parse_error",
                    "semantic_obligation": "well_formed_executable_model",
                    "message": str(contextual),
                    "recommendation": contextual.diagnostic.remediation,
                },
                "runbook": None,
            })
            continue
        for violation in Checker(runbook).check().violations:
            findings.append({"finding": _finding_from_violation(file, violation), "runbook": runbook})
    findings.sort(key=lambda item: (-int(item["finding"]["rank"]), str(item["finding"].get("path", "")), int(item["finding"].get("line") or 0), str(item["finding"].get("rule", ""))))
    for idx, item in enumerate(findings, start=1):
        item["finding"] = dict(item["finding"])
        item["finding"]["id"] = f"finding-{idx:03d}"
    return findings


def render_explanation_json(explanation: dict[str, Any]) -> str:
    return json.dumps(explanation, indent=2, sort_keys=True) + "\n"


def render_explanation_markdown(explanation: dict[str, Any]) -> str:
    lines = [
        f"# Finding explanation: {explanation['id']}",
        "",
        f"- Type: `{explanation['type']}`",
        f"- Rule: `{explanation['rule']}`",
        f"- Small-step rule: `{explanation['small_step_rule']}`",
        f"- Obligation: `{explanation['semantic_obligation']}`",
        f"- Location: `{explanation['source']['path']}:{explanation['source']['line'] or ''}`",
        f"- Message: {explanation['message']}",
        f"- Weakest-precondition hint: {explanation['weakest_precondition_hint']}",
        f"- Remediation: {explanation['remediation']}",
        "",
    ]
    if explanation.get("trace"):
        lines.extend(["## Trace", "", " -> ".join(explanation["trace"]), ""])
    if explanation.get("semantic_trace"):
        lines.extend(["## Small-step trace", ""])
        lines.extend(f"{idx}. `{rule}`" for idx, rule in enumerate(explanation["semantic_trace"], start=1))
        lines.append("")
    if explanation.get("state_delta"):
        lines.extend(["## State delta", "", "| Field | Before | After |", "| --- | --- | --- |"])
        for delta in explanation["state_delta"]:
            lines.append(f"| `{delta['field']}` | `{delta['before']}` | `{delta['after']}` |")
        lines.append("")
    if explanation.get("remediation_examples"):
        lines.extend(["## Remediation examples", ""])
        lines.extend(f"- {example}" for example in explanation["remediation_examples"])
        lines.append("")
    return "\n".join(lines)


def _finding_from_violation(path: Path, violation: Violation) -> dict[str, Any]:
    return {
        "type": "semantic",
        "severity": "error",
        "rank": SEVERITY_RANK["error"],
        "path": str(path),
        "line": None,
        "rule": violation.property,
        "semantic_obligation": violation.property,
        "step": violation.step,
        "trace": list(violation.trace),
        "semantic_trace": list(violation.semantic_trace),
        "small_step_rule": violation.small_step_rule,
        "message": violation.message,
        "recommendation": violation.remediation,
    }


def _explain_semantic_finding(finding: dict[str, Any], runbook: Runbook) -> dict[str, Any]:
    rule = str(finding["rule"])
    rule_info = RULE_EXPLANATIONS.get(rule, {})
    steps = {step.id: step for step in runbook.steps}
    step_id = str(finding.get("step") or "")
    step = steps.get(step_id)
    trace = [str(item) for item in finding.get("trace", [])]
    before = runbook.state
    for prior in trace:
        if prior == step_id:
            break
        if prior in steps:
            before = apply_action(before, steps[prior])
    after: SystemState | None = None
    action_error = None
    if step is not None:
        try:
            after = apply_action(before, step)
        except ActionError as exc:
            action_error = str(exc)
    source_path = step.source_path if step else str(finding.get("path", ""))
    source_line = step.source_line if step else finding.get("line")
    source = _source_excerpt(source_path, source_line)
    return {
        "id": finding["id"],
        "type": "semantic",
        "rule": rule,
        "severity": finding["severity"],
        "semantic_obligation": finding["semantic_obligation"],
        "small_step_rule": finding.get("small_step_rule") or rule_info.get("small_step_rule", f"SafetyInvariant.{rule}"),
        "message": finding["message"],
        "trace": trace,
        "semantic_trace": [str(item) for item in finding.get("semantic_trace", [])],
        "step": step_id or None,
        "action": step.action if step else None,
        "causal_dependencies": {
            "prior_trace_steps": [sid for sid in trace if sid != step_id],
            "declared_after": list(step.after) if step else [],
        },
        "source": source,
        "state_delta": _state_delta(before, after) if after is not None else [],
        "action_error": action_error,
        "weakest_precondition_hint": rule_info.get("weakest_precondition_hint", "Strengthen the runbook preconditions so this invariant holds before and after the action."),
        "remediation": finding.get("recommendation"),
        "remediation_examples": rule_info.get("remediation_examples", []),
    }


def _explain_prose_finding(finding: dict[str, Any]) -> dict[str, Any]:
    source = _source_excerpt(str(finding["path"]), int(finding["line"]))
    return {
        "id": finding["id"],
        "type": "prose",
        "rule": finding["rule"],
        "severity": finding["severity"],
        "semantic_obligation": finding["semantic_obligation"],
        "small_step_rule": f"ProseAudit.{finding['rule']}",
        "message": finding["message"],
        "trace": [],
        "source": source,
        "state_delta": [],
        "weakest_precondition_hint": "Map this prose claim to executable DSL actions/conditions, or document it as an explicit limitation/waiver.",
        "remediation": finding["recommendation"],
        "remediation_examples": [finding["recommendation"]],
    }


def _state_delta(before: SystemState, after: SystemState) -> list[dict[str, str]]:
    before_flat = _flatten(_state_projection(before))
    after_flat = _flatten(_state_projection(after))
    deltas = []
    for key in sorted(set(before_flat) | set(after_flat)):
        if before_flat.get(key) != after_flat.get(key):
            deltas.append({"field": key, "before": str(before_flat.get(key)), "after": str(after_flat.get(key))})
    return deltas[:40]


def _state_projection(state: SystemState) -> dict[str, Any]:
    return {
        "clock_minute": state.clock_minute,
        "regions": {name: {"healthy": region.healthy} for name, region in state.regions.items()},
        "services": {
            name: {
                "available": svc.available_count(),
                "min_available": svc.min_available,
                "replicas": {replica.id: {"region": replica.region, "healthy": replica.healthy, "drained": replica.drained} for replica in svc.replicas},
            }
            for name, svc in state.services.items()
        },
        "databases": {name: {"primary_region": db.primary_region, "quorum_confirmed": db.quorum_confirmed, "migration_in_progress": db.migration_in_progress, "migration_compatible": db.migration_compatible} for name, db in state.databases.items()},
        "queues": {
            name: {
                "depth": q.depth,
                "consumers": q.consumers,
                "paused": q.paused,
                "dead_letter_depth": q.dead_letter_depth,
                "dedupe_window_minutes": q.dedupe_window_minutes,
                "duplicate_risk": q.duplicate_risk,
                "consumer_group_stable": q.consumer_group_stable,
            }
            for name, q in state.queues.items()
        },
        "alerts": {name: {"active": alert.active, "suppressed_until_minute": alert.suppressed_until_minute} for name, alert in state.alerts.items()},
        "traffic_routes": {name: {"weights": route.weights, "drained_regions": sorted(route.drained_regions)} for name, route in state.traffic_routes.items()},
    }


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten(child, child_prefix))
        return out
    return {prefix: value}


def _source_excerpt(path: str | None, line: int | None) -> dict[str, Any]:
    if not path or line is None:
        return {"path": path, "line": line, "excerpt": None}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        excerpt = lines[line - 1].strip() if 0 < line <= len(lines) else None
    except OSError:
        excerpt = None
    return {"path": path, "line": line, "excerpt": excerpt}


def _executable_runbook_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml", ".md"} and (path.suffix.lower() != ".md" or _has_embedded_runbook(path)))


def _has_embedded_runbook(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "```runbook-json" in text or "```json" in text
