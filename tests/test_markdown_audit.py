from pathlib import Path

from runbook_verify.checker import Checker
from runbook_verify.parser import load_runbook


ROOT = Path(__file__).resolve().parents[1]


def test_markdown_case_study_confirms_real_world_style_runbook_bugs():
    runbook = load_runbook(ROOT / "examples/real_world/kubernetes_region_failover.md")
    result = Checker(runbook).check()
    properties = {violation.property for violation in result.violations}

    assert "bounded_alert_suppression" in properties
    assert "service_min_available" in properties
    assert "quorum_before_data_loss_action" in properties
