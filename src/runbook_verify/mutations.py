from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .checker import Checker
from .parser import RunbookParseError, load_document, parse_runbook


@dataclass(frozen=True)
class MutationResult:
    operator: str
    description: str
    applied: bool
    safe: bool | None = None
    violations_by_property: dict[str, int] = field(default_factory=dict)
    annotation_warnings_by_property: dict[str, int] = field(default_factory=dict)
    parse_error: str | None = None


@dataclass(frozen=True)
class MutationReport:
    path: str
    mutations: list[MutationResult]
    note: str = "Synthetic mutants are benchmark seeds for reviewer calibration; they are not claims about the source runbook's live infrastructure."

    def to_json_dict(self) -> dict[str, Any]:
        return {"path": self.path, "note": self.note, "mutations": [mutation.__dict__ for mutation in self.mutations]}


MUTATION_OPERATORS = (
    "missing_preconditions",
    "reordered_steps",
    "stale_owners",
    "unsafe_retries",
    "insufficient_waits",
    "underprovisioned_replicas",
    "invalid_waivers",
)

HIGH_RISK_ACTIONS = {
    "replay_messages", "drain_dead_letter_queue", "drain_region", "drain_replica", "drain_load_balancer",
    "failover_traffic", "shift_traffic", "failover_database", "run_migration", "rollback_deployment",
    "flush_cache", "restore_bucket_snapshot", "freeze_bucket_writes", "update_dns_record", "revoke_credential",
}


def run_mutations(path: str | Path, operators: list[str] | None = None) -> MutationReport:
    selected = tuple(operators or MUTATION_OPERATORS)
    unknown = sorted(set(selected) - set(MUTATION_OPERATORS))
    if unknown:
        raise ValueError(f"unknown mutation operator(s): {', '.join(unknown)}")
    base = load_document(path)
    results: list[MutationResult] = []
    for operator in selected:
        mutated, description = _apply_mutation(base, operator)
        if mutated is None:
            results.append(MutationResult(operator, description, applied=False))
            continue
        results.append(_evaluate_mutation(mutated, operator, description))
    return MutationReport(str(path), results)


def render_mutations_json(report: MutationReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_mutations_markdown(report: MutationReport) -> str:
    data = report.to_json_dict()
    lines = [
        f"# Synthetic mutation report: {data['path']}",
        "",
        f"- Scope note: {data['note']}",
        "",
        "| Operator | Applied | Safe | Violations | Annotation warnings | Parse error / description |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in data["mutations"]:
        details = item.get("parse_error") or item.get("description") or ""
        lines.append("| `{operator}` | `{applied}` | `{safe}` | `{violations}` | `{warnings}` | {details} |".format(
            operator=item["operator"],
            applied=item["applied"],
            safe=item.get("safe"),
            violations=json.dumps(item.get("violations_by_property", {}), sort_keys=True),
            warnings=json.dumps(item.get("annotation_warnings_by_property", {}), sort_keys=True),
            details=str(details).replace("|", "\\|"),
        ))
    return "\n".join(lines) + "\n"


def _apply_mutation(base: dict[str, Any], operator: str) -> tuple[dict[str, Any] | None, str]:
    doc = copy.deepcopy({k: v for k, v in base.items() if not str(k).startswith("__")})
    steps = doc.get("steps") if isinstance(doc.get("steps"), list) else []
    metadata = doc.setdefault("metadata", {}) if isinstance(doc.setdefault("metadata", {}), dict) else {}
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    if operator == "missing_preconditions":
        for step in steps:
            if isinstance(step, dict) and step.get("requires"):
                step["requires"] = []
                return doc, "Removed declared preconditions from one guarded step."
        return None, "No step with declared preconditions was available."
    if operator == "reordered_steps":
        for step in steps:
            if isinstance(step, dict) and step.get("after"):
                step["after"] = []
                doc["allow_reordering"] = True
                return doc, "Removed an ordering edge so the checker may schedule a dependent step early."
        return None, "No step with an ordering dependency was available."
    if operator == "stale_owners":
        metadata["owners"] = ["TODO-owner"]
        metadata["owner"] = "TODO-owner"
        return doc, "Replaced owner metadata with a stale placeholder for audit/readiness calibration."
    if operator == "unsafe_retries":
        for step in steps:
            if isinstance(step, dict) and step.get("action") in HIGH_RISK_ACTIONS:
                annotations = step.setdefault("effect_annotations", {})
                annotations.update({
                    "effect_types": ["irreversible_state_change"],
                    "idempotency": "non_idempotent",
                    "reversibility": "irreversible",
                    "retry_safety": "safe",
                    "blast_radius": "synthetic mutation",
                    "expected_user_impact": "operator review required",
                })
                return doc, "Marked a destructive/high-risk action retry-safe despite non-idempotent irreversible effects."
        return None, "No high-risk action was available."
    if operator == "insufficient_waits":
        for step in steps:
            if isinstance(step, dict) and step.get("action") == "wait" and isinstance(step.get("params"), dict):
                step["params"]["minutes"] = 0
                return doc, "Reduced a wait interval to zero to exercise duration validation or temporal guards."
        return None, "No wait step was available."
    if operator == "underprovisioned_replicas":
        services = system.get("services") if isinstance(system, dict) else {}
        if isinstance(services, dict):
            for service in services.values():
                if isinstance(service, dict):
                    replicas = service.get("replicas") if isinstance(service.get("replicas"), list) else []
                    service["min_available"] = len(replicas) + 1
                    service["allow_unachievable_min_available"] = True
                    return doc, "Raised min_available above declared replica count while explicitly modeling the weak assumption."
        return None, "No service inventory was available."
    if operator == "invalid_waivers":
        waivers = metadata.setdefault("waivers", [])
        if isinstance(waivers, list):
            waivers.append({
                "id": "mutation-expired-waiver",
                "owner": "TODO-owner",
                "expiry": "2000-01-01",
                "scope": "*",
                "rationale": "Synthetic expired waiver mutation.",
                "invariant": "effect_annotation_required",
                "benchmark_visibility": "visible",
            })
            return doc, "Added an expired owner-placeholder waiver that must remain visible rather than silently suppressing findings."
        return None, "Metadata waivers field was not a list."
    return None, "Unknown operator."


def _evaluate_mutation(doc: dict[str, Any], operator: str, description: str) -> MutationResult:
    try:
        runbook = parse_runbook(doc)
        result = Checker(runbook).check()
    except RunbookParseError as exc:
        return MutationResult(operator, description, applied=True, parse_error=str(exc))
    return MutationResult(
        operator=operator,
        description=description,
        applied=True,
        safe=result.safe,
        violations_by_property=_count_by_property(result.violations),
        annotation_warnings_by_property=_count_by_property(result.annotation_warnings),
    )


def _count_by_property(items: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        prop = str(getattr(item, "property", "unknown"))
        counts[prop] = counts.get(prop, 0) + 1
    return dict(sorted(counts.items()))
