from datetime import date
from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.readiness import ReadinessOptions, build_readiness_report


ROOT = Path(__file__).resolve().parents[1]


class ReadinessTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_current_public_case_readiness_summarizes_semantics_prose_and_freshness(self):
        report = build_readiness_report(
            ROOT / "case_studies" / "current" / "grafana_tempo",
            ReadinessOptions(service="tempo-query", region="prod", as_of=date(2026, 5, 29)),
        )

        self.assertEqual(report["summary"]["status"], "not_ready")
        self.assertEqual(report["summary"]["runbooks_considered"], 1)
        self.assertEqual(report["summary"]["semantic_counterexamples"], 6)
        self.assertEqual(report["summary"]["stale_preconditions"], 0)
        self.assertEqual(report["summary"]["benchmark_expectation_mismatches"], 0)
        self.assertIn("tempo-query", report["modeled_entities"]["services"])
        self.assertIn("prod", report["modeled_entities"]["regions"])
        properties = {item["property"] for item in report["highest_risk_counterexamples"]}
        self.assertIn("no_replay_without_dedupe", properties)
        rules = {item["rule"] for item in report["unverified_prose_claims"]}
        self.assertIn("data-deletion-needs-restore-precondition", rules)
        self.assertGreater(report["proof_obligations"]["checked"]["safety_postcondition"], 0)
        self.assertTrue(report["benchmark_expectations"][0]["pass"])

    def test_readiness_cli_json_exit_policy_and_coverage_finding(self):
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
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["summary"]["status"], "not_ready")

        advisory = self._run(
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
            "--fail-on",
            "none",
        )
        self.assertEqual(advisory.returncode, 0, advisory.stdout + advisory.stderr)

        missing = self._run(
            "readiness",
            "case_studies/current/grafana_tempo",
            "--service",
            "unknown-service",
            "--as-of",
            "2026-05-29",
            "--format",
            "json",
            "--fail-on",
            "none",
        )
        self.assertEqual(missing.returncode, 0, missing.stdout + missing.stderr)
        missing_payload = json.loads(missing.stdout)
        self.assertEqual(missing_payload["summary"]["coverage_findings"], 1)
        self.assertEqual(missing_payload["coverage_findings"][0]["kind"], "uncovered_service")

    def test_inventory_preconditions_detect_stale_public_case_assumptions(self):
        report = build_readiness_report(
            ROOT / "case_studies" / "current" / "grafana_tempo",
            ReadinessOptions(
                service="tempo-query",
                region="prod",
                as_of=date(2026, 5, 29),
                inventory_path=ROOT / "case_studies" / "current" / "grafana_tempo" / "tempo_inventory_current_impact.json",
            ),
        )

        self.assertEqual(report["inventory"]["services"], 1)
        self.assertGreaterEqual(report["summary"]["blocking_stale_preconditions"], 1)
        stale_kinds = {item["kind"] for item in report["stale_preconditions"]}
        self.assertIn("replica_count_mismatch", stale_kinds)
        self.assertIn("missing_service_alert", stale_kinds)
        self.assertIn("missing_dependency", stale_kinds)
        obligations = {item["semantic_obligation"] for item in report["stale_preconditions"]}
        self.assertIn("inventory_refinement_precondition", obligations)


if __name__ == "__main__":
    unittest.main()
