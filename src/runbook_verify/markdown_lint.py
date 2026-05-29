from __future__ import annotations

import json
import re
import shlex
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .parser import RunbookParseError, load_document


@dataclass(frozen=True)
class MarkdownFinding:
    rule: str
    severity: str
    path: str
    line: int
    excerpt: str
    message: str
    recommendation: str
    semantic_obligation: str


@dataclass(frozen=True)
class PhraseRule:
    rule: str
    severity: str
    pattern: re.Pattern[str]
    required_action: str | None
    required_condition_kinds: tuple[str, ...]
    semantic_obligation: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class ProseSuppression:
    line: int
    rule: str
    owner: str
    expires: str
    reason: str
    link: str


RULES: tuple[PhraseRule, ...] = (
    PhraseRule(
        "alert-suppression-needs-expiry",
        "error",
        re.compile(r"\b(silence|suppress|disable|mute)\b.{0,40}\b(alert|alarm|notification)s?\b", re.I),
        "suppress_alert",
        ("alert_suppressed_for_at_most",),
        "bounded_alert_suppression",
        "Prose mentions suppressing alerting without an executable bounded-expiry requirement.",
        "Model the alert action with suppress_alert.expires_after_minutes and an alert_suppressed_for_at_most effect.",
    ),
    PhraseRule(
        "failover-needs-health-and-quorum",
        "error",
        re.compile(r"\b(force\s+)?failover\b", re.I),
        "failover_database",
        ("region_healthy", "database_quorum_confirmed"),
        "no_failover_to_unhealthy_region; quorum_before_data_loss_action",
        "Prose mentions failover without executable health/quorum preconditions.",
        "Require region_healthy for the target and database_quorum_confirmed before failover_database.",
    ),
    PhraseRule(
        "drain-needs-capacity-precondition",
        "error",
        re.compile(r"\b(drain|evacuat(e|ion))\b.{0,60}\b(node|region|replica|pod|cluster)s?\b", re.I),
        "drain_region",
        ("service_available_at_least",),
        "service_min_available",
        "Prose mentions draining capacity without an executable availability precondition.",
        "Add service_available_at_least requires/effects and order scale-up before draining.",
    ),
    PhraseRule(
        "destructive-delete-needs-targeting",
        "warning",
        re.compile(r"\b(delete|remove|forget)\b.{0,80}\b(index|file|bucket|ring|member|instance|tenant)s?\b", re.I),
        None,
        ("service_available_at_least",),
        "blast_radius_limited_or_explicit_limitation",
        "Prose describes destructive removal/forgetting without executable blast-radius checks.",
        "Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions.",
    ),
    PhraseRule(
        "data-deletion-needs-restore-precondition",
        "error",
        re.compile(r"\b(delete|drop|truncate|purge|wipe|destroy)\b.{0,80}\b(data|database|table|bucket|object|index|tenant)s?\b", re.I),
        None,
        ("service_available_at_least",),
        "restore_path_and_blast_radius_limited",
        "Prose describes data deletion without executable restore/blast-radius preconditions.",
        "Require a targeted scope, backup/restore validation, and capacity guard before destructive data operations.",
    ),
    PhraseRule(
        "manual-sql-needs-migration-model",
        "error",
        re.compile(r"\b(manual(?:ly)?\s+)?(run|execute|apply)\b.{0,50}\b(sql|query|ddl|dml|mysql|postgres)\b|\b(update|delete|insert)\b.{0,40}\bwhere\b", re.I),
        "run_migration",
        ("database_quorum_confirmed",),
        "no_rollback_during_incompatible_migration; database_quorum_confirmed",
        "Prose mentions manual SQL without an executable migration/quorum model.",
        "Represent SQL changes as run_migration/finish_migration steps with quorum and rollback-compatibility obligations.",
    ),
    PhraseRule(
        "backfill-needs-queue-capacity",
        "warning",
        re.compile(r"\b(backfill|replay|reprocess|bulk\s+load)\b", re.I),
        None,
        ("queue_depth_at_most", "queue_has_consumers", "queue_replay_deduplicated"),
        "queue_backlog_requires_consumers; no_replay_without_dedupe; no_duplicate_processing_risk",
        "Prose mentions backfill/replay work without executable queue/backlog capacity guards.",
        "Add queue_depth_at_most, queue_has_consumers, and deduplicated replay preconditions, or document an explicit limitation.",
    ),
    PhraseRule(
        "cache-flush-needs-warmup-capacity",
        "warning",
        re.compile(r"\b(flush|purge|clear|invalidate)\b.{0,80}\b(cache|redis|memcached|key)s?\b|\b(cache|redis|memcached)\b.{0,80}\b(flush|purge|clear|invalidate)\b", re.I),
        "flush_cache",
        ("cache_writes_frozen", "cache_capacity_at_least", "cache_warm"),
        "cache_flush_requires_write_freeze; cache_warmup_before_traffic; cache_warmup_within_capacity",
        "Prose mentions cache flush/invalidation without executable write-freeze, warmup, and capacity obligations.",
        "Model flush_cache with cache_writes_frozen and cache_capacity_at_least preconditions plus warm_cache/cache_warm before resuming writes or traffic.",
    ),
    PhraseRule(
        "credential-handling-needs-rotation-model",
        "responsible-disclosure",
        re.compile(r"\b(revoke|rotate|delete|reset|share|copy)\b.{0,60}\b(token|secret|credential|key|password|cert(?:ificate)?)s?\b", re.I),
        None,
        (),
        "credential_revocation_or_rotation_unmodeled",
        "Prose handles credentials, but this DSL has no executable credential state yet.",
        "Treat this as an explicit limitation or add a credential rotation model before using it as a blocking safety claim.",
    ),
    PhraseRule(
        "customer-notification-gap",
        "warning",
        re.compile(r"\b(customer|tenant|user|client)s?\b.{0,80}\b(impact|downtime|data loss|degradation|notify|notification|status page)\b|\b(status page|notify customers|notify tenants)\b", re.I),
        None,
        (),
        "customer_visible_impact_requires_operator_acknowledgement",
        "Prose mentions customer-visible impact without an executable notification or acknowledgement obligation.",
        "Add a modeled precondition/effect for customer notification when the operation can be user-visible, or state why it is audit-only.",
    ),
    PhraseRule(
        "rollback-ambiguity-needs-explicit-action",
        "error",
        re.compile(r"\b(roll\s*back|rollback|revert|undo)\b", re.I),
        "rollback_deployment",
        ("service_deployment_is",),
        "no_rollback_during_incompatible_migration",
        "Prose mentions rollback/revert without an executable rollback action and postcondition.",
        "Model rollback_deployment with service_deployment_is effects and database migration compatibility guards.",
    ),
    PhraseRule(
        "unmodeled-escalation-path",
        "audit-only",
        re.compile(r"\b(escalate|page|contact|call)\b.{0,80}\b(on[- ]call|sre|owner|security|incident commander|team)\b", re.I),
        None,
        (),
        "ownership_and_escalation_out_of_scope",
        "Prose includes an escalation path that is not modeled by the executable DSL.",
        "Keep the escalation text, but treat it as audit evidence rather than a verified semantic action.",
    ),
)

SEVERITY_RANK = {
    "info": 0,
    "audit-only": 1,
    "warning": 2,
    "error": 3,
    "responsible-disclosure": 4,
}

SUPPRESSION_RE = re.compile(r"<!--\s*frv-suppress\s+(.*?)\s*-->", re.I)
SUPPRESSION_REQUIRED_FIELDS = ("rule", "owner", "expires", "reason", "link")
SUPPRESSION_LINK_PREFIXES = ("invariant:", "waiver:", "limitation:")


def lint_markdown_file(path: str | Path) -> list[MarkdownFinding]:
    p = Path(path)
    return lint_markdown_text(p.read_text(encoding="utf-8"), p)


def lint_markdown_tree(path: str | Path) -> list[MarkdownFinding]:
    root = Path(path)
    files = [root] if root.is_file() else sorted(root.rglob("*.md"))
    findings: list[MarkdownFinding] = []
    for file in files:
        findings.extend(lint_markdown_file(file))
    return findings


def lint_markdown_text(text: str, path: str | Path = "<memory>") -> list[MarkdownFinding]:
    doc = _load_doc_if_present(text, Path(path))
    actions = _actions(doc)
    condition_kinds = _condition_kinds(doc)
    findings: list[MarkdownFinding] = []
    pending_suppressions: list[ProseSuppression] = []
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line_suppressions, suppression_findings = _parse_suppressions(line, line_no, str(path))
        findings.extend(suppression_findings)
        line_without_suppressions = SUPPRESSION_RE.sub("", line)
        if line_suppressions and not line_without_suppressions.strip():
            pending_suppressions.extend(line_suppressions)
            continue
        active_suppressions = [*pending_suppressions, *line_suppressions]
        pending_suppressions = []
        for rule in RULES:
            if not rule.pattern.search(line_without_suppressions):
                continue
            missing_action = rule.required_action is not None and rule.required_action not in actions
            missing_conditions = [kind for kind in rule.required_condition_kinds if kind not in condition_kinds]
            always_emit_unmodeled_limitation = rule.required_action is None and not rule.required_condition_kinds
            if missing_action or missing_conditions or always_emit_unmodeled_limitation:
                detail = rule.message
                if missing_action:
                    detail += f" Missing action: {rule.required_action}."
                if missing_conditions:
                    detail += f" Missing condition(s): {', '.join(missing_conditions)}."
                finding = MarkdownFinding(
                    rule=rule.rule,
                    severity=rule.severity,
                    path=str(path),
                    line=line_no,
                    excerpt=line_without_suppressions.strip(),
                    message=detail,
                    recommendation=rule.recommendation,
                    semantic_obligation=rule.semantic_obligation,
                )
                suppression = _matching_suppression(active_suppressions, finding)
                if suppression is not None:
                    findings.append(_applied_suppression_finding(suppression, finding, str(path)))
                    continue
                findings.append(finding)
    return _rank(_dedupe(findings))


def render_lint_json(findings: list[MarkdownFinding]) -> str:
    return json.dumps([asdict(finding) for finding in findings], indent=2, sort_keys=True) + "\n"


def render_lint_markdown(findings: list[MarkdownFinding]) -> str:
    lines = ["# Markdown runbook lint report", "", f"- Findings: {len(findings)}", ""]
    if findings:
        lines.extend(["| Rule | Severity | Obligation | Location | Excerpt | Recommendation |", "| --- | --- | --- | --- | --- | --- |"])
        for finding in findings:
            location = f"{finding.path}:{finding.line}"
            lines.append(f"| {finding.rule} | {finding.severity} | `{finding.semantic_obligation}` | `{location}` | {finding.excerpt.replace('|', '\\|')} | {finding.recommendation.replace('|', '\\|')} |")
    return "\n".join(lines) + "\n"


def has_findings_at_or_above(findings: list[MarkdownFinding], threshold: str) -> bool:
    if threshold == "none":
        return False
    minimum = SEVERITY_RANK[threshold]
    return any(SEVERITY_RANK[finding.severity] >= minimum for finding in findings)


def _load_doc_if_present(text: str, path: Path) -> dict[str, Any] | None:
    if "```runbook-json" not in text.lower() and "```json" not in text.lower():
        return None
    try:
        return load_document(path)
    except (RunbookParseError, OSError):
        return None


def _actions(doc: dict[str, Any] | None) -> set[str]:
    if not doc:
        return set()
    return {str(step.get("action")) for step in doc.get("steps", []) if isinstance(step, dict)}


def _condition_kinds(doc: dict[str, Any] | None) -> set[str]:
    if not doc:
        return set()
    kinds: set[str] = set()
    for step in doc.get("steps", []):
        if not isinstance(step, dict):
            continue
        for section in ("requires", "effects"):
            for condition in step.get(section, []):
                if isinstance(condition, dict) and "kind" in condition:
                    kinds.add(str(condition["kind"]))
    return kinds


def _parse_suppressions(line: str, line_no: int, path: str) -> tuple[list[ProseSuppression], list[MarkdownFinding]]:
    suppressions: list[ProseSuppression] = []
    findings: list[MarkdownFinding] = []
    for match in SUPPRESSION_RE.finditer(line):
        raw = match.group(1).strip()
        fields, error = _parse_suppression_fields(raw)
        if error:
            findings.append(_invalid_suppression_finding(path, line_no, line.strip(), error))
            continue
        problems = _validate_suppression_fields(fields)
        if problems:
            findings.append(_invalid_suppression_finding(path, line_no, line.strip(), "; ".join(problems)))
            continue
        suppressions.append(ProseSuppression(
            line=line_no,
            rule=fields["rule"],
            owner=fields["owner"],
            expires=fields["expires"],
            reason=fields["reason"],
            link=fields["link"],
        ))
    return suppressions, findings


def _parse_suppression_fields(raw: str) -> tuple[dict[str, str], str | None]:
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        return {}, f"cannot parse suppression metadata: {exc}"
    fields: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            return {}, f"suppression token {part!r} must be key=value"
        key, value = part.split("=", 1)
        if not key or not value:
            return {}, f"suppression token {part!r} must have non-empty key and value"
        fields[key.strip().lower()] = value.strip()
    return fields, None


def _validate_suppression_fields(fields: dict[str, str]) -> list[str]:
    problems: list[str] = []
    missing = [field for field in SUPPRESSION_REQUIRED_FIELDS if not fields.get(field)]
    if missing:
        problems.append(f"missing required field(s): {', '.join(missing)}")
    if fields.get("rule") and fields["rule"] != "*" and fields["rule"] not in {rule.rule for rule in RULES}:
        problems.append(f"unknown suppressed rule: {fields['rule']}")
    expires = fields.get("expires")
    if expires:
        try:
            date.fromisoformat(expires)
        except ValueError:
            problems.append("expires must be an ISO date YYYY-MM-DD")
    link = fields.get("link")
    if link and not any(link.startswith(prefix) and len(link) > len(prefix) for prefix in SUPPRESSION_LINK_PREFIXES):
        problems.append("link must start with invariant:, waiver:, or limitation: and name a concrete obligation")
    unknown = sorted(set(fields) - set(SUPPRESSION_REQUIRED_FIELDS))
    if unknown:
        problems.append(f"unknown field(s): {', '.join(unknown)}")
    return problems


def _matching_suppression(suppressions: list[ProseSuppression], finding: MarkdownFinding) -> ProseSuppression | None:
    for suppression in suppressions:
        if suppression.rule in {"*", finding.rule}:
            return suppression
    return None


def _applied_suppression_finding(suppression: ProseSuppression, suppressed: MarkdownFinding, path: str) -> MarkdownFinding:
    return MarkdownFinding(
        rule="prose-suppression-applied",
        severity="audit-only",
        path=path,
        line=suppression.line,
        excerpt=f"frv-suppress rule={suppression.rule}",
        message=(
            f"Suppressed {suppressed.rule} at line {suppressed.line} with owner={suppression.owner}, "
            f"expires={suppression.expires}, reason={suppression.reason}, link={suppression.link}."
        ),
        recommendation="Review suppression owner, expiry, reason, and invariant/waiver/limitation link during runbook review.",
        semantic_obligation=suppression.link,
    )


def _invalid_suppression_finding(path: str, line_no: int, excerpt: str, problem: str) -> MarkdownFinding:
    return MarkdownFinding(
        rule="invalid-prose-suppression",
        severity="error",
        path=path,
        line=line_no,
        excerpt=excerpt,
        message=f"Invalid frv-suppress directive: {problem}.",
        recommendation="Use <!-- frv-suppress rule=<rule|*> owner=<owner> expires=YYYY-MM-DD reason=\"...\" link=invariant:<id>|waiver:<id>|limitation:<id> -->.",
        semantic_obligation="auditable_prose_suppression_waiver_contract",
    )


def _dedupe(findings: list[MarkdownFinding]) -> list[MarkdownFinding]:
    seen: set[tuple[str, str, int]] = set()
    unique: list[MarkdownFinding] = []
    for finding in findings:
        key = (finding.rule, finding.path, finding.line)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique


def _rank(findings: list[MarkdownFinding]) -> list[MarkdownFinding]:
    return sorted(findings, key=lambda f: (-SEVERITY_RANK[f.severity], f.path, f.line, f.rule))
