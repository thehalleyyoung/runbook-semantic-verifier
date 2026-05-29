from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .actions import ACTION_SCHEMAS, CONDITION_SCHEMAS
from .model import Alert, Database, Deployment, FeatureFlag, Queue, Region, Replica, Runbook, Service, Step, SystemState


class RunbookParseError(ValueError):
    pass


def load_document(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix == ".json":
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RunbookParseError(f"invalid JSON in {p}: {exc}") from exc
        if isinstance(doc, dict):
            doc.setdefault("__source_lines", _json_step_source_lines(text, 1))
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise RunbookParseError("YAML input requires optional dependency PyYAML; use JSON or install formal-runbook-verification[yaml]") from exc
        try:
            doc = yaml.safe_load(text)
        except Exception as exc:  # PyYAML exposes several parser exception classes.
            raise RunbookParseError(f"invalid YAML in {p}: {exc}") from exc
    else:
        if suffix == ".md":
            doc = _load_markdown_runbook(text, p)
        else:
            raise RunbookParseError(f"unsupported runbook extension {p.suffix!r}; use .json, .yaml, .yml, or .md")
    if not isinstance(doc, dict):
        raise RunbookParseError("runbook document must be an object")
    return doc


def _load_markdown_runbook(text: str, path: Path) -> dict[str, Any]:
    matches = list(re.finditer(r"```(?:runbook-json|json)\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE))
    blocks = [match.group(1) for match in matches]
    if not blocks:
        raise RunbookParseError(f"Markdown runbook {path} must contain a fenced ```runbook-json block")
    if len(blocks) > 1:
        raise RunbookParseError(f"Markdown runbook {path} contains multiple runbook-json blocks; keep one executable model per file")
    try:
        doc = json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        raise RunbookParseError(f"invalid runbook-json block in {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise RunbookParseError(f"runbook-json block in {path} must be an object")
    block_start_line = text[:matches[0].start(1)].count("\n") + 1
    doc.setdefault("__source_lines", _json_step_source_lines(blocks[0], block_start_line))
    return doc


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RunbookParseError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise RunbookParseError(f"{name} must be a list")
    return value


def _require_key(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise RunbookParseError(f"{where} is missing required field {key!r}")
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
                raise RunbookParseError(f"service {name}.replicas[{idx}] references unknown region {region!r}")
            replicas.append(Replica(id=str(rep.get("id", f"{name}-{idx}")), region=region, healthy=bool(rep.get("healthy", True)), drained=bool(rep.get("drained", False))))
        services[name] = Service(name=name, replicas=tuple(replicas), min_available=int(cfg.get("min_available", 1)), deployment=str(cfg.get("deployment", "current")))
        if services[name].min_available < 0:
            raise RunbookParseError(f"service {name}.min_available must be non-negative")

    databases = {}
    for name, cfg_any in _require_mapping(raw.get("databases", {}), "system.databases").items():
        name = str(name)
        cfg = _require_mapping(cfg_any, f"system.databases.{name}")
        primary_region = str(_require_key(cfg, "primary_region", f"database {name}"))
        if regions and primary_region not in regions:
            raise RunbookParseError(f"database {name}.primary_region references unknown region {primary_region!r}")
        healthy_regions = frozenset(str(r) for r in _require_list(cfg.get("healthy_regions", []), f"database {name}.healthy_regions"))
        unknown_healthy = sorted(r for r in healthy_regions if regions and r not in regions)
        if unknown_healthy:
            raise RunbookParseError(f"database {name}.healthy_regions references unknown region(s): {', '.join(unknown_healthy)}")
        databases[name] = Database(
            name=name,
            primary_region=primary_region,
            healthy_regions=healthy_regions,
            quorum_confirmed=bool(cfg.get("quorum_confirmed", False)),
            migration_in_progress=bool(cfg.get("migration_in_progress", False)),
            migration_compatible=bool(cfg.get("migration_compatible", True)),
        )

    queues = {name: Queue(name=name, depth=int(_require_mapping(cfg, f"queue {name}").get("depth", 0)), consumers=int(_require_mapping(cfg, f"queue {name}").get("consumers", 1)), paused=bool(_require_mapping(cfg, f"queue {name}").get("paused", False))) for name, cfg in _require_mapping(raw.get("queues", {}), "system.queues").items()}
    alerts = {name: Alert(name=name, active=bool(_require_mapping(cfg, f"alert {name}").get("active", True)), suppressed_until_minute=_require_mapping(cfg, f"alert {name}").get("suppressed_until_minute")) for name, cfg in _require_mapping(raw.get("alerts", {}), "system.alerts").items()}
    flags = {name: FeatureFlag(name=name, enabled=bool(_require_mapping(cfg, f"flag {name}").get("enabled", False))) for name, cfg in _require_mapping(raw.get("feature_flags", {}), "system.feature_flags").items()}
    deployments = {name: Deployment(service=str(_require_mapping(cfg, f"deployment {name}").get("service", name)), current=str(_require_mapping(cfg, f"deployment {name}").get("current", "current")), previous=_require_mapping(cfg, f"deployment {name}").get("previous")) for name, cfg in _require_mapping(raw.get("deployments", {}), "system.deployments").items()}
    for name, deployment in deployments.items():
        if deployment.service not in services:
            raise RunbookParseError(f"deployment {name} references unknown service {deployment.service!r}")
    return SystemState(regions=regions, services=services, databases=databases, queues=queues, alerts=alerts, flags=flags, deployments=deployments, clock_minute=int(raw.get("clock_minute", 0)))


def parse_runbook(doc: dict[str, Any], source_path: str | Path | None = None) -> Runbook:
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
            raise RunbookParseError(f"duplicate step id {sid!r}")
        seen.add(sid)
        action = str(raw_step.get("action", ""))
        if not action:
            raise RunbookParseError(f"step {sid!r} is missing action")
        params = dict(_require_mapping(raw_step.get("params", {}), f"step {sid}.params"))
        _validate_action_schema(action, params, f"step {sid}")
        requires = tuple(_condition(c, f"step {sid}.requires[{i}]") for i, c in enumerate(_require_list(raw_step.get("requires", []), f"step {sid}.requires")))
        effects = tuple(_condition(c, f"step {sid}.effects[{i}]") for i, c in enumerate(_require_list(raw_step.get("effects", []), f"step {sid}.effects")))
        steps.append(Step(
            id=sid,
            action=action,
            params=params,
            after=tuple(str(x) for x in raw_step.get("after", [])),
            requires=requires,
            effects=effects,
            source_path=str(source_path) if source_path is not None else None,
            source_line=int(source_lines[sid]) if sid in source_lines else None,
        ))
    missing = sorted(dep for step in steps for dep in step.after if dep not in seen)
    if missing:
        raise RunbookParseError(f"unknown dependency step id(s): {', '.join(missing)}")
    _validate_step_references(system, steps)
    return Runbook(
        name=str(doc.get("name", "unnamed runbook")),
        description=str(doc.get("description", "")),
        state=system,
        steps=tuple(steps),
        max_depth=int(doc.get("max_depth", len(steps))),
        allow_reordering=bool(doc.get("allow_reordering", True)),
        safety=dict(_require_mapping(doc.get("safety", {}), "safety")),
    )


def load_runbook(path: str | Path) -> Runbook:
    return parse_runbook(load_document(path), source_path=path)


def _condition(raw: Any, where: str) -> dict[str, Any]:
    condition = dict(_require_mapping(raw, where))
    kind = str(condition.get("kind", ""))
    if not kind:
        raise RunbookParseError(f"{where} is missing condition kind")
    schema = CONDITION_SCHEMAS.get(kind)
    if schema is None:
        raise RunbookParseError(f"{where} has unsupported condition kind {kind!r}")
    _validate_keys(condition, schema["required"] | {"kind"}, schema["optional"], where)
    return condition


def _validate_action_schema(action: str, params: dict[str, Any], where: str) -> None:
    schema = ACTION_SCHEMAS.get(action)
    if schema is None:
        raise RunbookParseError(f"{where} has unsupported action {action!r}")
    _validate_keys(params, schema["required"], schema["optional"], f"{where}.params")


def _validate_keys(mapping: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    missing = sorted(key for key in required if key not in mapping)
    if missing:
        raise RunbookParseError(f"{where} missing required field(s): {', '.join(missing)}")
    unknown = sorted(set(mapping) - required - optional)
    if unknown:
        raise RunbookParseError(f"{where} has unknown field(s): {', '.join(unknown)}")


def _validate_step_references(state: SystemState, steps: list[Step]) -> None:
    for step in steps:
        def require_entity(kind: str, name: str, values: dict[str, Any]) -> None:
            if name not in values:
                raise RunbookParseError(f"step {step.id} references unknown {kind} {name!r}")

        params = step.params
        if "service" in params:
            require_entity("service", str(params["service"]), state.services)
        if "database" in params:
            require_entity("database", str(params["database"]), state.databases)
        if "alert" in params:
            require_entity("alert", str(params["alert"]), state.alerts)
        if "queue" in params:
            require_entity("queue", str(params["queue"]), state.queues)
        if "region" in params:
            require_entity("region", str(params["region"]), state.regions)
        if "target_region" in params:
            require_entity("region", str(params["target_region"]), state.regions)
        if "replica" in params and "service" in params:
            svc = state.services[str(params["service"])]
            if str(params["replica"]) not in {replica.id for replica in svc.replicas}:
                raise RunbookParseError(f"step {step.id} references unknown replica {params['replica']!r} for service {svc.name!r}")
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
    ):
        if key in condition and str(condition[key]) not in collection:
            raise RunbookParseError(f"step {step_id} condition references unknown {label} {condition[key]!r}")
    if "replica" in condition and "service" in condition:
        svc = state.services[str(condition["service"])]
        if str(condition["replica"]) not in {replica.id for replica in svc.replicas}:
            raise RunbookParseError(f"step {step_id} condition references unknown replica {condition['replica']!r} for service {svc.name!r}")


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
