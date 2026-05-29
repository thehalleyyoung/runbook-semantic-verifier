from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmark import _load_config  # internal loader keeps benchmark metadata validation centralized
from .semantic_diff import diff_runbooks


@dataclass(frozen=True)
class LongitudinalReport:
    config_path: str
    pass_: bool
    revisions: list[dict[str, Any]]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "pass": self.pass_,
            "summary": {
                "revision_pairs": len(self.revisions),
                "would_block_before_merge": sum(1 for item in self.revisions if item["would_block_before_merge"]),
                "resolved_counterexamples": sum(item["summary"].get("resolved_counterexamples", 0) for item in self.revisions),
                "introduced_counterexamples": sum(item["summary"].get("introduced_counterexamples", 0) for item in self.revisions),
                "assumption_weakenings": sum(item["summary"].get("assumption_weakenings", 0) for item in self.revisions),
            },
            "revisions": self.revisions,
        }


def build_longitudinal_report(config_path: str | Path) -> LongitudinalReport:
    config_path = Path(config_path)
    _, _, diff_entries = _load_config(config_path)
    revisions: list[dict[str, Any]] = []
    for entry in diff_entries:
        diff = diff_runbooks(entry.old_path, entry.new_path)
        summary = dict(diff.summary)
        would_block = summary.get("introduced_counterexamples", 0) > 0 or summary.get("assumption_weakenings", 0) > 0 or not diff.old_safe
        revisions.append({
            "name": entry.name,
            "old_path": str(entry.old_path),
            "new_path": str(entry.new_path),
            "old_safe": diff.old_safe,
            "new_safe": diff.new_safe,
            "would_block_before_merge": would_block,
            "gate_reason": _gate_reason(diff.old_safe, summary),
            "summary": summary,
            "expected": entry.expected,
        })
    return LongitudinalReport(str(config_path), all(item["would_block_before_merge"] or item["new_safe"] or item["summary"].get("introduced_counterexamples", 0) == 0 for item in revisions), revisions)


def render_longitudinal_json(report: LongitudinalReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n"


def render_longitudinal_markdown(report: LongitudinalReport) -> str:
    data = report.to_json_dict()
    lines = [
        "# Longitudinal semantic-gate evaluation",
        "",
        f"- Config: `{report.config_path}`",
        f"- Pass: `{data['pass']}`",
        f"- Revision pairs: {data['summary']['revision_pairs']}",
        f"- Would block before merge: {data['summary']['would_block_before_merge']}",
        f"- Resolved counterexamples: {data['summary']['resolved_counterexamples']}",
        "",
        "| Revision pair | Old safe | New safe | Would block before merge | Reason | Summary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in data["revisions"]:
        lines.append(f"| {item['name']} | `{item['old_safe']}` | `{item['new_safe']}` | `{item['would_block_before_merge']}` | {item['gate_reason']} | `{json.dumps(item['summary'], sort_keys=True)}` |")
    if not data["revisions"]:
        lines.append("| none |  |  |  | no semantic-diff baselines configured | `{}` |")
    return "\n".join(lines) + "\n"


def _gate_reason(old_safe: bool, summary: dict[str, Any]) -> str:
    reasons = []
    if not old_safe:
        reasons.append("pre-existing counterexample debt")
    if summary.get("introduced_counterexamples", 0):
        reasons.append("introduced counterexamples")
    if summary.get("assumption_weakenings", 0):
        reasons.append("assumption weakenings")
    if summary.get("resolved_counterexamples", 0):
        reasons.append("remediation resolved counterexamples")
    return ", ".join(reasons) or "no blocking semantic regression"
