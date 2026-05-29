from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.checker import Checker
from runbook_verify.parser import load_runbook


ROOT = Path(__file__).resolve().parents[1]


class MarkdownCaseStudyTests(unittest.TestCase):
    def test_markdown_case_study_confirms_real_world_style_runbook_bugs(self):
        runbook = load_runbook(ROOT / "examples/real_world/kubernetes_region_failover.md")
        result = Checker(runbook).check()
        properties = {violation.property for violation in result.violations}

        self.assertIn("bounded_alert_suppression", properties)
        self.assertIn("service_min_available", properties)
        self.assertIn("quorum_before_data_loss_action", properties)

    def test_historical_github_case_study_reproduces_labeled_failure(self):
        runbook = load_runbook(ROOT / "case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md")
        result = Checker(runbook).check()
        properties = {violation.property for violation in result.violations}

        self.assertIn("precondition", properties)
        self.assertIn("quorum_before_data_loss_action", properties)

    def test_audit_cli_emits_ranked_semantic_and_prose_findings(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "runbook_verify.cli",
                "audit",
                "case_studies/current/grafana_tempo",
                "--format",
                "json",
                "--expect-findings",
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
        self.assertGreaterEqual(data["summary"]["findings"], 1)
        self.assertIn("destructive-delete-needs-targeting", data["summary"]["findings_by_rule"])
        self.assertIn("no_queue_pause_without_drain_plan", data["summary"]["findings_by_rule"])
        self.assertGreaterEqual(data["findings"][0]["rank"], data["findings"][-1]["rank"])
        self.assertIn("semantic_obligation", data["findings"][0])


if __name__ == "__main__":
    unittest.main()
