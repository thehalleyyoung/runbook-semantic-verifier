from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AdoptionDocumentationTests(unittest.TestCase):
    def test_adoption_pack_documents_and_templates_exist(self):
        expected = [
            "docs/templates/pre-commit-config.yaml",
            "docs/templates/github-actions-frv.yml",
            "docs/remediation_playbooks.md",
            "docs/onboarding_walkthrough.md",
            "docs/migration_guide.md",
            "docs/responsible_claims.md",
            "docs/governance.md",
            "docs/artifact_evaluation.md",
            "docs/evidence_ledger.md",
            "docs/release_criteria.md",
            "docs/security_privacy.md",
        ]
        for rel in expected:
            with self.subTest(rel=rel):
                path = ROOT / rel
                self.assertTrue(path.exists(), rel)
                self.assertGreater(len(path.read_text(encoding="utf-8")), 500, rel)

    def test_templates_exercise_real_checked_in_fixtures(self):
        pre_commit = (ROOT / "docs/templates/pre-commit-config.yaml").read_text(encoding="utf-8")
        actions = (ROOT / "docs/templates/github-actions-frv.yml").read_text(encoding="utf-8")
        for text in (pre_commit, actions):
            self.assertIn("PYTHONPATH=src python3 -m runbook_verify.cli", text)
            self.assertIn("case_studies/current/grafana_tempo", text)
        self.assertIn("make verify", actions)
        self.assertIn("benchmarks/builtin.json --format markdown", actions)

    def test_responsible_claims_and_ledger_keep_bounds_visible(self):
        claims = (ROOT / "docs/responsible_claims.md").read_text(encoding="utf-8")
        ledger = (ROOT / "docs/evidence_ledger.md").read_text(encoding="utf-8")
        self.assertIn("Avoid making this claim", claims)
        self.assertIn("live infrastructure safety", claims.lower())
        self.assertIn("frv check", ledger)
        self.assertIn("bounded", ledger.lower())
        self.assertIn("tests/test_adoption_docs.py", ledger)

    def test_remediation_playbooks_cover_existing_property_families(self):
        text = (ROOT / "docs/remediation_playbooks.md").read_text(encoding="utf-8")
        for token in [
            "quorum_before_data_loss_action",
            "dns_health_check_converged_before_cutover",
            "no_replay_without_dedupe",
            "cache_warmup_before_traffic",
            "inventory_refinement_precondition",
        ]:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
