from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .parser import load_runbook

TYPE_INVENTORY_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class TypeFact:
    name: str
    type: str
    fields: dict[str, Any] = field(default_factory=dict)


def build_type_inventory(path: str | Path) -> dict[str, Any]:
    runbook = load_runbook(path)
    state = runbook.state
    facts: list[TypeFact] = []
    for name, region in sorted(state.regions.items()):
        facts.append(TypeFact(name, "region", {"healthy": region.healthy}))
    for service_name, service in sorted(state.services.items()):
        facts.append(TypeFact(service_name, "service", {"min_available": service.min_available, "deployment": service.deployment}))
        for replica in service.replicas:
            facts.append(TypeFact(replica.id, "replica", {"service": service_name, "region": replica.region, "healthy": replica.healthy, "drained": replica.drained}))
    for name, db in sorted(state.databases.items()):
        facts.append(TypeFact(name, "database", {"primary_region": db.primary_region, "healthy_regions": sorted(db.healthy_regions), "quorum_confirmed": db.quorum_confirmed}))
    for name, queue in sorted(state.queues.items()):
        facts.append(TypeFact(name, "queue", {"depth": queue.depth, "consumers": queue.consumers, "paused": queue.paused}))
    for name, cache in sorted(state.caches.items()):
        facts.append(TypeFact(name, "cache", {"service": cache.service, "warm": cache.warm, "capacity_entries": cache.capacity_entries}))
    for name, bucket in sorted(state.object_buckets.items()):
        facts.append(TypeFact(name, "object_bucket", {"region": bucket.region, "replicated_regions": sorted(bucket.replicated_regions), "rpo_minutes": bucket.rpo_minutes, "rto_minutes": bucket.rto_minutes}))
        facts.append(TypeFact(f"{name}:rpo", "duration", {"minutes": bucket.rpo_minutes, "source": "object_bucket_rpo"}))
        facts.append(TypeFact(f"{name}:rto", "duration", {"minutes": bucket.rto_minutes, "source": "object_bucket_rto"}))
    for name, route in sorted(state.traffic_routes.items()):
        facts.append(TypeFact(name, "traffic_route", {"service": route.service, "weights": route.weights}))
        for region, percent in sorted(route.weights.items()):
            facts.append(TypeFact(f"{name}:{region}", "traffic_weight", {"route": name, "region": region, "percent": percent}))
    for name, record in sorted(state.dns_records.items()):
        facts.append(TypeFact(name, "dns_record", {"service": record.service, "region": record.region, "ttl_minutes": record.ttl_minutes}))
        facts.append(TypeFact(f"{name}:ttl", "duration", {"minutes": record.ttl_minutes, "source": "dns_ttl"}))
    for name, alert in sorted(state.alerts.items()):
        facts.append(TypeFact(name, "alert", {"active": alert.active, "suppressed_until_minute": alert.suppressed_until_minute}))
    for name, credential in sorted(state.credentials.items()):
        facts.append(TypeFact(name, "credential", {"owner": credential.owner, "revoked": credential.revoked}))
        facts.append(TypeFact(f"{name}:owner", "ownership_metadata", {"owner": credential.owner, "entity": name}))
    for owner in _metadata_owners(runbook.metadata):
        facts.append(TypeFact(f"metadata:owner:{owner}", "ownership_metadata", {"owner": owner, "entity": "runbook"}))
    for step in runbook.steps:
        if step.action == "wait":
            facts.append(TypeFact(f"{step.id}:wait", "duration", {"minutes": step.params["minutes"], "source": "step"}))
        if "owner" in step.params:
            facts.append(TypeFact(f"{step.id}:owner", "ownership_metadata", {"owner": step.params["owner"], "entity": step.id}))
    counts: dict[str, int] = {}
    for fact in facts:
        counts[fact.type] = counts.get(fact.type, 0) + 1
    return {
        "runbook": runbook.name,
        "path": str(path),
        "type_inventory_schema_version": TYPE_INVENTORY_SCHEMA_VERSION,
        "schema_migration": {
            "strategy": "additive_schema_preserving",
            "compatible_with_runbook_schema": True,
            "notes": "The inventory is derived from parsed runbook fields and does not rewrite the source DSL.",
        },
        "counts": dict(sorted(counts.items())),
        "facts": [asdict(fact) for fact in facts],
    }


def _metadata_owners(metadata: dict[str, Any]) -> list[str]:
    owners: set[str] = set()
    raw_owner = metadata.get("owner")
    if isinstance(raw_owner, str):
        owners.add(raw_owner)
    raw_owners = metadata.get("owners")
    if isinstance(raw_owners, list):
        for owner in raw_owners:
            if isinstance(owner, str):
                owners.add(owner)
            elif isinstance(owner, dict) and isinstance(owner.get("owner"), str):
                owners.add(str(owner["owner"]))
    service_owners = metadata.get("service_owners")
    if isinstance(service_owners, dict):
        for value in service_owners.values():
            if isinstance(value, str):
                owners.add(value)
            elif isinstance(value, list):
                owners.update(owner for owner in value if isinstance(owner, str))
    return sorted(owners)


def render_type_inventory_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_type_inventory_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Type inventory: {report['runbook']}",
        "",
        f"- Path: `{report['path']}`",
        f"- Inventory schema: `{report['type_inventory_schema_version']}`",
        f"- Migration: `{json.dumps(report['schema_migration'], sort_keys=True)}`",
        f"- Counts: `{json.dumps(report['counts'], sort_keys=True)}`",
        "",
        "| Name | Type | Fields |",
        "| --- | --- | --- |",
    ]
    for fact in report["facts"]:
        lines.append(f"| `{fact['name']}` | `{fact['type']}` | `{json.dumps(fact['fields'], sort_keys=True)}` |")
    return "\n".join(lines) + "\n"
