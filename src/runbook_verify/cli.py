from __future__ import annotations

import argparse
import sys

from .checker import Checker
from .exporter import export_alloy, export_tla
from .parser import RunbookParseError, load_runbook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="frv", description="Verify cloud incident runbooks with bounded state-space exploration.")
    sub = parser.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser("check", help="parse and verify a runbook")
    check_p.add_argument("runbook")
    check_p.add_argument("--expect-violations", action="store_true", help="exit 0 only when at least one violation is found")
    export_p = sub.add_parser("export", help="export a formal-ish model")
    export_p.add_argument("runbook")
    export_p.add_argument("--format", choices=["tla", "alloy"], default="tla")
    args = parser.parse_args(argv)

    try:
        runbook = load_runbook(args.runbook)
    except RunbookParseError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 2

    if args.command == "check":
        result = Checker(runbook).check()
        print(f"Runbook: {runbook.name}")
        print(f"States explored: {result.states_explored}; terminal traces: {result.traces_explored}")
        if result.violations:
            print("Violations:")
            for v in result.violations:
                print(f"- [{v.property}] trace={' -> '.join(v.trace)}: {v.message}")
        else:
            print("No safety violations found within bound.")
        if args.expect_violations:
            return 0 if result.violations else 1
        return 0 if result.safe else 1
    if args.command == "export":
        print(export_tla(runbook) if args.format == "tla" else export_alloy(runbook), end="")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
