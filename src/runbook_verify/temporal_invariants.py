from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TemporalInvariantTemplate:
    name: str
    temporal_form: str
    checker_property: str
    scope: str
    operator_hint: str


TEMPLATES: tuple[TemporalInvariantTemplate, ...] = (
    TemporalInvariantTemplate("blast_radius", "G(action_effect -> affected_entities <= declared_blast_radius)", "effect_annotation_required", "steps", "Annotate high-risk effects and keep blast-radius text reviewable."),
    TemporalInvariantTemplate("rpo", "G(restore_bucket_snapshot -> snapshot_age <= bucket.rpo_minutes)", "object_restore_within_rpo", "object_buckets", "Use a snapshot inside the modeled recovery-point window."),
    TemporalInvariantTemplate("rto", "G(restore_bucket_snapshot -> restore_duration <= bucket.rto_minutes)", "object_restore_within_rto", "object_buckets", "Keep restore duration inside the modeled recovery-time window."),
    TemporalInvariantTemplate("data_durability", "G(bucket_live -> replicated_regions >= min_replicated_regions)", "object_bucket_replication_min_regions", "object_buckets", "Maintain enough healthy object-storage replica regions."),
    TemporalInvariantTemplate("quorum", "G(data_loss_risk_failover -> database_quorum_confirmed)", "quorum_before_data_loss_action", "databases", "Confirm quorum before a data-loss-risk failover."),
    TemporalInvariantTemplate("write_availability", "G(traffic_weight>0 -> regional_capacity)", "traffic_requires_regional_capacity", "traffic", "Scale or restore capacity before routing users."),
    TemporalInvariantTemplate("regional_isolation", "G(region_unhealthy -> no_new_traffic_to_region)", "no_traffic_to_unhealthy_region", "regions", "Do not route traffic to unhealthy regions."),
    TemporalInvariantTemplate("alert_visibility", "G(alert_suppressed -> bounded_expiry)", "bounded_alert_suppression", "alerts", "Keep alert suppressions finite and policy-bounded."),
    TemporalInvariantTemplate("rollback_readiness", "G(rollback -> no_incompatible_migration)", "no_rollback_during_incompatible_migration", "steps", "Finish or prove compatibility before rollback."),
)


def build_temporal_invariant_catalog() -> dict[str, object]:
    return {"templates": [asdict(template) for template in TEMPLATES]}


def render_temporal_invariants_json() -> str:
    return json.dumps(build_temporal_invariant_catalog(), indent=2, sort_keys=True) + "\n"


def render_temporal_invariants_markdown() -> str:
    lines = [
        "# Temporal invariant templates",
        "",
        "These LTL-style templates document the bounded safety obligations checked by",
        "`frv check`. They are templates over the executable model, not claims about",
        "unmodeled live infrastructure behavior.",
        "",
        "| Template | Form | Checker property | Scope | Operator hint |",
        "| --- | --- | --- | --- | --- |",
    ]
    for template in TEMPLATES:
        lines.append(f"| `{template.name}` | `{template.temporal_form}` | `{template.checker_property}` | `{template.scope}` | {template.operator_hint} |")
    return "\n".join(lines) + "\n"
