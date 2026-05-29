# Semantic diff: github_oct21_reconstructed_runbook.md → github_oct21_reconstructed_with_quorum_guard.md

- Pass: `True`
- Old safe: `False`
- New safe: `True`
- Changes: 1
- Effect changes: 0
- Assumption changes: 0
- Invariant changes: 0
- Safety-relevant changes: 1
- Assumption weakenings: 0
- Introduced counterexamples: 0
- Resolved counterexamples: 2
- Persisting counterexamples: 0

## Changed semantics

| Classification | Kind | Object | Field | Old | New |
| --- | --- | --- | --- | --- | --- |
| `safety_relevant` | `step_order_changed` | `runbook` | `steps` | `["orchestrator-failover-to-west", "lock-deployments", "pause-webhooks", "pause-pages-builds", "confirm-reconciled-topology"]` | `["confirm-reconciled-topology", "orchestrator-failover-to-west", "lock-deployments", "pause-webhooks", "pause-pages-builds"]` |

## Counterexample delta

### Introduced

None.

### Resolved

- `[precondition]` step `orchestrator-failover-to-west` trace `orchestrator-failover-to-west`: step orchestrator-failover-to-west requires {'kind': 'database_quorum_confirmed', 'database': 'mysql-metadata'}
- `[quorum_before_data_loss_action]` step `orchestrator-failover-to-west` trace `orchestrator-failover-to-west`: database mysql-metadata failover has data-loss risk before quorum confirmation

### Persisting

None.

## Proof-obligation delta

```json
{
  "action_defined": {
    "checked": {
      "delta": 0,
      "new": 5,
      "old": 5
    },
    "failures": {
      "delta": 0,
      "new": 0,
      "old": 0
    }
  },
  "precondition": {
    "checked": {
      "delta": -1,
      "new": 1,
      "old": 2
    },
    "failures": {
      "delta": -2,
      "new": 0,
      "old": 2
    }
  },
  "promised_effect": {
    "checked": {
      "delta": 0,
      "new": 0,
      "old": 0
    },
    "failures": {
      "delta": 0,
      "new": 0,
      "old": 0
    }
  },
  "safety_postcondition": {
    "checked": {
      "delta": 0,
      "new": 60,
      "old": 60
    },
    "failures": {
      "delta": 0,
      "new": 0,
      "old": 0
    }
  }
}
```
