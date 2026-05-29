from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.benchmark import render_json, render_markdown, run_benchmark

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
        self.assertIn("runbooks", parsed)

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


if __name__ == "__main__":
    unittest.main()
