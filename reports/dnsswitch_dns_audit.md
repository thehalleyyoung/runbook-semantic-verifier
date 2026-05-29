# Runbook audit: case_studies/current/dnsswitch_dns_failover

- Profile: `none`
- Runbooks checked: 1
- Safe runbooks: 0
- Findings: 6
- Findings by severity: `{"error": 6}`
- Findings by rule: `{"dns_health_check_converged_before_cutover": 1, "dns_no_split_brain_during_ttl": 1, "dns_requires_regional_capacity": 3, "dns_ttl_elapsed_before_finalize": 1}`

| Runbook | Safe | States | Traces | Semantic rules | Violations |
| --- | --- | ---: | ---: | --- | ---: |
| `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `False` | 3 | 1 | `{"Action.Execute": 2, "ActionGuard.DNSHealthCheckConverged": 1, "ActionGuard.DNSRegionalCapacity": 3, "ActionGuard.DNSTTLBeforeFinalize": 1, "Explore.Terminal": 1, "PostInvariant.DNSNoSplitBrainDuringTTL": 1, "Schedule.DependencyReady": 2}` | 6 |

| ID | Rank | Type | Severity | Rule | Small-step rule | Obligation | Location | Message | Recommendation | Autofix suggestions |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `finding-001` | 3 | semantic | error | dns_health_check_converged_before_cutover | `ActionGuard.DNSHealthCheckConverged` | `dns_health_check_converged_before_cutover` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md:` | DNS record checkout.example.com target west health check has not converged | Run or wait for DNS health-check convergence before changing the record. |  |
| `finding-002` | 3 | semantic | error | dns_no_split_brain_during_ttl | `PostInvariant.DNSNoSplitBrainDuringTTL` | `dns_no_split_brain_during_ttl` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md:` | DNS record checkout.example.com may answer both east and west until minute 5 | Use an active-active-safe record (allow_split_brain=true) or avoid stateful writes until the TTL window elapses. |  |
| `finding-003` | 3 | semantic | error | dns_requires_regional_capacity | `ActionGuard.DNSRegionalCapacity` | `dns_requires_regional_capacity` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md:` | DNS record checkout.example.com targets west but service checkout has no available replica there | Scale or restore service replicas in the DNS target region before cutover. |  |
| `finding-004` | 3 | semantic | error | dns_requires_regional_capacity | `ActionGuard.DNSRegionalCapacity` | `dns_requires_regional_capacity` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md:` | DNS record checkout.example.com points to west but service checkout has no available replica there | Scale or restore service replicas in the DNS target region before cutover. |  |
| `finding-005` | 3 | semantic | error | dns_requires_regional_capacity | `ActionGuard.DNSRegionalCapacity` | `dns_requires_regional_capacity` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md:` | DNS record checkout.example.com points to west but service checkout has no available replica there | Scale or restore service replicas in the DNS target region before cutover. |  |
| `finding-006` | 3 | semantic | error | dns_ttl_elapsed_before_finalize | `ActionGuard.DNSTTLBeforeFinalize` | `dns_ttl_elapsed_before_finalize` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md:` | DNS record checkout.example.com TTL window has not elapsed before finalize | Insert a wait step long enough to cover the record TTL before finalizing DNS migration. |  |
