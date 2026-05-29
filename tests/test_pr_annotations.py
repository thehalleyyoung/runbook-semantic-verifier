from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.pr_annotations import build_annotation_report, render_annotations_github, render_annotations_json


ROOT = Path(__file__).resolve().parents[1]


class PullRequestAnnotationTests(unittest.TestCase):
    def test_annotation_report_groups_by_obligation_and_source_span(self):
        report = build_annotation_report(ROOT / "case_studies/current/grafana_tempo", fail_on="error")
        groups_by_obligation = {group.semantic_obligation: group for group in report.groups}

        self.assertFalse(report.pass_)
        self.assertGreaterEqual(report.summary["annotations"], 1)
        self.assertIn("restore_path_and_blast_radius_limited", groups_by_obligation)
        group = groups_by_obligation["restore_path_and_blast_radius_limited"]
        self.assertIn("tempo_runbook_current_impact.md:", group.source_span)
        self.assertTrue(all(annotation.small_step_rule for annotation in group.annotations))
        self.assertTrue(all(annotation.finding_id.startswith("finding-") for annotation in group.annotations))

        parsed = json.loads(render_annotations_json(report))
        self.assertEqual(parsed["groups"][0]["id"], "annotation-group-001")
        self.assertIn("findings_by_obligation", parsed["summary"])

    def test_github_output_contains_workflow_annotation_commands(self):
        report = build_annotation_report(ROOT / "case_studies/current/grafana_tempo", fail_on="none")
        output = render_annotations_github(report)

        self.assertIn("::group::frv annotation-group-", output)
        self.assertIn("::error file=", output)
        self.assertIn("Small-step rule:", output)

    def test_annotate_cli_validates_public_case_study(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "runbook_verify.cli",
                "annotate",
                "case_studies/current/grafana_tempo",
                "--format",
                "json",
                "--fail-on",
                "none",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertGreaterEqual(data["summary"]["groups"], 1)
        self.assertIn("no_replay_without_dedupe", data["summary"]["findings_by_rule"])


if __name__ == "__main__":
    unittest.main()
