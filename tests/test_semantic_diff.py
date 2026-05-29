from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.parser import parse_runbook
from runbook_verify.semantic_diff import _diff_models
from runbook_verify.semantic_diff import diff_runbooks

ROOT = Path(__file__).resolve().parents[1]


class SemanticDiffTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_diff_detects_introduced_counterexamples(self):
        result = diff_runbooks(ROOT / "examples" / "safe_runbook.json", ROOT / "examples" / "unsafe_runbook.json")
        props = {item["property"] for item in result.introduced_counterexamples}
        self.assertFalse(result.pass_)
        self.assertIn("service_min_available", props)
        self.assertGreaterEqual(result.summary["safety_relevant_changes"], 1)

    def test_diff_detects_resolved_historical_quorum_guard(self):
        result = diff_runbooks(
            ROOT / "case_studies" / "github_oct21_2018" / "github_oct21_reconstructed_runbook.md",
            ROOT / "case_studies" / "github_oct21_2018" / "github_oct21_reconstructed_with_quorum_guard.md",
        )
        props = {item["property"] for item in result.resolved_counterexamples}
        self.assertTrue(result.pass_, result.to_json_dict())
        self.assertIn("quorum_before_data_loss_action", props)
        self.assertEqual(result.summary["introduced_counterexamples"], 0)

    def test_cli_diff_json_and_exit_code(self):
        proc = self._run("diff", "examples/safe_runbook.json", "examples/unsafe_runbook.json", "--format", "json")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["pass"])
        self.assertGreater(payload["summary"]["introduced_counterexamples"], 0)

        advisory = self._run("diff", "examples/safe_runbook.json", "examples/unsafe_runbook.json", "--format", "json", "--fail-on", "none")
        self.assertEqual(advisory.returncode, 0, advisory.stdout + advisory.stderr)

    def test_requires_removal_is_assumption_weakening(self):
        old = parse_runbook({
            "system": {
                "regions": {"east": {"healthy": True}},
                "databases": {"db": {"primary_region": "east", "healthy_regions": ["east"], "quorum_confirmed": True}},
            },
            "steps": [{
                "id": "fail",
                "action": "failover_database",
                "params": {"database": "db", "target_region": "east", "data_loss_risk": True},
                "requires": [{"kind": "database_quorum_confirmed", "database": "db"}],
            }],
        })
        new = parse_runbook({
            "system": {
                "regions": {"east": {"healthy": True}},
                "databases": {"db": {"primary_region": "east", "healthy_regions": ["east"], "quorum_confirmed": True}},
            },
            "steps": [{"id": "fail", "action": "failover_database", "params": {"database": "db", "target_region": "east", "data_loss_risk": True}}],
        })
        changes = _diff_models(old, new)
        self.assertIn(
            ("step_changed", "fail", "requires", "assumption_weakening"),
            {(change["kind"], change["object"], change["field"], change["classification"]) for change in changes},
        )

    def test_effect_addition_is_proof_obligation_strengthening(self):
        old = parse_runbook({
            "system": {"regions": {"east": {"healthy": True}}, "services": {"api": {"min_available": 0, "replicas": []}}},
            "steps": [{"id": "restart", "action": "restart_service", "params": {"service": "api"}}],
        })
        new = parse_runbook({
            "system": {"regions": {"east": {"healthy": True}}, "services": {"api": {"min_available": 0, "replicas": []}}},
            "steps": [{"id": "restart", "action": "restart_service", "params": {"service": "api"}, "effects": [{"kind": "service_available_at_least", "service": "api", "count": 0}]}],
        })
        changes = _diff_models(old, new)
        self.assertIn(
            ("step_changed", "restart", "effects", "proof_obligation_strengthening"),
            {(change["kind"], change["object"], change["field"], change["classification"]) for change in changes},
        )


if __name__ == "__main__":
    unittest.main()
