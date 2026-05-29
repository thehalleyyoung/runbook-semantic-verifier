from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
        raise RunbookParseError(f"unsupported runbook extension {p.suffix!r}; use .json, .yaml, or .yml")
    if not isinstance(doc, dict):
        raise RunbookParseError("runbook document must be an object")
    return doc


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RunbookParseError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise RunbookParseError(f"{name} must be a list")
    return value


def parse_state(raw: dict[str, Any]) -> SystemState:
    regions_raw = _require_mapping(raw.get("regions", {}), "system.regions")
    regions = {name: Region(name=name, healthy=bool(cfg.get("healthy", True))) for name, cfg in ((n, _require_mapping(c, f"region {n}")) for n, c in regions_raw.items())}

    services = {}
    for name, cfg_any in _require_mapping(raw.get("services", {}), "system.services").items():
        cfg = _require_mapping(cfg_any, f"service {name}")
        replicas = []
        for idx, rep_any in enumerate(_require_list(cfg.get("replicas", []), f"service {name}.replicas")):
            rep = _require_mapping(rep_any, f"service {name}.replicas[{idx}]")
            replicas.append(Replica(id=str(rep.get("id", f"{name}-{idx}")), region=str(rep["region"]), healthy=bool(rep.get("healthy", True)), drained=bool(rep.get("drained", False))))
        services[name] = Service(name=name, replicas=tuple(replicas), min_available=int(cfg.get("min_available", 1)), deployment=str(cfg.get("deployment", "current")))

    databases = {}
    for name, cfg_any in _require_mapping(raw.get("databases", {}), "system.databases").items():
        cfg = _require_mapping(cfg_any, f"database {name}")
        databases[name] = Database(
            name=name,
            primary_region=str(cfg["primary_region"]),
            healthy_regions=frozenset(str(r) for r in _require_list(cfg.get("healthy_regions", []), f"database {name}.healthy_regions")),
            quorum_confirmed=bool(cfg.get("quorum_confirmed", False)),
            migration_in_progress=bool(cfg.get("migration_in_progress", False)),
            migration_compatible=bool(cfg.get("migration_compatible", True)),
        )

    queues = {name: Queue(name=name, depth=int(_require_mapping(cfg, f"queue {name}").get("depth", 0)), consumers=int(_require_mapping(cfg, f"queue {name}").get("consumers", 1)), paused=bool(_require_mapping(cfg, f"queue {name}").get("paused", False))) for name, cfg in _require_mapping(raw.get("queues", {}), "system.queues").items()}
    alerts = {name: Alert(name=name, active=bool(_require_mapping(cfg, f"alert {name}").get("active", True)), suppressed_until_minute=_require_mapping(cfg, f"alert {name}").get("suppressed_until_minute")) for name, cfg in _require_mapping(raw.get("alerts", {}), "system.alerts").items()}
    flags = {name: FeatureFlag(name=name, enabled=bool(_require_mapping(cfg, f"flag {name}").get("enabled", False))) for name, cfg in _require_mapping(raw.get("feature_flags", {}), "system.feature_flags").items()}
    deployments = {name: Deployment(service=str(_require_mapping(cfg, f"deployment {name}").get("service", name)), current=str(_require_mapping(cfg, f"deployment {name}").get("current", "current")), previous=_require_mapping(cfg, f"deployment {name}").get("previous")) for name, cfg in _require_mapping(raw.get("deployments", {}), "system.deployments").items()}
    return SystemState(regions=regions, services=services, databases=databases, queues=queues, alerts=alerts, flags=flags, deployments=deployments, clock_minute=int(raw.get("clock_minute", 0)))


def parse_runbook(doc: dict[str, Any]) -> Runbook:
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
        steps.append(Step(
            id=sid,
            action=action,
            params=dict(_require_mapping(raw_step.get("params", {}), f"step {sid}.params")),
            after=tuple(str(x) for x in raw_step.get("after", [])),
            requires=tuple(dict(x) for x in raw_step.get("requires", [])),
            effects=tuple(dict(x) for x in raw_step.get("effects", [])),
        ))
    missing = sorted(dep for step in steps for dep in step.after if dep not in seen)
    if missing:
        raise RunbookParseError(f"unknown dependency step id(s): {', '.join(missing)}")
    system = parse_state(_require_mapping(doc.get("system", {}), "system"))
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
    return parse_runbook(load_document(path))
