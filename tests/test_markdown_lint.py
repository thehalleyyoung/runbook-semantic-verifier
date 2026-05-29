from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.markdown_lint import lint_markdown_file, lint_markdown_text, render_lint_json

ROOT = Path(__file__).resolve().parents[1]


class MarkdownLintTests(unittest.TestCase):
    def test_current_tempo_case_study_flags_destructive_public_prose(self):
        path = ROOT / "case_studies" / "current" / "grafana_tempo" / "tempo_runbook_current_impact.md"
        findings = lint_markdown_file(path)
        rules = {finding.rule for finding in findings}
        self.assertIn("destructive-delete-needs-targeting", rules)
        parsed = json.loads(render_lint_json(findings))
        self.assertGreaterEqual(len(parsed), 1)

    def test_lint_cli_outputs_markdown(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [sys.executable, "-m", "runbook_verify.cli", "lint-markdown", "case_studies/current/grafana_tempo", "--expect-findings"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("# Markdown runbook lint report", proc.stdout)
        self.assertIn("destructive-delete-needs-targeting", proc.stdout)
        self.assertIn("Obligation", proc.stdout)

    def test_expanded_rules_are_severity_aware_and_link_obligations(self):
        text = "\n".join([
            "Manually execute SQL update where tenant_id = 7.",
            "Backfill and replay jobs after the outage.",
            "Rotate the service credential key.",
            "Notify customers about possible degradation.",
            "Rollback the deployment if errors continue.",
            "Escalate to the SRE on-call owner.",
        ])
        findings = lint_markdown_text(text, "synthetic.md")
        by_rule = {finding.rule: finding for finding in findings}

        self.assertEqual(by_rule["manual-sql-needs-migration-model"].severity, "error")
        self.assertEqual(by_rule["backfill-needs-queue-capacity"].severity, "warning")
        self.assertEqual(by_rule["credential-handling-needs-rotation-model"].severity, "responsible-disclosure")
        self.assertEqual(by_rule["customer-notification-gap"].severity, "warning")
        self.assertEqual(by_rule["rollback-ambiguity-needs-explicit-action"].severity, "error")
        self.assertEqual(by_rule["unmodeled-escalation-path"].severity, "audit-only")
        self.assertIn("database_quorum_confirmed", by_rule["manual-sql-needs-migration-model"].semantic_obligation)

    def test_lint_cli_fail_on_threshold_is_tunable(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [sys.executable, "-m", "runbook_verify.cli", "lint-markdown", "tests/fixtures/escalation_only.md", "--fail-on", "error"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("unmodeled-escalation-path", proc.stdout)


if __name__ == "__main__":
    unittest.main()
