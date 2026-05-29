# Counterexample remediation playbooks

These playbooks translate recurring `frv check`, `frv audit`, and `frv readiness` findings into reviewable runbook edits. They are not automatic proof repairs; the operator must confirm the operational facts and regenerate the relevant reports.

## Insufficient replicas or drained capacity

- Signals: `service_min_available`, `no_draining_all_replicas`, `dns_requires_regional_capacity`, or `cache_warmup_before_traffic`.
- Evidence commands: `PYTHONPATH=src python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations` and `PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md --expect-violations`.
- Runbook edits: add a modeled `scale_service`, `restore_replica`, `restore_load_balancer`, or target-region capacity precondition before traffic movement or replica drain steps.
- Review checks: `frv diff old.md new.md --format markdown` should show resolved capacity counterexamples without introducing assumption weakenings.

## Missing backup, restore, or data-safety guard

- Signals: `quorum_before_data_loss_action`, `precondition`, `data-deletion-needs-restore-precondition`, or destructive-delete prose findings.
- Evidence commands: `PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations --format json` and `PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format markdown --expect-findings`.
- Runbook edits: model `confirm_quorum`, include a restore/snapshot precondition in `requires`, identify the exact target scope, and link any public limitation to an auditable suppression.
- Review checks: `frv explain PATH finding-001 --format markdown` should point reviewers to the corrected precondition or explicit limitation.

## Skipped alert re-enable or unbounded suppression

- Signals: `bounded_alert_suppression` or stale alert inventory findings.
- Evidence command: `PYTHONPATH=src python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations`.
- Runbook edits: bound alert suppression with a positive duration, add ownership and escalation metadata, and include re-enable instructions in prose when the executable model represents the suppression.
- Review checks: `frv readiness PATH --as-of YYYY-MM-DD --format markdown --fail-on none` should list no expired waiver or stale alert assumptions for the scoped service.

## Premature DNS cutover or finalization

- Signals: `dns_health_check_converged_before_cutover`, `dns_ttl_elapsed_before_finalize`, `dns_no_split_brain_during_ttl`, or `dns_requires_regional_capacity`.
- Evidence command: `PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md --expect-violations`.
- Runbook edits: model target health-check convergence, preserve capacity in the destination region, wait through the TTL window, and only finalize after the wait.
- Review checks: regenerate `coverage` so DNS records, regions, and source sections remain covered by invariant templates.

## Unsafe queue replay or backfill

- Signals: `no_replay_without_dedupe`, `no_duplicate_processing_risk`, `queue_backlog_requires_consumers`, `no_rebalance_to_zero_consumers`, `no_unstable_consumer_group_with_backlog`, or `backfill-needs-queue-capacity`.
- Evidence commands: `PYTHONPATH=src python3 -m runbook_verify.cli check examples/queue_replay_unsafe.json --expect-violations` and `PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/current/grafana_tempo/tempo_runbook_current_impact.md --expect-violations`.
- Runbook edits: require a dedupe key or idempotency proof, keep a positive consumer count, document stable consumer-group state, and add queue capacity/backlog thresholds.
- Review checks: `frv audit PATH --format markdown --expect-findings` should make any remaining prose-only backfill claim explicit rather than implied verified behavior.

## Stale owner, alert, dependency, or replica assumptions

- Signals: `inventory_refinement_precondition`, readiness `stale_assumptions`, or owner-scorecard waiver debt.
- Evidence command: `PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --inventory case_studies/current/grafana_tempo/tempo_inventory_current_impact.json --as-of 2026-05-29 --format markdown --fail-on none`.
- Runbook edits: update `metadata.owners`, alert names, dependency names, and replica counts from the service inventory; if the inventory is intentionally incomplete, document that as a limitation.
- Review checks: `frv owner-scorecard PATH --format markdown --fail-on none` should assign remaining debt to a concrete owner.
