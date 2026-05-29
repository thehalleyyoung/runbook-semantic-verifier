from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checker import Checker, CheckResult, Violation
from .model import Runbook, Step, SystemState
from .parser import load_runbook


@dataclass(frozen=True)
class SemanticDiffResult:
    old_path: str
    new_path: str
    old_name: str
    new_name: str
    old_safe: bool
    new_safe: bool
    pass_: bool
    summary: dict[str, Any]
    changes: list[dict[str, Any]]
    introduced_counterexamples: list[dict[str, Any]]
    resolved_counterexamples: list[dict[str, Any]]
    persisting_counterexamples: list[dict[str, Any]]
    semantic_obligation_deltas: dict[str, Any]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "old_path": self.old_path,
            "new_path": self.new_path,
            "old_name": self.old_name,
            "new_name": self.new_name,
            "old_safe": self.old_safe,
            "new_safe": self.new_safe,
            "pass": self.pass_,
            "summary": self.summary,
            "changes": self.changes,
            "introduced_counterexamples": self.introduced_counterexamples,
            "resolved_counterexamples": self.resolved_counterexamples,
            "persisting_counterexamples": self.persisting_counterexamples,
            "semantic_obligation_deltas": self.semantic_obligation_deltas,
        }


def diff_runbooks(old_path: str | Path, new_path: str | Path) -> SemanticDiffResult:
    old = load_runbook(old_path)
    new = load_runbook(new_path)
    old_result = Checker(old).check()
    new_result = Checker(new).check()
    changes = _diff_models(old, new)
    introduced, resolved, persisting = _counterexample_delta(old_result, new_result)
    assumption_weakening = sum(1 for change in changes if change["classification"] == "assumption_weakening")
    safety_relevant = sum(1 for change in changes if change["classification"] in {"safety_relevant", "assumption_weakening"})
    summary = {
        "changes": len(changes),
        "effect_changes": sum(1 for change in changes if change["field"] == "effects"),
        "assumption_changes": sum(1 for change in changes if change["field"] in {"requires", "value"} or change["classification"] == "assumption_weakening"),
        "invariant_changes": sum(1 for change in changes if change["kind"] == "invariant_changed"),
        "safety_relevant_changes": safety_relevant,
        "assumption_weakenings": assumption_weakening,
        "introduced_counterexamples": len(introduced),
        "resolved_counterexamples": len(resolved),
        "persisting_counterexamples": len(persisting),
        "waiver_changes": 0,
        "old_states_explored": old_result.states_explored,
        "new_states_explored": new_result.states_explored,
    }
    pass_ = not introduced and assumption_weakening == 0
    return SemanticDiffResult(
        old_path=str(old_path),
        new_path=str(new_path),
        old_name=old.name,
        new_name=new.name,
        old_safe=old_result.safe,
        new_safe=new_result.safe,
        pass_=pass_,
        summary=summary,
        changes=changes,
        introduced_counterexamples=introduced,
        resolved_counterexamples=resolved,
        persisting_counterexamples=persisting,
        semantic_obligation_deltas=_obligation_deltas(old_result, new_result),
    )


def render_diff_json(result: SemanticDiffResult) -> str:
    return json.dumps(result.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_diff_markdown(result: SemanticDiffResult) -> str:
    data = result.to_json_dict()
    lines = [
        f"# Semantic diff: {Path(result.old_path).name} → {Path(result.new_path).name}",
        "",
        f"- Pass: `{data['pass']}`",
        f"- Old safe: `{result.old_safe}`",
        f"- New safe: `{result.new_safe}`",
        f"- Changes: {result.summary['changes']}",
        f"- Effect changes: {result.summary['effect_changes']}",
        f"- Assumption changes: {result.summary['assumption_changes']}",
        f"- Invariant changes: {result.summary['invariant_changes']}",
        f"- Safety-relevant changes: {result.summary['safety_relevant_changes']}",
        f"- Assumption weakenings: {result.summary['assumption_weakenings']}",
        f"- Introduced counterexamples: {result.summary['introduced_counterexamples']}",
        f"- Resolved counterexamples: {result.summary['resolved_counterexamples']}",
        f"- Persisting counterexamples: {result.summary['persisting_counterexamples']}",
        "",
        "## Changed semantics",
        "",
    ]
    if result.changes:
        lines.extend([
            "| Classification | Kind | Object | Field | Old | New |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for change in result.changes:
            lines.append(
                "| `{classification}` | `{kind}` | `{object}` | `{field}` | `{old}` | `{new}` |".format(
                    classification=change["classification"],
                    kind=change["kind"],
                    object=str(change["object"]).replace("|", "\\|"),
                    field=str(change["field"]).replace("|", "\\|"),
                    old=_cell(change.get("old")),
                    new=_cell(change.get("new")),
                )
            )
    else:
        lines.append("No semantic changes detected.")
    lines.extend(["", "## Counterexample delta", ""])
    for title, items in [
        ("Introduced", result.introduced_counterexamples),
        ("Resolved", result.resolved_counterexamples),
        ("Persisting", result.persisting_counterexamples),
    ]:
        lines.append(f"### {title}")
        lines.append("")
        if not items:
            lines.append("None.")
            lines.append("")
            continue
        for item in items:
            trace = " -> ".join(item["trace"])
            lines.append(f"- `[{item['property']}]` step `{item.get('step')}` trace `{trace}`: {item['message']}")
        lines.append("")
    lines.extend([
        "## Proof-obligation delta",
        "",
        "```json",
        json.dumps(result.semantic_obligation_deltas, indent=2, sort_keys=True),
        "```",
        "",
    ])
    return "\n".join(lines)


def _diff_models(old: Runbook, new: Runbook) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    _append_config_change(changes, "runbook", "allow_reordering", old.allow_reordering, new.allow_reordering)
    _append_config_change(changes, "runbook", "max_depth", old.max_depth, new.max_depth)
    for key in sorted(set(old.safety) | set(new.safety)):
        _append_config_change(changes, "invariant_changed", key, old.safety.get(key), new.safety.get(key))
    old_order = [step.id for step in old.steps]
    new_order = [step.id for step in new.steps]
    if old_order != new_order:
        _append_change(changes, "safety_relevant", "step_order_changed", "runbook", "steps", old_order, new_order)

    old_steps = {step.id: step for step in old.steps}
    new_steps = {step.id: step for step in new.steps}
    for step_id in sorted(set(old_steps) - set(new_steps)):
        _append_change(changes, "safety_relevant", "step_removed", step_id, "step", _step_signature(old_steps[step_id]), None)
    for step_id in sorted(set(new_steps) - set(old_steps)):
        _append_change(changes, "safety_relevant", "step_added", step_id, "step", None, _step_signature(new_steps[step_id]))
    for step_id in sorted(set(old_steps) & set(new_steps)):
        _diff_step(changes, old_steps[step_id], new_steps[step_id])

    old_state = _state_signature(old.state)
    new_state = _state_signature(new.state)
    for field in sorted(set(old_state) | set(new_state)):
        old_value = old_state.get(field)
        new_value = new_state.get(field)
        if old_value != new_value:
            _append_change(changes, _state_change_classification(field, old_value, new_value), "state_changed", field, "value", old_value, new_value)
    return changes


def _diff_step(changes: list[dict[str, Any]], old: Step, new: Step) -> None:
    for field in ("action", "params", "after", "requires", "effects"):
        old_value = _normal(old, field)
        new_value = _normal(new, field)
        if old_value == new_value:
            continue
        classification = "behavior_preserving"
        if field in {"action", "params", "after"}:
            classification = "safety_relevant"
        if field == "requires" and len(json.dumps(new_value, sort_keys=True)) < len(json.dumps(old_value, sort_keys=True)):
            classification = "assumption_weakening"
        if field == "effects":
            classification = "proof_obligation_changed"
        _append_change(changes, classification, "step_changed", old.id, field, old_value, new_value)


def _append_config_change(changes: list[dict[str, Any]], kind: str, field: str, old: Any, new: Any) -> None:
    if old == new:
        return
    classification = "safety_relevant"
    if field == "max_depth" and isinstance(old, int) and isinstance(new, int) and new < old:
        classification = "assumption_weakening"
    if field == "allow_reordering" and old is True and new is False:
        classification = "assumption_weakening"
    if field == "max_alert_suppression_minutes" and isinstance(old, int) and isinstance(new, int) and new > old:
        classification = "assumption_weakening"
    _append_change(changes, classification, kind, kind, field, old, new)


def _append_change(changes: list[dict[str, Any]], classification: str, kind: str, object_name: str, field: str, old: Any, new: Any) -> None:
    changes.append({
        "classification": classification,
        "kind": kind,
        "object": object_name,
        "field": field,
        "old": old,
        "new": new,
    })


def _counterexample_delta(old: CheckResult, new: CheckResult) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    old_map = {_violation_key(v): _violation_dict(v) for v in old.violations}
    new_map = {_violation_key(v): _violation_dict(v) for v in new.violations}
    introduced = [new_map[key] for key in sorted(set(new_map) - set(old_map))]
    resolved = [old_map[key] for key in sorted(set(old_map) - set(new_map))]
    persisting = [new_map[key] for key in sorted(set(new_map) & set(old_map))]
    return introduced, resolved, persisting


def _violation_key(violation: Violation) -> tuple[str, str | None, str]:
    return (violation.property, violation.step, violation.message)


def _violation_dict(violation: Violation) -> dict[str, Any]:
    return {
        "property": violation.property,
        "step": violation.step,
        "message": violation.message,
        "trace": list(violation.trace),
        "remediation": violation.remediation,
    }


def _obligation_deltas(old: CheckResult, new: CheckResult) -> dict[str, Any]:
    groups = sorted(set(old.proof_obligations_checked) | set(new.proof_obligations_checked) | set(old.proof_obligation_failures) | set(new.proof_obligation_failures))
    return {
        group: {
            "checked": {
                "old": old.proof_obligations_checked.get(group, 0),
                "new": new.proof_obligations_checked.get(group, 0),
                "delta": new.proof_obligations_checked.get(group, 0) - old.proof_obligations_checked.get(group, 0),
            },
            "failures": {
                "old": old.proof_obligation_failures.get(group, 0),
                "new": new.proof_obligation_failures.get(group, 0),
                "delta": new.proof_obligation_failures.get(group, 0) - old.proof_obligation_failures.get(group, 0),
            },
        }
        for group in groups
    }


def _step_signature(step: Step) -> dict[str, Any]:
    return {
        "action": step.action,
        "params": _stable(step.params),
        "after": list(step.after),
        "requires": _stable(list(step.requires)),
        "effects": _stable(list(step.effects)),
        "source_line": step.source_line,
    }


def _normal(step: Step, field: str) -> Any:
    value = getattr(step, field)
    if isinstance(value, tuple):
        return _stable(list(value))
    return _stable(value)


def _state_signature(state: SystemState) -> dict[str, Any]:
    data: dict[str, Any] = {"clock_minute": state.clock_minute}
    for name, region in state.regions.items():
        data[f"regions.{name}.healthy"] = region.healthy
    for name, service in state.services.items():
        data[f"services.{name}.min_available"] = service.min_available
        data[f"services.{name}.deployment"] = service.deployment
        data[f"services.{name}.replicas"] = sorted((r.id, r.region, r.healthy, r.drained) for r in service.replicas)
    for name, db in state.databases.items():
        data[f"databases.{name}.primary_region"] = db.primary_region
        data[f"databases.{name}.healthy_regions"] = sorted(db.healthy_regions)
        data[f"databases.{name}.quorum_confirmed"] = db.quorum_confirmed
        data[f"databases.{name}.migration_in_progress"] = db.migration_in_progress
        data[f"databases.{name}.migration_compatible"] = db.migration_compatible
    for name, queue in state.queues.items():
        data[f"queues.{name}.depth"] = queue.depth
        data[f"queues.{name}.consumers"] = queue.consumers
        data[f"queues.{name}.paused"] = queue.paused
    for name, alert in state.alerts.items():
        data[f"alerts.{name}.active"] = alert.active
        data[f"alerts.{name}.suppressed_until_minute"] = alert.suppressed_until_minute
    for name, flag in state.flags.items():
        data[f"feature_flags.{name}.enabled"] = flag.enabled
    for name, route in state.traffic_routes.items():
        data[f"traffic_routes.{name}.service"] = route.service
        data[f"traffic_routes.{name}.weights"] = dict(sorted(route.weights.items()))
        data[f"traffic_routes.{name}.drained_regions"] = sorted(route.drained_regions)
    for name, record in state.dns_records.items():
        data[f"dns_records.{name}.service"] = record.service
        data[f"dns_records.{name}.region"] = record.region
        data[f"dns_records.{name}.ttl_minutes"] = record.ttl_minutes
        data[f"dns_records.{name}.last_changed_minute"] = record.last_changed_minute
        data[f"dns_records.{name}.previous_region"] = record.previous_region
        data[f"dns_records.{name}.health_check_converged_regions"] = sorted(record.health_check_converged_regions)
        data[f"dns_records.{name}.allow_split_brain"] = record.allow_split_brain
    return data


def _state_change_classification(field: str, old: Any, new: Any) -> str:
    if field.endswith(".min_available") and isinstance(old, int) and isinstance(new, int) and new < old:
        return "assumption_weakening"
    if field.endswith(".quorum_confirmed") and old is False and new is True:
        return "assumption_weakening"
    if field.endswith(".healthy") and old is False and new is True:
        return "assumption_weakening"
    if field.endswith(".depth") and isinstance(old, int) and isinstance(new, int) and new < old:
        return "assumption_weakening"
    if field.endswith(".consumers") and isinstance(old, int) and isinstance(new, int) and new > old:
        return "assumption_weakening"
    if field.endswith(".allow_split_brain") and old is False and new is True:
        return "assumption_weakening"
    if field.endswith(".ttl_minutes") and isinstance(old, int) and isinstance(new, int) and new < old:
        return "assumption_weakening"
    return "safety_relevant"


def _stable(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, sort_keys=True).replace("|", "\\|")
