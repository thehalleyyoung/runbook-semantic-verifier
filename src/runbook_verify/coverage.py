from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .markdown_lint import MarkdownFinding, lint_markdown_file
from .model import Runbook, Step
from .parser import RunbookParseError, load_document, parse_runbook

RUNBOOK_SUFFIXES = {".json", ".yaml", ".yml", ".md"}


@dataclass(frozen=True)
class _LoadedRunbook:
    path: Path
    document: dict[str, Any]
    runbook: Runbook
    sections: dict[int, str]


class CoverageError(ValueError):
    pass


def build_coverage_report(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    if not root.exists():
        raise CoverageError(f"coverage path does not exist: {root}")

    loaded: list[_LoadedRunbook] = []
    parse_errors: list[dict[str, Any]] = []
    for file in _executable_runbook_files(root):
        try:
            doc = load_document(file)
            runbook = parse_runbook(doc, source_path=file)
        except RunbookParseError as exc:
            contextual = exc.with_context(path=str(file))
            parse_errors.append({
                "path": str(file),
                "line": contextual.diagnostic.line,
                "field": contextual.diagnostic.field,
                "message": str(contextual),
                "remediation": contextual.diagnostic.remediation,
            })
            continue
        loaded.append(_LoadedRunbook(file, doc, runbook, _markdown_sections(file)))

    if not loaded and not parse_errors:
        raise CoverageError(f"no executable runbooks found under {root}")

    prose_findings = [finding for file in _markdown_files(root) for finding in lint_markdown_file(file)]
    property_records = [_property_record(item, prop) for item in loaded for prop in _properties_for(item.runbook)]
    uncovered = _uncovered_records(loaded, property_records, prose_findings)
    summary = _summary(root, loaded, parse_errors, property_records, prose_findings, uncovered)
    return {
        "path": str(root),
        "summary": summary,
        "runbooks": [_runbook_record(item) for item in loaded],
        "properties": property_records,
        "unverified_prose_obligations": [_prose_record(finding) for finding in prose_findings],
        "uncovered_entities": uncovered,
        "parse_errors": parse_errors,
    }


def render_coverage_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_coverage_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# Property coverage report: {report['path']}",
        "",
        f"- Executable runbooks: {summary['runbooks']}",
        f"- Properties mapped: {summary['properties']}",
        f"- Services covered: {summary['covered_services']}/{summary['services']}",
        f"- Databases covered: {summary['covered_databases']}/{summary['databases']}",
        f"- Queues covered: {summary['covered_queues']}/{summary['queues']}",
        f"- Alerts covered: {summary['covered_alerts']}/{summary['alerts']}",
        f"- DNS records covered: {summary['covered_dns_records']}/{summary['dns_records']}",
        f"- Credentials covered: {summary['covered_credentials']}/{summary['credentials']} (credential state is not implemented in the current DSL)",
        f"- Regions covered: {summary['covered_regions']}/{summary['regions']}",
        f"- Owners: {_csv(summary['owners']) or 'none'}",
        f"- Unverified prose obligations: {summary['unverified_prose_obligations']}",
        f"- Coverage gaps: {summary['uncovered_entities']}",
        "",
        "## Invariant coverage",
        "",
    ]
    if report["properties"]:
        lines.extend(["| Property | Runbook | Owners | Services | Databases | Queues | Alerts | DNS records | Credentials | Regions | Steps/sections |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"])
        for item in report["properties"]:
            lines.append(
                "| `{property}` | `{path}` | {owners} | {services} | {databases} | {queues} | {alerts} | {dns_records} | {credentials} | {regions} | {steps} |".format(
                    property=item["property"],
                    path=item["path"],
                    owners=_csv(item["owners"]),
                    services=_csv(item["services"]),
                    databases=_csv(item["databases"]),
                    queues=_csv(item["queues"]),
                    alerts=_csv(item["alerts"]),
                    dns_records=_csv(item["dns_records"]),
                    credentials=_csv(item["credentials"]),
                    regions=_csv(item["regions"]),
                    steps=_step_summary(item["steps"]),
                )
            )
    else:
        lines.append("No properties were mapped.")
    lines.extend(["", "## Unverified prose obligations", ""])
    if report["unverified_prose_obligations"]:
        lines.extend(["| Rule | Severity | Obligation | Location | Section |", "| --- | --- | --- | --- | --- |"])
        for finding in report["unverified_prose_obligations"]:
            lines.append(f"| {finding['rule']} | {finding['severity']} | `{finding['semantic_obligation']}` | `{finding['path']}:{finding['line']}` | {finding['section'].replace('|', '\\|')} |")
    else:
        lines.append("None.")
    lines.extend(["", "## Coverage gaps", ""])
    if report["uncovered_entities"]:
        for item in report["uncovered_entities"]:
            lines.append(f"- `{item['kind']}` `{item['name']}` in `{item['path']}`: {item['message']}")
    else:
        lines.append("Every modeled service, database, queue, alert, DNS record, region, and prose obligation is linked to a current invariant template.")
    return "\n".join(lines) + "\n"


def _runbook_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() in RUNBOOK_SUFFIXES)


def _markdown_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*.md"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() == ".md")


def _executable_runbook_files(root: Path) -> list[Path]:
    return [path for path in _runbook_files(root) if path.suffix.lower() != ".md" or _has_embedded_runbook(path)]


def _has_embedded_runbook(path: Path) -> bool:
    text = path.read_text(encoding="utf-8").lower()
    return "```runbook-json" in text or "```json" in text


def _markdown_sections(path: Path) -> dict[int, str]:
    if path.suffix.lower() != ".md":
        return {}
    sections: dict[int, str] = {}
    current = path.name
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            current = match.group(2).strip()
        sections[line_no] = current
    return sections


def _section_for(item: _LoadedRunbook, line: int | None) -> str:
    if item.path.suffix.lower() != ".md":
        return "JSON/YAML document"
    if line is None:
        return item.path.name
    candidates = [candidate for candidate in item.sections if candidate <= line]
    if not candidates:
        return item.path.name
    return item.sections[max(candidates)]


def _properties_for(runbook: Runbook) -> list[str]:
    properties = {
        "service_min_available",
        "no_draining_all_replicas",
        "no_rollback_during_incompatible_migration",
        "no_failover_to_unhealthy_region",
        "quorum_before_data_loss_action",
        "bounded_alert_suppression",
        "no_queue_pause_without_drain_plan",
        "no_paused_queue_with_backlog",
        "no_replay_without_dedupe",
        "dead_letter_replay_has_messages",
        "dead_letter_drain_has_messages",
        "no_duplicate_processing_risk",
        "queue_backlog_requires_consumers",
        "no_rebalance_to_zero_consumers",
        "no_unstable_consumer_group_with_backlog",
        "traffic_weights_sum_to_100",
        "no_traffic_to_unhealthy_region",
        "no_traffic_to_drained_load_balancer",
        "no_draining_load_balancer_with_traffic",
        "traffic_requires_regional_capacity",
        "dns_target_region_healthy",
        "dns_health_check_converged_before_cutover",
        "dns_requires_regional_capacity",
        "dns_ttl_elapsed_before_finalize",
        "dns_ttl_elapsed_before_recursion",
        "dns_no_split_brain_during_ttl",
        "declared_precondition",
        "declared_effect",
    }
    if not runbook.state.traffic_routes and not any(step.action in {"shift_traffic", "failover_traffic", "drain_load_balancer", "restore_load_balancer"} for step in runbook.steps):
        properties -= {"traffic_weights_sum_to_100", "no_traffic_to_unhealthy_region", "no_traffic_to_drained_load_balancer", "no_draining_load_balancer_with_traffic", "traffic_requires_regional_capacity"}
    if not runbook.state.dns_records and not any("record" in step.params or step.action in {"update_dns_record", "mark_dns_health_check", "finalize_dns_record"} for step in runbook.steps):
        properties -= {"dns_target_region_healthy", "dns_health_check_converged_before_cutover", "dns_requires_regional_capacity", "dns_ttl_elapsed_before_finalize", "dns_ttl_elapsed_before_recursion", "dns_no_split_brain_during_ttl"}
    if not runbook.state.queues and not any("queue" in step.params for step in runbook.steps):
        properties -= {"no_queue_pause_without_drain_plan", "no_paused_queue_with_backlog", "no_replay_without_dedupe", "dead_letter_replay_has_messages", "dead_letter_drain_has_messages", "no_duplicate_processing_risk", "queue_backlog_requires_consumers", "no_rebalance_to_zero_consumers", "no_unstable_consumer_group_with_backlog"}
    if not runbook.state.alerts and not any("alert" in step.params for step in runbook.steps):
        properties -= {"bounded_alert_suppression"}
    if not runbook.state.databases and not any("database" in step.params for step in runbook.steps):
        properties -= {"no_rollback_during_incompatible_migration", "no_failover_to_unhealthy_region", "quorum_before_data_loss_action"}
    if not any(step.requires for step in runbook.steps):
        properties -= {"declared_precondition"}
    if not any(step.effects for step in runbook.steps):
        properties -= {"declared_effect"}
    return sorted(properties)


def _property_record(item: _LoadedRunbook, prop: str) -> dict[str, Any]:
    steps = _steps_for_property(item.runbook, prop)
    return {
        "path": str(item.path),
        "runbook": item.runbook.name,
        "property": prop,
        "owners": _owners(item.document),
        "services": sorted(_services_for_property(item.runbook, prop, steps)),
        "databases": sorted(_databases_for_property(item.runbook, prop, steps)),
        "queues": sorted(_queues_for_property(item.runbook, prop, steps)),
        "alerts": sorted(_alerts_for_property(item.runbook, prop, steps)),
        "dns_records": sorted(_dns_records_for_property(item.runbook, prop, steps)),
        "credentials": [],
        "regions": sorted(_regions_for_property(item.runbook, prop, steps)),
        "steps": [_step_record(item, step) for step in steps],
        "formal_obligation": _formal_obligation(prop),
    }


def _steps_for_property(runbook: Runbook, prop: str) -> list[Step]:
    if prop in {"service_min_available", "no_draining_all_replicas"}:
        return [step for step in runbook.steps if step.action in {"drain_replica", "drain_region", "restore_replica", "scale_service"} or "service" in step.params or "services" in step.params]
    if prop in {"no_rollback_during_incompatible_migration"}:
        return [step for step in runbook.steps if step.action in {"rollback_deployment", "run_migration", "finish_migration"} or "database" in step.params]
    if prop in {"no_failover_to_unhealthy_region", "quorum_before_data_loss_action"}:
        return [step for step in runbook.steps if step.action in {"failover_database", "confirm_quorum", "mark_region_health"} or "database" in step.params]
    if prop == "bounded_alert_suppression":
        return [step for step in runbook.steps if step.action == "suppress_alert" or "alert" in step.params]
    if prop in {"no_queue_pause_without_drain_plan", "no_paused_queue_with_backlog", "no_replay_without_dedupe", "dead_letter_replay_has_messages", "dead_letter_drain_has_messages", "no_duplicate_processing_risk", "queue_backlog_requires_consumers", "no_rebalance_to_zero_consumers", "no_unstable_consumer_group_with_backlog"}:
        return [step for step in runbook.steps if "queue" in step.params]
    if prop.startswith("traffic_") or prop in {"no_traffic_to_unhealthy_region", "no_traffic_to_drained_load_balancer", "no_draining_load_balancer_with_traffic"}:
        return [step for step in runbook.steps if "route" in step.params or step.action in {"shift_traffic", "failover_traffic", "drain_load_balancer", "restore_load_balancer"}]
    if prop.startswith("dns_"):
        return [step for step in runbook.steps if "record" in step.params or step.action in {"update_dns_record", "mark_dns_health_check", "finalize_dns_record", "wait"}]
    if prop == "declared_precondition":
        return [step for step in runbook.steps if step.requires]
    if prop == "declared_effect":
        return [step for step in runbook.steps if step.effects]
    return []


def _step_record(item: _LoadedRunbook, step: Step) -> dict[str, Any]:
    return {"id": step.id, "action": step.action, "line": step.source_line, "section": _section_for(item, step.source_line)}


def _services_for_property(runbook: Runbook, prop: str, steps: list[Step]) -> set[str]:
    names: set[str] = set()
    if prop in {"service_min_available", "no_draining_all_replicas", "traffic_requires_regional_capacity"}:
        names.update(runbook.state.services)
    if prop.startswith("traffic_") or prop.startswith("no_traffic"):
        names.update(route.service for route in runbook.state.traffic_routes.values())
    if prop.startswith("dns_"):
        names.update(record.service for record in runbook.state.dns_records.values())
    for step in steps:
        if "service" in step.params:
            names.add(str(step.params["service"]))
        if isinstance(step.params.get("services"), list):
            names.update(str(name) for name in step.params["services"])
    return names


def _databases_for_property(runbook: Runbook, prop: str, steps: list[Step]) -> set[str]:
    names: set[str] = set()
    if prop in {"no_rollback_during_incompatible_migration", "no_failover_to_unhealthy_region", "quorum_before_data_loss_action"}:
        names.update(runbook.state.databases)
    for step in steps:
        if "database" in step.params:
            names.add(str(step.params["database"]))
    return names


def _queues_for_property(runbook: Runbook, prop: str, steps: list[Step]) -> set[str]:
    names: set[str] = set()
    if prop in {"no_queue_pause_without_drain_plan", "no_paused_queue_with_backlog", "no_replay_without_dedupe", "dead_letter_replay_has_messages", "dead_letter_drain_has_messages", "no_duplicate_processing_risk", "queue_backlog_requires_consumers", "no_rebalance_to_zero_consumers", "no_unstable_consumer_group_with_backlog"}:
        names.update(runbook.state.queues)
    for step in steps:
        if "queue" in step.params:
            names.add(str(step.params["queue"]))
    return names


def _alerts_for_property(runbook: Runbook, prop: str, steps: list[Step]) -> set[str]:
    names: set[str] = set()
    if prop == "bounded_alert_suppression":
        names.update(runbook.state.alerts)
    for step in steps:
        if "alert" in step.params:
            names.add(str(step.params["alert"]))
    return names


def _dns_records_for_property(runbook: Runbook, prop: str, steps: list[Step]) -> set[str]:
    names: set[str] = set()
    if prop.startswith("dns_"):
        names.update(runbook.state.dns_records)
    for step in steps:
        if "record" in step.params:
            names.add(str(step.params["record"]))
    return names


def _regions_for_property(runbook: Runbook, prop: str, steps: list[Step]) -> set[str]:
    names: set[str] = set()
    if prop in {"service_min_available", "no_draining_all_replicas", "traffic_requires_regional_capacity"}:
        for service in runbook.state.services.values():
            names.update(replica.region for replica in service.replicas)
    if prop in {"no_failover_to_unhealthy_region", "quorum_before_data_loss_action"}:
        for db in runbook.state.databases.values():
            names.add(db.primary_region)
            names.update(db.healthy_regions)
    if prop.startswith("traffic_") or prop.startswith("no_traffic") or prop == "no_draining_load_balancer_with_traffic":
        for route in runbook.state.traffic_routes.values():
            names.update(route.weights)
            names.update(route.drained_regions)
    if prop.startswith("dns_"):
        for record in runbook.state.dns_records.values():
            names.add(record.region)
            if record.previous_region:
                names.add(record.previous_region)
            names.update(record.health_check_converged_regions)
    for step in steps:
        for key in ("region", "target_region"):
            if key in step.params:
                names.add(str(step.params[key]))
    return names


def _formal_obligation(prop: str) -> str:
    if prop in {"declared_precondition", "declared_effect"}:
        return "Hoare-style local assertion over step pre/postconditions"
    if prop in {"bounded_alert_suppression", "quorum_before_data_loss_action"}:
        return "safety invariant checked before the action transition"
    if prop.startswith("dns_"):
        return "DNS temporal safety invariant over health-check convergence, TTL propagation, and split-brain windows"
    if prop in {"no_replay_without_dedupe", "dead_letter_replay_has_messages", "dead_letter_drain_has_messages", "no_duplicate_processing_risk", "queue_backlog_requires_consumers", "no_rebalance_to_zero_consumers", "no_unstable_consumer_group_with_backlog"}:
        return "queue replay temporal safety invariant over deduplication, dead-letter bounds, and consumer-group progress"
    return "temporal safety invariant checked over bounded small-step traces"


def _owners(doc: dict[str, Any]) -> list[str]:
    metadata = doc.get("metadata", {})
    if not isinstance(metadata, dict):
        return ["unowned"]
    owners: set[str] = set()
    for key in ("owner", "team"):
        if metadata.get(key):
            owners.add(str(metadata[key]))
    raw_owners = metadata.get("owners")
    if isinstance(raw_owners, list):
        for item in raw_owners:
            if isinstance(item, dict) and item.get("id"):
                owners.add(str(item["id"]))
            elif item:
                owners.add(str(item))
    service_owners = metadata.get("service_owners")
    if isinstance(service_owners, dict):
        for values in service_owners.values():
            if isinstance(values, list):
                owners.update(str(value) for value in values)
            elif values:
                owners.add(str(values))
    return sorted(owners) or ["unowned"]


def _runbook_record(item: _LoadedRunbook) -> dict[str, Any]:
    return {
        "path": str(item.path),
        "name": item.runbook.name,
        "owners": _owners(item.document),
        "services": sorted(item.runbook.state.services),
        "databases": sorted(item.runbook.state.databases),
        "queues": sorted(item.runbook.state.queues),
        "alerts": sorted(item.runbook.state.alerts),
        "dns_records": sorted(item.runbook.state.dns_records),
        "credentials": [],
        "regions": sorted(item.runbook.state.regions),
    }


def _prose_record(finding: MarkdownFinding) -> dict[str, Any]:
    return {
        "rule": finding.rule,
        "severity": finding.severity,
        "path": finding.path,
        "line": finding.line,
        "section": _section_for_path(Path(finding.path), finding.line),
        "excerpt": finding.excerpt,
        "semantic_obligation": finding.semantic_obligation,
        "recommendation": finding.recommendation,
    }


def _section_for_path(path: Path, line: int) -> str:
    sections = _markdown_sections(path)
    candidates = [candidate for candidate in sections if candidate <= line]
    return sections[max(candidates)] if candidates else path.name


def _uncovered_records(loaded: list[_LoadedRunbook], property_records: list[dict[str, Any]], prose_findings: list[MarkdownFinding]) -> list[dict[str, Any]]:
    covered = {
        "services": {name for record in property_records for name in record["services"]},
        "databases": {name for record in property_records for name in record["databases"]},
        "queues": {name for record in property_records for name in record["queues"]},
        "alerts": {name for record in property_records for name in record["alerts"]},
        "dns_records": {name for record in property_records for name in record["dns_records"]},
        "regions": {name for record in property_records for name in record["regions"]},
    }
    records: list[dict[str, Any]] = []
    for item in loaded:
        for kind, names in (
            ("service", item.runbook.state.services),
            ("database", item.runbook.state.databases),
            ("queue", item.runbook.state.queues),
            ("alert", item.runbook.state.alerts),
            ("dns_record", item.runbook.state.dns_records),
            ("region", item.runbook.state.regions),
        ):
            plural = f"{kind}s" if kind not in {"queue", "dns_record"} else ("queues" if kind == "queue" else "dns_records")
            for name in names:
                if name not in covered[plural]:
                    records.append({"kind": kind, "name": name, "path": str(item.path), "message": "entity is declared but no current invariant template references it"})
    for finding in prose_findings:
        records.append({"kind": "prose_obligation", "name": finding.rule, "path": finding.path, "line": finding.line, "message": f"Markdown section has unverified obligation {finding.semantic_obligation}"})
    return records


def _summary(root: Path, loaded: list[_LoadedRunbook], parse_errors: list[dict[str, Any]], properties: list[dict[str, Any]], prose_findings: list[MarkdownFinding], uncovered: list[dict[str, Any]]) -> dict[str, Any]:
    entities = {
        "services": {name for item in loaded for name in item.runbook.state.services},
        "databases": {name for item in loaded for name in item.runbook.state.databases},
        "queues": {name for item in loaded for name in item.runbook.state.queues},
        "alerts": {name for item in loaded for name in item.runbook.state.alerts},
        "dns_records": {name for item in loaded for name in item.runbook.state.dns_records},
        "regions": {name for item in loaded for name in item.runbook.state.regions},
        "credentials": set(),
    }
    covered = {
        "services": {name for record in properties for name in record["services"]},
        "databases": {name for record in properties for name in record["databases"]},
        "queues": {name for record in properties for name in record["queues"]},
        "alerts": {name for record in properties for name in record["alerts"]},
        "dns_records": {name for record in properties for name in record["dns_records"]},
        "regions": {name for record in properties for name in record["regions"]},
        "credentials": {name for record in properties for name in record["credentials"]},
    }
    return {
        "path": str(root),
        "runbooks": len(loaded),
        "parse_errors": len(parse_errors),
        "properties": len(properties),
        "services": len(entities["services"]),
        "covered_services": len(entities["services"] & covered["services"]),
        "databases": len(entities["databases"]),
        "covered_databases": len(entities["databases"] & covered["databases"]),
        "queues": len(entities["queues"]),
        "covered_queues": len(entities["queues"] & covered["queues"]),
        "alerts": len(entities["alerts"]),
        "covered_alerts": len(entities["alerts"] & covered["alerts"]),
        "dns_records": len(entities["dns_records"]),
        "covered_dns_records": len(entities["dns_records"] & covered["dns_records"]),
        "credentials": len(entities["credentials"]),
        "covered_credentials": len(entities["credentials"] & covered["credentials"]),
        "regions": len(entities["regions"]),
        "covered_regions": len(entities["regions"] & covered["regions"]),
        "owners": sorted({owner for item in loaded for owner in _owners(item.document)}),
        "unverified_prose_obligations": len(prose_findings),
        "uncovered_entities": len(uncovered),
    }


def _csv(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else ""


def _step_summary(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return ""
    rendered = []
    for step in steps:
        location = f"L{step['line']}" if step["line"] else "no-line"
        rendered.append(f"`{step['id']}` ({location}, {step['section']})")
    return "<br>".join(rendered).replace("|", "\\|")
