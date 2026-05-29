from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .markdown_lint import MarkdownFinding, SEVERITY_RANK, lint_markdown_tree


HIGH_RISK_RULES = {
    "failover-needs-health-and-quorum": "traffic_or_data_failover_guard",
    "drain-needs-capacity-precondition": "traffic_capacity_guard",
    "destructive-delete-needs-targeting": "unsafe_deletion_guard",
    "data-deletion-needs-restore-precondition": "data_restoration_guard",
    "manual-sql-needs-migration-model": "data_restoration_guard",
    "cache-flush-needs-warmup-capacity": "traffic_or_cache_capacity_guard",
    "credential-handling-needs-rotation-model": "credential_owner_waiver_guard",
    "data-restore-needs-rpo-rto-guard": "data_restoration_guard",
}

OWNER_APPROVED_WAIVER_RULE = "prose-suppression-applied"


@dataclass(frozen=True)
class CIGateFinding:
    id: str
    status: str
    category: str
    rule: str
    severity: str
    path: str
    line: int
    excerpt: str
    message: str
    recommendation: str
    semantic_obligation: str
    baseline_state: str
    waiver: dict[str, str] | None


@dataclass(frozen=True)
class CIGateReport:
    target: str
    baseline: str | None
    profile: dict[str, str] | None
    pass_: bool
    summary: dict[str, Any]
    findings: tuple[CIGateFinding, ...]


def build_ci_gate_report(target: str | Path, baseline: str | Path | None = None, profile: dict[str, str] | None = None) -> CIGateReport:
    target_path = Path(target)
    baseline_path = Path(baseline) if baseline is not None else None
    target_findings = lint_markdown_tree(target_path)
    baseline_fingerprints = _baseline_fingerprints(baseline_path)
    gate_findings = _gate_findings(target_findings, baseline_fingerprints)
    blockers = [finding for finding in gate_findings if finding.status == "block"]
    waived = [finding for finding in gate_findings if finding.status == "waived"]
    existing = [finding for finding in gate_findings if finding.status == "existing"]
    summary = {
        "blocking_findings": len(blockers),
        "waived_findings": len(waived),
        "existing_findings": len(existing),
        "new_high_risk_findings": sum(1 for finding in gate_findings if finding.baseline_state == "new"),
        "high_risk_rules": sorted({finding.rule for finding in gate_findings}),
        "categories": _count_by_category(gate_findings),
    }
    return CIGateReport(
        target=str(target_path),
        baseline=str(baseline_path) if baseline_path is not None else None,
        profile=profile,
        pass_=not blockers,
        summary=summary,
        findings=tuple(gate_findings),
    )


def render_ci_gate_json(report: CIGateReport) -> str:
    data = {
        "target": report.target,
        "baseline": report.baseline,
        "profile": report.profile,
        "pass": report.pass_,
        "summary": report.summary,
        "findings": [asdict(finding) for finding in report.findings],
    }
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def render_ci_gate_markdown(report: CIGateReport) -> str:
    status = "PASS" if report.pass_ else "FAIL"
    lines = [
        f"# CI gate report: {report.target}",
        "",
        f"- Profile: `{report.profile['name']}`" if report.profile else "- Profile: `none`",
        f"- Status: **{status}**",
        f"- Baseline: `{report.baseline or 'none; all high-risk findings are treated as new'}`",
        f"- Blocking findings: {report.summary['blocking_findings']}",
        f"- Owner-approved waived findings: {report.summary['waived_findings']}",
        f"- Existing baseline findings: {report.summary['existing_findings']}",
        f"- Categories: `{json.dumps(report.summary['categories'], sort_keys=True)}`",
        "",
    ]
    if report.findings:
        lines.extend([
            "| ID | Status | Baseline | Category | Severity | Rule | Location | Obligation | Message | Recommendation | Waiver |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for finding in report.findings:
            location = f"{finding.path}:{finding.line}"
            waiver = ""
            if finding.waiver:
                waiver = "; ".join(f"{key}={value}" for key, value in finding.waiver.items())
            lines.append(
                "| {id} | {status} | {baseline} | {category} | {severity} | {rule} | `{location}` | `{obligation}` | {message} | {recommendation} | {waiver} |".format(
                    id=finding.id,
                    status=finding.status,
                    baseline=finding.baseline_state,
                    category=finding.category,
                    severity=finding.severity,
                    rule=finding.rule,
                    location=location,
                    obligation=finding.semantic_obligation,
                    message=_escape_md(finding.message),
                    recommendation=_escape_md(finding.recommendation),
                    waiver=_escape_md(waiver),
                )
            )
    else:
        lines.append("No high-risk Markdown findings matched the gate policy.")
    return "\n".join(lines) + "\n"


def _baseline_fingerprints(baseline_path: Path | None) -> set[str]:
    if baseline_path is None:
        return set()
    return {_fingerprint(finding) for finding in lint_markdown_tree(baseline_path) if finding.rule in HIGH_RISK_RULES}


def _gate_findings(findings: list[MarkdownFinding], baseline_fingerprints: set[str]) -> list[CIGateFinding]:
    waiver_by_line = _waiver_by_line(findings)
    rows: list[CIGateFinding] = []
    for finding in findings:
        if finding.rule == OWNER_APPROVED_WAIVER_RULE:
            metadata = _parse_applied_suppression(finding.message)
            suppressed_rule = metadata.pop("suppressed_rule", "")
            if suppressed_rule in HIGH_RISK_RULES:
                suppressed_line = int(metadata.pop("suppressed_line", finding.line))
                rows.append(CIGateFinding(
                    id=f"ci-gate-{len(rows) + 1:03d}",
                    status="waived",
                    category=HIGH_RISK_RULES[suppressed_rule],
                    rule=suppressed_rule,
                    severity=finding.severity,
                    path=finding.path,
                    line=suppressed_line,
                    excerpt=finding.excerpt,
                    message=f"Owner-approved waiver suppresses high-risk rule {suppressed_rule}. {finding.message}",
                    recommendation=finding.recommendation,
                    semantic_obligation=finding.semantic_obligation,
                    baseline_state="new" if baseline_fingerprints == set() else "waived",
                    waiver=metadata,
                ))
            continue
        if finding.rule not in HIGH_RISK_RULES:
            continue
        baseline_state = "existing" if _fingerprint(finding) in baseline_fingerprints else "new"
        waiver = waiver_by_line.get((finding.path, finding.line))
        if waiver is not None:
            status = "waived"
        elif baseline_state == "existing":
            status = "existing"
        else:
            status = "block"
        rows.append(_row(len(rows) + 1, finding, status, baseline_state, waiver))
    rows.sort(key=lambda item: (item.status != "block", -SEVERITY_RANK[item.severity], item.path, item.line, item.rule))
    return [_renumber(idx, row) for idx, row in enumerate(rows, start=1)]


def _row(index: int, finding: MarkdownFinding, status: str, baseline_state: str, waiver: dict[str, str] | None) -> CIGateFinding:
    return CIGateFinding(
        id=f"ci-gate-{index:03d}",
        status=status,
        category=HIGH_RISK_RULES[finding.rule],
        rule=finding.rule,
        severity=finding.severity,
        path=finding.path,
        line=finding.line,
        excerpt=finding.excerpt,
        message=finding.message,
        recommendation=finding.recommendation,
        semantic_obligation=finding.semantic_obligation,
        baseline_state=baseline_state,
        waiver=waiver,
    )


def _renumber(index: int, finding: CIGateFinding) -> CIGateFinding:
    return CIGateFinding(**{**asdict(finding), "id": f"ci-gate-{index:03d}"})


def _waiver_by_line(findings: list[MarkdownFinding]) -> dict[tuple[str, int], dict[str, str]]:
    waivers: dict[tuple[str, int], dict[str, str]] = {}
    for finding in findings:
        if finding.rule != OWNER_APPROVED_WAIVER_RULE:
            continue
        metadata = _parse_applied_suppression(finding.message)
        if metadata:
            target_line = int(metadata.pop("suppressed_line", finding.line))
            waivers[(finding.path, target_line)] = metadata
    return waivers


def _parse_applied_suppression(message: str) -> dict[str, str]:
    match = re.search(
        r"Suppressed (?P<suppressed_rule>[^ ]+) at line (?P<suppressed_line>\d+) with owner=(?P<owner>[^,]+), expires=(?P<expires>[^,]+), reason=(?P<reason>.*), link=(?P<link>[^.]+)\.",
        message,
    )
    if not match:
        return {}
    return {key: value.strip() for key, value in match.groupdict().items()}


def _fingerprint(finding: MarkdownFinding) -> str:
    return "|".join([finding.rule, _normalize_excerpt(finding.excerpt), finding.semantic_obligation])


def _normalize_excerpt(excerpt: str) -> str:
    return re.sub(r"\s+", " ", excerpt.strip().lower())


def _count_by_category(findings: list[CIGateFinding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1
    return dict(sorted(counts.items()))


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|")
