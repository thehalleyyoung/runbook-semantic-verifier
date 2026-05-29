from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.repository_scan import build_repository_scan, render_scan_markdown

ROOT = Path(__file__).resolve().parents[1]


class RepositoryScanTests(unittest.TestCase):
    def test_scan_ranks_current_public_tempo_case_study_by_dangerous_effects(self):
        report = build_repository_scan(ROOT / "case_studies" / "current" / "grafana_tempo")
        self.assertEqual(report["summary"]["candidates"], 1)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["priority"], "critical")
        self.assertTrue(candidate["has_executable_model"])
        self.assertIn("tempo_runbook_current_impact.md", candidate["path"])
        self.assertIn("destructive-delete-needs-targeting", candidate["matched_rules"])
        self.assertIn("restore_path_and_blast_radius_limited", candidate["findings_by_obligation"])
        self.assertIn("semantic obligation", report["ranking_semantics"]["formal_connection"])

    def test_scan_markdown_render_has_model_first_recommendations(self):
        report = build_repository_scan(ROOT / "case_studies" / "current" / "redis_cache_flush")
        markdown = render_scan_markdown(report)
        self.assertIn("# Repository runbook scan", markdown)
        self.assertIn("cache-flush-needs-warmup-capacity", markdown)
        self.assertIn("Review whether prose dangerous-effect matches refine", markdown)

    def test_scan_cli_outputs_json_for_ci_or_repository_triage(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [sys.executable, "-m", "runbook_verify.cli", "scan", "case_studies/current/grafana_tempo", "--format", "json"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["summary"]["priority_counts"]["critical"], 1)
        self.assertEqual(data["candidates"][0]["has_executable_model"], True)


if __name__ == "__main__":
    unittest.main()
