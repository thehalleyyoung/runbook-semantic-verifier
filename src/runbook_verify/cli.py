from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .benchmark import BenchmarkConfigError, render_json, render_markdown, run_benchmark
from .checker import Checker
from .exporter import export_alloy, export_tla
from .markdown_lint import lint_markdown_tree, render_lint_json, render_lint_markdown
from .parser import RunbookParseError, load_runbook
from .schema import render_json_schema


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="frv", description="Verify cloud incident runbooks with bounded state-space exploration.")
    sub = parser.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser("check", help="parse and verify a runbook")
    check_p.add_argument("runbook")
    check_p.add_argument("--expect-violations", action="store_true", help="exit 0 only when at least one violation is found")
    export_p = sub.add_parser("export", help="export a formal-ish model")
    export_p.add_argument("runbook")
    export_p.add_argument("--format", choices=["tla", "alloy"], default="tla")
    sub.add_parser("schema", help="print the JSON Schema for the runbook DSL")
    audit_p = sub.add_parser("audit", help="verify every runbook file in a directory tree")
    audit_p.add_argument("path")
    audit_p.add_argument("--expect-findings", action="store_true", help="exit 0 only when at least one violation is found")
    bench_p = sub.add_parser("benchmark", help="run a benchmark suite over built-in or user-provided runbooks")
    bench_p.add_argument("path", nargs="?", help="optional runbook file, runbook directory, or benchmark config JSON")
    bench_p.add_argument("--format", choices=["json", "markdown"], default="json")
    lint_p = sub.add_parser("lint-markdown", help="lint Markdown runbook prose for dangerous unmodeled operations")
    lint_p.add_argument("path")
    lint_p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    lint_p.add_argument("--expect-findings", action="store_true", help="exit 0 only when prose findings are found")
    args = parser.parse_args(argv)

    if args.command == "audit":
        return _audit(args.path, args.expect_findings)
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
        return 1 if findings else 0
    if args.command == "schema":
        print(render_json_schema(), end="")
        return 0

    try:
        runbook = load_runbook(args.runbook)
    except RunbookParseError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
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
    if args.command == "export":
        print(export_tla(runbook) if args.format == "tla" else export_alloy(runbook), end="")
        return 0
    return 2


def _audit(path: str, expect_findings: bool) -> int:
    root = Path(path)
    if not root.exists():
        print(f"audit path does not exist: {root}", file=sys.stderr)
        return 2
    files = _runbook_files(root)
    if not files:
        print(f"No runbook files found under {root}", file=sys.stderr)
        return 2
    total_violations = 0
    parse_errors = 0
    for file in files:
        try:
            runbook = load_runbook(file)
        except RunbookParseError as exc:
            parse_errors += 1
            print(f"{file}: parse error: {exc}", file=sys.stderr)
            continue
        result = Checker(runbook).check()
        total_violations += len(result.violations)
        status = "UNSAFE" if result.violations else "SAFE"
        print(f"{status} {file} states={result.states_explored} terminal_traces={result.traces_explored} violations={len(result.violations)}")
        for violation in result.violations:
            print(f"  - [{violation.property}] trace={' -> '.join(violation.trace)}: {violation.message}")
    if parse_errors:
        return 2
    if expect_findings:
        return 0 if total_violations else 1
    return 1 if total_violations else 0


def _runbook_files(root: Path) -> list[Path]:
    candidates = [root] if root.is_file() else list(root.rglob("*"))
    return sorted(path for path in candidates if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml", ".md"})


if __name__ == "__main__":
    raise SystemExit(main())
