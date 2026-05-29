from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from typing import Any

from .actions import ActionError, apply_action, condition_holds
from .model import Runbook, Step, SystemState
from .semantics import (
    ACTION_EXECUTE,
    ACTION_WAIT,
    EXPLORE_BUDGET_REACHED,
    EXPLORE_TERMINAL,
    action_rule,
    label_rule,
    scheduling_rules,
    small_step_rule,
)


@dataclass(frozen=True)
class Violation:
    property: str
    message: str
    trace: tuple[str, ...]
    step: str | None = None
    remediation: str | None = None
    small_step_rule: str | None = None
    semantic_trace: tuple[str, ...] = ()


@dataclass
class CheckResult:
    safe: bool
    violations: list[Violation] = field(default_factory=list)
    states_explored: int = 0
    traces_explored: int = 0
    max_depth_reached: bool = False
    transitions_explored: int = 0
    branch_points: int = 0
    branch_factor_total: int = 0
    max_branch_factor: int = 0
    reductions_applied: int = 0
    symbolic_splits: int = 0
    proof_obligations_checked: dict[str, int] = field(default_factory=dict)
    proof_obligation_failures: dict[str, int] = field(default_factory=dict)
    semantic_rule_counts: dict[str, int] = field(default_factory=dict)

    @property
    def avg_branch_factor(self) -> float:
        return self.branch_factor_total / self.branch_points if self.branch_points else 0.0

    @property
    def minimized_counterexample_trace_length(self) -> int | None:
        if not self.violations:
            return None
        return min(len(violation.trace) for violation in self.violations)

    def performance_counters(self) -> dict[str, Any]:
        return {
            "states_explored": self.states_explored,
            "transitions_explored": self.transitions_explored,
            "terminal_traces": self.traces_explored,
            "max_depth_reached": self.max_depth_reached,
            "branch_points": self.branch_points,
            "branch_factor_total": self.branch_factor_total,
            "avg_branch_factor": self.avg_branch_factor,
            "max_branch_factor": self.max_branch_factor,
            "reductions_applied": self.reductions_applied,
            "symbolic_splits": self.symbolic_splits,
            "minimized_counterexample_trace_length": self.minimized_counterexample_trace_length,
            "proof_obligations_checked": dict(sorted(self.proof_obligations_checked.items())),
            "proof_obligation_failures": dict(sorted(self.proof_obligation_failures.items())),
            "semantic_rule_counts": dict(sorted(self.semantic_rule_counts.items())),
        }


class Checker:
    """Bounded model checker over all dependency-respecting runbook step orders."""

    def __init__(self, runbook: Runbook):
        self.runbook = runbook
        self.steps_by_id = {s.id: s for s in runbook.steps}
        self.max_alert_suppression = int(runbook.safety.get("max_alert_suppression_minutes", 240))

    def check(self) -> CheckResult:
        result = CheckResult(safe=True)
        initial = (self.runbook.state, frozenset(), tuple(), tuple())
        queue: deque[tuple[SystemState, frozenset[str], tuple[str, ...], tuple[str, ...]]] = deque([initial])
        seen = set()
        while queue:
            state, done, trace, semantic_trace = queue.popleft()
            key = (state.fingerprint(), done)
            if key in seen:
                continue
            seen.add(key)
            result.states_explored += 1
            if len(trace) >= self.runbook.max_depth or len(done) == len(self.runbook.steps):
                result.traces_explored += 1
                if len(trace) >= self.runbook.max_depth and len(done) < len(self.runbook.steps):
                    result.max_depth_reached = True
                    _record_rule(result, EXPLORE_BUDGET_REACHED)
                else:
                    _record_rule(result, EXPLORE_TERMINAL)
                continue
            enabled = self._enabled_steps(done)
            result.branch_points += 1
            result.branch_factor_total += len(enabled)
            result.max_branch_factor = max(result.max_branch_factor, len(enabled))
            for step in enabled:
                result.transitions_explored += 1
                schedule_trace = semantic_trace + scheduling_rules(step, len(enabled), self.runbook.allow_reordering)
                _record_labeled_rules(result, schedule_trace[len(semantic_trace):])
                pre = self._pre_action_violations(state, step, trace, schedule_trace)
                _record_obligations(result, "precondition", len(step.requires), pre)
                if pre:
                    result.violations.extend(pre)
                    for violation in pre:
                        if violation.small_step_rule:
                            _record_rule(result, violation.small_step_rule)
                    result.safe = False
                try:
                    next_state = apply_action(state, step)
                except ActionError as exc:
                    failure_trace = schedule_trace + (label_rule(small_step_rule("action_defined"), step.id),)
                    _record_labeled_rules(result, failure_trace[len(schedule_trace):])
                    violation = _violation("action_defined", str(exc), trace + (step.id,), step.id, failure_trace)
                    _record_obligations(result, "action_defined", 1, [violation])
                    if violation.small_step_rule:
                        _record_rule(result, violation.small_step_rule)
                    result.violations.append(violation)
                    result.safe = False
                    continue
                _record_obligations(result, "action_defined", 1, [])
                next_semantic_trace = schedule_trace + (label_rule(action_rule(step), step.id),)
                _record_labeled_rules(result, next_semantic_trace[len(schedule_trace):])
                post = self._post_action_violations(next_state, step, trace + (step.id,), next_semantic_trace)
                _record_obligations(result, "safety_postcondition", _safety_obligation_count(next_state), post)
                _record_obligations(result, "promised_effect", len(step.effects), [v for v in post if v.property in {"effect", "effect_defined"}])
                if post:
                    result.violations.extend(post)
                    for violation in post:
                        if violation.small_step_rule:
                            _record_rule(result, violation.small_step_rule)
                    result.safe = False
                queue.append((next_state, done | {step.id}, trace + (step.id,), next_semantic_trace))
        result.violations = _dedupe_violations(result.violations)
        return result

    def _enabled_steps(self, done: frozenset[str]) -> list[Step]:
        if not self.runbook.allow_reordering:
            if len(done) >= len(self.runbook.steps):
                return []
            step = self.runbook.steps[len(done)]
            return [step] if all(dep in done for dep in step.after) else []
        return [step for step in self.runbook.steps if step.id not in done and all(dep in done for dep in step.after)]

    def _pre_action_violations(self, state: SystemState, step: Step, trace: tuple[str, ...], semantic_trace: tuple[str, ...]) -> list[Violation]:
        violations: list[Violation] = []
        for condition in step.requires:
            try:
                holds = condition_holds(state, condition)
            except ActionError as exc:
                violations.append(_violation("precondition_defined", str(exc), trace + (step.id,), step.id, _append_property_rule(semantic_trace, "precondition_defined", step.id)))
                continue
            if not holds:
                violations.append(_violation("precondition", f"step {step.id} requires {condition}", trace + (step.id,), step.id, _append_property_rule(semantic_trace, "precondition", step.id)))
        if step.action in {"drain_replica", "drain_region", "scale_service"}:
            violations.extend(self._availability_would_be_violated(state, step, trace, semantic_trace))
        if step.action == "rollback_deployment":
            for db in state.databases.values():
                if db.migration_in_progress and not db.migration_compatible:
                    violations.append(_violation("no_rollback_during_incompatible_migration", f"rollback {step.id} while database {db.name} has incompatible migration in progress", trace + (step.id,), step.id, _append_property_rule(semantic_trace, "no_rollback_during_incompatible_migration", step.id)))
        if step.action == "failover_database":
            db = state.databases[str(step.params["database"])]
            target = str(step.params["target_region"])
            if target not in db.healthy_regions or not state.regions.get(target, None) or not state.regions[target].healthy:
                violations.append(_violation("no_failover_to_unhealthy_region", f"database {db.name} failover target {target} is unhealthy", trace + (step.id,), step.id))
            if bool(step.params.get("data_loss_risk", False)) and not db.quorum_confirmed:
                violations.append(_violation("quorum_before_data_loss_action", f"database {db.name} failover has data-loss risk before quorum confirmation", trace + (step.id,), step.id))
        if step.action == "suppress_alert":
            expires = step.params.get("expires_after_minutes")
            if not isinstance(expires, int) or expires <= 0 or expires > self.max_alert_suppression:
                violations.append(_violation("bounded_alert_suppression", f"alert suppression {step.id} must have positive expiry <= {self.max_alert_suppression} minutes", trace + (step.id,), step.id))
        if step.action == "pause_queue":
            q = state.queues[str(step.params["queue"])]
            if q.depth > 0 and q.consumers <= 1:
                violations.append(_violation("no_queue_pause_without_drain_plan", f"queue {q.name} has depth={q.depth} and consumers={q.consumers} before pause", trace + (step.id,), step.id))
        if step.action == "replay_messages":
            q = state.queues[str(step.params["queue"])]
            count = int(step.params["count"])
            if bool(step.params.get("from_dead_letter", False)) and count > q.dead_letter_depth:
                violations.append(_violation("dead_letter_replay_has_messages", f"queue {q.name} has dead-letter depth={q.dead_letter_depth}, smaller than replay count={count}", trace + (step.id,), step.id))
            deduped = bool(step.params.get("dedupe_key")) or bool(step.params.get("idempotent", False)) or q.dedupe_window_minutes > 0 or count == 0
            if not deduped:
                violations.append(_violation("no_replay_without_dedupe", f"queue {q.name} replay count={count} lacks dedupe_key, idempotency proof, or dedupe window", trace + (step.id,), step.id))
        if step.action == "drain_dead_letter_queue":
            q = state.queues[str(step.params["queue"])]
            count = int(step.params["count"])
            if count > q.dead_letter_depth:
                violations.append(_violation("dead_letter_drain_has_messages", f"queue {q.name} has dead-letter depth={q.dead_letter_depth}, smaller than drain count={count}", trace + (step.id,), step.id))
        if step.action == "rebalance_consumers":
            q = state.queues[str(step.params["queue"])]
            target = int(step.params["consumers"])
            if q.depth > 0 and target <= 0:
                violations.append(_violation("no_rebalance_to_zero_consumers", f"queue {q.name} has depth={q.depth} before rebalance to {target} consumers", trace + (step.id,), step.id))
        if step.action == "flush_cache":
            cache = state.caches[str(step.params["cache"])]
            if not cache.write_frozen:
                violations.append(_violation("cache_flush_requires_write_freeze", f"cache {cache.name} writes are not frozen before flush", trace + (step.id,), step.id))
        if step.action == "warm_cache":
            cache = state.caches[str(step.params["cache"])]
            entries = int(step.params["entries"])
            if entries < cache.warmup_entries:
                violations.append(_violation("cache_warmup_before_traffic", f"cache {cache.name} warmup entries={entries}, requires at least {cache.warmup_entries}", trace + (step.id,), step.id))
            if entries > cache.capacity_entries:
                violations.append(_violation("cache_warmup_within_capacity", f"cache {cache.name} warmup entries={entries} exceed capacity={cache.capacity_entries}", trace + (step.id,), step.id))
        if step.action == "drain_load_balancer":
            route = state.traffic_routes[str(step.params["route"])]
            region = str(step.params["region"])
            if route.weights.get(region, 0) > 0:
                violations.append(_violation("no_draining_load_balancer_with_traffic", f"route {route.name} still sends {route.weights.get(region, 0)}% traffic to {region} before load balancer drain", trace + (step.id,), step.id))
        if step.action in {"shift_traffic", "failover_traffic"}:
            target = str(step.params.get("region", step.params.get("target_region")))
            route = state.traffic_routes[str(step.params["route"])]
            if target in route.drained_regions:
                violations.append(_violation("no_traffic_to_drained_load_balancer", f"route {route.name} target {target} load balancer is drained", trace + (step.id,), step.id))
            if target not in state.regions or not state.regions[target].healthy:
                violations.append(_violation("no_traffic_to_unhealthy_region", f"route {route.name} target {target} region is unhealthy", trace + (step.id,), step.id))
        if step.action == "update_dns_record":
            record = state.dns_records[str(step.params["record"])]
            target = str(step.params["target_region"])
            if target not in state.regions or not state.regions[target].healthy:
                violations.append(_violation("dns_target_region_healthy", f"DNS record {record.name} target {target} region is unhealthy", trace + (step.id,), step.id))
            if target not in record.health_check_converged_regions:
                violations.append(_violation("dns_health_check_converged_before_cutover", f"DNS record {record.name} target {target} health check has not converged", trace + (step.id,), step.id))
            if not _service_has_capacity_in_region(state, record.service, target):
                violations.append(_violation("dns_requires_regional_capacity", f"DNS record {record.name} targets {target} but service {record.service} has no available replica there", trace + (step.id,), step.id))
            if record.previous_region is not None and not record.ttl_elapsed(state.clock_minute) and not record.allow_split_brain:
                violations.append(_violation("dns_ttl_elapsed_before_recursion", f"DNS record {record.name} is still inside prior TTL window before another cutover", trace + (step.id,), step.id))
        if step.action == "finalize_dns_record":
            record = state.dns_records[str(step.params["record"])]
            if not record.ttl_elapsed(state.clock_minute):
                violations.append(_violation("dns_ttl_elapsed_before_finalize", f"DNS record {record.name} TTL window has not elapsed before finalize", trace + (step.id,), step.id))
        return [_with_semantic_prefix(violation, semantic_trace) for violation in violations]

    def _post_action_violations(self, state: SystemState, step: Step, trace: tuple[str, ...], semantic_trace: tuple[str, ...]) -> list[Violation]:
        violations: list[Violation] = []
        for svc in state.services.values():
            if svc.available_count() < svc.min_available:
                violations.append(_violation("service_min_available", f"service {svc.name} has {svc.available_count()} available replicas; requires {svc.min_available}", trace, step.id, _append_property_rule(semantic_trace, "service_min_available", step.id)))
            if svc.replicas and all(r.drained for r in svc.replicas):
                violations.append(_violation("no_draining_all_replicas", f"service {svc.name} has all replicas drained", trace, step.id, _append_property_rule(semantic_trace, "no_draining_all_replicas", step.id)))
        for q in state.queues.values():
            if q.paused and q.depth > 0 and q.consumers <= 1:
                violations.append(_violation("no_paused_queue_with_backlog", f"queue {q.name} is paused with depth={q.depth} and consumers={q.consumers}", trace, step.id))
            if q.duplicate_risk:
                violations.append(_violation("no_duplicate_processing_risk", f"queue {q.name} has replayed messages without modeled deduplication", trace, step.id))
            if q.depth > 0 and q.consumers <= 0:
                violations.append(_violation("queue_backlog_requires_consumers", f"queue {q.name} has depth={q.depth} with no active consumers", trace, step.id))
            if q.depth > 0 and not q.consumer_group_stable:
                violations.append(_violation("no_unstable_consumer_group_with_backlog", f"queue {q.name} has depth={q.depth} while consumer group rebalance is not stable", trace, step.id))
        for cache in state.caches.values():
            if not cache.warm and not cache.write_frozen:
                violations.append(_violation("cache_warmup_before_traffic", f"cache {cache.name} is cold; warmup threshold={cache.warmup_entries} entries", trace, step.id))
            if cache.entries > cache.capacity_entries:
                violations.append(_violation("cache_warmup_within_capacity", f"cache {cache.name} entries={cache.entries} exceed capacity={cache.capacity_entries}", trace, step.id))
            if cache.stale_read_risk:
                violations.append(_violation("no_stale_reads_after_cache_flush", f"cache {cache.name} may serve stale reads after flush without a write freeze/warmup guard", trace, step.id))
        for route in state.traffic_routes.values():
            total = sum(route.weights.values())
            if total != 100:
                violations.append(_violation("traffic_weights_sum_to_100", f"route {route.name} weights sum to {total}, expected 100", trace, step.id))
            svc = state.services.get(route.service)
            for region, weight in route.weights.items():
                if weight <= 0:
                    continue
                if region in route.drained_regions:
                    violations.append(_violation("no_traffic_to_drained_load_balancer", f"route {route.name} sends {weight}% traffic to drained load balancer in {region}", trace, step.id))
                if region not in state.regions or not state.regions[region].healthy:
                    violations.append(_violation("no_traffic_to_unhealthy_region", f"route {route.name} sends {weight}% traffic to unhealthy region {region}", trace, step.id))
                if svc is not None and not any(r.region == region and r.healthy and not r.drained for r in svc.replicas):
                    violations.append(_violation("traffic_requires_regional_capacity", f"route {route.name} sends {weight}% traffic to {region} but service {svc.name} has no available replica there", trace, step.id))
        for record in state.dns_records.values():
            if record.region not in state.regions or not state.regions[record.region].healthy:
                violations.append(_violation("dns_target_region_healthy", f"DNS record {record.name} points to unhealthy region {record.region}", trace, step.id))
            if not _service_has_capacity_in_region(state, record.service, record.region):
                violations.append(_violation("dns_requires_regional_capacity", f"DNS record {record.name} points to {record.region} but service {record.service} has no available replica there", trace, step.id))
            if record.previous_region is not None and not record.ttl_elapsed(state.clock_minute) and not record.allow_split_brain:
                violations.append(_violation("dns_no_split_brain_during_ttl", f"DNS record {record.name} may answer both {record.previous_region} and {record.region} until minute {record.last_changed_minute + record.ttl_minutes}", trace, step.id))
        for condition in step.effects:
            try:
                holds = condition_holds(state, condition)
            except ActionError as exc:
                violations.append(_violation("effect_defined", str(exc), trace, step.id))
                continue
            if not holds:
                violations.append(_violation("effect", f"step {step.id} promised effect {condition}", trace, step.id))
        return [_with_semantic_prefix(violation, semantic_trace) for violation in violations]

    def _availability_would_be_violated(self, state: SystemState, step: Step, trace: tuple[str, ...], semantic_trace: tuple[str, ...]) -> list[Violation]:
        try:
            next_state = apply_action(state, step)
        except ActionError as exc:
            return [_violation("action_defined", str(exc), trace + (step.id,), step.id, _append_property_rule(semantic_trace, "action_defined", step.id))]
        return [
            _violation("service_min_available", f"step {step.id} would leave service {svc.name} with {svc.available_count()} available replicas; requires {svc.min_available}", trace + (step.id,), step.id)
            for svc in next_state.services.values()
            if svc.available_count() < svc.min_available
        ]


def _record_obligations(result: CheckResult, group: str, checked: int, failures: list[Violation]) -> None:
    observed = max(checked, len(failures))
    result.proof_obligations_checked[group] = result.proof_obligations_checked.get(group, 0) + observed
    if failures:
        result.proof_obligation_failures[group] = result.proof_obligation_failures.get(group, 0) + len(failures)


def _record_rule(result: CheckResult, rule: str) -> None:
    result.semantic_rule_counts[rule] = result.semantic_rule_counts.get(rule, 0) + 1


def _record_labeled_rules(result: CheckResult, rules: tuple[str, ...]) -> None:
    for rule in rules:
        _record_rule(result, _unlabel_rule(rule))


def _unlabel_rule(rule: str) -> str:
    return rule.split("(", 1)[0]


def _safety_obligation_count(state: SystemState) -> int:
    return len(state.services) * 2 + len(state.queues) * 5 + len(state.caches) * 3 + len(state.traffic_routes) + len(state.dns_records) * 3


def _dedupe_violations(violations: list[Violation]) -> list[Violation]:
    seen: set[tuple[str, str, tuple[str, ...], str | None]] = set()
    unique: list[Violation] = []
    for violation in violations:
        key = (violation.property, violation.message, violation.trace, violation.step, violation.remediation, violation.small_step_rule, violation.semantic_trace)
        if key not in seen:
            seen.add(key)
            unique.append(violation)
    return unique


REMEDIATIONS = {
    "service_min_available": "Scale or restore capacity before draining; add service_available_at_least preconditions/effects.",
    "no_draining_all_replicas": "Drain one failure domain at a time and require at least one healthy replica remains.",
    "no_rollback_during_incompatible_migration": "Finish or prove compatibility for migrations before rollback.",
    "no_failover_to_unhealthy_region": "Require region_healthy for the target before failover.",
    "quorum_before_data_loss_action": "Confirm quorum or explicit data-loss approval before failover.",
    "bounded_alert_suppression": "Use a positive expires_after_minutes bounded by safety.max_alert_suppression_minutes.",
    "precondition": "Add an ordering dependency or earlier step establishing this precondition.",
    "effect": "Repair action parameters or expected effects so the promised postcondition holds.",
    "no_queue_pause_without_drain_plan": "Drain backlog or add queue_depth_at_most and queue_has_consumers preconditions before pausing.",
    "no_paused_queue_with_backlog": "Resume the queue or prove backlog is drained and alternate consumers are active.",
    "no_replay_without_dedupe": "Add a dedupe_key, prove the handler idempotent, or model a positive dedupe_window_minutes before replay.",
    "dead_letter_replay_has_messages": "Limit replay count to the current dead-letter backlog or add a prior dead-letter drain/triage step.",
    "dead_letter_drain_has_messages": "Limit dead-letter drain count to the current dead-letter backlog.",
    "no_duplicate_processing_risk": "Stop replay or add deduplication/idempotency guards before messages can be processed twice.",
    "queue_backlog_requires_consumers": "Keep at least one active consumer or drain backlog before rebalancing to zero consumers.",
    "no_rebalance_to_zero_consumers": "Rebalance to a positive consumer count while backlog exists, or drain the queue first.",
    "no_unstable_consumer_group_with_backlog": "Wait for consumer-group stability before leaving replay/backlog processing exposed.",
    "cache_flush_requires_write_freeze": "Freeze cache writes or otherwise quiesce repopulation before flushing shared keys.",
    "cache_warmup_before_traffic": "Warm the cache to its modeled threshold before restoring user traffic or resuming writes.",
    "cache_warmup_within_capacity": "Increase cache capacity or lower warmup size before preloading entries.",
    "no_stale_reads_after_cache_flush": "Freeze writes and complete warmup/verification before allowing reads after a destructive cache flush.",
    "traffic_weights_sum_to_100": "Keep route weights normalized to 100%; use failover_traffic or paired shift_traffic steps.",
    "no_traffic_to_unhealthy_region": "Require region_healthy and restore regional health before shifting or failing over traffic.",
    "no_traffic_to_drained_load_balancer": "Restore the regional load balancer or shift traffic away before relying on that route.",
    "no_draining_load_balancer_with_traffic": "Shift traffic weight to 0% for the region before draining its load balancer.",
    "traffic_requires_regional_capacity": "Scale or restore service replicas in the target region before assigning traffic there.",
    "dns_target_region_healthy": "Require region_healthy and restore DNS target health before cutover.",
    "dns_health_check_converged_before_cutover": "Run or wait for DNS health-check convergence before changing the record.",
    "dns_requires_regional_capacity": "Scale or restore service replicas in the DNS target region before cutover.",
    "dns_ttl_elapsed_before_recursion": "Wait for the prior DNS TTL window to elapse before issuing another cutover.",
    "dns_ttl_elapsed_before_finalize": "Insert a wait step long enough to cover the record TTL before finalizing DNS migration.",
    "dns_no_split_brain_during_ttl": "Use an active-active-safe record (allow_split_brain=true) or avoid stateful writes until the TTL window elapses.",
}


def _violation(property: str, message: str, trace: tuple[str, ...], step: str | None = None, semantic_trace: tuple[str, ...] | None = None) -> Violation:
    rule = small_step_rule(property)
    if semantic_trace is None:
        semantic_trace = (label_rule(rule, step),)
    return Violation(property, message, _minimize_trace(trace, step), step, REMEDIATIONS.get(property), rule, semantic_trace)


def _append_property_rule(semantic_trace: tuple[str, ...], property: str, step: str | None) -> tuple[str, ...]:
    return semantic_trace + (label_rule(small_step_rule(property), step),)


def _with_semantic_prefix(violation: Violation, semantic_trace: tuple[str, ...]) -> Violation:
    if violation.semantic_trace[:len(semantic_trace)] == semantic_trace:
        return violation
    return replace(violation, semantic_trace=semantic_trace + violation.semantic_trace)


def _service_has_capacity_in_region(state: SystemState, service: str, region: str) -> bool:
    svc = state.services.get(service)
    if svc is None:
        return False
    return any(replica.region == region and replica.healthy and not replica.drained for replica in svc.replicas)


def _minimize_trace(trace: tuple[str, ...], step: str | None) -> tuple[str, ...]:
    if not step:
        return trace
    # The checker explores breadth-first, so the first emitted trace is already
    # shortest. Drop duplicate step ids defensively for clearer reports.
    minimized: list[str] = []
    for item in trace:
        if item not in minimized:
            minimized.append(item)
    return tuple(minimized)
