from __future__ import annotations

import json
from typing import Any

from .contracts import PROPERTY_CONTRACTS, action_denotation
from .descriptors import ACTION_DESCRIPTORS
from .model import Runbook, Step

TLA_VARIABLES = (
    "done",
    "clock",
    "regions",
    "services",
    "replicas",
    "databases",
    "queues",
    "caches",
    "alerts",
    "flags",
    "deployments",
    "trafficRoutes",
    "dnsRecords",
    "credentials",
    "owners",
    "waivers",
    "dependencies",
)

ENTITY_COLLECTIONS = (
    "regions",
    "services",
    "replicas",
    "databases",
    "queues",
    "caches",
    "alerts",
    "flags",
    "deployments",
    "trafficRoutes",
    "dnsRecords",
    "credentials",
)

PROPERTY_TLA_NAME_OVERRIDES = {
    "service_min_available": "ServiceMinAvailable",
    "no_draining_all_replicas": "NoDrainingAllReplicas",
    "bounded_alert_suppression": "BoundedAlertSuppression",
    "no_failover_to_unhealthy_region": "NoUnsafeDatabaseFailover",
    "quorum_before_data_loss_action": "QuorumBeforeDataLossAction",
    "no_rollback_during_incompatible_migration": "NoRollbackDuringIncompatibleMigration",
    "queue_backlog_requires_consumers": "QueueBacklogRequiresConsumers",
    "no_paused_queue_with_backlog": "NoPausedQueueWithBacklog",
    "no_duplicate_processing_risk": "NoDuplicateProcessingRisk",
    "no_unstable_consumer_group_with_backlog": "NoUnstableConsumerGroupWithBacklog",
    "cache_flush_requires_write_freeze": "CacheFlushRequiresWriteFreeze",
    "cache_warmup_before_traffic": "CacheWarmupBeforeTraffic",
    "cache_warmup_within_capacity": "CacheWarmupWithinCapacity",
    "no_stale_reads_after_cache_flush": "NoStaleReadsAfterCacheFlush",
    "traffic_weights_sum_to_100": "TrafficWeightsSumTo100",
    "no_traffic_to_unhealthy_region": "NoTrafficToUnhealthyRegion",
    "no_traffic_to_drained_load_balancer": "NoTrafficToDrainedLoadBalancer",
    "traffic_requires_regional_capacity": "TrafficRequiresRegionalCapacity",
    "dns_target_region_healthy": "DNSTargetRegionHealthy",
    "dns_health_check_converged_before_cutover": "DNSHealthCheckConvergedBeforeCutover",
    "dns_requires_regional_capacity": "DNSRequiresRegionalCapacity",
    "dns_ttl_elapsed_before_finalize": "DNSTTLElapsedBeforeFinalize",
    "dns_no_split_brain_during_ttl": "DNSNoSplitBrainDuringTTL",
    "credential_active": "CredentialActive",
    "effect_annotation_required": "EffectAnnotationRequired",
    "unsafe_retry_annotation": "UnsafeRetryAnnotation",
}


def _property_tla_names() -> dict[str, str]:
    return {name: PROPERTY_TLA_NAME_OVERRIDES.get(name, _symbol(name)) for name in PROPERTY_CONTRACTS}


def export_tla(runbook: Runbook) -> str:
    manifest = export_conformance_manifest(runbook)
    step_names = ", ".join(_tla_string(s.id) for s in runbook.steps)
    variables = ", ".join(TLA_VARIABLES)
    lines = [
        f"---- MODULE {_module_name(runbook.name)} ----",
        "EXTENDS Naturals, Sequences, FiniteSets, TLC",
        "",
        f"\\* Generated starter spec for runbook: {runbook.name}",
        "\\* Native checker remains authoritative; see docs/formal_exports.md for limits.",
        f"CONSTANTS Steps \\* {{{step_names}}}",
        f"VARIABLES {variables}",
        "",
        f"AllVars == <<{variables}>>",
        f"StepSet == {{{step_names}}}",
        _tla_literal_definition("DependencyEdges", manifest["enabledness_edges"]),
        _tla_literal_definition("PropertyIdentifiers", manifest["property_identifiers"]),
        _tla_literal_definition("WaiverIdentifiers", [w["id"] for w in manifest["waivers"]]),
        "",
        "Init == /\\ done = <<>>",
        "        /\\ clock = 0",
        "        /\\ Steps = StepSet",
        "        /\\ dependencies = DependencyEdges",
        "        /\\ waivers = WaiverIdentifiers",
    ]
    for variable in ENTITY_COLLECTIONS:
        lines.append(f"        /\\ {variable} = {{{', '.join(_tla_string(x) for x in manifest['entities'][variable])}}}")
    lines.extend([
        f"        /\\ owners = {{{', '.join(_tla_string(owner) for owner in manifest['owners'])}}}",
        "",
        "Predecessors(step) == { edge[1] : edge \\in dependencies /\\ edge[2] = step }",
        "DoneSet == SeqToSet(done)",
        "CanRun(step) == /\\ step \\in StepSet",
        "                /\\ step \\notin DoneSet",
        "                /\\ Predecessors(step) \\subseteq DoneSet",
        "Run(step) == /\\ CanRun(step)",
        "             /\\ done' = Append(done, step)",
        "             /\\ UNCHANGED <<clock, regions, services, replicas, databases, queues, caches, alerts, flags, deployments, trafficRoutes, dnsRecords, credentials, owners, waivers, dependencies>>",
        "Wait(minutes) == /\\ minutes \\in Nat",
        "                 /\\ clock' = clock + minutes",
        "                 /\\ UNCHANGED <<done, regions, services, replicas, databases, queues, caches, alerts, flags, deployments, trafficRoutes, dnsRecords, credentials, owners, waivers, dependencies>>",
        "Next == \\E step \\in StepSet : Run(step)",
        "",
        "\\* Invariant templates preserve native property identifiers for round-trip checks.",
    ])
    for prop, tla_name in sorted(_property_tla_names().items(), key=lambda item: item[1]):
        contract = PROPERTY_CONTRACTS.get(prop)
        wp = contract.weakest_precondition if contract else "native checker property"
        lines.append(f"{tla_name} == TRUE \\* property={prop}; obligation={_escape_comment(wp)}")
    invariant_names = [_property_tla_names()[prop] for prop in sorted(_property_tla_names())]
    lines.extend([
        "",
        "Safety == " + " /\\ ".join(invariant_names),
        "Spec == Init /\\ [][Next]_AllVars",
        "THEOREM Spec => []Safety",
        "====",
        "",
        "\\* Action mapping from DSL:",
    ])
    for step in runbook.steps:
        lines.extend(_tla_step_comment(step))
    lines.extend([
        "\\* Proof obligations:",
    ])
    for obligation in build_proof_obligations(runbook):
        lines.append(f"\\* obligation {obligation['id']}: {obligation['kind']} {obligation['subject']} -> {obligation['claim']}")
    return "\n".join(lines) + "\n"


def export_alloy(runbook: Runbook) -> str:
    manifest = export_conformance_manifest(runbook)
    lines = [
        "module runbook_verification",
        "",
        "abstract sig Step { after: set Step, action: one ActionLabel }",
        "abstract sig ActionLabel {}",
        "abstract sig PropertyLabel {}",
        "abstract sig Entity {}",
        "abstract sig Service, Replica, Region, Database, Queue, Cache, Alert, Credential, TrafficRoute, DNSRecord, Owner, Waiver extends Entity {}",
        "sig State { done: set Step }",
        "",
    ]
    for action in sorted({s.action for s in runbook.steps}):
        lines.append(f"one sig {_symbol(action)}Action extends ActionLabel {{}}")
    for prop in manifest["property_identifiers"]:
        lines.append(f"one sig {_symbol(prop)}Property extends PropertyLabel {{}}")
    for collection, sig in (
        ("regions", "Region"),
        ("services", "Service"),
        ("replicas", "Replica"),
        ("databases", "Database"),
        ("queues", "Queue"),
        ("caches", "Cache"),
        ("alerts", "Alert"),
        ("credentials", "Credential"),
        ("trafficRoutes", "TrafficRoute"),
        ("dnsRecords", "DNSRecord"),
        ("owners", "Owner"),
    ):
        for name in manifest["entities"].get(collection, []) if collection != "owners" else manifest["owners"]:
            lines.append(f"one sig {_symbol(str(name))} extends {sig} {{}}")
    for waiver in manifest["waivers"]:
        lines.append(f"one sig {_symbol(waiver['id'])}Waiver extends Waiver {{}} // invariant={waiver['invariant']} scope={waiver['scope']}")
    lines.append("")
    for step in runbook.steps:
        descriptor = ACTION_DESCRIPTORS[step.action]
        lines.append(f"one sig {_symbol(step.id)} extends Step {{}} // {step.id}: {step.action}({descriptor.signature()}); denotation: {action_denotation(step.action)}")
    lines.extend([
        "",
        "fact DependencyGraph {",
    ])
    for step in runbook.steps:
        deps = " + ".join(_symbol(dep) for dep in step.after) or "none"
        lines.append(f"  {_symbol(step.id)}.after = {deps}")
        lines.append(f"  {_symbol(step.id)}.action = {_symbol(step.action)}Action")
    lines.extend([
        "  no iden & ^after",
        "}",
        "",
        "pred enabled[s: State, st: Step] { st not in s.done and st.after in s.done }",
        "pred transition[s, s': State] { some st: Step | enabled[s, st] and s'.done = s.done + st }",
        "pred preservesNativeEnabledness { all s: State, st: Step | enabled[s, st] iff (st not in s.done and st.after in s.done) }",
        "",
    ])
    for prop in manifest["property_identifiers"]:
        lines.append(f"pred {_symbol(prop)}Holds[s: State] {{ /* native property label: {prop}; concrete arithmetic checked by frv */ }}")
    lines.extend([
        "",
        "assert NativeEnablednessPreserved { preservesNativeEnabledness }",
        "assert SafetyLabelsPresent { all p: PropertyLabel | some p }",
        f"check NativeEnablednessPreserved for {max(8, len(runbook.steps) + 3)} but exactly {len(runbook.steps)} Step",
        f"check SafetyLabelsPresent for {max(8, len(manifest['property_identifiers']) + 3)}",
    ])
    return "\n".join(lines) + "\n"


def export_conformance_manifest(runbook: Runbook) -> dict[str, Any]:
    entities = _entity_manifest(runbook)
    properties = sorted(_property_tla_names())
    return {
        "runbook": runbook.name,
        "action_sequence": [step.id for step in runbook.steps],
        "action_comments": [
            {
                "id": step.id,
                "action": step.action,
                "signature": ACTION_DESCRIPTORS[step.action].signature(),
                "denotation": action_denotation(step.action),
                "after": list(step.after),
            }
            for step in runbook.steps
        ],
        "variables": list(TLA_VARIABLES),
        "entities": entities,
        "owners": _owners(runbook),
        "enabledness_edges": [[dep, step.id] for step in runbook.steps for dep in step.after],
        "property_identifiers": properties,
        "waivers": [
            {
                "id": waiver.id,
                "owner": waiver.owner,
                "scope": waiver.scope,
                "invariant": waiver.invariant,
                "expiry": waiver.expiry,
            }
            for waiver in runbook.waivers
        ],
        "abstractions": [
            "Exporter emits starter models preserving names, dependencies, property labels, and action comments; native Python checker remains the executable semantics.",
            "TLA+ invariant bodies are templates unless manually strengthened with concrete state encodings.",
            "Alloy assertions preserve bounded relations and labels; arithmetic service/queue/cache checks are delegated to frv.",
        ],
    }


def build_proof_obligations(runbook: Runbook) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    for prop in sorted(_property_tla_names()):
        contract = PROPERTY_CONTRACTS.get(prop)
        obligations.append({
            "id": f"invariant:{prop}",
            "kind": "invariant",
            "subject": prop,
            "claim": contract.postcondition if contract else f"{prop} holds",
            "weakest_precondition": contract.weakest_precondition if contract else "Strengthen modeled preconditions.",
            "checked_by": "native bounded checker; exported as TLA+/Alloy label",
        })
    for step in runbook.steps:
        for idx, condition in enumerate(step.requires, start=1):
            obligations.append({
                "id": f"precondition:{step.id}:{idx}",
                "kind": "refinement-precondition",
                "subject": step.id,
                "claim": json.dumps(condition, sort_keys=True),
                "checked_by": "native checker before action execution",
            })
        for idx, effect in enumerate(step.effects, start=1):
            obligations.append({
                "id": f"effect:{step.id}:{idx}",
                "kind": "promised-effect",
                "subject": step.id,
                "claim": json.dumps(effect, sort_keys=True),
                "checked_by": "native checker after action execution",
            })
        if step.action in {"wait", "suppress_alert", "update_dns_record", "finalize_dns_record"}:
            obligations.append({
                "id": f"temporal:{step.id}",
                "kind": "temporal-monitor-template",
                "subject": step.id,
                "claim": "runtime logs should preserve modeled wait/expiry/TTL ordering if used for runtime verification",
                "checked_by": "not checked without external execution log",
            })
    obligations.extend([
        {
            "id": "exporter:tla-abstraction",
            "kind": "exporter-abstraction",
            "subject": "TLA+",
            "claim": "Export preserves step ids, dependencies, state-variable names, property identifiers, and action denotation comments.",
            "checked_by": "round-trip exporter tests",
        },
        {
            "id": "exporter:alloy-abstraction",
            "kind": "exporter-abstraction",
            "subject": "Alloy",
            "claim": "Export preserves step signatures, dependency graph, waiver labels, entity signatures, and safety-property labels.",
            "checked_by": "round-trip exporter tests",
        },
        {
            "id": "checker:optimization-soundness",
            "kind": "checker-optimization",
            "subject": "bounded exploration",
            "claim": "Current exporter conformance assumes no partial-order or dominance pruning changes native counterexample labels.",
            "checked_by": "benchmark performance counters and regression tests",
        },
    ])
    return obligations


def render_proof_obligations_json(runbook: Runbook) -> str:
    payload = {
        "runbook": runbook.name,
        "conformance": export_conformance_manifest(runbook),
        "proof_obligations": build_proof_obligations(runbook),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_proof_obligations_markdown(runbook: Runbook) -> str:
    lines = [
        f"# Proof obligations: {runbook.name}",
        "",
        "These obligations make explicit what the native checker, exported starter models, and future runtime monitors are expected to preserve. They are bounded artifact obligations, not claims about live infrastructure.",
        "",
        "| ID | Kind | Subject | Claim | Checked by |",
        "| --- | --- | --- | --- | --- |",
    ]
    for obligation in build_proof_obligations(runbook):
        lines.append("| `{id}` | {kind} | `{subject}` | {claim} | {checked_by} |".format(
            id=obligation["id"],
            kind=obligation["kind"],
            subject=str(obligation["subject"]).replace("|", "\\|"),
            claim=str(obligation["claim"]).replace("|", "\\|"),
            checked_by=str(obligation["checked_by"]).replace("|", "\\|"),
        ))
    return "\n".join(lines) + "\n"


def _entity_manifest(runbook: Runbook) -> dict[str, list[str]]:
    state = runbook.state
    replicas = sorted(replica.id for service in state.services.values() for replica in service.replicas)
    return {
        "regions": sorted(state.regions),
        "services": sorted(state.services),
        "replicas": replicas,
        "databases": sorted(state.databases),
        "queues": sorted(state.queues),
        "caches": sorted(state.caches),
        "alerts": sorted(state.alerts),
        "flags": sorted(state.flags),
        "deployments": sorted(state.deployments),
        "trafficRoutes": sorted(state.traffic_routes),
        "dnsRecords": sorted(state.dns_records),
        "credentials": sorted(state.credentials),
    }


def _owners(runbook: Runbook) -> list[str]:
    owners = set()
    metadata_owner = runbook.metadata.get("owner")
    if metadata_owner:
        owners.add(str(metadata_owner))
    for credential in runbook.state.credentials.values():
        owners.add(credential.owner)
    for waiver in runbook.waivers:
        owners.add(waiver.owner)
    return sorted(owners)


def _tla_step_comment(step: Step) -> list[str]:
    descriptor = ACTION_DESCRIPTORS[step.action]
    return [
        f"\\* step {step.id}: action={step.action}; after={list(step.after)}",
        f"\\* signature: {step.action}({descriptor.signature()}) params={json.dumps(step.params, sort_keys=True)}",
        f"\\* denotation: {action_denotation(step.action)}",
    ]


def _tla_literal_definition(name: str, values: list[Any]) -> str:
    return f"{name} == {_tla_value(values)}"


def _tla_value(value: Any) -> str:
    if isinstance(value, str):
        return _tla_string(value)
    if isinstance(value, list):
        if value and all(isinstance(item, list) and len(item) == 2 for item in value):
            return "{" + ", ".join(f"<<{_tla_value(item[0])}, {_tla_value(item[1])}>>" for item in value) + "}"
        return "{" + ", ".join(_tla_value(item) for item in value) + "}"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return "NULL"
    return str(value)


def _tla_string(value: str) -> str:
    return json.dumps(value)


def _module_name(name: str) -> str:
    text = "".join(ch if ch.isalnum() else "_" for ch in name.title())
    return text or "Runbook"


def _symbol(name: str) -> str:
    text = "".join(ch if ch.isalnum() else "_" for ch in name.title())
    if text and text[0].isdigit():
        text = "_" + text
    return text or "Step"


def _escape_comment(text: str) -> str:
    return text.replace("\n", " ").replace("*)", "* )")
