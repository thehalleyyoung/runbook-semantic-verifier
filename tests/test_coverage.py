from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.coverage import build_coverage_report


ROOT = Path(__file__).resolve().parents[1]


class CoverageTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_current_public_case_maps_properties_to_entities_owners_and_sections(self):
        report = build_coverage_report(ROOT / "case_studies" / "current" / "grafana_tempo")

        self.assertEqual(report["summary"]["runbooks"], 1)
        self.assertEqual(report["summary"]["covered_services"], 1)
        self.assertEqual(report["summary"]["covered_queues"], 1)
        self.assertIn("grafana-tempo-public-fixture", report["summary"]["owners"])
        by_property = {item["property"]: item for item in report["properties"]}
        self.assertIn("no_queue_pause_without_drain_plan", by_property)
        self.assertEqual(by_property["no_queue_pause_without_drain_plan"]["queues"], ["tenant-index-fallback-scan"])
        sections = {step["section"] for step in by_property["no_queue_pause_without_drain_plan"]["steps"]}
        self.assertIn("Defensive interpretation", sections)
        self.assertIn("Hoare-style", by_property["declared_effect"]["formal_obligation"])
        prose_rules = {item["rule"] for item in report["unverified_prose_obligations"]}
        self.assertIn("data-deletion-needs-restore-precondition", prose_rules)

    def test_coverage_cli_json_and_markdown(self):
        proc = self._run("coverage", "case_studies/current/grafana_tempo", "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["summary"]["covered_regions"], 1)
        self.assertGreaterEqual(payload["summary"]["properties"], 5)

        markdown = self._run("coverage", "case_studies/current/grafana_tempo", "--format", "markdown")
        self.assertEqual(markdown.returncode, 0, markdown.stdout + markdown.stderr)
        self.assertIn("# Property coverage report", markdown.stdout)
        self.assertIn("no_queue_pause_without_drain_plan", markdown.stdout)


if __name__ == "__main__":
    unittest.main()
