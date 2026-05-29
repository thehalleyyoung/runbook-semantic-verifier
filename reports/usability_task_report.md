# SRE-style usability task report

- Pass: `True`
- Tasks: 3
- Trace-step reduction from minimization: 56
- Generated precondition hints: 113
- Generated JSON patches: 113

This is an instrumented task proxy over checked-in fixtures, not a human-subjects claim: it measures whether each repair task receives minimized traces and generated precondition/patch hints instead of only raw model-checker output.

| Task | CEX | Hinted CEX | Raw steps | Minimized steps | Hints | Patches | Properties |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| repair Unsafe emergency rollback and evacuation | 121 | 110 | 402 | 346 | 110 | 110 | `["bounded_alert_suppression", "no_draining_all_replicas", "no_failover_to_unhealthy_region", "no_rollback_during_incompatible_migration", "quorum_before_data_loss_action", "service_min_available"]` |
| repair GitHub Oct21 2018 MySQL failover reconstruction | 2 | 1 | 2 | 2 | 1 | 1 | `["precondition", "quorum_before_data_loss_action"]` |
| repair Grafana Tempo current public runbook derived safety model | 6 | 2 | 10 | 10 | 2 | 2 | `["no_duplicate_processing_risk", "no_rebalance_to_zero_consumers", "no_replay_without_dedupe", "no_unstable_consumer_group_with_backlog", "queue_backlog_requires_consumers"]` |
