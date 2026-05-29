from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.ci_gate import build_ci_gate_report, render_ci_gate_json
from runbook_verify.markdown_lint import lint_markdown_text


ROOT = Path(__file__).resolve().parents[1]


class CIGateTests(unittest.TestCase):
    def test_gate_blocks_only_new_high_risk_prose_relative_to_baseline(self):
        report = build_ci_gate_report(
            ROOT / "tests/fixtures/ci_gate_changed.md",
            ROOT / "tests/fixtures/ci_gate_baseline.md",
        )
        by_rule = {finding.rule: finding for finding in report.findings}

        self.assertFalse(report.pass_)
        self.assertEqual(by_rule["manual-sql-needs-migration-model"].status, "existing")
        self.assertEqual(by_rule["data-restore-needs-rpo-rto-guard"].status, "block")
        self.assertEqual(by_rule["destructive-delete-needs-targeting"].status, "waived")
        self.assertEqual(report.summary["blocking_findings"], 1)

        parsed = json.loads(render_ci_gate_json(report))
        self.assertEqual(parsed["findings"][0]["id"], "ci-gate-001")
        self.assertIn("data_restoration_guard", parsed["summary"]["categories"])

    def test_restore_rule_links_data_recovery_prose_to_formal_guard(self):
        findings = lint_markdown_text("Restore the database from snapshot before reopening writes.", "restore.md")
        by_rule = {finding.rule: finding for finding in findings}

        self.assertIn("data-restore-needs-rpo-rto-guard", by_rule)
        self.assertEqual(by_rule["data-restore-needs-rpo-rto-guard"].severity, "error")
        self.assertIn("restore_path_rpo_rto", by_rule["data-restore-needs-rpo-rto-guard"].semantic_obligation)

    def test_ci_gate_cli_expect_blocks_on_public_case_study(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "runbook_verify.cli",
                "ci-gate",
                "case_studies/current/grafana_tempo",
                "--format",
                "json",
                "--expect-blocks",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertGreaterEqual(data["summary"]["blocking_findings"], 1)
        self.assertIn("data-deletion-needs-restore-precondition", {finding["rule"] for finding in data["findings"]})


if __name__ == "__main__":
    unittest.main()
