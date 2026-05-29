# Exporter conformance fixtures

Representative round-trip exporter conformance cases covering synthetic, public historical, and current public fixtures.

| Fixture | Steps | Actions | Expected exported labels | Native checker labels | Enabledness edges |
| --- | ---: | --- | --- | --- | ---: |
| `examples/safe_runbook.json` | 6 | confirm_quorum, drain_region, failover_database, scale_service, suppress_alert, toggle_flag | none expected safe labels | none expected | 2 |
| `case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md` | 5 | confirm_quorum, failover_database, pause_queue, toggle_flag | precondition, quorum_before_data_loss_action | precondition, quorum_before_data_loss_action | 0 |
| `case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` | 2 | rebalance_consumers, replay_messages | no_duplicate_processing_risk, no_rebalance_to_zero_consumers, no_replay_without_dedupe, no_unstable_consumer_group_with_backlog, queue_backlog_requires_consumers | no_duplicate_processing_risk, no_rebalance_to_zero_consumers, no_replay_without_dedupe, no_unstable_consumer_group_with_backlog, queue_backlog_requires_consumers | 1 |
| `examples/credential_rotation_runbook.json` | 2 | revoke_credential, rotate_credential | credential_active, effect_annotation_required, unsafe_retry_annotation | none expected | 1 |

The test suite asserts that each expected action name, dependency edge, state-variable name, native checker property label, exported safety-property label, and proof-obligation id remains synchronized across TLA+, Alloy, and JSON proof-obligation output.
