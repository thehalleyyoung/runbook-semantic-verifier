from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .checker import Checker, CheckResult, Violation
from .markdown_lint import SEVERITY_RANK, MarkdownFinding, lint_markdown_file
from .model import Runbook, Step
from .parser import RunbookParseError, load_document, parse_runbook

RUNBOOK_SUFFIXES = {".json", ".yaml", ".yml", ".md"}
ROLLBACK_ACTIONS = {"restore_replica", "restore_load_balancer", "resume_queue", "rollback_deployment", "failover_traffic", "shift_traffic", "update_dns_record", "warm_cache", "resume_cache_writes"}
HIGH_RISK_ACTIONS = {"drain_replica", "drain_region", "drain_load_balancer", "failover_database", "pause_queue", "run_migration", "update_dns_record", "flush_cache"}


@dataclass(frozen=True)
class ReadinessOptions:
    service: str | None = None
    region: str | None = None
    freshness_days: int = 180
    as_of: date | None = None
    inventory_path: str | Path | None = None


@dataclass(frozen=True)
class _CheckedRunbook:
    path: Path
    runbook: Runbook
    result: CheckResult
    metadata: dict[str, Any]
    expected_labels: dict[str, Any] | None = None


def build_readiness_report(path: str | Path, options: ReadinessOptions | None = None) -> dict[str, Any]:
    options = options or ReadinessOptions()
    root = Path(path)
    if not root.exists():
        raise ReadinessError(f"readiness path does not exist: {root}")
    as_of = options.as_of or date.today()
    inventory = _load_inventory(options.inventory_path) if options.inventory_path else None
    executable_paths = _executable_runbook_files(root)
    checked: list[_CheckedRunbook] = []
    parse_errors: list[dict[str, Any]] = []
    for file in executable_paths:
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
        if _matches_scope(runbook, options):
            checked.append(_CheckedRunbook(file, runbook, Checker(runbook).check(), _metadata(doc), _expected_labels(doc)))

    markdown_paths = _markdown_files(root)
    relevant_paths = {item.path for item in checked}
    if options.service or options.region:
        lint_paths = [file for file in markdown_paths if file in relevant_paths]
    else:
        lint_paths = markdown_paths
    prose_findings = [finding for file in lint_paths for finding in lint_markdown_file(file)]
    freshness_paths = relevant_paths if options.service or options.region else set(executable_paths)
    stale_files = [_freshness_record(file, as_of, options.freshness_days) for file in sorted(freshness_paths | set(lint_paths))]
    stale_files = [item for item in stale_files if item["stale"]]
    stale_inventory = _inventory_stale_preconditions(checked, inventory) if inventory else []
    stale_preconditions = stale_files + stale_inventory
    missing_rollback = []
    for item in checked:
        rollback_record = _missing_rollback_record(item)
        if rollback_record is not None:
            missing_rollback.append(rollback_record)
    semantic_findings = [_violation_record(item, violation) for item in checked for violation in item.result.violations]
    benchmark_expectations = [_benchmark_expectation_record(item, prose_findings) for item in checked if item.expected_labels is not None]
    benchmark_mismatches = [item for item in benchmark_expectations if not item["pass"]]
    coverage_findings = _coverage_findings(options, checked)
    proof_obligations = _aggregate_obligations([item.result for item in checked])
    summary = _summary(checked, parse_errors, semantic_findings, prose_findings, stale_preconditions, missing_rollback, coverage_findings, benchmark_mismatches)
    return {
        "path": str(root),
        "filters": {"service": options.service, "region": options.region},
        "freshness": {"as_of": as_of.isoformat(), "max_age_days": options.freshness_days},
        "inventory": inventory["metadata"] if inventory else None,
        "summary": summary,
        "runbooks": [_runbook_record(item) for item in checked],
        "parse_errors": parse_errors,
        "highest_risk_counterexamples": semantic_findings[:10],
        "unverified_prose_claims": [_prose_record(finding) for finding in prose_findings],
        "missing_rollback_steps": missing_rollback,
        "stale_preconditions": stale_preconditions,
        "benchmark_expectations": benchmark_expectations,
        "coverage_findings": coverage_findings,
        "proof_obligations": proof_obligations,
        "modeled_entities": _modeled_entities(checked),
    }


def render_readiness_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_readiness_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# Incident readiness report: {report['path']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- Readiness score: {summary['readiness_score']}/100",
        f"- Filters: service=`{report['filters']['service'] or ''}` region=`{report['filters']['region'] or ''}`",
        f"- Inventory: `{report['inventory']['path'] if report.get('inventory') else ''}`",
        f"- Runbooks considered: {summary['runbooks_considered']}",
        f"- Safe runbooks: {summary['safe_runbooks']}",
        f"- Parse errors: {summary['parse_errors']}",
        f"- Semantic counterexamples: {summary['semantic_counterexamples']}",
        f"- Unverified prose claims: {summary['unverified_prose_claims']}",
        f"- Missing rollback/restore coverage: {summary['missing_rollback_steps']}",
        f"- Stale preconditions: {summary['stale_preconditions']}",
        f"- Blocking stale preconditions: {summary['blocking_stale_preconditions']}",
        f"- Benchmark expectation mismatches: {summary['benchmark_expectation_mismatches']}",
        "",
        "## Runbooks",
        "",
    ]
    if report["runbooks"]:
        lines.extend(["| Path | Name | Safe | States | Transitions | Terminal traces | Max depth reached |", "| --- | --- | --- | ---: | ---: | ---: | --- |"])
        for item in report["runbooks"]:
            lines.append(f"| `{item['path']}` | {str(item['name']).replace('|', '\\|')} | `{item['safe']}` | {item['states_explored']} | {item['transitions_explored']} | {item['terminal_traces']} | `{item['max_depth_reached']}` |")
    else:
        lines.append("No executable runbooks matched the requested scope.")
    lines.extend(["", "## Highest-risk counterexamples", ""])
    if report["highest_risk_counterexamples"]:
        for finding in report["highest_risk_counterexamples"]:
            trace = " -> ".join(finding["trace"])
            lines.append(f"- `[{finding['property']}]` `{finding['path']}` step `{finding.get('step')}` trace `{trace}`: {finding['message']}")
    else:
        lines.append("None within the configured bound.")
    lines.extend(["", "## Unverified prose claims", ""])
    if report["unverified_prose_claims"]:
        lines.extend(["| Rule | Severity | Obligation | Location | Excerpt | Recommendation |", "| --- | --- | --- | --- | --- | --- |"])
        for finding in report["unverified_prose_claims"]:
            lines.append(f"| {finding['rule']} | {finding['severity']} | `{finding['semantic_obligation']}` | `{finding['path']}:{finding['line']}` | {str(finding['excerpt']).replace('|', '\\|')} | {str(finding['recommendation']).replace('|', '\\|')} |")
    else:
        lines.append("None.")
    lines.extend(["", "## Missing rollback/restore coverage", ""])
    if report["missing_rollback_steps"]:
        for item in report["missing_rollback_steps"]:
            lines.append(f"- `{item['path']}` has high-risk steps `{', '.join(item['high_risk_steps'])}` but no modeled rollback/restore action.")
    else:
        lines.append("No high-risk executable step lacked a modeled rollback/restore action.")
    lines.extend(["", "## Stale preconditions", ""])
    if report["stale_preconditions"]:
        for item in report["stale_preconditions"]:
            if item["kind"] == "stale_file":
                lines.append(f"- `{item['path']}` age={item['age_days']} days source={item['source']} observed={item['observed_date']}")
            else:
                lines.append(f"- `{item['severity']}` `{item['kind']}` in `{item['path']}`: {item['message']} (obligation `{item['semantic_obligation']}`)")
    else:
        lines.append("No file exceeded the configured freshness window and no inventory-refinement precondition failed.")
    lines.extend(["", "## Proof obligations", "", "```json", json.dumps(report["proof_obligations"], indent=2, sort_keys=True), "```", ""])
    lines.extend(["## Benchmark expectations", ""])
    if report["benchmark_expectations"]:
        lines.extend(["| Path | Pass | Expected labels | Errors |", "| --- | --- | --- | --- |"])
        for item in report["benchmark_expectations"]:
            lines.append(f"| `{item['path']}` | `{item['pass']}` | `{json.dumps(item['expected_labels'], sort_keys=True)}` | `{json.dumps(item['errors'], sort_keys=True)}` |")
    else:
        lines.append("No embedded benchmark labels were present for matched runbooks.")
    lines.append("")
    return "\n".join(lines) + "\n"


class ReadinessError(ValueError):
    pass


def _runbook_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() in RUNBOOK_SUFFIXES)


def _markdown_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*.md"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() == ".md")


def _executable_runbook_files(root: Path) -> list[Path]:
    return [path for path in _runbook_files(root) if path.suffix.lower() != ".md" or _has_embedded_runbook(path)]


def _has_embedded_runbook(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "```runbook-json" in text or "```json" in text


def _matches_scope(runbook: Runbook, options: ReadinessOptions) -> bool:
    if options.service and options.service not in _services(runbook):
        return False
    if options.region and options.region not in _regions(runbook):
        return False
    return True


def _services(runbook: Runbook) -> set[str]:
    names = set(runbook.state.services)
    names.update(route.service for route in runbook.state.traffic_routes.values())
    names.update(record.service for record in runbook.state.dns_records.values())
    names.update(cache.service for cache in runbook.state.caches.values())
    for step in runbook.steps:
        if "service" in step.params:
            names.add(str(step.params["service"]))
        if "services" in step.params and isinstance(step.params["services"], list):
            names.update(str(item) for item in step.params["services"])
    return names


def _regions(runbook: Runbook) -> set[str]:
    names = set(runbook.state.regions)
    for service in runbook.state.services.values():
        names.update(replica.region for replica in service.replicas)
    for db in runbook.state.databases.values():
        names.add(db.primary_region)
        names.update(db.healthy_regions)
    for route in runbook.state.traffic_routes.values():
        names.update(route.weights)
        names.update(route.drained_regions)
    for record in runbook.state.dns_records.values():
        names.add(record.region)
        if record.previous_region:
            names.add(record.previous_region)
        names.update(record.health_check_converged_regions)
    for step in runbook.steps:
        for key in ("region", "target_region"):
            if key in step.params:
                names.add(str(step.params[key]))
    return names


def _missing_rollback_record(item: _CheckedRunbook) -> dict[str, Any] | None:
    high_risk = [step.id for step in item.runbook.steps if _is_high_risk(step)]
    has_rollback = any(step.action in ROLLBACK_ACTIONS for step in item.runbook.steps)
    if not high_risk or has_rollback:
        return None
    return {
        "path": str(item.path),
        "runbook": item.runbook.name,
        "high_risk_steps": high_risk,
        "semantic_obligation": "rollback_or_restore_readiness",
        "recommendation": "Model a rollback, restore, resume, or compensating traffic action for high-risk incident steps.",
    }


def _is_high_risk(step: Step) -> bool:
    if step.action == "failover_database":
        return bool(step.params.get("data_loss_risk", False))
    return step.action in HIGH_RISK_ACTIONS


def _freshness_record(path: Path, as_of: date, max_age_days: int) -> dict[str, Any]:
    observed, source = _observed_date(path)
    age = max((as_of - observed).days, 0)
    return {
        "path": str(path),
        "kind": "stale_file",
        "severity": "warning",
        "semantic_obligation": "fresh_operational_preconditions",
        "observed_date": observed.isoformat(),
        "source": source,
        "age_days": age,
        "max_age_days": max_age_days,
        "stale": age > max_age_days,
    }


def _observed_date(path: Path) -> tuple[date, str]:
    if path.suffix.lower() == ".md":
        text = path.read_text(encoding="utf-8")
        match = re.search(r"(?:Retrieval date|retrieved|Commit date observed)\s*:\s*`?(\d{4}-\d{2}-\d{2})", text, flags=re.I)
        if match:
            return date.fromisoformat(match.group(1)), "document_metadata"
    return datetime.fromtimestamp(path.stat().st_mtime).date(), "file_mtime"


def _violation_record(item: _CheckedRunbook, violation: Violation) -> dict[str, Any]:
    return {
        "path": str(item.path),
        "runbook": item.runbook.name,
        "property": violation.property,
        "step": violation.step,
        "trace": list(violation.trace),
        "message": violation.message,
        "remediation": violation.remediation,
        "semantic_obligation": violation.property,
        "severity": "error",
    }


def _prose_record(finding: MarkdownFinding) -> dict[str, Any]:
    return {
        "rule": finding.rule,
        "severity": finding.severity,
        "path": finding.path,
        "line": finding.line,
        "excerpt": finding.excerpt,
        "message": finding.message,
        "recommendation": finding.recommendation,
        "semantic_obligation": finding.semantic_obligation,
    }


def _expected_labels(doc: dict[str, Any]) -> dict[str, Any] | None:
    metadata = _metadata(doc)
    if not isinstance(metadata, dict):
        return None
    labels = metadata.get("labels", {})
    if not isinstance(labels, dict) or not labels:
        return None
    expected: dict[str, Any] = {}
    if "expected_safe" in labels:
        expected["expected_safe"] = bool(labels["expected_safe"])
    props = labels.get("expected_violation_properties")
    if isinstance(props, list):
        expected["expected_violation_properties"] = sorted(str(prop) for prop in props)
    prose_rules = labels.get("expected_prose_rules")
    if isinstance(prose_rules, list):
        expected["expected_prose_rules"] = sorted(str(rule) for rule in prose_rules)
    return expected or None


def _metadata(doc: dict[str, Any]) -> dict[str, Any]:
    metadata = doc.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _load_inventory(path: str | Path) -> dict[str, Any]:
    inventory_path = Path(path)
    if not inventory_path.exists():
        raise ReadinessError(f"inventory path does not exist: {inventory_path}")
    try:
        raw = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReadinessError(f"invalid inventory JSON in {inventory_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ReadinessError(f"inventory {inventory_path} must be a JSON object")
    services_raw = raw.get("services", {})
    if not isinstance(services_raw, dict):
        raise ReadinessError("inventory.services must be an object keyed by service name")
    services: dict[str, dict[str, Any]] = {}
    for name, cfg in services_raw.items():
        if not isinstance(cfg, dict):
            raise ReadinessError(f"inventory.services.{name} must be an object")
        replicas = cfg.get("replicas")
        if replicas is not None and (not isinstance(replicas, int) or replicas < 0):
            raise ReadinessError(f"inventory.services.{name}.replicas must be a non-negative integer")
        services[str(name)] = {
            "replicas": replicas,
            "owners": _string_list(cfg.get("owners", []), f"inventory.services.{name}.owners"),
            "alerts": _string_list(cfg.get("alerts", []), f"inventory.services.{name}.alerts"),
            "dependencies": _string_list(cfg.get("dependencies", []), f"inventory.services.{name}.dependencies"),
        }
    alerts = set(_string_collection(raw.get("alerts", []), "inventory.alerts"))
    dependencies = set(_string_collection(raw.get("dependencies", []), "inventory.dependencies"))
    owners = set(_string_collection(raw.get("owners", []), "inventory.owners"))
    for cfg in services.values():
        alerts.update(cfg["alerts"])
        dependencies.update(cfg["dependencies"])
        owners.update(cfg["owners"])
    metadata = raw.get("metadata", {})
    if metadata is not None and not isinstance(metadata, dict):
        raise ReadinessError("inventory.metadata must be an object when present")
    return {
        "metadata": {
            **(metadata or {}),
            "path": str(inventory_path),
            "services": len(services),
            "alerts": len(alerts),
            "dependencies": len(dependencies),
            "owners": len(owners),
        },
        "services": services,
        "alerts": alerts,
        "dependencies": dependencies,
        "owners": owners,
    }


def _string_collection(value: Any, field: str) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key in value]
    return _string_list(value, field)


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ReadinessError(f"{field} must be a list")
    result = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            result.append(item["id"])
        else:
            raise ReadinessError(f"{field} entries must be strings or objects with string id")
    return result


def _inventory_stale_preconditions(checked: list[_CheckedRunbook], inventory: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    inventory_services: dict[str, dict[str, Any]] = inventory["services"]
    inventory_alerts: set[str] = inventory["alerts"]
    inventory_dependencies: set[str] = inventory["dependencies"]
    inventory_owners: set[str] = inventory["owners"]
    for item in checked:
        modeled_services = item.runbook.state.services
        modeled_alerts = set(item.runbook.state.alerts)
        modeled_dependencies = _dependencies(item.runbook)
        modeled_owners = _owners(item.metadata)
        for service_name, service in modeled_services.items():
            cfg = inventory_services.get(service_name)
            if cfg is None:
                findings.append(_inventory_finding(item, "unknown_service_reference", "error", service_name, f"modeled service {service_name!r} is absent from the configured inventory"))
                continue
            expected_replicas = cfg.get("replicas")
            if expected_replicas is not None and expected_replicas != len(service.replicas):
                findings.append(_inventory_finding(item, "replica_count_mismatch", "error", service_name, f"service {service_name!r} models {len(service.replicas)} replica(s) but inventory expects {expected_replicas}"))
            expected_owners = set(cfg["owners"])
            service_owners = set(_service_owners(item.metadata, service_name)) or modeled_owners
            missing_owners = sorted(expected_owners - service_owners)
            if missing_owners:
                findings.append(_inventory_finding(item, "missing_service_owner", "warning", service_name, f"service {service_name!r} is missing inventory owner(s): {', '.join(missing_owners)}"))
            missing_alerts = sorted(set(cfg["alerts"]) - modeled_alerts)
            if missing_alerts:
                findings.append(_inventory_finding(item, "missing_service_alert", "warning", service_name, f"service {service_name!r} omits inventory alert(s): {', '.join(missing_alerts)}"))
            missing_dependencies = sorted(set(cfg["dependencies"]) - modeled_dependencies)
            if missing_dependencies:
                findings.append(_inventory_finding(item, "missing_dependency", "warning", service_name, f"service {service_name!r} omits inventory dependency name(s): {', '.join(missing_dependencies)}"))
        for service_name in sorted(set(inventory_services) - set(modeled_services)):
            if service_name in _services(item.runbook):
                findings.append(_inventory_finding(item, "service_used_but_not_modeled", "error", service_name, f"service {service_name!r} appears in steps/routes/caches but has no modeled service replica state"))
        for alert in sorted(modeled_alerts - inventory_alerts):
            findings.append(_inventory_finding(item, "unknown_alert_reference", "warning", alert, f"modeled alert {alert!r} is absent from the configured inventory"))
        for dependency in sorted(modeled_dependencies - inventory_dependencies):
            findings.append(_inventory_finding(item, "unknown_dependency_reference", "warning", dependency, f"modeled dependency {dependency!r} is absent from the configured inventory"))
        for owner in sorted(modeled_owners - inventory_owners):
            findings.append(_inventory_finding(item, "unknown_owner_reference", "warning", owner, f"modeled owner {owner!r} is absent from the configured inventory"))
    return findings


def _inventory_finding(item: _CheckedRunbook, kind: str, severity: str, entity: str, message: str) -> dict[str, Any]:
    return {
        "path": str(item.path),
        "kind": kind,
        "severity": severity,
        "entity": entity,
        "source": "configured_inventory",
        "semantic_obligation": "inventory_refinement_precondition",
        "message": message,
        "recommendation": "Refresh the runbook model or update the inventory fixture before treating the readiness result as current.",
    }


def _dependencies(runbook: Runbook) -> set[str]:
    names = set(runbook.state.databases) | set(runbook.state.queues) | set(runbook.state.caches) | set(runbook.state.traffic_routes) | set(runbook.state.dns_records)
    for step in runbook.steps:
        for key in ("database", "queue", "cache", "route", "record", "dependency"):
            if key in step.params:
                names.add(str(step.params[key]))
    return names


def _owners(metadata: dict[str, Any]) -> set[str]:
    owners: set[str] = set()
    owner = metadata.get("owner")
    if isinstance(owner, str):
        owners.add(owner)
    owners.update(_owner_ids(metadata.get("owners", [])))
    service_owners = metadata.get("service_owners", {})
    if isinstance(service_owners, dict):
        for value in service_owners.values():
            owners.update(_owner_ids(value))
    return owners


def _service_owners(metadata: dict[str, Any], service: str) -> list[str]:
    service_owners = metadata.get("service_owners", {})
    if not isinstance(service_owners, dict):
        return []
    return _owner_ids(service_owners.get(service, []))


def _owner_ids(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    owners: set[str] = set()
    for item in value:
        if isinstance(item, str):
            owners.add(item)
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            owners.add(item["id"])
    return owners


def _benchmark_expectation_record(item: _CheckedRunbook, prose_findings: list[MarkdownFinding]) -> dict[str, Any]:
    expected = item.expected_labels or {}
    observed_props = {violation.property for violation in item.result.violations}
    observed_prose = {finding.rule for finding in prose_findings if Path(finding.path) == item.path}
    errors = []
    if "expected_safe" in expected and item.result.safe is not bool(expected["expected_safe"]):
        errors.append(f"expected_safe={expected['expected_safe']} but observed safe={item.result.safe}")
    missing_props = sorted(set(expected.get("expected_violation_properties", [])) - observed_props)
    if missing_props:
        errors.append(f"missing expected violation properties: {', '.join(missing_props)}")
    missing_prose = sorted(set(expected.get("expected_prose_rules", [])) - observed_prose)
    if missing_prose:
        errors.append(f"missing expected prose rules: {', '.join(missing_prose)}")
    return {"path": str(item.path), "expected_labels": expected, "pass": not errors, "errors": errors}


def _coverage_findings(options: ReadinessOptions, checked: list[_CheckedRunbook]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if options.service and not any(options.service in _services(item.runbook) for item in checked):
        findings.append({"severity": "error", "kind": "uncovered_service", "message": f"no executable runbook covers service {options.service!r}"})
    if options.region and not any(options.region in _regions(item.runbook) for item in checked):
        findings.append({"severity": "error", "kind": "uncovered_region", "message": f"no executable runbook covers region {options.region!r}"})
    return findings


def _aggregate_obligations(results: list[CheckResult]) -> dict[str, Any]:
    checked: dict[str, int] = {}
    failures: dict[str, int] = {}
    for result in results:
        for key, value in result.proof_obligations_checked.items():
            checked[key] = checked.get(key, 0) + value
        for key, value in result.proof_obligation_failures.items():
            failures[key] = failures.get(key, 0) + value
    return {"checked": dict(sorted(checked.items())), "failures": dict(sorted(failures.items()))}


def _summary(
    checked: list[_CheckedRunbook],
    parse_errors: list[dict[str, Any]],
    semantic_findings: list[dict[str, Any]],
    prose_findings: list[MarkdownFinding],
    stale_preconditions: list[dict[str, Any]],
    missing_rollback: list[dict[str, Any]],
    coverage_findings: list[dict[str, Any]],
    benchmark_mismatches: list[dict[str, Any]],
) -> dict[str, Any]:
    blocking_prose = [finding for finding in prose_findings if SEVERITY_RANK[finding.severity] >= SEVERITY_RANK["error"]]
    warnings = [finding for finding in prose_findings if SEVERITY_RANK[finding.severity] == SEVERITY_RANK["warning"]]
    blocking_stale = [finding for finding in stale_preconditions if finding.get("severity") == "error"]
    not_ready = bool(parse_errors or semantic_findings or blocking_prose or blocking_stale or coverage_findings or benchmark_mismatches)
    advisory = bool(warnings or stale_preconditions or missing_rollback or prose_findings)
    status = "not_ready" if not_ready else "advisory" if advisory else "ready"
    score = 100
    score -= 25 * len(parse_errors)
    score -= 20 * len(semantic_findings)
    score -= 10 * len(blocking_prose)
    score -= 5 * len(warnings)
    score -= 15 * len(blocking_stale)
    score -= 5 * (len(stale_preconditions) - len(blocking_stale))
    score -= 5 * len(missing_rollback)
    score -= 25 * len(coverage_findings)
    score -= 15 * len(benchmark_mismatches)
    return {
        "status": status,
        "readiness_score": max(score, 0),
        "runbooks_considered": len(checked),
        "safe_runbooks": sum(1 for item in checked if item.result.safe),
        "unsafe_runbooks": sum(1 for item in checked if not item.result.safe),
        "parse_errors": len(parse_errors),
        "semantic_counterexamples": len(semantic_findings),
        "unverified_prose_claims": len(prose_findings),
        "missing_rollback_steps": len(missing_rollback),
        "stale_preconditions": len(stale_preconditions),
        "blocking_stale_preconditions": len(blocking_stale),
        "coverage_findings": len(coverage_findings),
        "benchmark_expectation_mismatches": len(benchmark_mismatches),
    }


def _runbook_record(item: _CheckedRunbook) -> dict[str, Any]:
    return {
        "path": str(item.path),
        "name": item.runbook.name,
        "safe": item.result.safe,
        "states_explored": item.result.states_explored,
        "transitions_explored": item.result.transitions_explored,
        "terminal_traces": item.result.traces_explored,
        "max_depth_reached": item.result.max_depth_reached,
        "services": sorted(_services(item.runbook)),
        "regions": sorted(_regions(item.runbook)),
        "expected_labels": item.expected_labels,
    }


def _modeled_entities(checked: list[_CheckedRunbook]) -> dict[str, list[str]]:
    services: set[str] = set()
    regions: set[str] = set()
    for item in checked:
        services.update(_services(item.runbook))
        regions.update(_regions(item.runbook))
    return {"services": sorted(services), "regions": sorted(regions)}
