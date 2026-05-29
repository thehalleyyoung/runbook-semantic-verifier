from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .markdown_lint import RULES, SEVERITY_RANK, MarkdownFinding, lint_markdown_file


@dataclass(frozen=True)
class ScanOptions:
    min_score: int = 1
    include_low_priority: bool = False


@dataclass
class ScanCandidate:
    path: str
    score: int
    priority: str
    has_executable_model: bool
    line_count: int
    matched_rules: dict[str, int] = field(default_factory=dict)
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    findings_by_obligation: dict[str, int] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class RepositoryScanError(ValueError):
    pass


_EFFECT_WEIGHTS = {
    "responsible-disclosure": 9,
    "error": 8,
    "warning": 5,
    "audit-only": 2,
    "info": 1,
}

_FINDING_WEIGHTS = {
    "responsible-disclosure": 14,
    "error": 12,
    "warning": 7,
    "audit-only": 3,
    "info": 1,
}

def build_repository_scan(path: str | Path, options: ScanOptions | None = None) -> dict[str, Any]:
    options = options or ScanOptions()
    root = Path(path)
    if not root.exists():
        raise RepositoryScanError(f"scan path does not exist: {root}")
    candidates: list[ScanCandidate] = []
    for file in _markdown_files(root):
        text = file.read_text(encoding="utf-8")
        matched_rules = _dangerous_effect_matches(text)
        findings = lint_markdown_file(file)
        candidate = _candidate(file, text, matched_rules, findings)
        if options.include_low_priority or candidate.score >= options.min_score:
            candidates.append(candidate)
    candidates = sorted(candidates, key=lambda item: (-item.score, item.path))
    summary = _summary(candidates)
    return {
        "path": str(root),
        "summary": summary,
        "candidates": [_candidate_dict(item) for item in candidates],
        "ranking_semantics": {
            "score": "sum of dangerous-effect vocabulary matches, uncovered prose findings, and a no-executable-model multiplier",
            "priority": "critical >= 40, high >= 24, medium >= 10, low >= 1",
            "formal_connection": "Each rule maps prose evidence to a semantic obligation already used by lint/audit/check workflows; high scores identify documents where Markdown prose should be refined into executable DSL models first.",
        },
    }


def render_scan_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_scan_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# Repository runbook scan: {report['path']}",
        "",
        f"- Markdown files ranked: {summary['candidates']}",
        f"- Files with executable models: {summary['with_executable_model']}",
        f"- Files needing first executable model: {summary['without_executable_model']}",
        f"- Highest score: {summary['highest_score']}",
        f"- Priority counts: `{json.dumps(summary['priority_counts'], sort_keys=True)}`",
        f"- Dangerous-effect rules: `{json.dumps(summary['matched_rules'], sort_keys=True)}`",
        "",
        "## Ranking semantics",
        "",
        f"{report['ranking_semantics']['formal_connection']}",
        "",
    ]
    candidates = report["candidates"]
    if not candidates:
        lines.append("No Markdown runbook-like files matched the dangerous-effect vocabulary threshold.")
        return "\n".join(lines) + "\n"
    lines.extend([
        "| Priority | Score | Executable model | Path | Matched dangerous-effect rules | Uncovered obligations | Recommendation |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ])
    for item in candidates:
        rules = json.dumps(item["matched_rules"], sort_keys=True)
        obligations = json.dumps(item["findings_by_obligation"], sort_keys=True)
        recommendations = " ".join(item["recommendations"]).replace("|", "\\|")
        lines.append(f"| {item['priority']} | {item['score']} | `{item['has_executable_model']}` | `{item['path']}` | `{rules}` | `{obligations}` | {recommendations} |")
    return "\n".join(lines) + "\n"


def _markdown_files(root: Path) -> list[Path]:
    files = [root] if root.is_file() else sorted(root.rglob("*.md"))
    return [file for file in files if file.is_file() and file.suffix.lower() == ".md"]


def _dangerous_effect_matches(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for rule in RULES:
            if rule.pattern.search(line):
                counts[rule.rule] = counts.get(rule.rule, 0) + 1
    return dict(sorted(counts.items()))


def _candidate(path: Path, text: str, matched_rules: dict[str, int], findings: list[MarkdownFinding]) -> ScanCandidate:
    has_model = _has_executable_model(text)
    severity_counts = _count_by((finding.severity for finding in findings), SEVERITY_RANK)
    obligation_counts = _count_by((finding.semantic_obligation for finding in findings), None)
    effect_score = 0
    rule_severity = {rule.rule: rule.severity for rule in RULES}
    for rule, count in matched_rules.items():
        effect_score += _EFFECT_WEIGHTS[rule_severity[rule]] * count
    finding_score = sum(_FINDING_WEIGHTS[finding.severity] for finding in findings)
    no_model_multiplier = 10 if matched_rules and not has_model else 0
    score = effect_score + finding_score + no_model_multiplier
    recommendations = _recommendations(has_model, matched_rules, findings)
    return ScanCandidate(
        path=str(path),
        score=score,
        priority=_priority(score),
        has_executable_model=has_model,
        line_count=len(text.splitlines()),
        matched_rules=matched_rules,
        findings_by_severity=severity_counts,
        findings_by_obligation=obligation_counts,
        recommendations=recommendations,
    )


def _has_executable_model(text: str) -> bool:
    lower = text.lower()
    return "```runbook-json" in lower or "```json" in lower


def _count_by(values: Any, known_order: dict[str, int] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    if known_order is None:
        return dict(sorted(counts.items()))
    return dict(sorted(counts.items(), key=lambda item: (-known_order[item[0]], item[0])))


def _recommendations(has_model: bool, matched_rules: dict[str, int], findings: list[MarkdownFinding]) -> list[str]:
    recommendations: list[str] = []
    if matched_rules and not has_model:
        recommendations.append("Add a fenced runbook-json block before relying on this Markdown as a verified procedure.")
    if findings:
        obligations = sorted({finding.semantic_obligation for finding in findings})
        recommendations.append("Model or explicitly limit uncovered semantic obligations: " + ", ".join(obligations[:4]) + ("." if len(obligations) <= 4 else ", ..."))
    if matched_rules and has_model:
        recommendations.append("Review whether prose dangerous-effect matches refine to the existing executable model and coverage reports.")
    if not recommendations:
        recommendations.append("No model-first action recommended by the current dangerous-effect vocabulary.")
    return recommendations


def _priority(score: int) -> str:
    if score >= 40:
        return "critical"
    if score >= 24:
        return "high"
    if score >= 10:
        return "medium"
    if score >= 1:
        return "low"
    return "none"


def _summary(candidates: list[ScanCandidate]) -> dict[str, Any]:
    priority_counts = _count_by((item.priority for item in candidates), {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0})
    matched: dict[str, int] = {}
    for item in candidates:
        for rule, count in item.matched_rules.items():
            matched[rule] = matched.get(rule, 0) + count
    return {
        "candidates": len(candidates),
        "with_executable_model": sum(1 for item in candidates if item.has_executable_model),
        "without_executable_model": sum(1 for item in candidates if not item.has_executable_model),
        "highest_score": max((item.score for item in candidates), default=0),
        "priority_counts": priority_counts,
        "matched_rules": dict(sorted(matched.items())),
    }


def _candidate_dict(candidate: ScanCandidate) -> dict[str, Any]:
    return {
        "path": candidate.path,
        "score": candidate.score,
        "priority": candidate.priority,
        "has_executable_model": candidate.has_executable_model,
        "line_count": candidate.line_count,
        "matched_rules": candidate.matched_rules,
        "findings_by_severity": candidate.findings_by_severity,
        "findings_by_obligation": candidate.findings_by_obligation,
        "recommendations": candidate.recommendations,
    }
