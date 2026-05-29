from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .explanation import RULE_EXPLANATIONS, collect_explain_findings
from .markdown_lint import SEVERITY_RANK


@dataclass(frozen=True)
class PullRequestAnnotation:
    id: str
    finding_id: str
    level: str
    severity: str
    type: str
    rule: str
    semantic_obligation: str
    small_step_rule: str
    path: str
    start_line: int | None
    end_line: int | None
    title: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class AnnotationGroup:
    id: str
    semantic_obligation: str
    source_span: str
    highest_severity: str
    annotations: tuple[PullRequestAnnotation, ...]


@dataclass(frozen=True)
class AnnotationReport:
    target: str
    pass_: bool
    fail_on: str
    summary: dict[str, Any]
    groups: tuple[AnnotationGroup, ...]


def build_annotation_report(path: str | Path, fail_on: str = "warning") -> AnnotationReport:
    root = Path(path)
    items = collect_explain_findings(root)
    annotations = [_annotation_from_item(item) for item in items]
    groups = _group_annotations(annotations)
    blocking = [annotation for annotation in annotations if _blocks(annotation, fail_on)]
    summary = {
        "annotations": len(annotations),
        "groups": len(groups),
        "blocking_annotations": len(blocking),
        "findings_by_rule": _count_by(annotations, "rule"),
        "findings_by_severity": _count_by(annotations, "severity"),
        "findings_by_obligation": _count_by(annotations, "semantic_obligation"),
    }
    return AnnotationReport(
        target=str(root),
        pass_=not blocking,
        fail_on=fail_on,
        summary=summary,
        groups=tuple(groups),
    )


def render_annotations_json(report: AnnotationReport) -> str:
    data = {
        "target": report.target,
        "pass": report.pass_,
        "fail_on": report.fail_on,
        "summary": report.summary,
        "groups": [
            {
                **asdict(group),
                "annotations": [asdict(annotation) for annotation in group.annotations],
            }
            for group in report.groups
        ],
    }
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def render_annotations_markdown(report: AnnotationReport) -> str:
    status = "PASS" if report.pass_ else "FAIL"
    lines = [
        f"# Pull-request annotation report: {report.target}",
        "",
        f"- Status: **{status}**",
        f"- Fail-on: `{report.fail_on}`",
        f"- Annotation groups: {report.summary['groups']}",
        f"- Annotations: {report.summary['annotations']}",
        f"- Blocking annotations: {report.summary['blocking_annotations']}",
        f"- Findings by severity: `{json.dumps(report.summary['findings_by_severity'], sort_keys=True)}`",
        f"- Findings by obligation: `{json.dumps(report.summary['findings_by_obligation'], sort_keys=True)}`",
        "",
    ]
    if not report.groups:
        lines.append("No audit/check findings were available for pull-request annotation.")
        return "\n".join(lines) + "\n"

    for group in report.groups:
        lines.extend([
            f"## {group.id}: `{group.semantic_obligation}`",
            "",
            f"- Source span: `{group.source_span}`",
            f"- Highest severity: `{group.highest_severity}`",
            "",
            "| Annotation | Finding | Level | Type | Rule | Small-step rule | Message | Recommendation |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for annotation in group.annotations:
            lines.append(
                "| {annotation} | {finding} | {level} | {type_} | {rule} | `{small_step}` | {message} | {recommendation} |".format(
                    annotation=annotation.id,
                    finding=annotation.finding_id,
                    level=annotation.level,
                    type_=annotation.type,
                    rule=annotation.rule,
                    small_step=annotation.small_step_rule,
                    message=_escape_md(annotation.message),
                    recommendation=_escape_md(annotation.recommendation),
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_annotations_github(report: AnnotationReport) -> str:
    lines: list[str] = []
    for group in report.groups:
        lines.append(f"::group::{_escape_command('frv ' + group.id + ' ' + group.semantic_obligation + ' at ' + group.source_span)}")
        for annotation in group.annotations:
            props = {
                "file": annotation.path,
                "title": annotation.title,
            }
            if annotation.start_line is not None:
                props["line"] = str(annotation.start_line)
            if annotation.end_line is not None and annotation.end_line != annotation.start_line:
                props["endLine"] = str(annotation.end_line)
            prop_text = ",".join(f"{key}={_escape_property(value)}" for key, value in props.items())
            message = (
                f"{annotation.finding_id}: {annotation.message} "
                f"Obligation: {annotation.semantic_obligation}. "
                f"Small-step rule: {annotation.small_step_rule}. "
                f"Recommendation: {annotation.recommendation}"
            )
            lines.append(f"::{annotation.level} {prop_text}::{_escape_command(message)}")
        lines.append("::endgroup::")
    return "\n".join(lines) + ("\n" if lines else "")


def has_blocking_annotations(report: AnnotationReport) -> bool:
    return not report.pass_


def _annotation_from_item(item: dict[str, Any]) -> PullRequestAnnotation:
    finding = item["finding"]
    runbook = item.get("runbook")
    path = str(finding.get("path", ""))
    line = finding.get("line")
    if runbook is not None and finding.get("step"):
        step = {step.id: step for step in runbook.steps}.get(str(finding["step"]))
        if step is not None:
            path = step.source_path or path
            line = step.source_line
    severity = str(finding.get("severity", "warning"))
    rule = str(finding.get("rule", "finding"))
    obligation = str(finding.get("semantic_obligation", rule))
    type_ = str(finding.get("type", "finding"))
    return PullRequestAnnotation(
        id="",
        finding_id=str(finding["id"]),
        level=_annotation_level(severity),
        severity=severity,
        type=type_,
        rule=rule,
        semantic_obligation=obligation,
        small_step_rule=_small_step_rule(type_, rule),
        path=path,
        start_line=int(line) if isinstance(line, int) and line > 0 else None,
        end_line=int(line) if isinstance(line, int) and line > 0 else None,
        title=f"frv {rule}: {obligation}",
        message=str(finding.get("message", "")),
        recommendation=str(finding.get("recommendation") or ""),
    )


def _group_annotations(annotations: list[PullRequestAnnotation]) -> list[AnnotationGroup]:
    buckets: dict[tuple[str, str, int | None, int | None], list[PullRequestAnnotation]] = {}
    for annotation in annotations:
        key = (annotation.semantic_obligation, annotation.path, annotation.start_line, annotation.end_line)
        buckets.setdefault(key, []).append(annotation)
    groups: list[AnnotationGroup] = []
    for index, (key, items) in enumerate(sorted(buckets.items(), key=_group_sort_key), start=1):
        obligation, path, start_line, end_line = key
        renumbered = tuple(
            PullRequestAnnotation(**{**asdict(annotation), "id": f"annotation-{index:03d}-{offset:02d}"})
            for offset, annotation in enumerate(items, start=1)
        )
        groups.append(AnnotationGroup(
            id=f"annotation-group-{index:03d}",
            semantic_obligation=obligation,
            source_span=_source_span(path, start_line, end_line),
            highest_severity=_highest_severity(items),
            annotations=renumbered,
        ))
    return groups


def _group_sort_key(item: tuple[tuple[str, str, int | None, int | None], list[PullRequestAnnotation]]) -> tuple[int, str, str, int]:
    key, annotations = item
    obligation, path, start_line, _end_line = key
    return (-max(SEVERITY_RANK[annotation.severity] for annotation in annotations), obligation, path, start_line or 0)


def _source_span(path: str, start_line: int | None, end_line: int | None) -> str:
    if start_line is None:
        return f"{path}:"
    if end_line is None or end_line == start_line:
        return f"{path}:{start_line}"
    return f"{path}:{start_line}-{end_line}"


def _small_step_rule(type_: str, rule: str) -> str:
    if type_ == "parse":
        return "Parser.WellFormedExecutableModel"
    if type_ == "prose":
        return f"ProseAudit.{rule}"
    return str(RULE_EXPLANATIONS.get(rule, {}).get("small_step_rule", f"SafetyInvariant.{rule}"))


def _annotation_level(severity: str) -> str:
    if severity in {"error", "responsible-disclosure"}:
        return "error"
    if severity == "warning":
        return "warning"
    return "notice"


def _highest_severity(annotations: list[PullRequestAnnotation]) -> str:
    return max(annotations, key=lambda annotation: SEVERITY_RANK[annotation.severity]).severity


def _count_by(annotations: list[PullRequestAnnotation], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for annotation in annotations:
        value = str(getattr(annotation, field))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _blocks(annotation: PullRequestAnnotation, threshold: str) -> bool:
    if threshold == "none":
        return False
    return SEVERITY_RANK[annotation.severity] >= SEVERITY_RANK[threshold]


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|")


def _escape_property(value: str) -> str:
    return _escape_command(value).replace(":", "%3A").replace(",", "%2C")


def _escape_command(value: str) -> str:
    return re.sub("%", "%25", value).replace("\r", "%0D").replace("\n", "%0A")
