# GitHub Oct. 21 2018 check explanations

Safe: `False`

| Finding | Rule | Source | Hoare triple | State delta fields |
| --- | --- | --- | --- | --- |
| `finding-001` | `precondition` | `case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md:87` | `{ all declared step.requires conditions hold } action_effect: enabled action consumes the pre-state { declared requires obligations are true before action }` | databases.mysql-metadata.primary_region |
| `finding-002` | `quorum_before_data_loss_action` | `case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md:87` | `{ database_quorum_confirmed(database) when data_loss_risk=true } action_effect: failover_database may risk data loss { data-loss-risk failover has quorum evidence }` | databases.mysql-metadata.primary_region |
