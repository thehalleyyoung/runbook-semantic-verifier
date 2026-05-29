# Runtime verification: GitHub Oct21 2018 MySQL failover reconstruction

- Log: `examples/runtime_logs/github_oct21_observed_unsafe.json`
- Conformant: `False`
- Events checked: 2
- Completed steps: `["lock-deployments"]`
- Missing modeled steps: `["orchestrator-failover-to-west", "pause-webhooks", "pause-pages-builds", "confirm-reconciled-topology"]`
- Scope note: Runtime verification checks observed event conformance against the bounded DSL model; it is not live-infrastructure proof.

| Index | Rule | Step | Expected enabled | Trace | Message | Remediation |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `runtime_precondition_violation` | `orchestrator-failover-to-west` | `["orchestrator-failover-to-west"]` | `` | step orchestrator-failover-to-west requires {'kind': 'database_quorum_confirmed', 'database': 'mysql-metadata'} | Add an ordering dependency or earlier step establishing this precondition. |
| 1 | `runtime_precondition_violation` | `orchestrator-failover-to-west` | `["orchestrator-failover-to-west"]` | `` | database mysql-metadata failover has data-loss risk before quorum confirmation | Confirm quorum or explicit data-loss approval before failover. |
