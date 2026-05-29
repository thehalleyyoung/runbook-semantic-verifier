from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .checker import Checker, CheckResult, Violation
from .markdown_lint import SEVERITY_RANK, MarkdownFinding, lint_markdown_file
from .model import Runbook
from .parser import RunbookParseError, load_document, parse_runbook

RUNBOOK_SUFFIXES = {".json", ".yaml", ".yml", ".md"}
ROLLBACK_ACTIONS = {"restore_replica", "restore_load_balancer", "resume_queue", "rollback_deployment", "failover_traffic", "shift_traffic"}
HIGH_RISK_ACTIONS = {"drain_replica", "drain_region", "drain_load_balancer", "failover_database", "pause_queue", "run_migration"}
UNASSIGNED_OWNER = "unassigned"


@dataclass(frozen=True)
class OwnerScorecardOptions:
    owner: str | None = None
    freshness_days: int = 180
    as_of: date | None = None


@dataclass(frozen=True)
class _RunbookAssessment:
    path: Path
    doc: dict[str, Any]
    runbook: Runbook
    result: CheckResult
    owners: tuple[str, ...]
    service_owners: dict[str, tuple[str, ...]]
    remediation_history: tuple[dict[str, Any], ...]
    waivers: tuple[dict[str, Any], ...]


@dataclass
class _OwnerAccumulator:
    owner: str
    runbooks: list[_RunbookAssessment] = field(default_factory=list)
    prose_findings: list[MarkdownFinding] = field(default_factory=list)
    semantic_findings: list[tuple[_RunbookAssessment, Violation]] = field(default_factory=list)
    parse_errors: list[dict[str, Any]] = field(default_factory=list)
    missing_rollback: list[dict[str, Any]] = field(default_factory=list)
    stale_assumptions: list[dict[str, Any]] = field(default_factory=list)
    waivers: list[dict[str, Any]] = field(default_factory=list)
    remediation_history: list[dict[str, Any]] = field(default_factory=list)


def build_owner_scorecard(path: str | Path, options: OwnerScorecardOptions | None = None) -> dict[str, Any]:
    options = options or OwnerScorecardOptions()
    root = Path(path)
    if not root.exists():
        raise OwnerScorecardError(f"owner-scorecard path does not exist: {root}")
    as_of = options.as_of or date.today()
    executable_paths = _executable_runbook_files(root)
    markdown_paths = _markdown_files(root)
    assessments: list[_RunbookAssessment] = []
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
                "owners": (UNASSIGNED_OWNER,),
            })
            continue
        metadata = _metadata(doc)
        service_owners = _service_owners(metadata)
        owners = _owners_for_runbook(metadata, service_owners, _services(runbook))
        assessment = _RunbookAssessment(
            path=file,
            doc=doc,
            runbook=runbook,
            result=Checker(runbook).check(),
            owners=owners,
            service_owners=service_owners,
            remediation_history=tuple(_remediation_history(metadata, file)),
            waivers=tuple(_waivers(metadata, file, as_of)),
        )
        assessments.append(assessment)

    prose_by_path = {file: lint_markdown_file(file) for file in markdown_paths}
    accumulators: dict[str, _OwnerAccumulator] = {}

    for error in parse_errors:
        for owner in error["owners"]:
            accumulators.setdefault(owner, _OwnerAccumulator(owner)).parse_errors.append(error)

    for assessment in assessments:
        for owner in assessment.owners:
            acc = accumulators.setdefault(owner, _OwnerAccumulator(owner))
            acc.runbooks.append(assessment)
            acc.semantic_findings.extend((assessment, violation) for violation in assessment.result.violations)
            acc.prose_findings.extend(prose_by_path.get(assessment.path, []))
            rollback = _missing_rollback_record(assessment)
            if rollback is not None:
                acc.missing_rollback.append(rollback)
            stale = _freshness_record(assessment.path, as_of, options.freshness_days)
            if stale["stale"]:
                acc.stale_assumptions.append(stale)
            acc.waivers.extend(assessment.waivers)
            acc.remediation_history.extend(assessment.remediation_history)
        for waiver in assessment.waivers:
            waiver_owner = str(waiver.get("owner", ""))
            if waiver_owner and waiver_owner not in assessment.owners:
                accumulators.setdefault(waiver_owner, _OwnerAccumulator(waiver_owner)).waivers.append(waiver)

    executable_markdown = {item.path for item in assessments}
    for file, findings in prose_by_path.items():
        if file in executable_markdown or not findings:
            continue
        acc = accumulators.setdefault(UNASSIGNED_OWNER, _OwnerAccumulator(UNASSIGNED_OWNER))
        acc.prose_findings.extend(findings)
        stale = _freshness_record(file, as_of, options.freshness_days)
        if stale["stale"]:
            acc.stale_assumptions.append(stale)

    owners = [_owner_record(acc, as_of) for acc in accumulators.values()]
    owners = sorted(owners, key=lambda item: (item["status"] != "not_ready", -int(item["open_hazards"]), str(item["owner"])))
    if options.owner is not None:
        owners = [owner for owner in owners if owner["owner"] == options.owner]
    summary = _summary(owners, parse_errors)
    return {
        "path": str(root),
        "filters": {"owner": options.owner},
        "freshness": {"as_of": as_of.isoformat(), "max_age_days": options.freshness_days},
        "summary": summary,
        "owners": owners,
        "parse_errors": parse_errors,
        "semantics": {
            "owner_assignment": "metadata.owners, metadata.owner, metadata.team, or metadata.service_owners; otherwise unassigned",
            "verified_runbook": "parsed executable model with no bounded semantic counterexamples",
            "open_hazard": "parse error, failed Hoare-style/safety obligation, blocking prose finding, missing rollback, stale assumption, or expired waiver",
            "waiver_debt": "metadata.waivers entries with active or expired expiry dates; expired waivers are blocking debt",
        },
    }


def render_owner_scorecard_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_owner_scorecard_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# Owner scorecard: {report['path']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- Owners: {summary['owners']}",
        f"- Runbooks: {summary['runbooks']}",
        f"- Verified runbooks: {summary['verified_runbooks']}",
        f"- Open hazards: {summary['open_hazards']}",
        f"- Stale assumptions: {summary['stale_assumptions']}",
        f"- Waiver debt: {summary['waiver_debt']}",
        "",
        "The scorecard groups executable runbooks by owner metadata and treats each runbook as a bounded operational program. Failed preconditions, safety postconditions, and prose-obligation gaps are counted as owner-visible remediation debt, not as live infrastructure proof.",
        "",
    ]
    if report["owners"]:
        lines.extend(["| Owner | Status | Score | Runbooks | Verified | Open hazards | Semantic CEX | Prose findings | Stale | Waiver debt | Services | Recent remediation |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"])
        for owner in report["owners"]:
            services = ", ".join(f"`{svc}`" for svc in owner["services"])
            remediation = str(owner.get("recent_remediation", "")).replace("|", "\\|")
            lines.append(
                f"| `{owner['owner']}` | `{owner['status']}` | {owner['score']} | {owner['runbooks']} | {owner['verified_runbooks']} | {owner['open_hazards']} | {owner['semantic_counterexamples']} | {owner['prose_findings']} | {owner['stale_assumptions']} | {owner['waiver_debt']} | {services} | {remediation} |"
            )
    else:
        lines.append("No owners matched the requested filter.")
    lines.extend(["", "## Owner details", ""])
    for owner in report["owners"]:
        lines.extend([
            f"### `{owner['owner']}`",
            "",
            f"- Status: `{owner['status']}` score={owner['score']}/100",
            f"- Regions: {', '.join(f'`{region}`' for region in owner['regions']) or 'none'}",
            f"- Proof obligations checked: `{json.dumps(owner['proof_obligations']['checked'], sort_keys=True)}`",
            f"- Proof obligation failures: `{json.dumps(owner['proof_obligations']['failures'], sort_keys=True)}`",
            "",
        ])
        if owner["top_hazards"]:
            lines.append("Top hazards:")
            for hazard in owner["top_hazards"]:
                lines.append(f"- `{hazard['kind']}` `{hazard.get('rule') or hazard.get('property')}` `{hazard['path']}`: {hazard['message']}")
        else:
            lines.append("Top hazards: none within the configured bound.")
        lines.append("")
    return "\n".join(lines) + "\n"


class OwnerScorecardError(ValueError):
    pass


def _metadata(doc: dict[str, Any]) -> dict[str, Any]:
    metadata = doc.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _owners_for_runbook(metadata: dict[str, Any], service_owners: dict[str, tuple[str, ...]], services: set[str]) -> tuple[str, ...]:
    owners: set[str] = set()
    owners.update(_owner_values(metadata.get("owners")))
    owners.update(_owner_values(metadata.get("owner")))
    owners.update(_owner_values(metadata.get("team")))
    for service in services:
        owners.update(service_owners.get(service, ()))
    return tuple(sorted(owners or {UNASSIGNED_OWNER}))


def _owner_values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, dict):
        for key in ("id", "owner", "team", "name"):
            item = value.get(key)
            if isinstance(item, str) and item:
                return {item}
        return set()
    if isinstance(value, list):
        owners: set[str] = set()
        for item in value:
            owners.update(_owner_values(item))
        return owners
    return set()


def _service_owners(metadata: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    raw = metadata.get("service_owners", {})
    if not isinstance(raw, dict):
        return {}
    owners = {}
    for service, value in raw.items():
        names = tuple(sorted(_owner_values(value)))
        if names:
            owners[str(service)] = names
    return owners


def _remediation_history(metadata: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    raw = metadata.get("remediation_history", [])
    if not isinstance(raw, list):
        return []
    history = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        history.append({
            "path": str(path),
            "date": str(item.get("date", "")),
            "status": str(item.get("status", "")),
            "summary": str(item.get("summary", "")),
        })
    return history


def _waivers(metadata: dict[str, Any], path: Path, as_of: date) -> list[dict[str, Any]]:
    raw = metadata.get("waivers", [])
    if not isinstance(raw, list):
        return []
    waivers = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        expiry = str(item.get("expiry") or item.get("expires") or item.get("expires_on") or "")
        expired = False
        if expiry:
            try:
                expired = date.fromisoformat(expiry) < as_of
            except ValueError as exc:
                raise OwnerScorecardError(f"{path}: metadata.waivers[{index}] has invalid ISO expiry date {expiry!r}") from exc
        waivers.append({
            "path": str(path),
            "id": str(item.get("id", f"waiver-{index + 1}")),
            "owner": str(item.get("owner", "")),
            "scope": str(item.get("scope", "")),
            "invariant": str(item.get("invariant", item.get("semantic_obligation", ""))),
            "expiry": expiry,
            "expired": expired,
            "rationale": str(item.get("rationale", "")),
        })
    return waivers


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


def _services(runbook: Runbook) -> set[str]:
    names = set(runbook.state.services)
    names.update(route.service for route in runbook.state.traffic_routes.values())
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
    return names


def _missing_rollback_record(assessment: _RunbookAssessment) -> dict[str, Any] | None:
    high_risk = [step.id for step in assessment.runbook.steps if step.action in HIGH_RISK_ACTIONS or (step.action == "failover_database" and step.params.get("data_loss_risk"))]
    if not high_risk or any(step.action in ROLLBACK_ACTIONS for step in assessment.runbook.steps):
        return None
    return {"path": str(assessment.path), "runbook": assessment.runbook.name, "high_risk_steps": high_risk, "semantic_obligation": "rollback_or_restore_readiness", "message": "high-risk steps lack a modeled rollback/restore/resume action"}


def _freshness_record(path: Path, as_of: date, max_age_days: int) -> dict[str, Any]:
    observed, source = _observed_date(path)
    age = max((as_of - observed).days, 0)
    return {"path": str(path), "observed_date": observed.isoformat(), "source": source, "age_days": age, "max_age_days": max_age_days, "stale": age > max_age_days}


def _observed_date(path: Path) -> tuple[date, str]:
    if path.suffix.lower() == ".md":
        text = path.read_text(encoding="utf-8")
        import re
        match = re.search(r"(?:Retrieval date|retrieved|Commit date observed)\s*:\s*`?(\d{4}-\d{2}-\d{2})", text, flags=re.I)
        if match:
            return date.fromisoformat(match.group(1)), "document_metadata"
    return datetime.fromtimestamp(path.stat().st_mtime).date(), "file_mtime"


def _owner_record(acc: _OwnerAccumulator, as_of: date) -> dict[str, Any]:
    blocking_prose = [finding for finding in acc.prose_findings if SEVERITY_RANK[finding.severity] >= SEVERITY_RANK["error"]]
    active_waivers = [waiver for waiver in acc.waivers if waiver["expiry"] and not waiver["expired"]]
    expired_waivers = [waiver for waiver in acc.waivers if waiver["expired"]]
    services = sorted({service for assessment in acc.runbooks for service in _services(assessment.runbook)})
    regions = sorted({region for assessment in acc.runbooks for region in _regions(assessment.runbook)})
    checked, failures = _aggregate_obligations([assessment.result for assessment in acc.runbooks])
    verified = sum(1 for assessment in acc.runbooks if assessment.result.safe)
    open_hazards = len(acc.parse_errors) + len(acc.semantic_findings) + len(blocking_prose) + len(acc.missing_rollback) + len(acc.stale_assumptions) + len(expired_waivers)
    advisory = len(acc.prose_findings) + len(active_waivers)
    status = "not_ready" if open_hazards else "advisory" if advisory else "ready"
    score = max(0, 100 - 25 * len(acc.parse_errors) - 20 * len(acc.semantic_findings) - 10 * len(blocking_prose) - 5 * len(acc.missing_rollback) - 5 * len(acc.stale_assumptions) - 10 * len(expired_waivers) - 2 * len(active_waivers))
    remediation = sorted(acc.remediation_history, key=lambda item: item.get("date", ""), reverse=True)
    return {
        "owner": acc.owner,
        "status": status,
        "score": score,
        "runbooks": len(acc.runbooks),
        "verified_runbooks": verified,
        "unsafe_runbooks": len(acc.runbooks) - verified,
        "parse_errors": len(acc.parse_errors),
        "open_hazards": open_hazards,
        "semantic_counterexamples": len(acc.semantic_findings),
        "prose_findings": len(acc.prose_findings),
        "blocking_prose_findings": len(blocking_prose),
        "missing_rollback_steps": len(acc.missing_rollback),
        "stale_assumptions": len(acc.stale_assumptions),
        "waiver_debt": len(active_waivers) + len(expired_waivers),
        "active_waivers": len(active_waivers),
        "expired_waivers": len(expired_waivers),
        "services": services,
        "regions": regions,
        "proof_obligations": {"checked": checked, "failures": failures},
        "top_hazards": _top_hazards(acc),
        "remediation_history": remediation[:10],
        "recent_remediation": _recent_remediation(remediation),
        "as_of": as_of.isoformat(),
    }


def _aggregate_obligations(results: list[CheckResult]) -> tuple[dict[str, int], dict[str, int]]:
    checked: dict[str, int] = {}
    failures: dict[str, int] = {}
    for result in results:
        for key, value in result.proof_obligations_checked.items():
            checked[key] = checked.get(key, 0) + value
        for key, value in result.proof_obligation_failures.items():
            failures[key] = failures.get(key, 0) + value
    return dict(sorted(checked.items())), dict(sorted(failures.items()))


def _top_hazards(acc: _OwnerAccumulator) -> list[dict[str, Any]]:
    hazards: list[dict[str, Any]] = []
    for error in acc.parse_errors:
        hazards.append({"kind": "parse", "path": error["path"], "rule": "parse_error", "message": error["message"]})
    for assessment, violation in acc.semantic_findings:
        hazards.append({"kind": "semantic", "path": str(assessment.path), "property": violation.property, "message": violation.message, "trace": list(violation.trace)})
    for finding in acc.prose_findings:
        hazards.append({"kind": "prose", "path": finding.path, "rule": finding.rule, "message": finding.message, "severity": finding.severity})
    for item in acc.missing_rollback:
        hazards.append({"kind": "coverage", "path": item["path"], "rule": item["semantic_obligation"], "message": item["message"]})
    for item in acc.stale_assumptions:
        hazards.append({"kind": "freshness", "path": item["path"], "rule": "stale_precondition", "message": f"age={item['age_days']} days exceeds {item['max_age_days']} days"})
    return hazards[:10]


def _recent_remediation(history: list[dict[str, Any]]) -> str:
    if not history:
        return "none recorded"
    item = history[0]
    return f"{item.get('date', '')} {item.get('status', '')}: {item.get('summary', '')}".strip()


def _summary(owners: list[dict[str, Any]], parse_errors: list[dict[str, Any]]) -> dict[str, Any]:
    status = "not_ready" if any(owner["status"] == "not_ready" for owner in owners) or parse_errors else "advisory" if any(owner["status"] == "advisory" for owner in owners) else "ready"
    return {
        "status": status,
        "owners": len(owners),
        "runbooks": sum(int(owner["runbooks"]) for owner in owners),
        "verified_runbooks": sum(int(owner["verified_runbooks"]) for owner in owners),
        "open_hazards": sum(int(owner["open_hazards"]) for owner in owners),
        "semantic_counterexamples": sum(int(owner["semantic_counterexamples"]) for owner in owners),
        "prose_findings": sum(int(owner["prose_findings"]) for owner in owners),
        "stale_assumptions": sum(int(owner["stale_assumptions"]) for owner in owners),
        "waiver_debt": sum(int(owner["waiver_debt"]) for owner in owners),
        "parse_errors": len(parse_errors),
    }
