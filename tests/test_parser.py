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


if __name__ == "__main__":
    unittest.main()
