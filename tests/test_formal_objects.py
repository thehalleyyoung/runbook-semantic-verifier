from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.formal_objects import build_formal_objects_report


ROOT = Path(__file__).resolve().parents[1]


class FormalObjectsTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_current_public_case_maps_objects_to_cli_fields(self):
        report = build_formal_objects_report(ROOT / "case_studies" / "current" / "grafana_tempo")

        self.assertEqual(report["object_schema_version"], "1.0")
        self.assertEqual(report["summary"]["runbooks"], 1)
        self.assertGreaterEqual(report["summary"]["hazard_counterexamples"], 6)
        object_names = {item["object"] for item in report["mathematical_objects"]}
        self.assertIn("syntax", object_names)
        self.assertIn("entity_universe", object_names)
        self.assertIn("hazard", object_names)
        self.assertIn("waiver", object_names)
        runbook = report["runbooks"][0]
        self.assertIn("tempo-query", runbook["entity_universe"]["names"]["services"])
        self.assertIn("tenant-index-fallback-scan", runbook["entity_universe"]["names"]["queues"])
        self.assertIn("no_replay_without_dedupe", runbook["hazards"]["properties"])
        self.assertTrue(runbook["steps"][0]["source"]["line"])
        self.assertIn("expected_violation_properties", runbook["benchmark_labels"]["labels"])
        self.assertTrue(any(item["object"] == "waiver" for item in report["observations"]))

    def test_formal_objects_cli_json_and_markdown(self):
        proc = self._run("formal-objects", "case_studies/current/grafana_tempo", "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["summary"]["runbooks"], 1)
        self.assertIn("runbooks[].hazards", payload["runbooks"][0]["hazards"]["cli_json_fields"])

        md = self._run("formal-objects", "case_studies/current/grafana_tempo", "--format", "markdown")
        self.assertEqual(md.returncode, 0, md.stdout + md.stderr)
        self.assertIn("# Formal object map", md.stdout)
        self.assertIn("tenant-index-fallback-scan", md.stdout)


if __name__ == "__main__":
    unittest.main()
