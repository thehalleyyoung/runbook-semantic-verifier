from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class Region:
    name: str
    healthy: bool = True


@dataclass(frozen=True)
class Replica:
    id: str
    region: str
    healthy: bool = True
    drained: bool = False


@dataclass(frozen=True)
class Service:
    name: str
    replicas: tuple[Replica, ...]
    min_available: int = 1
    deployment: str = "current"

    def available_count(self) -> int:
        return sum(1 for r in self.replicas if r.healthy and not r.drained)

    def with_replicas(self, replicas: tuple[Replica, ...]) -> "Service":
        return replace(self, replicas=replicas)


@dataclass(frozen=True)
class Database:
    name: str
    primary_region: str
    healthy_regions: frozenset[str]
    quorum_confirmed: bool = False
    migration_in_progress: bool = False
    migration_compatible: bool = True


@dataclass(frozen=True)
class Queue:
    name: str
    depth: int = 0
    consumers: int = 1
    paused: bool = False
    dead_letter_depth: int = 0
    dedupe_window_minutes: int = 0
    duplicate_risk: bool = False
    consumer_group_stable: bool = True


@dataclass(frozen=True)
class Alert:
    name: str
    active: bool = True
    suppressed_until_minute: int | None = None


@dataclass(frozen=True)
class FeatureFlag:
    name: str
    enabled: bool


@dataclass(frozen=True)
class Deployment:
    service: str
    current: str
    previous: str | None = None


@dataclass(frozen=True)
class TrafficRoute:
    name: str
    service: str
    weights: dict[str, int]
    drained_regions: frozenset[str] = frozenset()


@dataclass(frozen=True)
class DNSRecord:
    name: str
    service: str
    region: str
    ttl_minutes: int = 5
    last_changed_minute: int = 0
    previous_region: str | None = None
    health_check_converged_regions: frozenset[str] = frozenset()
    allow_split_brain: bool = False

    def ttl_elapsed(self, clock_minute: int) -> bool:
        if self.previous_region is None:
            return True
        return clock_minute - self.last_changed_minute >= self.ttl_minutes


@dataclass(frozen=True)
class SystemState:
    regions: dict[str, Region]
    services: dict[str, Service]
    databases: dict[str, Database]
    queues: dict[str, Queue]
    alerts: dict[str, Alert]
    flags: dict[str, FeatureFlag]
    deployments: dict[str, Deployment]
    traffic_routes: dict[str, TrafficRoute]
    dns_records: dict[str, DNSRecord]
    clock_minute: int = 0

    def fingerprint(self) -> tuple[Any, ...]:
        services = tuple(sorted((
            name,
            svc.min_available,
            svc.deployment,
            tuple(sorted((r.id, r.region, r.healthy, r.drained) for r in svc.replicas)),
        ) for name, svc in self.services.items()))
        databases = tuple(sorted((
            name, db.primary_region, tuple(sorted(db.healthy_regions)), db.quorum_confirmed,
            db.migration_in_progress, db.migration_compatible,
        ) for name, db in self.databases.items()))
        alerts = tuple(sorted((n, a.active, a.suppressed_until_minute) for n, a in self.alerts.items()))
        flags = tuple(sorted((n, f.enabled) for n, f in self.flags.items()))
        deployments = tuple(sorted((n, d.current, d.previous) for n, d in self.deployments.items()))
        regions = tuple(sorted((n, r.healthy) for n, r in self.regions.items()))
        queues = tuple(sorted((
            n,
            q.depth,
            q.consumers,
            q.paused,
            q.dead_letter_depth,
            q.dedupe_window_minutes,
            q.duplicate_risk,
            q.consumer_group_stable,
        ) for n, q in self.queues.items()))
        traffic_routes = tuple(sorted((
            n, route.service, tuple(sorted(route.weights.items())), tuple(sorted(route.drained_regions))
        ) for n, route in self.traffic_routes.items()))
        dns_records = tuple(sorted((
            n,
            record.service,
            record.region,
            record.ttl_minutes,
            record.last_changed_minute,
            record.previous_region,
            tuple(sorted(record.health_check_converged_regions)),
            record.allow_split_brain,
        ) for n, record in self.dns_records.items()))
        return (self.clock_minute, regions, services, databases, queues, alerts, flags, deployments, traffic_routes, dns_records)


@dataclass(frozen=True)
class Step:
    id: str
    action: str
    params: dict[str, Any]
    after: tuple[str, ...] = ()
    requires: tuple[dict[str, Any], ...] = ()
    effects: tuple[dict[str, Any], ...] = ()
    source_path: str | None = None
    source_line: int | None = None


@dataclass(frozen=True)
class Runbook:
    name: str
    description: str
    state: SystemState
    steps: tuple[Step, ...]
    max_depth: int
    allow_reordering: bool = True
    safety: dict[str, Any] = field(default_factory=dict)
