# Synthetic mutation report: case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md

- Scope note: Synthetic mutants are benchmark seeds for reviewer calibration; they are not claims about the source runbook's live infrastructure.

| Operator | Applied | Safe | Violations | Annotation warnings | Parse error / description |
| --- | --- | --- | --- | --- | --- |
| `missing_preconditions` | `True` | `False` | `{"quorum_before_data_loss_action": 1}` | `{"effect_annotation_required": 1}` | Removed declared preconditions from one guarded step. |
| `reordered_steps` | `False` | `None` | `{}` | `{}` | No step with an ordering dependency was available. |
| `stale_owners` | `True` | `False` | `{"precondition": 1, "quorum_before_data_loss_action": 1}` | `{"effect_annotation_required": 1}` | Replaced owner metadata with a stale placeholder for audit/readiness calibration. |
| `unsafe_retries` | `True` | `False` | `{"precondition": 1, "quorum_before_data_loss_action": 1}` | `{"unsafe_retry_annotation": 1}` | Marked a destructive/high-risk action retry-safe despite non-idempotent irreversible effects. |
| `insufficient_waits` | `False` | `None` | `{}` | `{}` | No wait step was available. |
| `underprovisioned_replicas` | `True` | `False` | `{"precondition": 1, "quorum_before_data_loss_action": 1, "service_min_available": 5}` | `{"effect_annotation_required": 1}` | Raised min_available above declared replica count while explicitly modeling the weak assumption. |
| `invalid_waivers` | `True` | `False` | `{"precondition": 1, "quorum_before_data_loss_action": 1}` | `{"effect_annotation_required": 1}` | Added an expired owner-placeholder waiver that must remain visible rather than silently suppressing findings. |
