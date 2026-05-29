from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .descriptors import ACTION_DESCRIPTORS, CONDITION_DESCRIPTORS, OperationDescriptor
from .model import Alert, Database, Deployment, FeatureFlag, Queue, Region, Replica, Runbook, Service, Step, SystemState, TrafficRoute


@dataclass
class RunbookDiagnostic:
    message: str
    path: str | None = None
    line: int | None = None
    field: str | None = None
    severity: str = "error"
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunbookParseError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        line: int | None = None,
        field: str | None = None,
        severity: str = "error",
        remediation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic = RunbookDiagnostic(
            message=message,
            path=path,
            line=line,
            field=_normalize_field(field),
            severity=severity,
            remediation=remediation or _remediation_for(message),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.diagnostic.to_dict()

    def with_context(self, *, path: str | None = None, line: int | None = None, field: str | None = None) -> "RunbookParseError":
        if path is not None and self.diagnostic.path is None:
            self.diagnostic.path = path
        if line is not None and self.diagnostic.line is None:
            self.diagnostic.line = line
        if field is not None and self.diagnostic.field is None:
            self.diagnostic.field = _normalize_field(field)
        return self


def _normalize_field(field: str | None) -> str | None:
    if field is None:
        return None
    normalized = field.replace("service ", "system.services.")
    normalized = normalized.replace("database ", "system.databases.")
    normalized = normalized.replace("queue ", "system.queues.")
    normalized = normalized.replace("alert ", "system.alerts.")
    normalized = normalized.replace("flag ", "system.feature_flags.")
    normalized = normalized.replace("traffic route ", "system.traffic_routes.")
    normalized = normalized.replace("step ", "steps.")
    return normalized


def _remediation_for(message: str) -> str:
    lower = message.lower()
    if "missing required field" in lower or "is missing" in lower:
        return "Add the required DSL field at the reported location."
    if "unknown field" in lower:
        return "Remove the unsupported field or rename it to a field allowed by the DSL schema."
    if "unsupported action" in lower or "unsupported condition" in lower:
        return "Use one of the actions or condition kinds listed by `frv schema`."
    if "unknown" in lower and "references" in lower:
        return "Declare the referenced entity in system before using it in steps, preconditions, or effects."
    if "non-negative integer" in lower or "positive integer" in lower:
        return "Replace the value with an integer inside the documented bound."
    if "dependency cycle" in lower:
        return "Break the step `after` cycle so dependencies form an acyclic graph."
    if "invalid json" in lower:
        return "Fix the JSON syntax and rerun `frv validate`."
    return "Fix the runbook DSL at the reported location and rerun `frv validate`."


def load_document(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix == ".json":
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RunbookParseError(f"invalid JSON in {p}: {exc}", path=str(p), line=exc.lineno, field=None) from exc
        if isinstance(doc, dict):
            doc.setdefault("__source_lines", _json_step_source_lines(text, 1))
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise RunbookParseError("YAML input requires optional dependency PyYAML; use JSON or install formal-runbook-verification[yaml]", path=str(p)) from exc
        try:
            doc = yaml.safe_load(text)
        except Exception as exc:  # PyYAML exposes several parser exception classes.
            raise RunbookParseError(f"invalid YAML in {p}: {exc}", path=str(p)) from exc
    else:
        if suffix == ".md":
            doc = _load_markdown_runbook(text, p)
        else:
            raise RunbookParseError(f"unsupported runbook extension {p.suffix!r}; use .json, .yaml, .yml, or .md", path=str(p))
    if not isinstance(doc, dict):
        raise RunbookParseError("runbook document must be an object", path=str(p))
    return doc


def _load_markdown_runbook(text: str, path: Path) -> dict[str, Any]:
    matches = list(re.finditer(r"```(?:runbook-json|json)\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE))
    blocks = [match.group(1) for match in matches]
    if not blocks:
        raise RunbookParseError(f"Markdown runbook {path} must contain a fenced ```runbook-json block", path=str(path))
    if len(blocks) > 1:
        raise RunbookParseError(f"Markdown runbook {path} contains multiple runbook-json blocks; keep one executable model per file", path=str(path))
    block_start_line = text[:matches[0].start(1)].count("\n") + 1
    try:
        doc = json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        raise RunbookParseError(f"invalid runbook-json block in {path}: {exc}", path=str(path), line=block_start_line + exc.lineno - 1) from exc
    if not isinstance(doc, dict):
        raise RunbookParseError(f"runbook-json block in {path} must be an object", path=str(path), line=block_start_line)
    doc.setdefault("__source_lines", _json_step_source_lines(blocks[0], block_start_line))
    return doc


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RunbookParseError(f"{name} must be an object", field=name)
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise RunbookParseError(f"{name} must be a list", field=name)
    return value


def _require_key(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise RunbookParseError(f"{where} is missing required field {key!r}", field=f"{where}.{key}")
    return mapping[key]


def parse_state(raw: dict[str, Any]) -> SystemState:
    regions_raw = _require_mapping(raw.get("regions", {}), "system.regions")
    regions = {str(name): Region(name=str(name), healthy=bool(cfg.get("healthy", True))) for name, cfg in ((n, _require_mapping(c, f"system.regions.{n}")) for n, c in regions_raw.items())}

    services = {}
    for name, cfg_any in _require_mapping(raw.get("services", {}), "system.services").items():
        name = str(name)
        cfg = _require_mapping(cfg_any, f"system.services.{name}")
        replicas = []
        for idx, rep_any in enumerate(_require_list(cfg.get("replicas", []), f"service {name}.replicas")):
            rep = _require_mapping(rep_any, f"service {name}.replicas[{idx}]")
            region = str(_require_key(rep, "region", f"service {name}.replicas[{idx}]"))
            if regions and region not in regions:
                raise RunbookParseError(f"service {name}.replicas[{idx}] references unknown region {region!r}", field=f"system.services.{name}.replicas[{idx}].region")
            replicas.append(Replica(id=str(rep.get("id", f"{name}-{idx}")), region=region, healthy=bool(rep.get("healthy", True)), drained=bool(rep.get("drained", False))))
        replica_ids = [replica.id for replica in replicas]
        duplicate_replica_ids = sorted({rid for rid in replica_ids if replica_ids.count(rid) > 1})
        if duplicate_replica_ids:
            raise RunbookParseError(f"service {name}.replicas contains duplicate replica id(s): {', '.join(duplicate_replica_ids)}", field=f"system.services.{name}.replicas")
        min_available = _non_negative_int(cfg.get("min_available", 1), f"service {name}.min_available")
        if min_available > len(replicas) and not bool(cfg.get("allow_unachievable_min_available", False)):
            raise RunbookParseError(
                f"service {name}.min_available={min_available} is not achievable with {len(replicas)} declared replica(s); "
                "add replicas or set allow_unachievable_min_available=true with a documented waiver",
                field=f"system.services.{name}.min_available",
                remediation="Add enough replicas to meet min_available or set allow_unachievable_min_available=true with an explicit documented waiver.",
            )
        services[name] = Service(name=name, replicas=tuple(replicas), min_available=min_available, deployment=str(cfg.get("deployment", "current")))

    databases = {}
    for name, cfg_any in _require_mapping(raw.get("databases", {}), "system.databases").items():
        name = str(name)
        cfg = _require_mapping(cfg_any, f"system.databases.{name}")
        primary_region = str(_require_key(cfg, "primary_region", f"database {name}"))
        if regions and primary_region not in regions:
            raise RunbookParseError(f"database {name}.primary_region references unknown region {primary_region!r}", field=f"system.databases.{name}.primary_region")
        healthy_regions = frozenset(str(r) for r in _require_list(cfg.get("healthy_regions", []), f"database {name}.healthy_regions"))
        unknown_healthy = sorted(r for r in healthy_regions if regions and r not in regions)
        if unknown_healthy:
            raise RunbookParseError(f"database {name}.healthy_regions references unknown region(s): {', '.join(unknown_healthy)}", field=f"system.databases.{name}.healthy_regions")
        databases[name] = Database(
            name=name,
            primary_region=primary_region,
            healthy_regions=healthy_regions,
            quorum_confirmed=bool(cfg.get("quorum_confirmed", False)),
            migration_in_progress=bool(cfg.get("migration_in_progress", False)),
            migration_compatible=bool(cfg.get("migration_compatible", True)),
        )

    queues = {name: Queue(name=name, depth=_non_negative_int(_require_mapping(cfg, f"queue {name}").get("depth", 0), f"queue {name}.depth"), consumers=_non_negative_int(_require_mapping(cfg, f"queue {name}").get("consumers", 1), f"queue {name}.consumers"), paused=bool(_require_mapping(cfg, f"queue {name}").get("paused", False))) for name, cfg in _require_mapping(raw.get("queues", {}), "system.queues").items()}
    alerts = {name: Alert(name=name, active=bool(_require_mapping(cfg, f"alert {name}").get("active", True)), suppressed_until_minute=_optional_non_negative_int(_require_mapping(cfg, f"alert {name}").get("suppressed_until_minute"), f"alert {name}.suppressed_until_minute")) for name, cfg in _require_mapping(raw.get("alerts", {}), "system.alerts").items()}
    flags = {name: FeatureFlag(name=name, enabled=bool(_require_mapping(cfg, f"flag {name}").get("enabled", False))) for name, cfg in _require_mapping(raw.get("feature_flags", {}), "system.feature_flags").items()}
    deployments = {name: Deployment(service=str(_require_mapping(cfg, f"deployment {name}").get("service", name)), current=str(_require_mapping(cfg, f"deployment {name}").get("current", "current")), previous=_require_mapping(cfg, f"deployment {name}").get("previous")) for name, cfg in _require_mapping(raw.get("deployments", {}), "system.deployments").items()}
    for name, deployment in deployments.items():
        if deployment.service not in services:
            raise RunbookParseError(f"deployment {name} references unknown service {deployment.service!r}", field=f"system.deployments.{name}.service")
        service = services[deployment.service]
        if deployment.current != service.deployment:
            raise RunbookParseError(
                f"deployment {name}.current={deployment.current!r} does not match "
                f"service {deployment.service}.deployment={service.deployment!r}",
                field=f"system.deployments.{name}.current",
                remediation="Keep deployment.current synchronized with the referenced service.deployment value.",
            )
    traffic_routes: dict[str, TrafficRoute] = {}
    for name, cfg_any in _require_mapping(raw.get("traffic_routes", {}), "system.traffic_routes").items():
        name = str(name)
        cfg = _require_mapping(cfg_any, f"system.traffic_routes.{name}")
        service = str(_require_key(cfg, "service", f"traffic route {name}"))
        if service not in services:
            raise RunbookParseError(f"traffic route {name}.service references unknown service {service!r}", field=f"system.traffic_routes.{name}.service")
        weights_raw = _require_mapping(_require_key(cfg, "weights", f"traffic route {name}"), f"traffic route {name}.weights")
        weights: dict[str, int] = {}
        for region, value in weights_raw.items():
            region = str(region)
            if regions and region not in regions:
                raise RunbookParseError(f"traffic route {name}.weights references unknown region {region!r}", field=f"system.traffic_routes.{name}.weights.{region}")
            weights[region] = _bounded_percent(value, f"traffic route {name}.weights.{region}")
        drained_regions = frozenset(str(region) for region in _require_list(cfg.get("drained_regions", []), f"traffic route {name}.drained_regions"))
        unknown_drained = sorted(region for region in drained_regions if regions and region not in regions)
        if unknown_drained:
            raise RunbookParseError(f"traffic route {name}.drained_regions references unknown region(s): {', '.join(unknown_drained)}", field=f"system.traffic_routes.{name}.drained_regions")
        traffic_routes[name] = TrafficRoute(name=name, service=service, weights=weights, drained_regions=drained_regions)
    return SystemState(regions=regions, services=services, databases=databases, queues=queues, alerts=alerts, flags=flags, deployments=deployments, traffic_routes=traffic_routes, clock_minute=_non_negative_int(raw.get("clock_minute", 0), "system.clock_minute"))


def parse_runbook(doc: dict[str, Any], source_path: str | Path | None = None) -> Runbook:
    try:
        return _parse_runbook(doc, source_path)
    except RunbookParseError as exc:
        exc.with_context(path=str(source_path) if source_path is not None else None)
        raise


def _parse_runbook(doc: dict[str, Any], source_path: str | Path | None = None) -> Runbook:
    system = parse_state(_require_mapping(doc.get("system", {}), "system"))
    source_lines = doc.get("__source_lines", {})
    if not isinstance(source_lines, dict):
        source_lines = {}
    steps = []
    seen: set[str] = set()
    for idx, raw_step_any in enumerate(_require_list(doc.get("steps", []), "steps")):
        raw_step = _require_mapping(raw_step_any, f"steps[{idx}]")
        sid = str(raw_step.get("id", f"step-{idx}"))
        if sid in seen:
            raise RunbookParseError(f"duplicate step id {sid!r}", field=f"steps[{idx}].id")
        seen.add(sid)
        step_line = int(source_lines[sid]) if sid in source_lines else None
        try:
            action = str(raw_step.get("action", ""))
            if not action:
                raise RunbookParseError(f"step {sid!r} is missing action", field=f"steps[{idx}].action")
            params = dict(_require_mapping(raw_step.get("params", {}), f"step {sid}.params"))
            _validate_action_schema(action, params, f"step {sid}")
            requires = tuple(_condition(c, f"step {sid}.requires[{i}]") for i, c in enumerate(_require_list(raw_step.get("requires", []), f"step {sid}.requires")))
            effects = tuple(_condition(c, f"step {sid}.effects[{i}]") for i, c in enumerate(_require_list(raw_step.get("effects", []), f"step {sid}.effects")))
        except RunbookParseError as exc:
            exc.with_context(line=step_line, field=f"steps[{idx}]")
            raise
        steps.append(Step(
            id=sid,
            action=action,
            params=params,
            after=tuple(str(x) for x in raw_step.get("after", [])),
            requires=requires,
            effects=effects,
            source_path=str(source_path) if source_path is not None else None,
            source_line=step_line,
        ))
    missing = sorted(dep for step in steps for dep in step.after if dep not in seen)
    if missing:
        raise RunbookParseError(f"unknown dependency step id(s): {', '.join(missing)}", field="steps.after")
    _validate_dependency_graph(steps)
    _validate_step_references(system, steps)
    _validate_generated_scale_replicas(system, steps)
    max_depth = _non_negative_int(doc.get("max_depth", len(steps)), "max_depth")
    safety = dict(_require_mapping(doc.get("safety", {}), "safety"))
    if "max_alert_suppression_minutes" in safety:
        safety["max_alert_suppression_minutes"] = _positive_int(safety["max_alert_suppression_minutes"], "safety.max_alert_suppression_minutes")
    return Runbook(
        name=str(doc.get("name", "unnamed runbook")),
        description=str(doc.get("description", "")),
        state=system,
        steps=tuple(steps),
        max_depth=max_depth,
        allow_reordering=bool(doc.get("allow_reordering", True)),
        safety=safety,
    )


def load_runbook(path: str | Path) -> Runbook:
    return parse_runbook(load_document(path), source_path=path)


def _condition(raw: Any, where: str) -> dict[str, Any]:
    condition = dict(_require_mapping(raw, where))
    kind = str(condition.get("kind", ""))
    if not kind:
        raise RunbookParseError(f"{where} is missing condition kind", field=f"{where}.kind")
    descriptor = CONDITION_DESCRIPTORS.get(kind)
    if descriptor is None:
        raise RunbookParseError(f"{where} has unsupported condition kind {kind!r}", field=f"{where}.kind")
    _validate_payload(descriptor, condition, where, extra_required={"kind"})
    return condition


def _validate_action_schema(action: str, params: dict[str, Any], where: str) -> None:
    descriptor = ACTION_DESCRIPTORS.get(action)
    if descriptor is None:
        raise RunbookParseError(f"{where} has unsupported action {action!r}", field=f"{where}.action")
    _validate_payload(descriptor, params, f"{where}.params")


def _validate_keys(mapping: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    missing = sorted(key for key in required if key not in mapping)
    if missing:
        raise RunbookParseError(f"{where} missing required field(s): {', '.join(missing)}", field=f"{where}.{missing[0]}")
    unknown = sorted(set(mapping) - required - optional)
    if unknown:
        raise RunbookParseError(f"{where} has unknown field(s): {', '.join(unknown)}", field=f"{where}.{unknown[0]}")


def _validate_payload(descriptor: OperationDescriptor, mapping: dict[str, Any], where: str, extra_required: set[str] | None = None) -> None:
    extra_required = extra_required or set()
    _validate_keys(mapping, descriptor.required | extra_required, descriptor.optional, where)
    for name, value in mapping.items():
        if name in extra_required:
            continue
        field = descriptor.field_map[name]
        error = field.validate(value)
        if error:
            raise RunbookParseError(f"{where}.{name} {error}", field=f"{where}.{name}")


def _validate_dependency_graph(steps: list[Step]) -> None:
    deps = {step.id: set(step.after) for step in steps}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str, path: list[str]) -> None:
        if step_id in visited:
            return
        if step_id in visiting:
            cycle = path[path.index(step_id):] + [step_id]
            raise RunbookParseError(f"dependency cycle detected: {' -> '.join(cycle)}", field="steps.after")
        visiting.add(step_id)
        for dep in deps[step_id]:
            visit(dep, path + [dep])
        visiting.remove(step_id)
        visited.add(step_id)

    for step in steps:
        visit(step.id, [step.id])


def _non_negative_int(value: Any, where: str) -> int:
    if type(value) is not int or value < 0:
        raise RunbookParseError(f"{where} must be a non-negative integer", field=where)
    return value


def _positive_int(value: Any, where: str) -> int:
    if type(value) is not int or value <= 0:
        raise RunbookParseError(f"{where} must be a positive integer", field=where)
    return value


def _bounded_percent(value: Any, where: str) -> int:
    value = _non_negative_int(value, where)
    if value > 100:
        raise RunbookParseError(f"{where} must be an integer less than or equal to 100", field=where)
    return value


def _optional_non_negative_int(value: Any, where: str) -> int | None:
    if value is None:
        return None
    return _non_negative_int(value, where)


def _validate_step_references(state: SystemState, steps: list[Step]) -> None:
    for step in steps:
        def require_entity(kind: str, name: str, values: dict[str, Any]) -> None:
            if name not in values:
                raise RunbookParseError(f"step {step.id} references unknown {kind} {name!r}", line=step.source_line, field=f"step {step.id}.params.{kind}")

        params = step.params
        if "service" in params:
            require_entity("service", str(params["service"]), state.services)
        if "database" in params:
            require_entity("database", str(params["database"]), state.databases)
        if "alert" in params:
            require_entity("alert", str(params["alert"]), state.alerts)
        if "queue" in params:
            require_entity("queue", str(params["queue"]), state.queues)
        if "route" in params:
            require_entity("traffic route", str(params["route"]), state.traffic_routes)
        if "region" in params:
            require_entity("region", str(params["region"]), state.regions)
        if "target_region" in params:
            require_entity("region", str(params["target_region"]), state.regions)
        if "replica" in params and "service" in params:
            svc = state.services[str(params["service"])]
            if str(params["replica"]) not in {replica.id for replica in svc.replicas}:
                raise RunbookParseError(f"step {step.id} references unknown replica {params['replica']!r} for service {svc.name!r}", line=step.source_line, field=f"step {step.id}.params.replica")
        if "services" in params:
            for svc_name in _require_list(params["services"], f"step {step.id}.params.services"):
                require_entity("service", str(svc_name), state.services)
        for condition in (*step.requires, *step.effects):
            _validate_condition_references(state, step.id, condition)


def _validate_condition_references(state: SystemState, step_id: str, condition: dict[str, Any]) -> None:
    for key, collection, label in (
        ("service", state.services, "service"),
        ("database", state.databases, "database"),
        ("alert", state.alerts, "alert"),
        ("queue", state.queues, "queue"),
        ("region", state.regions, "region"),
        ("flag", state.flags, "feature flag"),
        ("route", state.traffic_routes, "traffic route"),
    ):
        if key in condition and str(condition[key]) not in collection:
            raise RunbookParseError(f"step {step_id} condition references unknown {label} {condition[key]!r}", field=f"step {step_id}.condition.{key}")
    if "replica" in condition and "service" in condition:
        svc = state.services[str(condition["service"])]
        if str(condition["replica"]) not in {replica.id for replica in svc.replicas}:
            raise RunbookParseError(f"step {step_id} condition references unknown replica {condition['replica']!r} for service {svc.name!r}", field=f"step {step_id}.condition.replica")


def _validate_generated_scale_replicas(state: SystemState, steps: list[Step]) -> None:
    generated_by: dict[tuple[str, str], str] = {}
    for step in steps:
        if step.action != "scale_service":
            continue
        service_name = str(step.params["service"])
        service = state.services[service_name]
        declared_ids = {replica.id for replica in service.replicas}
        target = int(step.params["replicas"])
        for index in range(len(service.replicas), target):
            replica_id = f"{service.name}-{index}"
            if replica_id in declared_ids:
                raise RunbookParseError(
                    f"step {step.id} would generate duplicate replica id {replica_id!r} for service {service.name!r}",
                    line=step.source_line,
                    field=f"step {step.id}.params.replicas",
                )
            key = (service.name, replica_id)
            previous_step = generated_by.get(key)
            if previous_step is not None:
                raise RunbookParseError(
                    f"steps {previous_step} and {step.id} would both generate replica id {replica_id!r} for service {service.name!r}",
                    line=step.source_line,
                    field=f"step {step.id}.params.replicas",
                )
            generated_by[key] = step.id


def _json_step_source_lines(text: str, base_line: int) -> dict[str, int]:
    lines: dict[str, int] = {}
    in_steps = False
    for offset, line in enumerate(text.splitlines(), start=base_line):
        if '"steps"' in line:
            in_steps = True
        if not in_steps:
            continue
        match = re.search(r'"id"\s*:\s*"([^"]+)"', line)
        if match:
            lines.setdefault(match.group(1), offset)
    return lines
