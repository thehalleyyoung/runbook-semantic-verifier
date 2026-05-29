#!/usr/bin/env python3
"""Regenerate checked-in benchmark evidence with bounded reproducibility budgets."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PYTHON = sys.executable
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
COMMANDS = [
    (
        "builtin-json",
        [PYTHON, "-m", "runbook_verify.cli", "benchmark", "benchmarks/builtin.json", "--format", "json"],
        REPORTS / "builtin_benchmark.json",
    ),
    (
        "builtin-markdown",
        [PYTHON, "-m", "runbook_verify.cli", "benchmark", "benchmarks/builtin.json", "--format", "markdown"],
        REPORTS / "builtin_benchmark.md",
    ),
    (
        "builtin-profile-markdown",
        [PYTHON, "-m", "runbook_verify.cli", "benchmark", "benchmarks/builtin.json", "--format", "markdown", "--profile", "benchmark-reproduction"],
        REPORTS / "builtin_benchmark_profile.md",
    ),
    (
        "current-impact-markdown",
        [PYTHON, "-m", "runbook_verify.cli", "benchmark", "benchmarks/current_impact.json", "--format", "markdown"],
        REPORTS / "current_impact_benchmark.md",
    ),
]


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    manifest = []
    for name, command, output_path in COMMANDS:
        completed = subprocess.run(command, cwd=ROOT, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        output_path.write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            sys.stderr.write(completed.stderr)
            return completed.returncode
        manifest.append({"name": name, "command": command, "output": str(output_path.relative_to(ROOT)), "bytes": len(completed.stdout)})
    (REPORTS / "benchmark_reproduction_manifest.json").write_text(json.dumps({"commands": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"regenerated {len(manifest)} benchmark reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
