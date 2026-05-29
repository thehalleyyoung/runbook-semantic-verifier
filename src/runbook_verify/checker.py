from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .actions import ActionError, apply_action, condition_holds
from .model import Runbook, Step, SystemState


@dataclass(frozen=True)
class Violation:
    property: str
    message: str
    trace: tuple[str, ...]
    step: str | None = None


@dataclass
class CheckResult:
    safe: bool
    violations: list[Violation] = field(default_factory=list)
    states_explored: int = 0
    traces_explored: int = 0


class Checker:
    """Bounded model checker over all dependency-respecting runbook step orders."""

    def __init__(self, runbook: Runbook):
        self.runbook = runbook
        self.steps_by_id = {s.id: s for s in runbook.steps}
        self.max_alert_suppression = int(runbook.safety.get("max_alert_suppression_minutes", 240))

    def check(self) -> CheckResult:
        result = CheckResult(safe=True)
        initial = (self.runbook.state, frozenset(), tuple())
        queue: deque[tuple[SystemState, frozenset[str], tuple[str, ...]]] = deque([initial])
        seen = set()
        while queue:
            state, done, trace = queue.popleft()
            key = (state.fingerprint(), done)
            if key in seen:
                continue
            seen.add(key)
            result.states_explored += 1
            if len(trace) >= self.runbook.max_depth or len(done) == len(self.runbook.steps):
                result.traces_explored += 1
                continue
            for step in self._enabled_steps(done):
                pre = self._pre_action_violations(state, step, trace)
                if pre:
                    result.violations.extend(pre)
                    result.safe = False
                try:
                    next_state = apply_action(state, step)
                except ActionError as exc:
                    result.violations.append(Violation("action_defined", str(exc), trace + (step.id,), step.id))
                    result.safe = False
                    continue
                post = self._post_action_violations(next_state, step, trace + (step.id,))
                if post:
                    result.violations.extend(post)
                    result.safe = False
                queue.append((next_state, done | {step.id}, trace + (step.id,)))
        result.violations = _dedupe_violations(result.violations)
        return result

    def _enabled_steps(self, done: frozenset[str]) -> list[Step]:
        if not self.runbook.allow_reordering:
            if len(done) >= len(self.runbook.steps):
                return []
            step = self.runbook.steps[len(done)]
            return [step] if all(dep in done for dep in step.after) else []
        return [step for step in self.runbook.steps if step.id not in done and all(dep in done for dep in step.after)]

    def _pre_action_violations(self, state: SystemState, step: Step, trace: tuple[str, ...]) -> list[Violation]:
        violations: list[Violation] = []
        for condition in step.requires:
            if not condition_holds(state, condition):
                violations.append(Violation("precondition", f"step {step.id} requires {condition}", trace + (step.id,), step.id))
        if step.action in {"drain_replica", "drain_region", "scale_service"}:
            violations.extend(self._availability_would_be_violated(state, step, trace))
        if step.action == "rollback_deployment":
            for db in state.databases.values():
                if db.migration_in_progress and not db.migration_compatible:
                    violations.append(Violation("no_rollback_during_incompatible_migration", f"rollback {step.id} while database {db.name} has incompatible migration in progress", trace + (step.id,), step.id))
        if step.action == "failover_database":
            db = state.databases[str(step.params["database"])]
            target = str(step.params["target_region"])
            if target not in db.healthy_regions or not state.regions.get(target, None) or not state.regions[target].healthy:
                violations.append(Violation("no_failover_to_unhealthy_region", f"database {db.name} failover target {target} is unhealthy", trace + (step.id,), step.id))
            if bool(step.params.get("data_loss_risk", False)) and not db.quorum_confirmed:
                violations.append(Violation("quorum_before_data_loss_action", f"database {db.name} failover has data-loss risk before quorum confirmation", trace + (step.id,), step.id))
        if step.action == "suppress_alert":
            expires = step.params.get("expires_after_minutes")
            if not isinstance(expires, int) or expires <= 0 or expires > self.max_alert_suppression:
                violations.append(Violation("bounded_alert_suppression", f"alert suppression {step.id} must have positive expiry <= {self.max_alert_suppression} minutes", trace + (step.id,), step.id))
        return violations

    def _post_action_violations(self, state: SystemState, step: Step, trace: tuple[str, ...]) -> list[Violation]:
        violations: list[Violation] = []
        for svc in state.services.values():
            if svc.available_count() < svc.min_available:
                violations.append(Violation("service_min_available", f"service {svc.name} has {svc.available_count()} available replicas; requires {svc.min_available}", trace, step.id))
            if svc.replicas and all(r.drained for r in svc.replicas):
                violations.append(Violation("no_draining_all_replicas", f"service {svc.name} has all replicas drained", trace, step.id))
        for condition in step.effects:
            if not condition_holds(state, condition):
                violations.append(Violation("effect", f"step {step.id} promised effect {condition}", trace, step.id))
        return violations

    def _availability_would_be_violated(self, state: SystemState, step: Step, trace: tuple[str, ...]) -> list[Violation]:
        try:
            next_state = apply_action(state, step)
        except ActionError as exc:
            return [Violation("action_defined", str(exc), trace + (step.id,), step.id)]
        return [
            Violation("service_min_available", f"step {step.id} would leave service {svc.name} with {svc.available_count()} available replicas; requires {svc.min_available}", trace + (step.id,), step.id)
            for svc in next_state.services.values()
            if svc.available_count() < svc.min_available
        ]


def _dedupe_violations(violations: list[Violation]) -> list[Violation]:
    seen: set[tuple[str, str, tuple[str, ...], str | None]] = set()
    unique: list[Violation] = []
    for violation in violations:
        key = (violation.property, violation.message, violation.trace, violation.step)
        if key not in seen:
            seen.add(key)
            unique.append(violation)
    return unique
