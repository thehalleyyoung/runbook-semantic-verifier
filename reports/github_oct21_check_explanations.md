Runbook: GitHub Oct21 2018 MySQL failover reconstruction
States explored: 6; terminal traces: 1; max depth reached: False
Small-step rules observed: {"Action.Execute": 5, "ActionGuard.DatabaseFailoverQuorum": 1, "Explore.Terminal": 1, "Schedule.SequenceNext": 5, "StepEnabled.Requires": 1}
Violations:
- [precondition] rule=StepEnabled.Requires source=case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md:95 field=requires[0] trace=orchestrator-failover-to-west: step orchestrator-failover-to-west requires {'kind': 'database_quorum_confirmed', 'database': 'mysql-metadata'}
  hoare: { all declared step.requires conditions hold } action_effect: enabled action consumes the pre-state { declared requires obligations are true before action }
  semantic_trace: Schedule.SequenceNext(orchestrator-failover-to-west) -> StepEnabled.Requires(orchestrator-failover-to-west)
  remediation: Add an ordering dependency or earlier step establishing this precondition.
- [quorum_before_data_loss_action] rule=ActionGuard.DatabaseFailoverQuorum source=case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md:89 field=params trace=orchestrator-failover-to-west: database mysql-metadata failover has data-loss risk before quorum confirmation
  hoare: { database_quorum_confirmed(database) when data_loss_risk=true } action_effect: failover_database may risk data loss { data-loss-risk failover has quorum evidence }
  semantic_trace: Schedule.SequenceNext(orchestrator-failover-to-west) -> ActionGuard.DatabaseFailoverQuorum(orchestrator-failover-to-west)
  remediation: Confirm quorum or explicit data-loss approval before failover.
  synthesized_preconditions: [{"database": "mysql-metadata", "kind": "database_quorum_confirmed"}]
Effect annotation warnings:
- [effect_annotation_required] rule=SafetyInvariant.effect_annotation_required source=case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md:86 field=effect_annotations trace=orchestrator-failover-to-west: step orchestrator-failover-to-west action failover_database must declare reviewed effect_annotations including irreversible_state_change
