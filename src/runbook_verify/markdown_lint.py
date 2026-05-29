from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
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


@dataclass(frozen=True)
class PhraseRule:
    rule: str
    pattern: re.Pattern[str]
    required_action: str | None
    required_condition_kinds: tuple[str, ...]
    message: str
    recommendation: str


RULES: tuple[PhraseRule, ...] = (
    PhraseRule(
        "alert-suppression-needs-expiry",
        re.compile(r"\b(silence|suppress|disable|mute)\b.{0,40}\b(alert|alarm|notification)s?\b", re.I),
        "suppress_alert",
        ("alert_suppressed_for_at_most",),
        "Prose mentions suppressing alerting without an executable bounded-expiry requirement.",
        "Model the alert action with suppress_alert.expires_after_minutes and an alert_suppressed_for_at_most effect.",
    ),
    PhraseRule(
        "failover-needs-health-and-quorum",
        re.compile(r"\b(force\s+)?failover\b", re.I),
        "failover_database",
        ("region_healthy", "database_quorum_confirmed"),
        "Prose mentions failover without executable health/quorum preconditions.",
        "Require region_healthy for the target and database_quorum_confirmed before failover_database.",
    ),
    PhraseRule(
        "drain-needs-capacity-precondition",
        re.compile(r"\b(drain|evacuat(e|ion))\b.{0,60}\b(node|region|replica|pod|cluster)s?\b", re.I),
        "drain_region",
        ("service_available_at_least",),
        "Prose mentions draining capacity without an executable availability precondition.",
        "Add service_available_at_least requires/effects and order scale-up before draining.",
    ),
    PhraseRule(
        "destructive-delete-needs-targeting",
        re.compile(r"\b(delete|remove|forget)\b.{0,80}\b(index|file|bucket|ring|member|instance|tenant)s?\b", re.I),
        None,
        ("service_available_at_least",),
        "Prose describes destructive removal/forgetting without executable blast-radius checks.",
        "Model the removal as an action guarded by targeted scope, capacity, and rollback/restore preconditions.",
    ),
)


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
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for rule in RULES:
            if not rule.pattern.search(line):
                continue
            missing_action = rule.required_action is not None and rule.required_action not in actions
            missing_conditions = [kind for kind in rule.required_condition_kinds if kind not in condition_kinds]
            if missing_action or missing_conditions:
                detail = rule.message
                if missing_action:
                    detail += f" Missing action: {rule.required_action}."
                if missing_conditions:
                    detail += f" Missing condition(s): {', '.join(missing_conditions)}."
                findings.append(MarkdownFinding(
                    rule=rule.rule,
                    severity="warning",
                    path=str(path),
                    line=line_no,
                    excerpt=line.strip(),
                    message=detail,
                    recommendation=rule.recommendation,
                ))
    return _dedupe(findings)


def render_lint_json(findings: list[MarkdownFinding]) -> str:
    return json.dumps([asdict(finding) for finding in findings], indent=2, sort_keys=True) + "\n"


def render_lint_markdown(findings: list[MarkdownFinding]) -> str:
    lines = ["# Markdown runbook lint report", "", f"- Findings: {len(findings)}", ""]
    if findings:
        lines.extend(["| Rule | Severity | Location | Excerpt | Recommendation |", "| --- | --- | --- | --- | --- |"])
        for finding in findings:
            location = f"{finding.path}:{finding.line}"
            lines.append(f"| {finding.rule} | {finding.severity} | `{location}` | {finding.excerpt.replace('|', '\\|')} | {finding.recommendation.replace('|', '\\|')} |")
    return "\n".join(lines) + "\n"


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


def _dedupe(findings: list[MarkdownFinding]) -> list[MarkdownFinding]:
    seen: set[tuple[str, str, int]] = set()
    unique: list[MarkdownFinding] = []
    for finding in findings:
        key = (finding.rule, finding.path, finding.line)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique
