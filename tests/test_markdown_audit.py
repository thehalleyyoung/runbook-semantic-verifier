from pathlib import Path
import json
import os
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

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
        self.assertEqual(data["findings"][0]["id"], "finding-001")

    def test_explain_cli_expands_historical_finding_with_rule_delta_and_source(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        audit_proc = subprocess.run(
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
        self.assertEqual(audit_proc.returncode, 0, audit_proc.stdout + audit_proc.stderr)
        audit = json.loads(audit_proc.stdout)
        semantic_finding = next(finding for finding in audit["findings"] if finding["type"] == "semantic")

        explain_proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "runbook_verify.cli",
                "explain",
                "case_studies/current/grafana_tempo",
                semantic_finding["id"],
                "--format",
                "json",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(explain_proc.returncode, 0, explain_proc.stdout + explain_proc.stderr)
        explanation = json.loads(explain_proc.stdout)
        self.assertEqual(explanation["id"], semantic_finding["id"])
        self.assertEqual(explanation["rule"], semantic_finding["rule"])
        self.assertIn("small_step_rule", explanation)
        self.assertIn("weakest_precondition_hint", explanation)
        self.assertGreaterEqual(len(explanation["state_delta"]), 1)
        self.assertEqual(explanation["source"]["path"], semantic_finding["path"])
        self.assertIsNotNone(explanation["source"]["line"])

    def test_audit_cli_emits_sarif_for_code_scanning(self):
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
                "sarif",
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
        sarif = json.loads(proc.stdout)
        self.assertEqual(sarif["version"], "2.1.0")
        run = sarif["runs"][0]
        self.assertEqual(run["tool"]["driver"]["name"], "formal-runbook-verification")
        rule_ids = {rule["id"] for rule in run["tool"]["driver"]["rules"]}
        result_rule_ids = {result["ruleId"] for result in run["results"]}
        self.assertIn("no_queue_pause_without_drain_plan", result_rule_ids)
        self.assertIn("destructive-delete-needs-targeting", rule_ids)
        self.assertTrue(all(result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for result in run["results"]))

    def test_audit_cli_emits_junit_for_ci_dashboards(self):
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
                "junit",
                "--expect-findings",
                "--fail-on",
                "error",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        suite = ET.fromstring(proc.stdout)
        self.assertEqual(suite.attrib["name"], "frv.audit")
        self.assertGreaterEqual(int(suite.attrib["tests"]), 1)
        self.assertGreaterEqual(int(suite.attrib["failures"]), 1)
        failure_messages = [failure.attrib["message"] for failure in suite.findall(".//failure")]
        self.assertTrue(any("Recommendation:" in message for message in failure_messages))


if __name__ == "__main__":
    unittest.main()
