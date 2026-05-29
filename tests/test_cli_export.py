from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.checker import Checker
from runbook_verify.exporter import export_tla, export_alloy, export_conformance_manifest, render_proof_obligations_json
from runbook_verify.descriptors import render_action_reference_markdown
from runbook_verify.contracts import render_weakest_preconditions_markdown
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
        self.assertIn("hoare:", proc.stdout)

    def test_export_contains_tla_safety_theorem(self):
        text = export_tla(load_runbook(ROOT / "examples" / "safe_runbook.json"))
        self.assertIn("THEOREM Spec => []Safety", text)
        self.assertIn("scale-api-west", text)
        self.assertIn("scale_service(service:string, replicas:integer>=0", text)
        self.assertIn("\\* denotation:", text)

    def test_cli_export_alloy(self):
        proc = self._run("export", "examples/safe_runbook.json", "--format", "alloy")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("module runbook_verification", proc.stdout)
        self.assertIn("denotation:", proc.stdout)


    def test_cli_proof_obligations_markdown(self):
        proc = self._run("proof-obligations", "examples/safe_runbook.json", "--format", "markdown")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("# Proof obligations: Safe regional database failover", proc.stdout)
        self.assertIn("exporter:tla-abstraction", proc.stdout)
        self.assertIn("runtime logs should preserve modeled wait/expiry/TTL ordering", proc.stdout)

    def test_exporter_round_trip_conformance_cases(self):
        fixture = json.loads((ROOT / "tests" / "fixtures" / "exporter_conformance_cases.json").read_text(encoding="utf-8"))
        for case in fixture["cases"]:
            with self.subTest(path=case["path"]):
                runbook = load_runbook(ROOT / case["path"])
                manifest = export_conformance_manifest(runbook)
                tla = export_tla(runbook)
                alloy = export_alloy(runbook)
                obligations = json.loads(render_proof_obligations_json(runbook))
                native_properties = {violation.property for violation in Checker(runbook).check().violations}
                self.assertEqual(manifest["action_sequence"], [step.id for step in runbook.steps])
                self.assertIn("dependencies", manifest["variables"])
                for action in case["expected_actions"]:
                    self.assertIn(action, {entry["action"] for entry in manifest["action_comments"]})
                    self.assertIn(f"action={action}", tla)
                    self.assertIn(f"{action}(", tla)
                for prop in case["expected_native_properties"]:
                    self.assertIn(prop, native_properties)
                for prop in case["expected_properties"]:
                    self.assertIn(prop, manifest["property_identifiers"])
                    self.assertIn(f"property={prop}", tla)
                    self.assertIn(f"native property label: {prop}", alloy)
                    self.assertTrue(any(item["id"] == f"invariant:{prop}" for item in obligations["proof_obligations"]))
                for dep, step in manifest["enabledness_edges"]:
                    self.assertIn(f"<<\"{dep}\", \"{step}\">>", tla)

    def test_cli_schema_exports_runbook_contract(self):
        proc = self._run("schema")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        schema = json.loads(proc.stdout)
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIn("failover_database", schema["$defs"]["step"]["properties"]["action"]["enum"])
        self.assertIn("condition", schema["$defs"])
        self.assertTrue(any("Denotation:" in item["then"]["$comment"] for item in schema["$defs"]["step"]["allOf"]))

    def test_checked_in_schema_matches_cli_output(self):
        proc = self._run("schema")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, (ROOT / "docs" / "schema" / "runbook.schema.json").read_text(encoding="utf-8"))

    def test_action_reference_matches_descriptor_metadata(self):
        self.assertEqual(
            render_action_reference_markdown(),
            (ROOT / "docs" / "action_semantics.md").read_text(encoding="utf-8"),
        )
        self.assertIn("Denotational state transformer", render_action_reference_markdown())

    def test_weakest_precondition_doc_matches_contract_catalog(self):
        self.assertEqual(
            render_weakest_preconditions_markdown(),
            (ROOT / "docs" / "weakest_preconditions.md").read_text(encoding="utf-8"),
        )

    def test_cli_check_json_includes_explanation_trace_contract_and_source(self):
        proc = self._run("check", "case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md", "--expect-violations", "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["safe"])
        finding = payload["findings"][0]
        self.assertIn("state_delta", finding)
        self.assertIn("causal_dependencies", finding)
        self.assertIn("semantic_trace", finding)
        self.assertIn("hoare_triple", finding)
        self.assertTrue(finding["source"]["path"].endswith("github_oct21_reconstructed_runbook.md"))

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
