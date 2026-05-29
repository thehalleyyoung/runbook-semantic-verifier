from pathlib import Path
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.exporter import export_tla
from runbook_verify.parser import load_runbook

ROOT = Path(__file__).resolve().parents[1]


class CliAndExportTests(unittest.TestCase):
    def _run(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run([sys.executable, "-m", "runbook_verify.cli", *args], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_cli_safe_returns_zero(self):
        proc = self._run("check", "examples/safe_runbook.json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("No safety violations", proc.stdout)

    def test_cli_unsafe_expect_violations_returns_zero(self):
        proc = self._run("check", "examples/unsafe_runbook.json", "--expect-violations")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Violations", proc.stdout)

    def test_export_contains_tla_safety_theorem(self):
        text = export_tla(load_runbook(ROOT / "examples" / "safe_runbook.json"))
        self.assertIn("THEOREM Spec => []Safety", text)
        self.assertIn("scale-api-west", text)

    def test_cli_export_alloy(self):
        proc = self._run("export", "examples/safe_runbook.json", "--format", "alloy")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("module runbook_verification", proc.stdout)


if __name__ == "__main__":
    unittest.main()
