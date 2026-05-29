from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VerificationProfile:
    name: str
    description: str
    audit_fail_on: str
    lint_fail_on: str
    ci_gate_fail_on: str
    readiness_fail_on: str
    owner_scorecard_fail_on: str
    benchmark_mode: str
    intended_use: str

    def to_json_dict(self) -> dict[str, str]:
        return asdict(self)


PROFILES: dict[str, VerificationProfile] = {
    "conservative-production": VerificationProfile(
        name="conservative-production",
        description="Fail protected-branch workflows on warning-or-higher audit/lint findings, CI gate blockers, and not-ready service reports.",
        audit_fail_on="warning",
        lint_fail_on="warning",
        ci_gate_fail_on="blocks",
        readiness_fail_on="not-ready",
        owner_scorecard_fail_on="not-ready",
        benchmark_mode="enforce-expected-labels",
        intended_use="Production runbook repositories and protected branch gates.",
    ),
    "advisory-research": VerificationProfile(
        name="advisory-research",
        description="Emit the same semantic/audit evidence but do not fail on findings; parse/config errors still fail.",
        audit_fail_on="none",
        lint_fail_on="none",
        ci_gate_fail_on="none",
        readiness_fail_on="none",
        owner_scorecard_fail_on="none",
        benchmark_mode="record-evidence",
        intended_use="Exploratory evaluation, public case-study reproduction, and non-blocking review comments.",
    ),
    "documentation-only-audit": VerificationProfile(
        name="documentation-only-audit",
        description="Treat Markdown/wiki prose findings as documentation debt; preserve executable parse errors and evidence in reports.",
        audit_fail_on="none",
        lint_fail_on="none",
        ci_gate_fail_on="none",
        readiness_fail_on="none",
        owner_scorecard_fail_on="none",
        benchmark_mode="not-targeted",
        intended_use="Early prose triage before teams have embedded executable runbook-json models.",
    ),
    "benchmark-reproduction": VerificationProfile(
        name="benchmark-reproduction",
        description="Keep default benchmark pass/fail labels while recording the profile used for artifact reproduction.",
        audit_fail_on="warning",
        lint_fail_on="warning",
        ci_gate_fail_on="blocks",
        readiness_fail_on="none",
        owner_scorecard_fail_on="none",
        benchmark_mode="reproduce-checked-in-metadata",
        intended_use="Artifact evaluation and checked-in public benchmark/report regeneration.",
    ),
}


def profile_names() -> list[str]:
    return sorted(PROFILES)


def get_profile(name: str | None) -> VerificationProfile | None:
    if name is None:
        return None
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown verification profile {name!r}; choose one of {', '.join(profile_names())}") from exc


def render_profiles_json() -> str:
    return json.dumps([profile.to_json_dict() for profile in (PROFILES[name] for name in profile_names())], indent=2, sort_keys=True) + "\n"


def render_profiles_markdown() -> str:
    lines = [
        "# Verification profiles",
        "",
        "| Profile | Intended use | Audit fail-on | Lint fail-on | CI gate fail-on | Readiness fail-on | Owner scorecard fail-on | Benchmark mode |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name in profile_names():
        profile = PROFILES[name]
        lines.append(
            "| {name} | {use} | `{audit}` | `{lint}` | `{ci}` | `{readiness}` | `{owner}` | `{benchmark}` |".format(
                name=profile.name,
                use=profile.intended_use.replace("|", "\\|"),
                audit=profile.audit_fail_on,
                lint=profile.lint_fail_on,
                ci=profile.ci_gate_fail_on,
                readiness=profile.readiness_fail_on,
                owner=profile.owner_scorecard_fail_on,
                benchmark=profile.benchmark_mode,
            )
        )
    lines.extend([
        "",
        "Profiles set default exit policies only when the command line does not pass an explicit `--fail-on` value.",
        "They do not weaken parser/schema errors or change bounded checker semantics.",
    ])
    return "\n".join(lines) + "\n"
