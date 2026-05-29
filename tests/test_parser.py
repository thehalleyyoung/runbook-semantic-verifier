from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.parser import RunbookParseError, load_runbook, parse_runbook

ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_loads_safe_example(self):
        runbook = load_runbook(ROOT / "examples" / "safe_runbook.json")
        self.assertEqual(runbook.name, "Safe regional database failover")
        self.assertEqual(len(runbook.steps), 6)
        self.assertIn("api", runbook.state.services)

    def test_rejects_duplicate_step_ids(self):
        with self.assertRaises(RunbookParseError):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "toggle_flag"}, {"id": "x", "action": "toggle_flag"}]})

    def test_rejects_unknown_dependency(self):
        with self.assertRaises(RunbookParseError):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "toggle_flag", "after": ["missing"]}]})

    def test_rejects_dependency_cycles(self):
        with self.assertRaisesRegex(RunbookParseError, "dependency cycle"):
            parse_runbook({
                "system": {},
                "steps": [
                    {"id": "a", "action": "wait", "params": {"minutes": 1}, "after": ["b"]},
                    {"id": "b", "action": "wait", "params": {"minutes": 1}, "after": ["a"]},
                ],
            })


if __name__ == "__main__":
    unittest.main()

class ParserValidationTests(unittest.TestCase):
    def test_rejects_unknown_action_and_params(self):
        with self.assertRaisesRegex(RunbookParseError, "unsupported action"):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "rm_rf", "params": {}}]})
        with self.assertRaisesRegex(RunbookParseError, "unknown field"):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "wait", "params": {"minutes": 1, "extra": True}}]})

    def test_rejects_unknown_entity_references(self):
        doc = {
            "system": {"regions": {"a": {}}, "services": {}, "databases": {}, "queues": {}, "alerts": {}, "feature_flags": {}, "deployments": {}},
            "steps": [{"id": "x", "action": "suppress_alert", "params": {"alert": "missing", "expires_after_minutes": 5}}],
        }
        with self.assertRaisesRegex(RunbookParseError, "unknown alert"):
            parse_runbook(doc)

    def test_rejects_invalid_numeric_bounds(self):
        with self.assertRaisesRegex(RunbookParseError, "positive integer"):
            parse_runbook({
                "system": {"alerts": {"a": {}}},
                "steps": [{"id": "x", "action": "suppress_alert", "params": {"alert": "a", "expires_after_minutes": 0}}],
            })
        with self.assertRaisesRegex(RunbookParseError, "non-negative integer"):
            parse_runbook({
                "system": {},
                "steps": [{"id": "x", "action": "wait", "params": {"minutes": -1}}],
            })

    def test_source_path_is_attached_to_steps(self):
        runbook = load_runbook(ROOT / "examples" / "safe_runbook.json")
        self.assertTrue(runbook.steps[0].source_path.endswith("safe_runbook.json"))
        self.assertIsInstance(runbook.steps[0].source_line, int)
