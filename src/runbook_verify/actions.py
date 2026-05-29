from __future__ import annotations

from dataclasses import replace
from typing import Any

from .descriptors import ACTION_SCHEMAS, CONDITION_SCHEMAS
from .model import Alert, Database, Deployment, FeatureFlag, Queue, Replica, Service, Step, SystemState, TrafficRoute


class ActionError(ValueError):
    pass


def _copy_state(state: SystemState, **updates: Any) -> SystemState:
    data = {
        "regions": state.regions,
        "services": state.services,
        "databases": state.databases,
        "queues": state.queues,
        "alerts": state.alerts,
        "flags": state.flags,
        "deployments": state.deployments,
        "traffic_routes": state.traffic_routes,
        "clock_minute": state.clock_minute,
    }
    data.update(updates)
    return SystemState(**data)


def _service(state: SystemState, name: str) -> Service:
    try:
        return state.services[name]
    except KeyError as exc:
        raise ActionError(f"unknown service {name!r}") from exc


def _database(state: SystemState, name: str) -> Database:
    try:
        return state.databases[name]
    except KeyError as exc:
        raise ActionError(f"unknown database {name!r}") from exc


def _alert(state: SystemState, name: str) -> Alert:
    try:
        return state.alerts[name]
    except KeyError as exc:
        raise ActionError(f"unknown alert {name!r}") from exc


def _queue(state: SystemState, name: str) -> Queue:
    try:
        return state.queues[name]
    except KeyError as exc:
        raise ActionError(f"unknown queue {name!r}") from exc


def _route(state: SystemState, name: str) -> TrafficRoute:
    try:
        return state.traffic_routes[name]
    except KeyError as exc:
        raise ActionError(f"unknown traffic route {name!r}") from exc


def _with_service(state: SystemState, service: Service) -> SystemState:
    services = dict(state.services)
    services[service.name] = service
    return _copy_state(state, services=services)


def apply_action(state: SystemState, step: Step) -> SystemState:
    p = step.params
    action = step.action
    if action == "restart_service":
        svc = _service(state, str(p["service"]))
        return _with_service(state, svc)
    if action == "drain_replica":
        svc = _service(state, str(p["service"]))
        rid = str(p["replica"])
        found = False
        replicas = []
        for r in svc.replicas:
            if r.id == rid:
                found = True
                replicas.append(replace(r, drained=True))
            else:
                replicas.append(r)
        if not found:
            raise ActionError(f"unknown replica {rid!r} for service {svc.name!r}")
        return _with_service(state, svc.with_replicas(tuple(replicas)))
    if action == "restore_replica":
        svc = _service(state, str(p["service"]))
        rid = str(p["replica"])
        found = False
        replicas = []
        for r in svc.replicas:
            if r.id == rid:
                found = True
                replicas.append(replace(r, drained=False))
            else:
                replicas.append(r)
        if not found:
            raise ActionError(f"unknown replica {rid!r} for service {svc.name!r}")
        return _with_service(state, svc.with_replicas(tuple(replicas)))
    if action == "drain_region":
        region = str(p["region"])
        services = dict(state.services)
        for svc_name in p.get("services", list(services.keys())):
            svc = _service(state, str(svc_name))
            replicas = tuple(replace(r, drained=True) if r.region == region else r for r in svc.replicas)
            services[svc.name] = svc.with_replicas(replicas)
        return _copy_state(state, services=services)
    if action == "rollback_deployment":
        svc = _service(state, str(p["service"]))
        target = str(p.get("to", "previous"))
        services = dict(state.services)
        deployments = dict(state.deployments)
        services[svc.name] = replace(svc, deployment=target)
        dep = deployments.get(svc.name, Deployment(service=svc.name, current=svc.deployment, previous=None))
        deployments[svc.name] = replace(dep, current=target)
        return _copy_state(state, services=services, deployments=deployments)
    if action == "failover_database":
        db = _database(state, str(p["database"]))
        target = str(p["target_region"])
        databases = dict(state.databases)
        databases[db.name] = replace(db, primary_region=target)
        return _copy_state(state, databases=databases)
    if action == "confirm_quorum":
        db = _database(state, str(p["database"]))
        databases = dict(state.databases)
        databases[db.name] = replace(db, quorum_confirmed=True)
        return _copy_state(state, databases=databases)
    if action == "suppress_alert":
        alert = _alert(state, str(p["alert"]))
        expires = int(p["expires_after_minutes"])
        alerts = dict(state.alerts)
        alerts[alert.name] = replace(alert, suppressed_until_minute=state.clock_minute + expires)
        return _copy_state(state, alerts=alerts)
    if action == "scale_service":
        svc = _service(state, str(p["service"]))
        target = int(p["replicas"])
        replicas = list(svc.replicas)
        if target < len(replicas):
            replicas = replicas[:target]
        else:
            region = str(p.get("region", replicas[0].region if replicas else next(iter(state.regions), "default")))
            for i in range(len(replicas), target):
                replicas.append(Replica(id=f"{svc.name}-{i}", region=region, healthy=True, drained=False))
        return _with_service(state, svc.with_replicas(tuple(replicas)))
    if action == "toggle_flag":
        name = str(p["flag"])
        enabled = bool(p["enabled"])
        flags = dict(state.flags)
        flags[name] = FeatureFlag(name=name, enabled=enabled)
        return _copy_state(state, flags=flags)
    if action == "run_migration":
        db = _database(state, str(p["database"]))
        databases = dict(state.databases)
        databases[db.name] = replace(db, migration_in_progress=bool(p.get("in_progress", True)), migration_compatible=bool(p.get("compatible", db.migration_compatible)))
        return _copy_state(state, databases=databases)
    if action == "finish_migration":
        db = _database(state, str(p["database"]))
        databases = dict(state.databases)
        databases[db.name] = replace(db, migration_in_progress=False)
        return _copy_state(state, databases=databases)
    if action == "pause_queue":
        q = _queue(state, str(p["queue"]))
        queues = dict(state.queues)
        queues[q.name] = replace(q, paused=True)
        return _copy_state(state, queues=queues)
    if action == "resume_queue":
        q = _queue(state, str(p["queue"]))
        queues = dict(state.queues)
        queues[q.name] = replace(q, paused=False)
        return _copy_state(state, queues=queues)
    if action == "wait":
        minutes = int(p["minutes"])
        if minutes < 0:
            raise ActionError("wait minutes must be non-negative")
        return _copy_state(state, clock_minute=state.clock_minute + minutes)
    if action == "mark_region_health":
        name = str(p["region"])
        if name not in state.regions:
            raise ActionError(f"unknown region {name!r}")
        regions = dict(state.regions)
        regions[name] = replace(regions[name], healthy=bool(p["healthy"]))
        return _copy_state(state, regions=regions)
    if action == "shift_traffic":
        route = _route(state, str(p["route"]))
        region = str(p["region"])
        percent = int(p["percent"])
        if region not in state.regions:
            raise ActionError(f"unknown region {region!r}")
        weights = dict(route.weights)
        weights.setdefault(region, 0)
        if len(weights) == 2:
            peer = next(other for other in weights if other != region)
            weights[peer] = 100 - percent
        weights[region] = percent
        routes = dict(state.traffic_routes)
        routes[route.name] = replace(route, weights=weights)
        return _copy_state(state, traffic_routes=routes)
    if action == "failover_traffic":
        route = _route(state, str(p["route"]))
        target = str(p["target_region"])
        if target not in state.regions:
            raise ActionError(f"unknown region {target!r}")
        weights = {region: 0 for region in route.weights}
        weights[target] = 100
        routes = dict(state.traffic_routes)
        routes[route.name] = replace(route, weights=weights)
        return _copy_state(state, traffic_routes=routes)
    if action == "drain_load_balancer":
        route = _route(state, str(p["route"]))
        region = str(p["region"])
        if region not in state.regions:
            raise ActionError(f"unknown region {region!r}")
        routes = dict(state.traffic_routes)
        routes[route.name] = replace(route, drained_regions=route.drained_regions | {region})
        return _copy_state(state, traffic_routes=routes)
    if action == "restore_load_balancer":
        route = _route(state, str(p["route"]))
        region = str(p["region"])
        if region not in state.regions:
            raise ActionError(f"unknown region {region!r}")
        routes = dict(state.traffic_routes)
        routes[route.name] = replace(route, drained_regions=route.drained_regions - {region})
        return _copy_state(state, traffic_routes=routes)
    raise ActionError(f"unsupported action {action!r}")


def condition_holds(state: SystemState, condition: dict[str, Any]) -> bool:
    kind = condition.get("kind")
    if kind == "service_available_at_least":
        return _service(state, str(condition["service"])).available_count() >= int(condition["count"])
    if kind == "database_quorum_confirmed":
        return _database(state, str(condition["database"])).quorum_confirmed
    if kind == "database_primary_region":
        return _database(state, str(condition["database"])).primary_region == str(condition["region"])
    if kind == "region_healthy":
        return bool(state.regions[str(condition["region"])].healthy)
    if kind == "flag_enabled":
        return state.flags[str(condition["flag"])].enabled is bool(condition["enabled"])
    if kind == "alert_active":
        return _alert(state, str(condition["alert"])).active is bool(condition["active"])
    if kind == "alert_suppressed_for_at_most":
        alert = _alert(state, str(condition["alert"]))
        until = alert.suppressed_until_minute
        return until is not None and until - state.clock_minute <= int(condition["minutes"])
    if kind == "queue_depth_at_most":
        return _queue(state, str(condition["queue"])).depth <= int(condition["depth"])
    if kind == "queue_has_consumers":
        return _queue(state, str(condition["queue"])).consumers >= int(condition["count"])
    if kind == "queue_resumed":
        return not _queue(state, str(condition["queue"])).paused
    if kind == "service_deployment_is":
        return _service(state, str(condition["service"])).deployment == str(condition["deployment"])
    if kind == "replica_not_drained":
        svc = _service(state, str(condition["service"]))
        return any(r.id == str(condition["replica"]) and not r.drained for r in svc.replicas)
    if kind == "traffic_weight_is":
        route = _route(state, str(condition["route"]))
        return route.weights.get(str(condition["region"]), 0) == int(condition["percent"])
    if kind == "traffic_weight_at_most":
        route = _route(state, str(condition["route"]))
        return route.weights.get(str(condition["region"]), 0) <= int(condition["percent"])
    if kind == "traffic_weight_at_least":
        route = _route(state, str(condition["route"]))
        return route.weights.get(str(condition["region"]), 0) >= int(condition["percent"])
    if kind == "load_balancer_active":
        route = _route(state, str(condition["route"]))
        return str(condition["region"]) not in route.drained_regions
    raise ActionError(f"unsupported condition kind {kind!r}")
