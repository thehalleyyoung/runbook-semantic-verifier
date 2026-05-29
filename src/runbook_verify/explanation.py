from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .actions import ActionError, apply_action
from .checker import Checker, Violation
from .markdown_lint import SEVERITY_RANK, lint_markdown_tree
from .model import Runbook, SystemState
from .parser import RunbookParseError, load_runbook


RULE_EXPLANATIONS: dict[str, dict[str, object]] = {
    "precondition": {
        "small_step_rule": "StepEnabled.Requires",
        "weakest_precondition_hint": "Before this action is enabled, an earlier step or explicit assumption must establish the failed `requires` condition.",
        "remediation_examples": ["Add an `after` dependency on the step that proves the condition.", "Add a concrete guard such as `region_healthy`, `database_quorum_confirmed`, or `service_available_at_least`."],
    },
    "service_min_available": {
        "small_step_rule": "ActionPreserves.ServiceAvailability",
        "weakest_precondition_hint": "The pre-state must contain enough healthy, undrained replicas that the action cannot reduce availability below `min_available`.",
        "remediation_examples": ["Scale or restore replacement replicas before draining.", "Add `service_available_at_least` preconditions/effects around capacity-changing steps."],
    },
    "no_queue_pause_without_drain_plan": {
        "small_step_rule": "ActionGuard.QueuePause",
        "weakest_precondition_hint": "Before pausing a queue, prove backlog is drained or enough alternate consumers exist.",
        "remediation_examples": ["Require `queue_depth_at_most` before pause.", "Require `queue_has_consumers` with enough consumers to process backlog safely."],
    },
    "no_paused_queue_with_backlog": {
        "small_step_rule": "PostInvariant.QueueBacklogProgress",
        "weakest_precondition_hint": "A terminal paused queue is safe only when backlog is bounded or alternate consumers remain active.",
        "remediation_examples": ["Resume the queue after the maintenance step.", "Drain backlog before pausing consumers."],
    },
    "no_replay_without_dedupe": {
        "small_step_rule": "ActionGuard.MessageReplayDeduplication",
        "weakest_precondition_hint": "Before replaying messages, the pre-state or action parameters must prove a dedupe key, idempotent handler, or bounded dedupe window.",
        "remediation_examples": ["Set `dedupe_key` on `replay_messages`.", "Add a positive `dedupe_window_minutes` queue assumption.", "Use `idempotent: true` only when the replay handler is documented idempotent."],
    },
    "no_duplicate_processing_risk": {
        "small_step_rule": "PostInvariant.NoDuplicateReplayProcessing",
        "weakest_precondition_hint": "A replay step may not leave the queue in a duplicate-risk state unless deduplication/idempotency was modeled.",
        "remediation_examples": ["Replay from the dead-letter queue with a stable dedupe key.", "Drain or quarantine duplicate-risk messages before resuming consumers."],
    },
    "dead_letter_replay_has_messages": {
        "small_step_rule": "ActionGuard.DeadLetterReplayBound",
        "weakest_precondition_hint": "The requested replay count must be bounded by the modeled dead-letter backlog.",
        "remediation_examples": ["Lower `count` to the modeled `dead_letter_depth`.", "Refresh the queue inventory before replay."],
    },
    "dead_letter_drain_has_messages": {
        "small_step_rule": "ActionGuard.DeadLetterDrainBound",
        "weakest_precondition_hint": "The requested drain count must be bounded by the modeled dead-letter backlog.",
        "remediation_examples": ["Lower `count` to the modeled `dead_letter_depth`.", "Inspect the DLQ before running the drain step."],
    },
    "no_rebalance_to_zero_consumers": {
        "small_step_rule": "ActionGuard.ConsumerRebalanceProgress",
        "weakest_precondition_hint": "A queue with backlog requires a positive post-rebalance consumer count.",
        "remediation_examples": ["Use `rebalance_consumers` with `consumers` greater than zero.", "Drain the queue before scaling consumers to zero."],
    },
    "queue_backlog_requires_consumers": {
        "small_step_rule": "PostInvariant.QueueBacklogHasConsumers",
        "weakest_precondition_hint": "Every reachable queue state with backlog must retain at least one active consumer.",
        "remediation_examples": ["Restore consumers before replay.", "Pause replay until consumer capacity is available."],
    },
    "no_unstable_consumer_group_with_backlog": {
        "small_step_rule": "PostInvariant.ConsumerGroupStableForBacklog",
        "weakest_precondition_hint": "Consumer-group rebalancing must converge before the runbook leaves backlog to be processed.",
        "remediation_examples": ["Set `stable: true` only after a modeled wait/health check.", "Add a `consumer_group_stable` effect to the stabilization step."],
    },
    "quorum_before_data_loss_action": {
        "small_step_rule": "ActionGuard.DatabaseFailoverQuorum",
        "weakest_precondition_hint": "A data-loss-risk failover requires database quorum/data-safety confirmation in the pre-state.",
        "remediation_examples": ["Run `confirm_quorum` before `failover_database`.", "Add a `database_quorum_confirmed` precondition to the failover step."],
    },
    "no_failover_to_unhealthy_region": {
        "small_step_rule": "ActionGuard.DatabaseTargetHealth",
        "weakest_precondition_hint": "The target region must be modeled healthy and listed among healthy database regions before failover.",
        "remediation_examples": ["Add a `region_healthy` precondition.", "Restore or choose a healthy target region before failover."],
    },
    "bounded_alert_suppression": {
        "small_step_rule": "ActionGuard.AlertSuppressionBound",
        "weakest_precondition_hint": "Alert suppression must have a positive finite expiry no greater than the configured safety bound.",
        "remediation_examples": ["Set `expires_after_minutes` to a bounded value.", "Lower the suppression duration or raise the explicit safety policy with review."],
    },
    "no_draining_load_balancer_with_traffic": {
        "small_step_rule": "ActionGuard.LoadBalancerDrainTraffic",
        "weakest_precondition_hint": "A regional load balancer may be drained only after weighted traffic to that region is 0%.",
        "remediation_examples": ["Run `failover_traffic` or `shift_traffic` before `drain_load_balancer`.", "Add `traffic_weight_at_most: 0` as a precondition."],
    },
    "no_traffic_to_unhealthy_region": {
        "small_step_rule": "RouteInvariant.TargetRegionHealthy",
        "weakest_precondition_hint": "Any region receiving positive traffic must be modeled healthy.",
        "remediation_examples": ["Require `region_healthy` before shifting traffic.", "Restore regional health or route elsewhere."],
    },
    "no_traffic_to_drained_load_balancer": {
        "small_step_rule": "RouteInvariant.LoadBalancerActive",
        "weakest_precondition_hint": "Any region receiving positive traffic must have an active, undrained load balancer.",
        "remediation_examples": ["Restore the load balancer before assigning traffic.", "Shift traffic away before draining the load balancer."],
    },
    "traffic_requires_regional_capacity": {
        "small_step_rule": "RouteInvariant.RegionalServiceCapacity",
        "weakest_precondition_hint": "A route can send positive traffic to a region only if the service has a healthy undrained replica there.",
        "remediation_examples": ["Scale service replicas in the target region first.", "Keep traffic on regions with available capacity."],
    },
    "traffic_weights_sum_to_100": {
        "small_step_rule": "RouteInvariant.NormalizedWeights",
        "weakest_precondition_hint": "Traffic weights form a total distribution and must sum to exactly 100.",
        "remediation_examples": ["Use `failover_traffic` for single-target routing.", "Pair `shift_traffic` changes so weights remain normalized."],
    },
}


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
            runbook = load_runbook(file)
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
        "small_step_rule": rule_info.get("small_step_rule", f"SafetyInvariant.{rule}"),
        "message": finding["message"],
        "trace": trace,
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
