from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .actions import ActionError, apply_action
from .checker import Checker, Violation
from .model import Runbook, SystemState
from .parser import RunbookParseError, load_runbook


@dataclass(frozen=True)
class RuntimeEvent:
    index: int
    step: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class RuntimeDeviation:
    index: int
    step: str | None
    rule: str
    message: str
    expected: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    modeled_property: str | None = None
    remediation: str | None = None


@dataclass
class RuntimeVerificationReport:
    runbook: str
    log_path: str
    conformant: bool
    events_checked: int
    completed_steps: list[str]
    missing_steps: list[str]
    deviations: list[RuntimeDeviation]
    note: str = "Runtime verification checks observed event conformance against the bounded DSL model; it is not live-infrastructure proof."

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "runbook": self.runbook,
            "log_path": self.log_path,
            "conformant": self.conformant,
            "events_checked": self.events_checked,
            "completed_steps": self.completed_steps,
            "missing_steps": self.missing_steps,
            "deviations": [deviation.__dict__ for deviation in self.deviations],
            "note": self.note,
        }


class RuntimeVerificationError(ValueError):
    pass


def verify_runtime_log(runbook_path: str | Path, log_path: str | Path) -> RuntimeVerificationReport:
    try:
        runbook = load_runbook(runbook_path)
    except RunbookParseError:
        raise
    events = _load_events(log_path)
    checker = Checker(runbook)
    steps = {step.id: step for step in runbook.steps}
    state: SystemState = runbook.state
    done: set[str] = set()
    trace: list[str] = []
    deviations: list[RuntimeDeviation] = []
    for event in events:
        step = steps.get(event.step)
        enabled = [candidate.id for candidate in checker._enabled_steps(frozenset(done))]
        if step is None:
            deviations.append(RuntimeDeviation(event.index, event.step, "runtime_unknown_step", f"observed step {event.step!r} is not declared in the runbook", enabled, list(trace)))
            continue
        missing_deps = [dep for dep in step.after if dep not in done]
        if missing_deps:
            deviations.append(RuntimeDeviation(event.index, step.id, "runtime_dependency_violation", f"observed step {step.id!r} before dependencies completed: {', '.join(missing_deps)}", enabled, list(trace)))
            continue
        semantic_prefix: tuple[str, ...] = ()
        pre = checker._pre_action_violations(state, step, tuple(trace), semantic_prefix)
        if pre:
            for violation in pre:
                deviations.append(_deviation_from_violation(event.index, violation, enabled, trace, "runtime_precondition_violation"))
            # Keep checking later events from the modeled pre-state; an observed step
            # that violates preconditions is not trusted as a valid model transition.
            continue
        try:
            state = apply_action(state, step)
        except ActionError as exc:
            deviations.append(RuntimeDeviation(event.index, step.id, "runtime_action_error", str(exc), enabled, list(trace)))
            continue
        done.add(step.id)
        trace.append(step.id)
        post = checker._post_action_violations(state, step, tuple(trace), semantic_prefix)
        for violation in post:
            deviations.append(_deviation_from_violation(event.index, violation, enabled, trace, "runtime_postcondition_violation"))
    missing_steps = [step.id for step in runbook.steps if step.id not in done]
    return RuntimeVerificationReport(
        runbook=runbook.name,
        log_path=str(log_path),
        conformant=not deviations,
        events_checked=len(events),
        completed_steps=list(trace),
        missing_steps=missing_steps,
        deviations=deviations,
    )


def render_runtime_json(report: RuntimeVerificationReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_runtime_markdown(report: RuntimeVerificationReport) -> str:
    data = report.to_json_dict()
    lines = [
        f"# Runtime verification: {data['runbook']}",
        "",
        f"- Log: `{data['log_path']}`",
        f"- Conformant: `{data['conformant']}`",
        f"- Events checked: {data['events_checked']}",
        f"- Completed steps: `{json.dumps(data['completed_steps'])}`",
        f"- Missing modeled steps: `{json.dumps(data['missing_steps'])}`",
        f"- Scope note: {data['note']}",
        "",
    ]
    if data["deviations"]:
        lines.extend(["| Index | Rule | Step | Expected enabled | Trace | Message | Remediation |", "| ---: | --- | --- | --- | --- | --- | --- |"])
        for item in data["deviations"]:
            lines.append("| {index} | `{rule}` | `{step}` | `{expected}` | `{trace}` | {message} | {remediation} |".format(
                index=item["index"],
                rule=item["rule"],
                step=item.get("step") or "",
                expected=json.dumps(item.get("expected", [])),
                trace=" -> ".join(item.get("trace", [])),
                message=str(item["message"]).replace("|", "\\|"),
                remediation=str(item.get("remediation") or "").replace("|", "\\|"),
            ))
    else:
        lines.append("No runtime deviations found in the observed event prefix.")
    return "\n".join(lines) + "\n"


def _load_events(path: str | Path) -> list[RuntimeEvent]:
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeVerificationError(f"invalid runtime log JSON in {p}: {exc}") from exc
    raw_events: Any
    if isinstance(raw, list):
        raw_events = raw
    elif isinstance(raw, dict) and isinstance(raw.get("events"), list):
        raw_events = raw["events"]
    else:
        raise RuntimeVerificationError("runtime log must be a JSON list or an object with an 'events' list")
    events: list[RuntimeEvent] = []
    for index, item in enumerate(raw_events, start=1):
        if isinstance(item, str):
            events.append(RuntimeEvent(index, item, {"step": item}))
            continue
        if not isinstance(item, dict):
            raise RuntimeVerificationError(f"runtime events[{index - 1}] must be a string or object")
        step = item.get("step") or item.get("step_id") or item.get("runbook_step") or item.get("command")
        if not isinstance(step, str) or not step.strip():
            raise RuntimeVerificationError(f"runtime events[{index - 1}] must include a non-empty step/step_id/runbook_step/command")
        events.append(RuntimeEvent(index, step, item))
    return events


def _deviation_from_violation(index: int, violation: Violation, expected: list[str], trace: list[str], rule: str) -> RuntimeDeviation:
    return RuntimeDeviation(index, violation.step, rule, violation.message, expected, list(trace), violation.property, violation.remediation)
