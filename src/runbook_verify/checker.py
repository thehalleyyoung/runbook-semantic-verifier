from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field, replace
from datetime import date
import random
import time
from typing import Any

from .actions import ActionError, apply_action, condition_holds
from .contracts import hoare_triple_for
from .model import Runbook, Step, SystemState, Waiver
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
    hoare_triple: str | None = None
    source_path: str | None = None
    source_line: int | None = None
    source_field: str | None = None
    suggested_preconditions: tuple[dict[str, Any], ...] = ()
    json_patches: tuple[dict[str, Any], ...] = ()
    original_trace: tuple[str, ...] = ()
    minimization: dict[str, Any] = field(default_factory=dict)


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
    exploration_strategy: str = "breadth_first"
    exploration_seed: int | None = None
    fairness_model: str = "dependency"
    timeout_seconds: int | None = None
    inconclusive: bool = False
    inconclusive_reason: str | None = None
    proof_obligations_checked: dict[str, int] = field(default_factory=dict)
    proof_obligation_failures: dict[str, int] = field(default_factory=dict)
    semantic_rule_counts: dict[str, int] = field(default_factory=dict)
    annotation_warnings: list[Violation] = field(default_factory=list)
    waivers_applied: list[dict[str, Any]] = field(default_factory=list)

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
            "exploration_strategy": self.exploration_strategy,
            "exploration_seed": self.exploration_seed,
            "fairness_model": self.fairness_model,
            "timeout_seconds": self.timeout_seconds,
            "inconclusive": self.inconclusive,
            "inconclusive_reason": self.inconclusive_reason,
            "minimized_counterexample_trace_length": self.minimized_counterexample_trace_length,
            "counterexamples_minimized": sum(1 for violation in self.violations if violation.minimization.get("reduced")),
            "proof_obligations_checked": dict(sorted(self.proof_obligations_checked.items())),
            "proof_obligation_failures": dict(sorted(self.proof_obligation_failures.items())),
            "semantic_rule_counts": dict(sorted(self.semantic_rule_counts.items())),
            "annotation_warnings": len(self.annotation_warnings),
            "waivers_applied": len(self.waivers_applied),
        }


class Checker:
    """Bounded model checker over all dependency-respecting runbook step orders."""

    def __init__(self, runbook: Runbook):
        self.runbook = runbook
        self.steps_by_id = {s.id: s for s in runbook.steps}
        self.max_alert_suppression = int(runbook.safety.get("max_alert_suppression_minutes", 240))
        self.strategy = str(runbook.safety.get("exploration_strategy", "breadth_first"))
        if self.strategy not in EXPLORATION_STRATEGIES:
            self.strategy = "breadth_first"
        seed = runbook.safety.get("exploration_seed")
        self.seed = int(seed) if isinstance(seed, int) else None
        self.max_states = runbook.safety.get("max_states")
        timeout = runbook.safety.get("timeout_seconds")
        self.timeout_seconds = int(timeout) if isinstance(timeout, int) else None
        self.fairness_model = str(runbook.safety.get("fairness", "dependency" if runbook.allow_reordering else "fifo"))
        self.partial_order_reduction = bool(runbook.safety.get("partial_order_reduction", True))
        self._rng = random.Random(self.seed)

    def check(self) -> CheckResult:
        result = CheckResult(safe=True)
        result.exploration_strategy = self.strategy
        result.exploration_seed = self.seed
        result.fairness_model = self.fairness_model
        result.timeout_seconds = self.timeout_seconds
        deadline = time.monotonic() + self.timeout_seconds if isinstance(self.timeout_seconds, int) else None
        initial = (self.runbook.state, frozenset(), tuple(), tuple())
        queue: deque[tuple[SystemState, frozenset[str], tuple[str, ...], tuple[str, ...]]] = deque([initial])
        seen = set()
        while queue:
            if deadline is not None and time.monotonic() >= deadline:
                result.max_depth_reached = True
                result.inconclusive = True
                result.inconclusive_reason = f"timeout_seconds={self.timeout_seconds} reached before exhausting the transition system"
                _record_rule(result, EXPLORE_BUDGET_REACHED)
                break
            if isinstance(self.max_states, int) and result.states_explored >= self.max_states:
                result.max_depth_reached = True
                result.inconclusive = True
                result.inconclusive_reason = f"max_states={self.max_states} reached before exhausting the transition system"
                _record_rule(result, EXPLORE_BUDGET_REACHED)
                break
            state, done, trace, semantic_trace = self._pop_frontier(queue)
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
            enabled_all = self._ordered_enabled_steps(self._enabled_steps(done))
            enabled = self._partial_order_reduced_enabled(enabled_all, len(trace))
            result.reductions_applied += len(enabled_all) - len(enabled)
            result.branch_points += 1
            result.branch_factor_total += len(enabled)
            result.max_branch_factor = max(result.max_branch_factor, len(enabled))
            for step in enabled:
                result.transitions_explored += 1
                schedule_trace = semantic_trace + scheduling_rules(step, len(enabled), self.runbook.allow_reordering)
                _record_labeled_rules(result, schedule_trace[len(semantic_trace):])
                pre = self._pre_action_violations(state, step, trace, schedule_trace)
                for warning in _effect_annotation_warnings(step, trace + (step.id,), schedule_trace):
                    warning = self._with_step_context(warning)
                    waiver = _matching_active_waiver(self.runbook.waivers, warning.property, step.id)
                    if waiver is None:
                        result.annotation_warnings.append(warning)
                    else:
                        result.waivers_applied.append({"waiver": asdict(waiver), "property": warning.property, "step": step.id})
                _record_obligations(result, "precondition", len(step.requires), pre)
                if pre:
                    pre = [self._with_step_context(violation) for violation in pre]
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
                    result.violations.append(self._with_step_context(violation))
                    result.safe = False
                    continue
                _record_obligations(result, "action_defined", 1, [])
                next_semantic_trace = schedule_trace + (label_rule(action_rule(step), step.id),)
                _record_labeled_rules(result, next_semantic_trace[len(schedule_trace):])
                post = self._post_action_violations(next_state, step, trace + (step.id,), next_semantic_trace)
                _record_obligations(result, "safety_postcondition", _safety_obligation_count(next_state), post)
                _record_obligations(result, "promised_effect", len(step.effects), [v for v in post if v.property in {"effect", "effect_defined"}])
                if post:
                    post = [self._with_step_context(violation) for violation in post]
                    result.violations.extend(post)
                    for violation in post:
                        if violation.small_step_rule:
                            _record_rule(result, violation.small_step_rule)
                    result.safe = False
                self._push_frontier(queue, (next_state, done | {step.id}, trace + (step.id,), next_semantic_trace))
        result.violations = _dedupe_violations(result.violations)
        result.violations = [self._minimized_violation(violation) for violation in result.violations]
        result.annotation_warnings = _dedupe_violations(result.annotation_warnings)
        return result

    def _enabled_steps(self, done: frozenset[str]) -> list[Step]:
        if not self.runbook.allow_reordering:
            if len(done) >= len(self.runbook.steps):
                return []
            step = self.runbook.steps[len(done)]
            return [step] if all(dep in done for dep in step.after) else []
        return [step for step in self.runbook.steps if step.id not in done and all(dep in done for dep in step.after)]

    def _pop_frontier(self, queue: deque[tuple[SystemState, frozenset[str], tuple[str, ...], tuple[str, ...]]]) -> tuple[SystemState, frozenset[str], tuple[str, ...], tuple[str, ...]]:
        if self.strategy in {"depth_first", "seeded_chaos_style"}:
            return queue.pop()
        return queue.popleft()

    def _push_frontier(self, queue: deque[tuple[SystemState, frozenset[str], tuple[str, ...], tuple[str, ...]]], item: tuple[SystemState, frozenset[str], tuple[str, ...], tuple[str, ...]]) -> None:
        queue.append(item)

    def _ordered_enabled_steps(self, enabled: list[Step]) -> list[Step]:
        if self.strategy in {"randomized_bounded", "seeded_chaos_style"}:
            shuffled = list(enabled)
            self._rng.shuffle(shuffled)
            return shuffled
        return enabled

    def _partial_order_reduced_enabled(self, enabled: list[Step], trace_len: int) -> list[Step]:
        if not self.partial_order_reduction or not self.runbook.allow_reordering or len(enabled) <= 1:
            return enabled
        if trace_len + len(enabled) > self.runbook.max_depth:
            return enabled
        if all(_independent_steps(left, right) for idx, left in enumerate(enabled) for right in enabled[idx + 1:]):
            return enabled[:1]
        return enabled

    def _pre_action_violations(self, state: SystemState, step: Step, trace: tuple[str, ...], semantic_trace: tuple[str, ...]) -> list[Violation]:
        violations: list[Violation] = []
        for condition_index, condition in enumerate(step.requires):
            try:
                holds = condition_holds(state, condition)
            except ActionError as exc:
                violations.append(_with_source_field(_violation("precondition_defined", str(exc), trace + (step.id,), step.id, _append_property_rule(semantic_trace, "precondition_defined", step.id)), f"requires[{condition_index}]"))
                continue
            if not holds:
                violations.append(_with_source_field(_violation("precondition", f"step {step.id} requires {condition}", trace + (step.id,), step.id, _append_property_rule(semantic_trace, "precondition", step.id)), f"requires[{condition_index}]"))
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
        if step.action == "restore_bucket_snapshot":
            bucket = state.object_buckets[str(step.params["bucket"])]
            age = int(step.params["snapshot_age_minutes"])
            duration = int(step.params.get("duration_minutes", 0))
            if not bucket.writes_frozen:
                violations.append(_violation("object_restore_requires_write_freeze", f"bucket {bucket.name} writes are not frozen before snapshot restore", trace + (step.id,), step.id))
            if not bucket.snapshot_available:
                violations.append(_violation("object_restore_requires_snapshot", f"bucket {bucket.name} has no available restore snapshot modeled", trace + (step.id,), step.id))
            if age > bucket.rpo_minutes:
                violations.append(_violation("object_restore_within_rpo", f"bucket {bucket.name} snapshot age={age} minutes exceeds RPO={bucket.rpo_minutes}", trace + (step.id,), step.id))
            if duration > bucket.rto_minutes:
                violations.append(_violation("object_restore_within_rto", f"bucket {bucket.name} restore duration={duration} minutes exceeds RTO={bucket.rto_minutes}", trace + (step.id,), step.id))
        if step.action == "replicate_bucket":
            target = str(step.params["region"])
            if target not in state.regions or not state.regions[target].healthy:
                violations.append(_violation("object_replication_target_region_healthy", f"bucket replication target {target} is unhealthy", trace + (step.id,), step.id))
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
        for bucket in state.object_buckets.values():
            if len(bucket.replicated_regions) < bucket.min_replicated_regions:
                violations.append(_violation("object_bucket_replication_min_regions", f"bucket {bucket.name} has {len(bucket.replicated_regions)} replicated region(s); requires {bucket.min_replicated_regions}", trace, step.id))
            unhealthy_replicas = sorted(region for region in bucket.replicated_regions if region not in state.regions or not state.regions[region].healthy)
            if unhealthy_replicas:
                violations.append(_violation("object_bucket_replication_regions_healthy", f"bucket {bucket.name} has unhealthy replicated region(s): {', '.join(unhealthy_replicas)}", trace, step.id))
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
        for condition_index, condition in enumerate(step.effects):
            try:
                holds = condition_holds(state, condition)
            except ActionError as exc:
                violations.append(_with_source_field(_violation("effect_defined", str(exc), trace, step.id), f"effects[{condition_index}]"))
                continue
            if not holds:
                violations.append(_with_source_field(_violation("effect", f"step {step.id} promised effect {condition}", trace, step.id), f"effects[{condition_index}]"))
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

    def _with_step_context(self, violation: Violation) -> Violation:
        step = self.steps_by_id.get(violation.step or "")
        if step is None:
            return violation
        source_field = violation.source_field or _default_source_field(violation.property)
        source_line = step.source_map.get(source_field or "", step.source_line)
        suggested = violation.suggested_preconditions or tuple(_suggested_preconditions(violation.property, step))
        patches = violation.json_patches or tuple(_json_patches_for_preconditions(step, suggested))
        return replace(violation, source_path=step.source_path, source_line=source_line, source_field=source_field, suggested_preconditions=suggested, json_patches=patches)

    def _minimized_violation(self, violation: Violation) -> Violation:
        original = tuple(violation.trace)
        if not original or not violation.step:
            return replace(violation, original_trace=original, minimization={"reduced": False, "reason": "no step-scoped witness"})
        minimized = list(original)
        changed = True
        while changed and len(minimized) > 1:
            changed = False
            for idx in range(len(minimized) - 1):
                candidate = tuple(minimized[:idx] + minimized[idx + 1:])
                witness = self._replay_violation(candidate, violation.property, violation.step)
                if witness is not None:
                    minimized = list(candidate)
                    changed = True
                    break
        reduced = tuple(minimized) != original
        witness = self._replay_violation(tuple(minimized), violation.property, violation.step) if reduced else None
        chosen = self._with_step_context(witness) if witness is not None else violation
        return replace(
            chosen,
            original_trace=original,
            minimization={
                "reduced": reduced,
                "original_length": len(original),
                "minimized_length": len(tuple(minimized)),
                "removed_steps": [step for step in original if step not in tuple(minimized)],
                "method": "greedy_dependency_preserving_subsequence_replay",
            },
        )

    def _replay_violation(self, trace: tuple[str, ...], property_name: str, step_id: str | None) -> Violation | None:
        if not self.runbook.allow_reordering:
            ordered = tuple(step.id for step in self.runbook.steps[:len(trace)])
            if trace != ordered:
                return None
        state = self.runbook.state
        done: set[str] = set()
        semantic_trace: tuple[str, ...] = ()
        prefix: tuple[str, ...] = ()
        for item in trace:
            step = self.steps_by_id.get(item)
            if step is None or any(dep not in done for dep in step.after):
                return None
            schedule_trace = semantic_trace + scheduling_rules(step, 1, self.runbook.allow_reordering)
            pre = self._pre_action_violations(state, step, prefix, schedule_trace)
            for violation in pre:
                if violation.property == property_name and (step_id is None or violation.step == step_id):
                    return self._with_step_context(violation)
            if pre:
                return None
            try:
                state = apply_action(state, step)
            except ActionError as exc:
                violation = _violation("action_defined", str(exc), prefix + (step.id,), step.id, schedule_trace + (label_rule(small_step_rule("action_defined"), step.id),))
                if violation.property == property_name and (step_id is None or violation.step == step_id):
                    return self._with_step_context(violation)
                return None
            semantic_trace = schedule_trace + (label_rule(action_rule(step), step.id),)
            prefix = prefix + (step.id,)
            post = self._post_action_violations(state, step, prefix, semantic_trace)
            for violation in post:
                if violation.property == property_name and (step_id is None or violation.step == step_id):
                    return self._with_step_context(violation)
            done.add(step.id)
        return None


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
    return len(state.services) * 2 + len(state.queues) * 5 + len(state.caches) * 3 + len(state.object_buckets) * 2 + len(state.traffic_routes) + len(state.dns_records) * 3 + len(state.credentials)


HIGH_RISK_EFFECT_TYPES_BY_ACTION = {
    "replay_messages": "queue_replay",
    "drain_dead_letter_queue": "deletion",
    "drain_region": "traffic_drain",
    "drain_replica": "traffic_drain",
    "drain_load_balancer": "traffic_drain",
    "failover_traffic": "customer_visible_degradation",
    "shift_traffic": "customer_visible_degradation",
    "failover_database": "irreversible_state_change",
    "run_migration": "manual_sql",
    "rollback_deployment": "customer_visible_degradation",
    "flush_cache": "deletion",
    "restore_bucket_snapshot": "irreversible_state_change",
    "freeze_bucket_writes": "customer_visible_degradation",
    "update_dns_record": "customer_visible_degradation",
    "revoke_credential": "credential_revocation",
}


def _effect_annotation_warnings(step: Step, trace: tuple[str, ...], semantic_trace: tuple[str, ...]) -> list[Violation]:
    expected = HIGH_RISK_EFFECT_TYPES_BY_ACTION.get(step.action)
    if expected is None:
        return []
    annotations = step.effect_annotations
    if not annotations:
        return [_violation("effect_annotation_required", f"step {step.id} action {step.action} must declare reviewed effect_annotations including {expected}", trace, step.id, _append_property_rule(semantic_trace, "effect_annotation_required", step.id))]
    warnings: list[Violation] = []
    effect_types = set(str(item) for item in annotations.get("effect_types", []))
    if expected not in effect_types:
        warnings.append(_violation("effect_annotation_required", f"step {step.id} effect_annotations.effect_types must include {expected} for action {step.action}", trace, step.id, _append_property_rule(semantic_trace, "effect_annotation_required", step.id)))
    retry_safety = str(annotations.get("retry_safety", "unknown"))
    idempotency = str(annotations.get("idempotency", "unknown"))
    reversibility = str(annotations.get("reversibility", "unknown"))
    if retry_safety == "safe" and (idempotency != "idempotent" or reversibility == "irreversible"):
        warnings.append(_violation("unsafe_retry_annotation", f"step {step.id} marks retry_safety=safe but idempotency={idempotency} and reversibility={reversibility}", trace, step.id, _append_property_rule(semantic_trace, "unsafe_retry_annotation", step.id)))
    return [_with_semantic_prefix(warning, semantic_trace) for warning in warnings]


def _matching_active_waiver(waivers: tuple[Waiver, ...], property_name: str, step_id: str) -> Waiver | None:
    today = date.today()
    for waiver in waivers:
        if waiver.invariant != property_name:
            continue
        if waiver.scope not in {step_id, f"step:{step_id}", "*"}:
            continue
        try:
            if date.fromisoformat(waiver.expiry) < today:
                continue
        except ValueError:
            continue
        return waiver
    return None


def _dedupe_violations(violations: list[Violation]) -> list[Violation]:
    seen: set[tuple[str, str, tuple[str, ...], str | None]] = set()
    unique: list[Violation] = []
    for violation in violations:
        key = (violation.property, violation.message, violation.trace, violation.step, violation.remediation, violation.small_step_rule, violation.semantic_trace, violation.source_field)
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
    "effect_annotation_required": "Add reviewed effect_annotations with effect_types, idempotency, reversibility, retry_safety, blast_radius, and expected_user_impact.",
    "unsafe_retry_annotation": "Do not mark destructive or non-idempotent operations retry-safe unless the runbook models an idempotency guard and reversible outcome.",
    "credential_active": "Rotate or restore the credential before dependent operations require it.",
    "object_restore_requires_write_freeze": "Freeze object writes before restoring a bucket snapshot.",
    "object_restore_requires_snapshot": "Model an available snapshot before invoking restore-from-snapshot.",
    "object_restore_within_rpo": "Use a snapshot whose age is within the bucket RPO or document/waive the recovery objective.",
    "object_restore_within_rto": "Keep the modeled restore duration within the bucket RTO or split the procedure with an explicit approval.",
    "object_replication_target_region_healthy": "Replicate only to a healthy modeled region.",
    "object_bucket_replication_min_regions": "Add or restore replicated regions before relying on bucket durability.",
    "object_bucket_replication_regions_healthy": "Restore unhealthy replicated regions or remove them from the durability assumption.",
}


EXPLORATION_STRATEGIES = {"breadth_first", "depth_first", "shortest_counterexample", "randomized_bounded", "seeded_chaos_style"}


def _violation(property: str, message: str, trace: tuple[str, ...], step: str | None = None, semantic_trace: tuple[str, ...] | None = None) -> Violation:
    rule = small_step_rule(property)
    if semantic_trace is None:
        semantic_trace = (label_rule(rule, step),)
    return Violation(property, message, _normalize_trace(trace, step), step, REMEDIATIONS.get(property), rule, semantic_trace, hoare_triple_for(property))


def _with_source_field(violation: Violation, source_field: str) -> Violation:
    return replace(violation, source_field=source_field)


def _default_source_field(property_name: str) -> str:
    if property_name in {"precondition", "precondition_defined"}:
        return "requires"
    if property_name in {"effect", "effect_defined"}:
        return "effects"
    if property_name in {"effect_annotation_required", "unsafe_retry_annotation"}:
        return "effect_annotations"
    return "params"


def _suggested_preconditions(property_name: str, step: Step) -> list[dict[str, Any]]:
    params = step.params
    suggestions: dict[str, list[dict[str, Any]]] = {
        "service_min_available": [{"kind": "service_available_at_least", "service": str(params.get("service", "TODO-service")), "count": 1}],
        "no_draining_all_replicas": [{"kind": "service_available_at_least", "service": str(params.get("service", "TODO-service")), "count": 1}],
        "no_rollback_during_incompatible_migration": [{"kind": "service_deployment_is", "service": str(params.get("service", "TODO-service")), "deployment": str(params.get("target", params.get("version", "TODO-version")))}],
        "no_failover_to_unhealthy_region": [{"kind": "region_healthy", "region": str(params.get("target_region", "TODO-region"))}],
        "quorum_before_data_loss_action": [{"kind": "database_quorum_confirmed", "database": str(params.get("database", "TODO-database"))}],
        "no_queue_pause_without_drain_plan": [{"kind": "queue_depth_at_most", "queue": str(params.get("queue", "TODO-queue")), "depth": 0}, {"kind": "queue_has_consumers", "queue": str(params.get("queue", "TODO-queue")), "consumers": 2}],
        "no_replay_without_dedupe": [{"kind": "queue_replay_deduplicated", "queue": str(params.get("queue", "TODO-queue")), "window_minutes": 60}],
        "dead_letter_replay_has_messages": [{"kind": "queue_depth_at_most", "queue": str(params.get("queue", "TODO-queue")), "depth": int(params.get("count", 1))}],
        "dead_letter_drain_has_messages": [{"kind": "queue_depth_at_most", "queue": str(params.get("queue", "TODO-queue")), "depth": int(params.get("count", 1))}],
        "no_rebalance_to_zero_consumers": [{"kind": "queue_depth_at_most", "queue": str(params.get("queue", "TODO-queue")), "depth": 0}],
        "cache_flush_requires_write_freeze": [{"kind": "cache_writes_frozen", "cache": str(params.get("cache", "TODO-cache"))}],
        "cache_warmup_before_traffic": [{"kind": "cache_warm", "cache": str(params.get("cache", "TODO-cache"))}],
        "cache_warmup_within_capacity": [{"kind": "cache_capacity_at_least", "cache": str(params.get("cache", "TODO-cache")), "entries": int(params.get("entries", 1))}],
        "no_draining_load_balancer_with_traffic": [{"kind": "traffic_weight_at_most", "route": str(params.get("route", "TODO-route")), "region": str(params.get("region", "TODO-region")), "percent": 0}],
        "no_traffic_to_unhealthy_region": [{"kind": "region_healthy", "region": str(params.get("region", params.get("target_region", "TODO-region")))}],
        "no_traffic_to_drained_load_balancer": [{"kind": "region_healthy", "region": str(params.get("region", params.get("target_region", "TODO-region")))}],
        "traffic_requires_regional_capacity": [{"kind": "service_available_at_least", "service": "TODO-service", "count": 1}],
        "dns_target_region_healthy": [{"kind": "region_healthy", "region": str(params.get("target_region", "TODO-region"))}],
        "dns_health_check_converged_before_cutover": [{"kind": "dns_health_check_converged", "record": str(params.get("record", "TODO-record")), "region": str(params.get("target_region", "TODO-region"))}],
        "dns_requires_regional_capacity": [{"kind": "service_available_at_least", "service": "TODO-service", "count": 1}],
        "dns_ttl_elapsed_before_recursion": [],
        "dns_ttl_elapsed_before_finalize": [],
        "object_restore_requires_write_freeze": [{"kind": "bucket_writes_frozen", "bucket": str(params.get("bucket", "TODO-bucket"))}],
        "object_restore_requires_snapshot": [{"kind": "bucket_snapshot_available", "bucket": str(params.get("bucket", "TODO-bucket"))}],
        "object_restore_within_rpo": [{"kind": "bucket_snapshot_available", "bucket": str(params.get("bucket", "TODO-bucket"))}],
        "object_restore_within_rto": [{"kind": "bucket_snapshot_available", "bucket": str(params.get("bucket", "TODO-bucket"))}],
        "object_replication_target_region_healthy": [{"kind": "region_healthy", "region": str(params.get("region", "TODO-region"))}],
        "credential_active": [{"kind": "credential_active", "credential": str(params.get("credential", "TODO-credential"))}],
    }
    return suggestions.get(property_name, [])


def _json_patches_for_preconditions(step: Step, preconditions: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not preconditions:
        return []
    step_index = step.source_index if step.source_index is not None else step.id
    return [{"op": "add", "path": f"/steps/{step_index}/requires/-", "value": condition} for condition in preconditions]


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


def _normalize_trace(trace: tuple[str, ...], step: str | None) -> tuple[str, ...]:
    if not step:
        return trace
    # The checker explores breadth-first, so the first emitted trace is already
    # shortest. Drop duplicate step ids defensively for clearer reports.
    minimized: list[str] = []
    for item in trace:
        if item not in minimized:
            minimized.append(item)
    return tuple(minimized)


READ_RESOURCE_ACTIONS: dict[str, tuple[str, ...]] = {
    "drain_replica": ("service", "replica"),
    "restore_replica": ("service", "replica"),
    "scale_service": ("service",),
    "restart_service": ("service",),
    "failover_database": ("database", "target_region"),
    "confirm_quorum": ("database",),
    "pause_queue": ("queue",),
    "resume_queue": ("queue",),
    "replay_messages": ("queue",),
    "drain_dead_letter_queue": ("queue",),
    "rebalance_consumers": ("queue",),
    "freeze_cache_writes": ("cache",),
    "resume_cache_writes": ("cache",),
    "flush_cache": ("cache",),
    "warm_cache": ("cache",),
    "freeze_bucket_writes": ("bucket",),
    "resume_bucket_writes": ("bucket",),
    "replicate_bucket": ("bucket", "region"),
    "restore_bucket_snapshot": ("bucket",),
    "suppress_alert": ("alert",),
    "toggle_flag": ("flag",),
    "shift_traffic": ("route", "region"),
    "failover_traffic": ("route", "target_region"),
    "drain_load_balancer": ("route", "region"),
    "restore_load_balancer": ("route", "region"),
    "update_dns_record": ("record", "target_region"),
    "mark_dns_health_check": ("record", "region"),
    "finalize_dns_record": ("record",),
    "rotate_credential": ("credential",),
    "revoke_credential": ("credential",),
}


def _independent_steps(left: Step, right: Step) -> bool:
    if left.id in right.after or right.id in left.after:
        return False
    if left.action == "wait" or right.action == "wait":
        return False
    left_resources = _step_resources(left)
    right_resources = _step_resources(right)
    return bool(left_resources and right_resources and left_resources.isdisjoint(right_resources))


def _step_resources(step: Step) -> set[tuple[str, str]]:
    keys = READ_RESOURCE_ACTIONS.get(step.action)
    if not keys:
        return set()
    resources: set[tuple[str, str]] = set()
    for key in keys:
        value = step.params.get(key)
        if value is not None:
            resources.add((key, str(value)))
    # Preconditions/effects can make an otherwise local action depend on another entity.
    for condition in (*step.requires, *step.effects):
        for key, value in condition.items():
            if key != "kind" and isinstance(value, (str, int, bool)):
                resources.add((key, str(value)))
    return resources
