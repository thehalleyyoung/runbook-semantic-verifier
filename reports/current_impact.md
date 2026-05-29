# Benchmark: current public runbook impact benchmark

- Pass: `True`
- Runbooks: 1
- States explored: 3
- Traces explored: 1
- Runtime seconds: 0.000965
- Performance counters: `{"avg_branch_factor": 1.0, "branch_factor_total": 2, "branch_points": 2, "max_branch_factor": 1, "max_depth_reached": false, "minimized_counterexample_trace_length": 1, "proof_obligation_failures": {"precondition": 1, "safety_postcondition": 1}, "proof_obligations_checked": {"action_defined": 2, "precondition": 1, "promised_effect": 1, "safety_postcondition": 6}, "reductions_applied": 0, "states_explored": 3, "symbolic_splits": 0, "terminal_traces": 1, "transitions_explored": 2}`
- Violations by property: `{"no_paused_queue_with_backlog": 1, "no_queue_pause_without_drain_plan": 1}`
- Prose findings by rule: `{"data-deletion-needs-restore-precondition": 1, "destructive-delete-needs-targeting": 2}`

| Runbook | Pass | Safe | States | Transitions | Max branch | Min CEX trace | Runtime (s) | Violations | Prose findings | Expected labels |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Grafana Tempo current public runbook derived safety model | `True` | `False` | 3 | 2 | 1 | 1 | 0.000954 | `{"no_paused_queue_with_backlog": 1, "no_queue_pause_without_drain_plan": 1}` | `{"data-deletion-needs-restore-precondition": 1, "destructive-delete-needs-targeting": 2}` | `{"expected_prose_rules": ["data-deletion-needs-restore-precondition", "destructive-delete-needs-targeting"], "expected_safe": false, "expected_violation_properties": ["no_paused_queue_with_backlog", "no_queue_pause_without_drain_plan"]}` |
