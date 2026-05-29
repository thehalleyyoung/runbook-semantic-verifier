from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.profiles import PROFILES, render_profiles_json


ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_profiles_are_listed_as_machine_readable_policy(self):
        parsed = json.loads(render_profiles_json())
        names = {item["name"] for item in parsed}

        self.assertIn("conservative-production", names)
        self.assertIn("advisory-research", names)
        self.assertEqual(PROFILES["advisory-research"].ci_gate_fail_on, "none")

        proc = self._run("profiles", "--format", "markdown")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Verification profiles", proc.stdout)
        self.assertIn("benchmark-reproduction", proc.stdout)

    def test_advisory_profile_keeps_evidence_but_does_not_fail_on_public_case_study(self):
        default_gate = self._run("ci-gate", "case_studies/current/grafana_tempo", "--format", "json")
        self.assertEqual(default_gate.returncode, 1, default_gate.stdout + default_gate.stderr)
        default_payload = json.loads(default_gate.stdout)
        self.assertGreaterEqual(default_payload["summary"]["blocking_findings"], 1)

        advisory_gate = self._run("ci-gate", "case_studies/current/grafana_tempo", "--format", "json", "--profile", "advisory-research")
        self.assertEqual(advisory_gate.returncode, 0, advisory_gate.stdout + advisory_gate.stderr)
        advisory_payload = json.loads(advisory_gate.stdout)
        self.assertEqual(advisory_payload["summary"]["blocking_findings"], default_payload["summary"]["blocking_findings"])

    def test_explicit_fail_on_overrides_profile_default(self):
        proc = self._run(
            "readiness",
            "case_studies/current/grafana_tempo",
            "--service",
            "tempo-query",
            "--region",
            "prod",
            "--as-of",
            "2026-05-29",
            "--format",
            "json",
            "--profile",
            "advisory-research",
            "--fail-on",
            "not-ready",
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_benchmark_profile_is_recorded_for_reproducibility(self):
        proc = self._run("benchmark", "benchmarks/builtin.json", "--format", "json", "--profile", "benchmark-reproduction")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["profile"]["name"], "benchmark-reproduction")
        self.assertTrue(payload["aggregate"]["pass"])


if __name__ == "__main__":
    unittest.main()
