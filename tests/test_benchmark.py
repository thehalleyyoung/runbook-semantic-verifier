from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.benchmark import BenchmarkConfigError, render_json, render_markdown, run_benchmark

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def test_builtin_benchmark_reports_expected_metrics(self):
        cwd = os.getcwd()
        try:
            os.chdir(ROOT)
            result = run_benchmark()
        finally:
            os.chdir(cwd)
        data = result.to_json_dict()
        self.assertTrue(data["aggregate"]["pass"])
        self.assertGreaterEqual(data["aggregate"]["runbooks"], 4)
        self.assertGreater(data["aggregate"]["states_explored"], 0)
        self.assertGreater(data["aggregate"]["performance_counters"]["transitions_explored"], 0)
        self.assertIn("proof_obligations_checked", data["aggregate"]["performance_counters"])
        self.assertIn("quorum_before_data_loss_action", data["aggregate"]["violations_by_property"])

    def test_benchmark_cli_outputs_json_and_markdown(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        json_proc = subprocess.run(
            [sys.executable, "-m", "runbook_verify.cli", "benchmark", "benchmarks/builtin.json", "--format", "json"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(json_proc.returncode, 0, json_proc.stdout + json_proc.stderr)
        parsed = json.loads(json_proc.stdout)
        self.assertTrue(parsed["aggregate"]["pass"])
        self.assertIn("performance_counters", parsed["aggregate"])
        self.assertIn("runbooks", parsed)
        self.assertEqual(parsed["runbooks"][0]["benchmark_metadata"]["license"]["status"], "original")
        self.assertIn("semantic_features", parsed["runbooks"][0]["benchmark_metadata"])

        md_proc = subprocess.run(
            [sys.executable, "-m", "runbook_verify.cli", "benchmark", "case_studies/github_oct21_2018", "--format", "markdown"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(md_proc.returncode, 0, md_proc.stdout + md_proc.stderr)
        self.assertIn("# Benchmark:", md_proc.stdout)
        self.assertIn("Performance counters", md_proc.stdout)
        self.assertIn("Benchmark metadata", md_proc.stdout)
        self.assertIn("quorum_before_data_loss_action", md_proc.stdout)

    def test_renderers_include_expected_labels(self):
        cwd = os.getcwd()
        try:
            os.chdir(ROOT)
            result = run_benchmark("case_studies/github_oct21_2018")
        finally:
            os.chdir(cwd)
        self.assertIn("expected_violation_properties", render_json(result))
        self.assertIn("expected_violation_properties", render_markdown(result))

    def test_direct_json_runbook_benchmarks_without_config_metadata(self):
        result = run_benchmark(ROOT / "examples" / "safe_runbook.json")
        data = result.to_json_dict()
        self.assertTrue(data["aggregate"]["pass"])
        self.assertEqual(data["aggregate"]["runbooks"], 1)

    def test_benchmark_config_requires_public_metadata(self):
        with self.assertRaises(BenchmarkConfigError) as raised:
            run_benchmark(ROOT / "tests" / "fixtures" / "invalid_benchmark_config.json")
        self.assertIn("missing required public benchmark field 'provenance'", str(raised.exception))

    def test_config_metadata_drives_expected_labels(self):
        cwd = os.getcwd()
        try:
            os.chdir(ROOT)
            result = run_benchmark("benchmarks/current_impact.json")
        finally:
            os.chdir(cwd)
        data = result.to_json_dict()
        self.assertTrue(data["aggregate"]["pass"])
        item = data["runbooks"][0]
        self.assertEqual(item["benchmark_metadata"]["provenance"]["kind"], "public-current")
        self.assertEqual(item["benchmark_metadata"]["abstraction_level"], "derived-public-runbook")
        self.assertIn("Public runbook excerpts are incomplete", item["benchmark_metadata"]["validity_threats"])
        self.assertIn("no_replay_without_dedupe", item["expected_labels"]["expected_violation_properties"])


if __name__ == "__main__":
    unittest.main()
