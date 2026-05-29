# Runbook schema examples

`docs/schema/runbook.schema.json` is the canonical machine-readable schema. The strict JSON fixture in `docs/schema/examples/complete_runbook.json` is valid input for `frv validate` and intentionally exercises every supported top-level field:

- `name`: short human-readable runbook title.
- `description`: longer summary of the modeled incident procedure.
- `metadata`: free-form automation labels and provenance. The benchmark harness reads `metadata.labels.expected_safe`, `expected_violation_properties`, and `expected_prose_rules` when present.
- `allow_reordering`: whether the checker can explore any order that respects each step's `after` dependencies.
- `max_depth`: non-negative exploration bound.
- `safety`: checker policy configuration such as `max_alert_suppression_minutes`.
- `system`: initial regions, services and replicas, databases, queues, alerts, feature flags, deployments, traffic routes, and optional `clock_minute`.
- `steps`: executable actions with `id`, `action`, `params`, optional `after`, and optional `requires`/`effects` conditions.

JSON does not permit comments, so keep automation fixtures strict and place explanatory comments in prose like this file.

Action parameters and condition fields are defined in typed descriptors in the
implementation. Those same descriptors drive parser validation, JSON Schema
payloads, exporter comments, and the generated reference table in
`docs/action_semantics.md`.

Validate the example:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli validate docs/schema/examples/complete_runbook.json
```
