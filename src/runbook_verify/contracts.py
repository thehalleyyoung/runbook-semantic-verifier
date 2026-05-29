from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PropertyContract:
    property: str
    precondition: str
    action_effect: str
    postcondition: str
    weakest_precondition: str

    @property
    def hoare_triple(self) -> str:
        return f"{{ {self.precondition} }} action_effect: {self.action_effect} {{ {self.postcondition} }}"


ACTION_DENOTATIONS: dict[str, str] = {
    "restart_service": "Identity transformer on service capacity and deployment; validates the referenced service exists.",
    "drain_replica": "Sets services[service].replicas[replica].drained := true; all other state fields are framed.",
    "restore_replica": "Sets services[service].replicas[replica].drained := false; all other state fields are framed.",
    "drain_region": "For each selected service replica in params.region, sets drained := true; replicas in other regions are framed.",
    "rollback_deployment": "Sets services[service].deployment and deployments[service].current to params.to or 'previous'.",
    "failover_database": "Sets databases[database].primary_region := target_region; quorum and health facts are not created by the action.",
    "confirm_quorum": "Sets databases[database].quorum_confirmed := true.",
    "suppress_alert": "Sets alerts[alert].suppressed_until_minute := clock_minute + expires_after_minutes.",
    "scale_service": "Resizes services[service].replicas to params.replicas, generating healthy undrained replicas in params.region when growing.",
    "toggle_flag": "Sets feature_flags[flag].enabled := enabled, creating the modeled flag if absent.",
    "run_migration": "Sets database migration_in_progress and migration_compatible from parameters, defaulting to preserve compatibility.",
    "finish_migration": "Sets databases[database].migration_in_progress := false.",
    "pause_queue": "Sets queues[queue].paused := true.",
    "resume_queue": "Sets queues[queue].paused := false.",
    "replay_messages": "Adds count to queues[queue].depth, optionally subtracts count from dead_letter_depth, and sets duplicate_risk unless dedupe/idempotency is modeled.",
    "drain_dead_letter_queue": "Subtracts count from queues[queue].dead_letter_depth after validating the modeled backlog bound.",
    "rebalance_consumers": "Sets queues[queue].consumers := consumers and consumer_group_stable := stable (default false).",
    "freeze_cache_writes": "Sets caches[cache].write_frozen := true.",
    "resume_cache_writes": "Sets caches[cache].write_frozen := false.",
    "flush_cache": "Sets caches[cache].entries := 0, warm := false, and stale_read_risk := not write_frozen.",
    "warm_cache": "Sets caches[cache].entries := entries, warm according to warmup threshold, and clears stale_read_risk.",
    "wait": "Advances clock_minute by params.minutes; all modeled entities are framed.",
    "mark_region_health": "Sets regions[region].healthy := healthy.",
    "shift_traffic": "Sets traffic_routes[route].weights[region] := percent and, for two-region routes, assigns the peer region 100 - percent.",
    "failover_traffic": "Sets traffic_routes[route].weights[target_region] := 100 and all other modeled route weights to 0.",
    "drain_load_balancer": "Adds region to traffic_routes[route].drained_regions.",
    "restore_load_balancer": "Removes region from traffic_routes[route].drained_regions.",
    "update_dns_record": "Sets dns_records[record].region := target_region, previous_region := old region, and last_changed_minute := clock_minute.",
    "mark_dns_health_check": "Adds or removes region from dns_records[record].health_check_converged_regions according to converged.",
    "finalize_dns_record": "Sets dns_records[record].previous_region := None after the TTL proof obligation has elapsed.",
    "revoke_credential": "Sets credentials[credential].revoked := true; ownership metadata and all non-credential state are framed.",
    "rotate_credential": "Sets credentials[credential].revoked := false and rotation_due_minute := None after modeled rotation evidence.",
}

PROPERTY_CONTRACTS: dict[str, PropertyContract] = {
    "service_min_available": PropertyContract("service_min_available", "available(service) >= min_available(service) before and after capacity-changing actions", "drain/scale/restore may change available(service)", "available(service) >= min_available(service)", "Scale or restore replacement replicas before draining; require service_available_at_least for the affected service."),
    "no_draining_all_replicas": PropertyContract("no_draining_all_replicas", "service has at least one healthy undrained replica or the runbook explicitly models zero-replica safety", "drain actions may set replica.drained", "not all replicas of any non-empty service are drained", "Drain one failure domain at a time; require a remaining replica or add a modeled restore/scale step first."),
    "no_rollback_during_incompatible_migration": PropertyContract("no_rollback_during_incompatible_migration", "no database has migration_in_progress and migration_compatible=false", "rollback_deployment changes service deployment", "rollback does not occur during incompatible migration", "Finish the migration or prove compatibility before rollback."),
    "no_failover_to_unhealthy_region": PropertyContract("no_failover_to_unhealthy_region", "target_region is healthy in both region and database health sets", "failover_database changes primary_region", "database primary region remains healthy", "Require region_healthy and database healthy_regions membership before failover."),
    "quorum_before_data_loss_action": PropertyContract("quorum_before_data_loss_action", "database_quorum_confirmed(database) when data_loss_risk=true", "failover_database may risk data loss", "data-loss-risk failover has quorum evidence", "Run confirm_quorum first or add a database_quorum_confirmed precondition."),
    "bounded_alert_suppression": PropertyContract("bounded_alert_suppression", "expires_after_minutes is positive and within safety.max_alert_suppression_minutes", "suppress_alert sets suppressed_until_minute", "alert suppression remains bounded", "Use a finite reviewed expiry within policy."),
    "precondition": PropertyContract("precondition", "all declared step.requires conditions hold", "enabled action consumes the pre-state", "declared requires obligations are true before action", "Add an after dependency or a prior step establishing the failed condition."),
    "effect": PropertyContract("effect", "action parameters are capable of establishing every declared effect", "action transformer updates modeled fields", "all declared step.effects conditions hold", "Repair action parameters or effects so the promised postcondition is true."),
    "no_queue_pause_without_drain_plan": PropertyContract("no_queue_pause_without_drain_plan", "queue depth is zero or alternate consumers are modeled", "pause_queue sets paused=true", "paused queues do not strand backlog", "Drain backlog or require sufficient consumers before pause."),
    "no_paused_queue_with_backlog": PropertyContract("no_paused_queue_with_backlog", "queue will not be paused with depth>0 and consumers<=1", "queue actions may change paused/depth/consumers", "no reachable paused backlog without processing capacity", "Resume the queue or drain backlog before terminal state."),
    "no_replay_without_dedupe": PropertyContract("no_replay_without_dedupe", "replay has dedupe_key, idempotent=true, positive dedupe window, or count=0", "replay_messages adds messages", "replay does not introduce duplicate-processing risk", "Model dedupe/idempotency before replay."),
    "dead_letter_replay_has_messages": PropertyContract("dead_letter_replay_has_messages", "dead_letter_depth >= replay count", "replay_messages may subtract from dead_letter_depth", "DLQ depth never goes negative", "Limit replay count to current DLQ depth."),
    "dead_letter_drain_has_messages": PropertyContract("dead_letter_drain_has_messages", "dead_letter_depth >= drain count", "drain_dead_letter_queue subtracts from dead_letter_depth", "DLQ depth never goes negative", "Limit drain count to current DLQ depth."),
    "no_duplicate_processing_risk": PropertyContract("no_duplicate_processing_risk", "duplicate_risk is false and replay guards preserve it", "unsafe replay may set duplicate_risk=true", "duplicate_risk remains false", "Add dedupe/idempotency or quarantine duplicate-risk messages."),
    "queue_backlog_requires_consumers": PropertyContract("queue_backlog_requires_consumers", "depth=0 or consumers>0", "replay/rebalance may change depth or consumers", "backlog has at least one consumer", "Restore consumers before creating or leaving backlog."),
    "no_rebalance_to_zero_consumers": PropertyContract("no_rebalance_to_zero_consumers", "depth=0 or target consumers>0", "rebalance_consumers sets consumer count", "backlog is not assigned zero consumers", "Drain queue or rebalance to a positive consumer count."),
    "no_unstable_consumer_group_with_backlog": PropertyContract("no_unstable_consumer_group_with_backlog", "depth=0 or consumer_group_stable=true", "rebalance/replay may leave backlog", "backlog is processed only by a stable consumer group", "Wait for consumer-group stability before leaving backlog."),
    "cache_flush_requires_write_freeze": PropertyContract("cache_flush_requires_write_freeze", "cache_writes_frozen(cache)", "flush_cache evicts entries", "destructive flush cannot race writers", "Freeze cache writes before flushing."),
    "cache_warmup_before_traffic": PropertyContract("cache_warmup_before_traffic", "warmup entries meet threshold before resuming writes/traffic", "flush/warm/resume alter cache warmness", "cold cache is not exposed to traffic", "Warm to the modeled threshold before resuming."),
    "cache_warmup_within_capacity": PropertyContract("cache_warmup_within_capacity", "warmup entries <= capacity_entries", "warm_cache sets entries", "cache entries stay within capacity", "Increase capacity or lower warmup size."),
    "no_stale_reads_after_cache_flush": PropertyContract("no_stale_reads_after_cache_flush", "writes frozen or stale-read risk cleared by warmup", "flush_cache may set stale_read_risk", "no stale-read-risk state remains", "Freeze writes and complete warmup/verification."),
    "traffic_weights_sum_to_100": PropertyContract("traffic_weights_sum_to_100", "route weights form a 100% distribution", "traffic actions update weights", "sum(weights)=100", "Use failover_traffic or paired shift_traffic updates."),
    "no_traffic_to_unhealthy_region": PropertyContract("no_traffic_to_unhealthy_region", "target region is healthy", "traffic actions assign positive weight", "positive traffic only reaches healthy regions", "Require region_healthy before traffic shift."),
    "no_traffic_to_drained_load_balancer": PropertyContract("no_traffic_to_drained_load_balancer", "target load balancer is active", "traffic/drain actions change route and LB status", "positive traffic only reaches active load balancers", "Restore LB or shift traffic away before draining."),
    "no_draining_load_balancer_with_traffic": PropertyContract("no_draining_load_balancer_with_traffic", "traffic weight to drained region is 0", "drain_load_balancer adds drained region", "drained LB receives no traffic", "Shift traffic weight to 0 before draining."),
    "traffic_requires_regional_capacity": PropertyContract("traffic_requires_regional_capacity", "target region has a healthy undrained service replica", "traffic actions assign positive weight", "positive traffic has regional capacity", "Scale or restore capacity before assigning traffic."),
    "dns_target_region_healthy": PropertyContract("dns_target_region_healthy", "DNS target region is healthy", "update_dns_record changes target", "DNS points only to healthy regions", "Require region_healthy before cutover."),
    "dns_health_check_converged_before_cutover": PropertyContract("dns_health_check_converged_before_cutover", "target DNS health check has converged", "update_dns_record changes target", "DNS cutover follows health convergence", "Run/record DNS health-check convergence first."),
    "dns_requires_regional_capacity": PropertyContract("dns_requires_regional_capacity", "DNS target has service capacity", "update/finalize DNS changes routing", "DNS target can serve the service", "Scale or restore service replicas in the DNS target region."),
    "dns_ttl_elapsed_before_recursion": PropertyContract("dns_ttl_elapsed_before_recursion", "prior TTL elapsed or active-active split brain is safe", "update_dns_record starts a TTL window", "recursive cutovers do not overlap stateful TTL windows", "Wait for previous TTL or explicitly model active-active safety."),
    "dns_ttl_elapsed_before_finalize": PropertyContract("dns_ttl_elapsed_before_finalize", "record.ttl_elapsed(clock_minute)", "finalize_dns_record clears previous_region", "finalization happens after TTL", "Insert a wait covering the record TTL."),
    "dns_no_split_brain_during_ttl": PropertyContract("dns_no_split_brain_during_ttl", "record allows split brain or TTL has elapsed", "DNS cutover maintains previous_region during propagation", "stateful split-brain window is absent", "Wait for TTL or set allow_split_brain only for active-active-safe records."),
    "effect_annotation_required": PropertyContract("effect_annotation_required", "high-risk actions declare reviewed effect metadata", "operator action may delete, revoke, drain, replay, degrade users, or make irreversible state changes", "effect annotations make retry/reversal/blast-radius assumptions auditable", "Add effect_annotations with effect_types, idempotency, reversibility, retry_safety, blast_radius, and expected_user_impact."),
    "unsafe_retry_annotation": PropertyContract("unsafe_retry_annotation", "non-idempotent or irreversible actions are not marked retry-safe", "operator retry may repeat destructive effects", "retry policy matches modeled effect risk", "Mark retry_safety=unsafe/unknown or make the action idempotent/reversible with a reviewed guard."),
    "credential_active": PropertyContract("credential_active", "credential is not revoked before dependent use", "credential actions may revoke or rotate credentials", "credential remains active unless explicitly revoked", "Rotate the credential or add a credential_active precondition before dependent operations."),
}


def action_denotation(action: str) -> str:
    return ACTION_DENOTATIONS.get(action, "No denotation registered for this action.")


def hoare_triple_for(property_name: str) -> str:
    contract = PROPERTY_CONTRACTS.get(property_name)
    if contract is None:
        return f"{{ invariant precondition for {property_name} }} action_effect {{ {property_name} holds }}"
    return contract.hoare_triple


def weakest_precondition_for(property_name: str) -> str:
    contract = PROPERTY_CONTRACTS.get(property_name)
    if contract is None:
        return "Strengthen the runbook preconditions so the invariant holds before and after the action."
    return contract.weakest_precondition


def render_weakest_preconditions_markdown() -> str:
    lines = [
        "# Weakest-precondition templates",
        "",
        "These templates are bounded-model obligations used by `frv check`, `frv explain`,",
        "and generated Hoare triples. They are repair hints for executable runbook models,",
        "not claims about live infrastructure safety.",
        "",
        "| Property | Hoare triple | Weakest-precondition template |",
        "| --- | --- | --- |",
    ]
    for name in sorted(PROPERTY_CONTRACTS):
        contract = PROPERTY_CONTRACTS[name]
        lines.append(f"| `{name}` | `{contract.hoare_triple}` | {contract.weakest_precondition} |")
    return "\n".join(lines) + "\n"
