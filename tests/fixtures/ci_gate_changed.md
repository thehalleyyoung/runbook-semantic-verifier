# CI gate changed runbook

Manually execute SQL update where tenant_id = 7 after quorum is reviewed.

Restore the tenant database from the latest snapshot and resume traffic.

<!-- frv-suppress rule=destructive-delete-needs-targeting owner=docs-sre expires=2099-12-31 reason="scoped fixture deletion is tracked as waiver evidence" link=waiver:ci-gate-delete-fixture -->
Delete the stale index file after owner review.

