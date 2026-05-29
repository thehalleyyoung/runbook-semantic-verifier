from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.checker import Checker
from runbook_verify.longitudinal import build_longitudinal_report
from runbook_verify.parser import load_runbook, parse_runbook
from runbook_verify.symbolic import run_symbolic_check
from runbook_verify.trace_equivalence import build_trace_equivalence, default_trace_equivalence_paths
from runbook_verify.usability import build_usability_report, default_usability_paths

ROOT = Path(__file__).resolve().parents[1]


class EvaluationWorkflowTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_dominance_pruning_is_opt_in_and_counted(self):
        doc = {
            "allow_reordering": True,
            "safety": {"dominance_pruning": True, "partial_order_reduction": False},
            "system": {"regions": {"east": {}}, "services": {"api": {"min_available": 0, "replicas": []}}},
            "steps": [
                {"id": "wait-a", "action": "wait", "params": {"minutes": 1}},
                {"id": "wait-b", "action": "wait", "params": {"minutes": 1}}
            ]
        }
        result = Checker(parse_runbook(doc)).check()
        counters = result.performance_counters()
        self.assertGreaterEqual(counters["abstract_states"], 1)
        self.assertGreaterEqual(counters["dominance_pruned_states"], 1)

    def test_symbolic_check_expands_capacity_and_wait_choices(self):
        report = run_symbolic_check(ROOT / "tests" / "fixtures" / "symbolic_capacity_runbook.json")
        data = report.to_json_dict()
        self.assertEqual(data["summary"]["variants"], 8)
        self.assertEqual(data["summary"]["symbolic_splits"], 7)
        self.assertGreater(data["summary"]["unsafe_variants"], 0)
        self.assertGreater(data["summary"]["safe_variants"], 0)
        proc = self._run("symbolic-check", "tests/fixtures/symbolic_capacity_runbook.json", "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["summary"]["variants"], 8)

    def test_trace_equivalence_covers_representative_families(self):
        report = build_trace_equivalence(default_trace_equivalence_paths(ROOT))
        data = report.to_json_dict()
        self.assertTrue(data["pass"])
        self.assertEqual(data["summary"]["cases"], 4)
        self.assertGreater(data["summary"]["matched_counterexamples"], 0)
        proc = self._run("trace-equivalence", "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["pass"])

    def test_longitudinal_evaluation_uses_semantic_diff_baselines(self):
        cwd = os.getcwd()
        try:
            os.chdir(ROOT)
            report = build_longitudinal_report("benchmarks/builtin.json")
        finally:
            os.chdir(cwd)
        data = report.to_json_dict()
        self.assertTrue(data["pass"])
        self.assertGreaterEqual(data["summary"]["revision_pairs"], 1)
        self.assertGreaterEqual(data["summary"]["would_block_before_merge"], 1)
        proc = self._run("longitudinal", "benchmarks/builtin.json", "--format", "markdown")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Would block before merge", proc.stdout)

    def test_usability_tasks_measure_hints_and_minimization(self):
        report = build_usability_report(default_usability_paths(ROOT))
        data = report.to_json_dict()
        self.assertTrue(data["pass"])
        self.assertGreater(data["summary"]["generated_precondition_hints"], 0)
        self.assertGreaterEqual(data["summary"]["trace_step_reduction"], 0)
        proc = self._run("usability-tasks", "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertGreater(json.loads(proc.stdout)["summary"]["generated_json_patches"], 0)


if __name__ == "__main__":
    unittest.main()
