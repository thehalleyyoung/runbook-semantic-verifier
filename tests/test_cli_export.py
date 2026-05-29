from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.exporter import export_tla
from runbook_verify.descriptors import render_action_reference_markdown
from runbook_verify.parser import load_runbook

ROOT = Path(__file__).resolve().parents[1]


class CliAndExportTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_cli_safe_returns_zero(self):
        proc = self._run("check", "examples/safe_runbook.json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("No safety violations", proc.stdout)

    def test_cli_unsafe_expect_violations_returns_zero(self):
        proc = self._run("check", "examples/unsafe_runbook.json", "--expect-violations")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Violations", proc.stdout)

    def test_export_contains_tla_safety_theorem(self):
        text = export_tla(load_runbook(ROOT / "examples" / "safe_runbook.json"))
        self.assertIn("THEOREM Spec => []Safety", text)
        self.assertIn("scale-api-west", text)
        self.assertIn("scale_service(service:string, replicas:integer>=0", text)

    def test_cli_export_alloy(self):
        proc = self._run("export", "examples/safe_runbook.json", "--format", "alloy")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("module runbook_verification", proc.stdout)

    def test_cli_schema_exports_runbook_contract(self):
        proc = self._run("schema")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        schema = json.loads(proc.stdout)
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIn("failover_database", schema["$defs"]["step"]["properties"]["action"]["enum"])
        self.assertIn("condition", schema["$defs"])

    def test_checked_in_schema_matches_cli_output(self):
        proc = self._run("schema")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, (ROOT / "docs" / "schema" / "runbook.schema.json").read_text(encoding="utf-8"))

    def test_action_reference_matches_descriptor_metadata(self):
        self.assertEqual(
            render_action_reference_markdown(),
            (ROOT / "docs" / "action_semantics.md").read_text(encoding="utf-8"),
        )

    def test_cli_validate_does_not_run_checker(self):
        proc = self._run("validate", "examples/unsafe_runbook.json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Valid runbook:", proc.stdout)
        self.assertNotIn("Violations", proc.stdout)

    def test_cli_parse_error_json_diagnostics(self):
        proc = self._run("validate", "tests/fixtures/invalid_json_syntax.json", "--diagnostics-format", "json")
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stderr)
        diagnostic = payload["diagnostics"][0]
        self.assertEqual(diagnostic["severity"], "error")
        self.assertEqual(diagnostic["line"], 4)
        self.assertTrue(diagnostic["path"].endswith("invalid_json_syntax.json"))
        self.assertIn("Fix the JSON syntax", diagnostic["remediation"])


if __name__ == "__main__":
    unittest.main()
