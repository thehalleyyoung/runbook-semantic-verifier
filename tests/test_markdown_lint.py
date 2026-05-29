from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.markdown_lint import lint_markdown_file, render_lint_json

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


if __name__ == "__main__":
    unittest.main()
