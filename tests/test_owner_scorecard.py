from datetime import date
from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.owner_scorecard import OwnerScorecardOptions, build_owner_scorecard


ROOT = Path(__file__).resolve().parents[1]


class OwnerScorecardTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_current_public_case_owner_scorecard_groups_hazards_and_proof_obligations(self):
        report = build_owner_scorecard(
            ROOT / "case_studies" / "current" / "grafana_tempo",
            OwnerScorecardOptions(as_of=date(2026, 5, 29)),
        )

        self.assertEqual(report["summary"]["status"], "not_ready")
        self.assertEqual(report["summary"]["owners"], 1)
        owner = report["owners"][0]
        self.assertEqual(owner["owner"], "grafana-tempo-public-fixture")
        self.assertEqual(owner["status"], "not_ready")
        self.assertEqual(owner["runbooks"], 1)
        self.assertEqual(owner["verified_runbooks"], 0)
        self.assertEqual(owner["semantic_counterexamples"], 6)
        self.assertGreaterEqual(owner["prose_findings"], 3)
        self.assertEqual(owner["stale_assumptions"], 0)
        self.assertEqual(owner["waiver_debt"], 0)
        self.assertIn("tempo-query", owner["services"])
        self.assertGreater(owner["proof_obligations"]["checked"]["safety_postcondition"], 0)
        self.assertIn("queue fallback replay", owner["recent_remediation"])
        hazard_kinds = {hazard["kind"] for hazard in owner["top_hazards"]}
        self.assertIn("semantic", hazard_kinds)
        self.assertIn("prose", hazard_kinds)

    def test_owner_scorecard_cli_json_exit_policy_and_owner_filter(self):
        proc = self._run(
            "owner-scorecard",
            "case_studies/current/grafana_tempo",
            "--as-of",
            "2026-05-29",
            "--format",
            "json",
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["summary"]["status"], "not_ready")
        self.assertEqual(payload["owners"][0]["owner"], "grafana-tempo-public-fixture")

        advisory = self._run(
            "owner-scorecard",
            "case_studies/current/grafana_tempo",
            "--owner",
            "grafana-tempo-public-fixture",
            "--as-of",
            "2026-05-29",
            "--format",
            "json",
            "--fail-on",
            "none",
        )
        self.assertEqual(advisory.returncode, 0, advisory.stdout + advisory.stderr)
        filtered = json.loads(advisory.stdout)
        self.assertEqual(filtered["summary"]["owners"], 1)


if __name__ == "__main__":
    unittest.main()
