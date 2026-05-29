# Benchmark: current public runbook impact benchmark

- Pass: `True`
- Runbooks: 1
- States explored: 3
- Traces explored: 1
- Runtime seconds: 0.000828
- Violations by property: `{"no_paused_queue_with_backlog": 1, "no_queue_pause_without_drain_plan": 1}`
- Prose findings by rule: `{"destructive-delete-needs-targeting": 2}`

| Runbook | Pass | Safe | States | Traces | Runtime (s) | Violations | Prose findings | Expected labels |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| Grafana Tempo current public runbook derived safety model | `True` | `False` | 3 | 1 | 0.000820 | `{"no_paused_queue_with_backlog": 1, "no_queue_pause_without_drain_plan": 1}` | `{"destructive-delete-needs-targeting": 2}` | `{"expected_prose_rules": ["destructive-delete-needs-targeting"], "expected_safe": false, "expected_violation_properties": ["no_paused_queue_with_backlog", "no_queue_pause_without_drain_plan"]}` |
