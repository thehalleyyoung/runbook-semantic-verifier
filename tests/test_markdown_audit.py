from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.checker import Checker
from runbook_verify.parser import load_runbook


ROOT = Path(__file__).resolve().parents[1]


class MarkdownCaseStudyTests(unittest.TestCase):
    def test_markdown_case_study_confirms_real_world_style_runbook_bugs(self):
        runbook = load_runbook(ROOT / "examples/real_world/kubernetes_region_failover.md")
        result = Checker(runbook).check()
        properties = {violation.property for violation in result.violations}

        self.assertIn("bounded_alert_suppression", properties)
        self.assertIn("service_min_available", properties)
        self.assertIn("quorum_before_data_loss_action", properties)

    def test_historical_github_case_study_reproduces_labeled_failure(self):
        runbook = load_runbook(ROOT / "case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md")
        result = Checker(runbook).check()
        properties = {violation.property for violation in result.violations}

        self.assertIn("precondition", properties)
        self.assertIn("quorum_before_data_loss_action", properties)


if __name__ == "__main__":
    unittest.main()
