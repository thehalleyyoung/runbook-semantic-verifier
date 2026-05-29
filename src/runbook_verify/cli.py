from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from xml.sax.saxutils import escape

from .benchmark import BenchmarkConfigError, render_json, render_markdown, run_benchmark
from .checker import Checker
from .ci_gate import build_ci_gate_report, render_ci_gate_json, render_ci_gate_markdown
from .coverage import CoverageError, build_coverage_report, render_coverage_json, render_coverage_markdown
from .explanation import ExplainError, explain_finding, render_explanation_json, render_explanation_markdown
from .exporter import export_alloy, export_tla
from .markdown_lint import SEVERITY_RANK, has_findings_at_or_above, lint_markdown_tree, render_lint_json, render_lint_markdown
from .owner_scorecard import OwnerScorecardError, OwnerScorecardOptions, build_owner_scorecard, render_owner_scorecard_json, render_owner_scorecard_markdown
from .parser import RunbookParseError, load_runbook
from .readiness import ReadinessError, ReadinessOptions, build_readiness_report, render_readiness_json, render_readiness_markdown
from .repository_scan import RepositoryScanError, ScanOptions, build_repository_scan, render_scan_json, render_scan_markdown
from .schema import render_json_schema
from .semantic_diff import diff_runbooks, render_diff_json, render_diff_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="frv", description="Verify cloud incident runbooks with bounded state-space exploration.")
    sub = parser.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser("check", help="parse and verify a runbook")
    check_p.add_argument("runbook")
    check_p.add_argument("--expect-violations", action="store_true", help="exit 0 only when at least one violation is found")
    check_p.add_argument("--diagnostics-format", choices=["text", "json"], default="text", help="format for parse diagnostics on failure")
    validate_p = sub.add_parser("validate", help="parse and validate a runbook without state-space exploration")
    validate_p.add_argument("runbook")
    validate_p.add_argument("--diagnostics-format", choices=["text", "json"], default="text", help="format for parse diagnostics on failure")
    export_p = sub.add_parser("export", help="export a formal-ish model")
    export_p.add_argument("runbook")
    export_p.add_argument("--format", choices=["tla", "alloy"], default="tla")
    export_p.add_argument("--diagnostics-format", choices=["text", "json"], default="text", help="format for parse diagnostics on failure")
    sub.add_parser("schema", help="print the JSON Schema for the runbook DSL")
    audit_p = sub.add_parser("audit", help="verify every runbook file in a directory tree")
    audit_p.add_argument("path")
    audit_p.add_argument("--expect-findings", action="store_true", help="exit 0 only when at least one violation is found")
    audit_p.add_argument("--diagnostics-format", choices=["text", "json"], default="text", help="format for parse diagnostics on failure")
    audit_p.add_argument("--format", choices=["text", "json", "markdown", "sarif", "junit"], default="text", help="audit report format")
    audit_p.add_argument("--fail-on", choices=["info", "audit-only", "warning", "error", "responsible-disclosure", "none"], default="warning", help="minimum severity that fails the command when --expect-findings is not set")
    bench_p = sub.add_parser("benchmark", help="run a benchmark suite over built-in or user-provided runbooks")
    bench_p.add_argument("path", nargs="?", help="optional runbook file, runbook directory, or benchmark config JSON")
    bench_p.add_argument("--format", choices=["json", "markdown"], default="json")
    explain_p = sub.add_parser("explain", help="explain an audit/check finding with rule, trace, source, and remediation context")
    explain_p.add_argument("path", help="runbook file or directory used to produce the finding")
    explain_p.add_argument("finding_id", help="finding id such as finding-001 from `frv audit --format json`")
    explain_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    diff_p = sub.add_parser("diff", help="compare two runbooks as semantic programs for PR review")
    diff_p.add_argument("old")
    diff_p.add_argument("new")
    diff_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    diff_p.add_argument("--fail-on", choices=["semantic-regression", "none"], default="semantic-regression")
    readiness_p = sub.add_parser("readiness", help="summarize incident-readiness signals for a runbook path, service, or region")
    readiness_p.add_argument("path")
    readiness_p.add_argument("--service", help="limit readiness to executable runbooks covering this service")
    readiness_p.add_argument("--region", help="limit readiness to executable runbooks covering this region")
    readiness_p.add_argument("--freshness-days", type=int, default=180, help="maximum allowed age for source metadata or file mtime")
    readiness_p.add_argument("--as-of", help="ISO date used for reproducible freshness calculations")
    readiness_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    readiness_p.add_argument("--fail-on", choices=["not-ready", "none"], default="not-ready")
    owner_p = sub.add_parser("owner-scorecard", help="summarize runbook readiness, hazards, waivers, and remediation history by owner")
    owner_p.add_argument("path")
    owner_p.add_argument("--owner", help="limit scorecard to one owner id")
    owner_p.add_argument("--freshness-days", type=int, default=180, help="maximum allowed age for source metadata or file mtime")
    owner_p.add_argument("--as-of", help="ISO date used for reproducible freshness calculations")
    owner_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    owner_p.add_argument("--fail-on", choices=["not-ready", "none"], default="not-ready")
    coverage_p = sub.add_parser("coverage", help="map safety properties to modeled entities, owners, and Markdown sections")
    coverage_p.add_argument("path")
    coverage_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    lint_p = sub.add_parser("lint-markdown", help="lint Markdown runbook prose for dangerous unmodeled operations")
    lint_p.add_argument("path")
    lint_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    lint_p.add_argument("--expect-findings", action="store_true", help="exit 0 only when prose findings are found")
    lint_p.add_argument("--fail-on", choices=["info", "audit-only", "warning", "error", "responsible-disclosure", "none"], default="warning", help="minimum severity that fails the command when --expect-findings is not set")
    scan_p = sub.add_parser("scan", help="rank Markdown/wiki runbooks by dangerous-effect vocabulary and model-first priority")
    scan_p.add_argument("path")
    scan_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    scan_p.add_argument("--min-score", type=int, default=1, help="minimum scan score to include")
    scan_p.add_argument("--include-low-priority", action="store_true", help="include Markdown files with score below --min-score")
    gate_p = sub.add_parser("ci-gate", help="block new high-risk operations prose unless owner-approved waivers exist")
    gate_p.add_argument("path", help="changed runbook file or directory to gate")
    gate_p.add_argument("--baseline", help="optional baseline path; matching high-risk findings are treated as existing debt")
    gate_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    gate_p.add_argument("--expect-blocks", action="store_true", help="exit 0 only when the gate finds blocking high-risk changes")
    args = parser.parse_args(argv)

    if args.command == "audit":
        return _audit(args.path, args.expect_findings, args.diagnostics_format, args.format, args.fail_on)
    if args.command == "benchmark":
        try:
            result = run_benchmark(args.path)
        except BenchmarkConfigError as exc:
            print(f"benchmark error: {exc}", file=sys.stderr)
            return 2
        print(render_json(result) if args.format == "json" else render_markdown(result), end="")
        return 0 if result.pass_ else 1
    if args.command == "lint-markdown":
        findings = lint_markdown_tree(args.path)
        print(render_lint_json(findings) if args.format == "json" else render_lint_markdown(findings), end="")
        if args.expect_findings:
            return 0 if findings else 1
        return 1 if has_findings_at_or_above(findings, args.fail_on) else 0
    if args.command == "scan":
        try:
            report = build_repository_scan(args.path, ScanOptions(min_score=args.min_score, include_low_priority=args.include_low_priority))
        except RepositoryScanError as exc:
            print(f"scan error: {exc}", file=sys.stderr)
            return 2
        print(render_scan_json(report) if args.format == "json" else render_scan_markdown(report), end="")
        return 0
    if args.command == "ci-gate":
        report = build_ci_gate_report(args.path, args.baseline)
        print(render_ci_gate_json(report) if args.format == "json" else render_ci_gate_markdown(report), end="")
        if args.expect_blocks:
            return 0 if report.summary["blocking_findings"] else 1
        return 0 if report.pass_ else 1
    if args.command == "explain":
        try:
            explanation = explain_finding(args.path, args.finding_id)
        except ExplainError as exc:
            print(f"explain error: {exc}", file=sys.stderr)
            return 2
        print(render_explanation_json(explanation) if args.format == "json" else render_explanation_markdown(explanation), end="")
        return 0
    if args.command == "diff":
        try:
            result = diff_runbooks(args.old, args.new)
        except RunbookParseError as exc:
            _print_parse_error(exc, "text")
            return 2
        print(render_diff_json(result) if args.format == "json" else render_diff_markdown(result), end="")
        if args.fail_on == "none":
            return 0
        return 0 if result.pass_ else 1
    if args.command == "readiness":
        as_of = None
        if args.as_of:
            from datetime import date
            try:
                as_of = date.fromisoformat(args.as_of)
            except ValueError as exc:
                print(f"readiness error: invalid --as-of date {args.as_of!r}: {exc}", file=sys.stderr)
                return 2
        try:
            result = build_readiness_report(args.path, ReadinessOptions(service=args.service, region=args.region, freshness_days=args.freshness_days, as_of=as_of))
        except ReadinessError as exc:
            print(f"readiness error: {exc}", file=sys.stderr)
            return 2
        print(render_readiness_json(result) if args.format == "json" else render_readiness_markdown(result), end="")
        if args.fail_on == "none":
            return 0
        return 1 if result["summary"]["status"] == "not_ready" else 0
    if args.command == "owner-scorecard":
        as_of = None
        if args.as_of:
            from datetime import date
            try:
                as_of = date.fromisoformat(args.as_of)
            except ValueError as exc:
                print(f"owner-scorecard error: invalid --as-of date {args.as_of!r}: {exc}", file=sys.stderr)
                return 2
        try:
            result = build_owner_scorecard(args.path, OwnerScorecardOptions(owner=args.owner, freshness_days=args.freshness_days, as_of=as_of))
        except OwnerScorecardError as exc:
            print(f"owner-scorecard error: {exc}", file=sys.stderr)
            return 2
        print(render_owner_scorecard_json(result) if args.format == "json" else render_owner_scorecard_markdown(result), end="")
        if args.fail_on == "none":
            return 0
        return 1 if result["summary"]["status"] == "not_ready" else 0
    if args.command == "coverage":
        try:
            result = build_coverage_report(args.path)
        except CoverageError as exc:
            print(f"coverage error: {exc}", file=sys.stderr)
            return 2
        print(render_coverage_json(result) if args.format == "json" else render_coverage_markdown(result), end="")
        return 0 if not result["parse_errors"] else 2
    if args.command == "schema":
        print(render_json_schema(), end="")
        return 0

    try:
        runbook = load_runbook(args.runbook)
    except RunbookParseError as exc:
        _print_parse_error(exc, args.diagnostics_format)
        return 2

    if args.command == "check":
        result = Checker(runbook).check()
        print(f"Runbook: {runbook.name}")
        print(f"States explored: {result.states_explored}; terminal traces: {result.traces_explored}; max depth reached: {result.max_depth_reached}")
        if result.violations:
            print("Violations:")
            for v in result.violations:
                print(f"- [{v.property}] trace={' -> '.join(v.trace)}: {v.message}")
                if v.remediation:
                    print(f"  remediation: {v.remediation}")
        else:
            print("No safety violations found within bound.")
        if args.expect_violations:
            return 0 if result.violations else 1
        return 0 if result.safe else 1
    if args.command == "validate":
        print(f"Valid runbook: {runbook.name}")
        print(f"Services: {len(runbook.state.services)}; steps: {len(runbook.steps)}; max depth: {runbook.max_depth}")
        return 0
    if args.command == "export":
        print(export_tla(runbook) if args.format == "tla" else export_alloy(runbook), end="")
        return 0
    return 2


def _audit(path: str, expect_findings: bool, diagnostics_format: str = "text", output_format: str = "text", fail_on: str = "warning") -> int:
    root = Path(path)
    if not root.exists():
        print(f"audit path does not exist: {root}", file=sys.stderr)
        return 2
    executable_files = _executable_runbook_files(root)
    markdown_findings = lint_markdown_tree(root)
    if not executable_files and not markdown_findings:
        print(f"No runbook files or Markdown findings found under {root}", file=sys.stderr)
        return 2
    audit_findings = [_finding_from_markdown(finding) for finding in markdown_findings]
    parse_errors = 0
    runbook_summaries = []
    for file in executable_files:
        try:
            runbook = load_runbook(file)
        except RunbookParseError as exc:
            parse_errors += 1
            contextual = exc.with_context(path=str(file))
            if output_format == "text":
                _print_parse_error(contextual, diagnostics_format, prefix=str(file))
            audit_findings.append({
                "type": "parse",
                "severity": "error",
                "rank": SEVERITY_RANK["error"],
                "path": str(file),
                "line": contextual.diagnostic.line,
                "rule": "parse_error",
                "semantic_obligation": "well_formed_executable_model",
                "message": str(contextual),
                "recommendation": contextual.diagnostic.remediation,
            })
            continue
        result = Checker(runbook).check()
        runbook_summaries.append({
            "path": str(file),
            "name": runbook.name,
            "safe": not result.violations,
            "states_explored": result.states_explored,
            "terminal_traces": result.traces_explored,
            "violations": len(result.violations),
        })
        status = "UNSAFE" if result.violations else "SAFE"
        if output_format == "text":
            print(f"{status} {file} states={result.states_explored} terminal_traces={result.traces_explored} violations={len(result.violations)}")
        for violation in result.violations:
            if output_format == "text":
                print(f"  - [{violation.property}] trace={' -> '.join(violation.trace)}: {violation.message}")
            audit_findings.append({
                "type": "semantic",
                "severity": "error",
                "rank": SEVERITY_RANK["error"],
                "path": str(file),
                "line": None,
                "rule": violation.property,
                "semantic_obligation": violation.property,
                "step": violation.step,
                "trace": list(violation.trace),
                "message": violation.message,
                "recommendation": violation.remediation,
            })
    audit_findings = _with_finding_ids(_rank_audit_findings(audit_findings))
    audit_report = {"summary": _audit_summary(runbook_summaries, audit_findings), "runbooks": runbook_summaries, "findings": audit_findings}
    if output_format == "json":
        print(json.dumps(audit_report, indent=2, sort_keys=True))
    elif output_format == "markdown":
        print(_render_audit_markdown(root, runbook_summaries, audit_findings), end="")
    elif output_format == "sarif":
        print(_render_audit_sarif(audit_report), end="")
    elif output_format == "junit":
        print(_render_audit_junit(audit_report, fail_on), end="")
    elif markdown_findings:
        print(f"Markdown prose findings: {len(markdown_findings)}")
        for finding in markdown_findings:
            print(f"  - [{finding.severity}] {finding.rule} {finding.path}:{finding.line} obligation={finding.semantic_obligation}: {finding.message}")
    if parse_errors:
        return 2
    if expect_findings:
        return 0 if audit_findings else 1
    return 1 if _has_audit_findings_at_or_above(audit_findings, fail_on) else 0


def _print_parse_error(exc: RunbookParseError, diagnostics_format: str = "text", prefix: str | None = None) -> None:
    if diagnostics_format == "json":
        print(json.dumps({"diagnostics": [exc.to_dict()]}, sort_keys=True), file=sys.stderr)
        return
    location = prefix or exc.diagnostic.path
    if location:
        print(f"{location}: parse error: {exc}", file=sys.stderr)
    else:
        print(f"parse error: {exc}", file=sys.stderr)


def _runbook_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml", ".md"})


def _executable_runbook_files(root: Path) -> list[Path]:
    return [path for path in _runbook_files(root) if path.suffix.lower() != ".md" or _has_embedded_runbook(path)]


def _has_embedded_runbook(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "```runbook-json" in text or "```json" in text


def _finding_from_markdown(finding: object) -> dict[str, object]:
    data = asdict(finding)
    data["type"] = "prose"
    data["rank"] = SEVERITY_RANK[str(data["severity"])]
    return data


def _rank_audit_findings(findings: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(findings, key=lambda item: (-int(item["rank"]), str(item.get("path", "")), int(item.get("line") or 0), str(item.get("rule", ""))))


def _with_finding_ids(findings: list[dict[str, object]]) -> list[dict[str, object]]:
    return [dict(finding, id=f"finding-{idx:03d}") for idx, finding in enumerate(findings, start=1)]


def _audit_summary(runbooks: list[dict[str, object]], findings: list[dict[str, object]]) -> dict[str, object]:
    by_severity: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for finding in findings:
        severity = str(finding["severity"])
        rule = str(finding["rule"])
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_rule[rule] = by_rule.get(rule, 0) + 1
    return {
        "runbooks": len(runbooks),
        "safe_runbooks": sum(1 for item in runbooks if item["safe"]),
        "findings": len(findings),
        "findings_by_severity": dict(sorted(by_severity.items())),
        "findings_by_rule": dict(sorted(by_rule.items())),
    }


def _render_audit_markdown(root: Path, runbooks: list[dict[str, object]], findings: list[dict[str, object]]) -> str:
    summary = _audit_summary(runbooks, findings)
    lines = [
        f"# Runbook audit: {root}",
        "",
        f"- Runbooks checked: {summary['runbooks']}",
        f"- Safe runbooks: {summary['safe_runbooks']}",
        f"- Findings: {summary['findings']}",
        f"- Findings by severity: `{json.dumps(summary['findings_by_severity'], sort_keys=True)}`",
        f"- Findings by rule: `{json.dumps(summary['findings_by_rule'], sort_keys=True)}`",
        "",
    ]
    if runbooks:
        lines.extend(["| Runbook | Safe | States | Traces | Violations |", "| --- | --- | ---: | ---: | ---: |"])
        for item in runbooks:
            lines.append(f"| `{item['path']}` | `{item['safe']}` | {item['states_explored']} | {item['terminal_traces']} | {item['violations']} |")
        lines.append("")
    if findings:
        lines.extend(["| ID | Rank | Type | Severity | Rule | Obligation | Location | Message | Recommendation | Autofix suggestions |", "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |"])
        for finding in findings:
            location = f"{finding.get('path')}:{finding.get('line') or ''}"
            message = str(finding.get("message", "")).replace("|", "\\|")
            recommendation = str(finding.get("recommendation", "") or "").replace("|", "\\|")
            suggestions = _autofix_summary(finding).replace("|", "\\|")
            lines.append(f"| `{finding['id']}` | {finding['rank']} | {finding['type']} | {finding['severity']} | {finding['rule']} | `{finding['semantic_obligation']}` | `{location}` | {message} | {recommendation} | {suggestions} |")
    return "\n".join(lines) + "\n"


def _autofix_summary(finding: dict[str, object]) -> str:
    raw = finding.get("autofix_suggestions")
    if not isinstance(raw, (list, tuple)):
        return ""
    summaries: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            kind = str(item.get("kind", "autofix"))
            title = str(item.get("title", "suggested edit"))
            summaries.append(f"{kind}: {title}")
    return "; ".join(summaries)


def _render_audit_sarif(report: dict[str, object]) -> str:
    findings = list(report["findings"])  # type: ignore[index]
    rules = {}
    results = []
    for finding in findings:
        rule_id = str(finding["rule"])
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": rule_id,
                "shortDescription": {"text": str(finding.get("semantic_obligation", rule_id))},
                "help": {"text": str(finding.get("recommendation") or finding.get("message") or "")},
                "defaultConfiguration": {"level": _sarif_level(str(finding.get("severity", "warning")))},
            }
        location: dict[str, object] = {
            "physicalLocation": {
                "artifactLocation": {"uri": str(finding.get("path", ""))},
            }
        }
        line = finding.get("line")
        if isinstance(line, int) and line > 0:
            location["physicalLocation"]["region"] = {"startLine": line}  # type: ignore[index]
        result = {
            "ruleId": rule_id,
            "level": _sarif_level(str(finding.get("severity", "warning"))),
            "message": {"text": _finding_message(finding)},
            "locations": [location],
            "properties": {
                "findingId": str(finding.get("id", "")),
                "findingType": str(finding.get("type", "")),
                "semanticObligation": str(finding.get("semantic_obligation", "")),
            },
        }
        results.append(result)
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "formal-runbook-verification",
                        "informationUri": "https://github.com/",
                        "rules": [rules[key] for key in sorted(rules)],
                    }
                },
                "results": results,
                "properties": {"summary": report["summary"]},
            }
        ],
    }
    return json.dumps(sarif, indent=2, sort_keys=True) + "\n"


def _render_audit_junit(report: dict[str, object], fail_on: str) -> str:
    findings = list(report["findings"])  # type: ignore[index]
    blocking = [finding for finding in findings if _finding_blocks_for_threshold(finding, fail_on)]
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name="frv.audit" tests="{len(findings)}" failures="{len(blocking)}" errors="0" skipped="0">',
    ]
    for finding in findings:
        name = f"{finding.get('id', '')} {finding.get('path', '')}:{finding.get('line') or ''}"
        classname = f"frv.audit.{finding.get('rule', 'finding')}"
        lines.append(f'  <testcase classname="{_xml_attr(classname)}" name="{_xml_attr(name)}">')
        message = _finding_message(finding)
        if _finding_blocks_for_threshold(finding, fail_on):
            lines.append(f'    <failure type="{_xml_attr(str(finding.get("severity", "")))}" message="{_xml_attr(message)}">{escape(message)}</failure>')
        else:
            lines.append(f"    <system-out>{escape(message)}</system-out>")
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    return "\n".join(lines) + "\n"


def _sarif_level(severity: str) -> str:
    if severity in {"error", "responsible-disclosure"}:
        return "error"
    if severity == "warning":
        return "warning"
    return "note"


def _finding_message(finding: dict[str, object]) -> str:
    recommendation = str(finding.get("recommendation") or "")
    if recommendation:
        return f"{finding.get('message', '')} Recommendation: {recommendation}"
    return str(finding.get("message", ""))


def _finding_blocks_for_threshold(finding: dict[str, object], threshold: str) -> bool:
    if threshold == "none":
        return False
    return int(finding["rank"]) >= SEVERITY_RANK[threshold]


def _xml_attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def _has_audit_findings_at_or_above(findings: list[dict[str, object]], threshold: str) -> bool:
    if threshold == "none":
        return False
    minimum = SEVERITY_RANK[threshold]
    return any(int(finding["rank"]) >= minimum for finding in findings)


if __name__ == "__main__":
    raise SystemExit(main())
