from __future__ import annotations

from .model import Step


SMALL_STEP_RULES: dict[str, str] = {
    "action_defined": "Action.Failure",
    "precondition": "StepEnabled.Requires",
    "precondition_defined": "StepEnabled.RequiresDefined",
    "effect": "Postcondition.PromisedEffect",
    "effect_defined": "Postcondition.PromisedEffectDefined",
    "service_min_available": "ActionPreserves.ServiceAvailability",
    "no_draining_all_replicas": "PostInvariant.ServiceHasReplica",
    "no_rollback_during_incompatible_migration": "ActionGuard.RollbackMigrationCompatibility",
    "no_queue_pause_without_drain_plan": "ActionGuard.QueuePause",
    "no_paused_queue_with_backlog": "PostInvariant.QueueBacklogProgress",
    "no_replay_without_dedupe": "ActionGuard.MessageReplayDeduplication",
    "no_duplicate_processing_risk": "PostInvariant.NoDuplicateReplayProcessing",
    "dead_letter_replay_has_messages": "ActionGuard.DeadLetterReplayBound",
    "dead_letter_drain_has_messages": "ActionGuard.DeadLetterDrainBound",
    "no_rebalance_to_zero_consumers": "ActionGuard.ConsumerRebalanceProgress",
    "queue_backlog_requires_consumers": "PostInvariant.QueueBacklogHasConsumers",
    "no_unstable_consumer_group_with_backlog": "PostInvariant.ConsumerGroupStableForBacklog",
    "quorum_before_data_loss_action": "ActionGuard.DatabaseFailoverQuorum",
    "no_failover_to_unhealthy_region": "ActionGuard.DatabaseTargetHealth",
    "bounded_alert_suppression": "ActionGuard.AlertSuppressionBound",
    "cache_flush_requires_write_freeze": "ActionGuard.CacheFlushWriteFreeze",
    "cache_warmup_before_traffic": "ActionGuard.CacheWarmupBeforeTraffic",
    "cache_warmup_within_capacity": "ActionGuard.CacheWarmupCapacity",
    "no_stale_reads_after_cache_flush": "PostInvariant.NoStaleReadsAfterCacheFlush",
    "no_draining_load_balancer_with_traffic": "ActionGuard.LoadBalancerDrainTraffic",
    "no_traffic_to_unhealthy_region": "RouteInvariant.TargetRegionHealthy",
    "no_traffic_to_drained_load_balancer": "RouteInvariant.LoadBalancerActive",
    "traffic_requires_regional_capacity": "RouteInvariant.RegionalServiceCapacity",
    "traffic_weights_sum_to_100": "RouteInvariant.NormalizedWeights",
    "dns_target_region_healthy": "ActionGuard.DNSTargetRegionHealthy",
    "dns_health_check_converged_before_cutover": "ActionGuard.DNSHealthCheckConverged",
    "dns_requires_regional_capacity": "ActionGuard.DNSRegionalCapacity",
    "dns_ttl_elapsed_before_recursion": "ActionGuard.DNSTTLBeforeRecursiveCutover",
    "dns_ttl_elapsed_before_finalize": "ActionGuard.DNSTTLBeforeFinalize",
    "dns_no_split_brain_during_ttl": "PostInvariant.DNSNoSplitBrainDuringTTL",
}

SCHEDULER_DEPENDENCY_READY = "Schedule.DependencyReady"
SCHEDULER_SEQUENCE_NEXT = "Schedule.SequenceNext"
SCHEDULER_OPERATOR_CHOICE = "Schedule.OperatorChoice"
ACTION_EXECUTE = "Action.Execute"
ACTION_WAIT = "Action.Wait"
EXPLORE_BUDGET_REACHED = "Explore.BudgetReached"
EXPLORE_TERMINAL = "Explore.Terminal"


RULE_EXPLANATIONS: dict[str, dict[str, object]] = {
    "precondition": {
        "small_step_rule": SMALL_STEP_RULES["precondition"],
        "weakest_precondition_hint": "Before this action is enabled, an earlier step or explicit assumption must establish the failed `requires` condition.",
        "remediation_examples": ["Add an `after` dependency on the step that proves the condition.", "Add a concrete guard such as `region_healthy`, `database_quorum_confirmed`, or `service_available_at_least`."],
    },
    "service_min_available": {
        "small_step_rule": SMALL_STEP_RULES["service_min_available"],
        "weakest_precondition_hint": "The pre-state must contain enough healthy, undrained replicas that the action cannot reduce availability below `min_available`.",
        "remediation_examples": ["Scale or restore replacement replicas before draining.", "Add `service_available_at_least` preconditions/effects around capacity-changing steps."],
    },
    "no_queue_pause_without_drain_plan": {
        "small_step_rule": SMALL_STEP_RULES["no_queue_pause_without_drain_plan"],
        "weakest_precondition_hint": "Before pausing a queue, prove backlog is drained or enough alternate consumers exist.",
        "remediation_examples": ["Require `queue_depth_at_most` before pause.", "Require `queue_has_consumers` with enough consumers to process backlog safely."],
    },
    "no_paused_queue_with_backlog": {
        "small_step_rule": SMALL_STEP_RULES["no_paused_queue_with_backlog"],
        "weakest_precondition_hint": "A terminal paused queue is safe only when backlog is bounded or alternate consumers remain active.",
        "remediation_examples": ["Resume the queue after the maintenance step.", "Drain backlog before pausing consumers."],
    },
    "no_replay_without_dedupe": {
        "small_step_rule": SMALL_STEP_RULES["no_replay_without_dedupe"],
        "weakest_precondition_hint": "Before replaying messages, the pre-state or action parameters must prove a dedupe key, idempotent handler, or bounded dedupe window.",
        "remediation_examples": ["Set `dedupe_key` on `replay_messages`.", "Add a positive `dedupe_window_minutes` queue assumption.", "Use `idempotent: true` only when the replay handler is documented idempotent."],
    },
    "no_duplicate_processing_risk": {
        "small_step_rule": SMALL_STEP_RULES["no_duplicate_processing_risk"],
        "weakest_precondition_hint": "A replay step may not leave the queue in a duplicate-risk state unless deduplication/idempotency was modeled.",
        "remediation_examples": ["Replay from the dead-letter queue with a stable dedupe key.", "Drain or quarantine duplicate-risk messages before resuming consumers."],
    },
    "dead_letter_replay_has_messages": {
        "small_step_rule": SMALL_STEP_RULES["dead_letter_replay_has_messages"],
        "weakest_precondition_hint": "The requested replay count must be bounded by the modeled dead-letter backlog.",
        "remediation_examples": ["Lower `count` to the modeled `dead_letter_depth`.", "Refresh the queue inventory before replay."],
    },
    "dead_letter_drain_has_messages": {
        "small_step_rule": SMALL_STEP_RULES["dead_letter_drain_has_messages"],
        "weakest_precondition_hint": "The requested drain count must be bounded by the modeled dead-letter backlog.",
        "remediation_examples": ["Lower `count` to the modeled `dead_letter_depth`.", "Inspect the DLQ before running the drain step."],
    },
    "no_rebalance_to_zero_consumers": {
        "small_step_rule": SMALL_STEP_RULES["no_rebalance_to_zero_consumers"],
        "weakest_precondition_hint": "A queue with backlog requires a positive post-rebalance consumer count.",
        "remediation_examples": ["Use `rebalance_consumers` with `consumers` greater than zero.", "Drain the queue before scaling consumers to zero."],
    },
    "queue_backlog_requires_consumers": {
        "small_step_rule": SMALL_STEP_RULES["queue_backlog_requires_consumers"],
        "weakest_precondition_hint": "Every reachable queue state with backlog must retain at least one active consumer.",
        "remediation_examples": ["Restore consumers before replay.", "Pause replay until consumer capacity is available."],
    },
    "no_unstable_consumer_group_with_backlog": {
        "small_step_rule": SMALL_STEP_RULES["no_unstable_consumer_group_with_backlog"],
        "weakest_precondition_hint": "Consumer-group rebalancing must converge before the runbook leaves backlog to be processed.",
        "remediation_examples": ["Set `stable: true` only after a modeled wait/health check.", "Add a `consumer_group_stable` effect to the stabilization step."],
    },
    "quorum_before_data_loss_action": {
        "small_step_rule": SMALL_STEP_RULES["quorum_before_data_loss_action"],
        "weakest_precondition_hint": "A data-loss-risk failover requires database quorum/data-safety confirmation in the pre-state.",
        "remediation_examples": ["Run `confirm_quorum` before `failover_database`.", "Add a `database_quorum_confirmed` precondition to the failover step."],
    },
    "no_failover_to_unhealthy_region": {
        "small_step_rule": SMALL_STEP_RULES["no_failover_to_unhealthy_region"],
        "weakest_precondition_hint": "The target region must be modeled healthy and listed among healthy database regions before failover.",
        "remediation_examples": ["Add a `region_healthy` precondition.", "Restore or choose a healthy target region before failover."],
    },
    "bounded_alert_suppression": {
        "small_step_rule": SMALL_STEP_RULES["bounded_alert_suppression"],
        "weakest_precondition_hint": "Alert suppression must have a positive finite expiry no greater than the configured safety bound.",
        "remediation_examples": ["Set `expires_after_minutes` to a bounded value.", "Lower the suppression duration or raise the explicit safety policy with review."],
    },
    "no_draining_load_balancer_with_traffic": {
        "small_step_rule": SMALL_STEP_RULES["no_draining_load_balancer_with_traffic"],
        "weakest_precondition_hint": "A regional load balancer may be drained only after weighted traffic to that region is 0%.",
        "remediation_examples": ["Run `failover_traffic` or `shift_traffic` before `drain_load_balancer`.", "Add `traffic_weight_at_most: 0` as a precondition."],
    },
    "no_traffic_to_unhealthy_region": {
        "small_step_rule": SMALL_STEP_RULES["no_traffic_to_unhealthy_region"],
        "weakest_precondition_hint": "Any region receiving positive traffic must be modeled healthy.",
        "remediation_examples": ["Require `region_healthy` before shifting traffic.", "Restore regional health or route elsewhere."],
    },
    "no_traffic_to_drained_load_balancer": {
        "small_step_rule": SMALL_STEP_RULES["no_traffic_to_drained_load_balancer"],
        "weakest_precondition_hint": "Any region receiving positive traffic must have an active, undrained load balancer.",
        "remediation_examples": ["Restore the load balancer before assigning traffic.", "Shift traffic away before draining the load balancer."],
    },
    "traffic_requires_regional_capacity": {
        "small_step_rule": SMALL_STEP_RULES["traffic_requires_regional_capacity"],
        "weakest_precondition_hint": "A route can send positive traffic to a region only if the service has a healthy undrained replica there.",
        "remediation_examples": ["Scale service replicas in the target region first.", "Keep traffic on regions with available capacity."],
    },
    "traffic_weights_sum_to_100": {
        "small_step_rule": SMALL_STEP_RULES["traffic_weights_sum_to_100"],
        "weakest_precondition_hint": "Traffic weights form a total distribution and must sum to exactly 100.",
        "remediation_examples": ["Use `failover_traffic` for single-target routing.", "Pair `shift_traffic` changes so weights remain normalized."],
    },
}


def small_step_rule(property_name: str) -> str:
    return SMALL_STEP_RULES.get(property_name, f"SafetyInvariant.{property_name}")


def scheduling_rules(step: Step, branch_factor: int, allow_reordering: bool) -> tuple[str, ...]:
    scheduled = SCHEDULER_DEPENDENCY_READY if allow_reordering else SCHEDULER_SEQUENCE_NEXT
    rules = [label_rule(scheduled, step.id)]
    if allow_reordering and branch_factor > 1:
        rules.append(label_rule(SCHEDULER_OPERATOR_CHOICE, step.id))
    return tuple(rules)


def action_rule(step: Step) -> str:
    return ACTION_WAIT if step.action == "wait" else ACTION_EXECUTE


def label_rule(rule: str, step_id: str | None = None) -> str:
    return f"{rule}({step_id})" if step_id else rule
