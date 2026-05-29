from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify import Checker, load_runbook
from runbook_verify.parser import parse_runbook

ROOT = Path(__file__).resolve().parents[1]


class CheckerTests(unittest.TestCase):
    def test_safe_example_has_no_violations(self):
        result = Checker(load_runbook(ROOT / "examples" / "safe_runbook.json")).check()
        self.assertTrue(result.safe)
        self.assertEqual(result.violations, [])
        self.assertGreater(result.states_explored, 1)

    def test_unsafe_example_finds_multiple_property_classes(self):
        result = Checker(load_runbook(ROOT / "examples" / "unsafe_runbook.json")).check()
        props = {v.property for v in result.violations}
        self.assertFalse(result.safe)
        self.assertIn("service_min_available", props)
        self.assertIn("no_rollback_during_incompatible_migration", props)
        self.assertIn("no_failover_to_unhealthy_region", props)
        self.assertIn("quorum_before_data_loss_action", props)
        self.assertIn("bounded_alert_suppression", props)

    def test_dependency_order_prevents_premature_failover(self):
        result = Checker(load_runbook(ROOT / "examples" / "safe_runbook.json")).check()
        traces = [v.trace for v in result.violations]
        self.assertNotIn(("failover-orders-west",), traces)


if __name__ == "__main__":
    unittest.main()

class CheckerExplanationTests(unittest.TestCase):
    def test_queue_pause_hazard_has_remediation(self):
        runbook = parse_runbook({
            "system": {
                "regions": {}, "services": {}, "databases": {}, "alerts": {}, "feature_flags": {}, "deployments": {},
                "queues": {"q": {"depth": 10, "consumers": 1}}
            },
            "steps": [{"id": "pause", "action": "pause_queue", "params": {"queue": "q"}}]
        })
        result = Checker(runbook).check()
        props = {v.property for v in result.violations}
        self.assertIn("no_queue_pause_without_drain_plan", props)
        self.assertIn("no_paused_queue_with_backlog", props)
        self.assertTrue(all(v.remediation for v in result.violations))
