# Property coverage report: case_studies/current/dnsswitch_dns_failover

- Executable runbooks: 1
- Properties mapped: 8
- Services covered: 1/1
- Databases covered: 0/0
- Queues covered: 0/0
- Alerts covered: 0/0
- DNS records covered: 1/1
- Credentials covered: 0/0 (credential state is not implemented in the current DSL)
- Regions covered: 2/2
- Owners: `edge-sre`
- Unverified prose obligations: 0
- Coverage gaps: 0

## Invariant coverage

| Property | Runbook | Owners | Services | Databases | Queues | Alerts | DNS records | Credentials | Regions | Steps/sections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dns_health_check_converged_before_cutover` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  | `checkout.example.com` |  | `east`, `west` | `cutover-dns-west` (L59, DNS cutover TTL and health-check convergence case study)<br>`finalize-before-ttl` (L64, DNS cutover TTL and health-check convergence case study) |
| `dns_no_split_brain_during_ttl` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  | `checkout.example.com` |  | `east`, `west` | `cutover-dns-west` (L59, DNS cutover TTL and health-check convergence case study)<br>`finalize-before-ttl` (L64, DNS cutover TTL and health-check convergence case study) |
| `dns_requires_regional_capacity` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  | `checkout.example.com` |  | `east`, `west` | `cutover-dns-west` (L59, DNS cutover TTL and health-check convergence case study)<br>`finalize-before-ttl` (L64, DNS cutover TTL and health-check convergence case study) |
| `dns_target_region_healthy` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  | `checkout.example.com` |  | `east`, `west` | `cutover-dns-west` (L59, DNS cutover TTL and health-check convergence case study)<br>`finalize-before-ttl` (L64, DNS cutover TTL and health-check convergence case study) |
| `dns_ttl_elapsed_before_finalize` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  | `checkout.example.com` |  | `east`, `west` | `cutover-dns-west` (L59, DNS cutover TTL and health-check convergence case study)<br>`finalize-before-ttl` (L64, DNS cutover TTL and health-check convergence case study) |
| `dns_ttl_elapsed_before_recursion` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  | `checkout.example.com` |  | `east`, `west` | `cutover-dns-west` (L59, DNS cutover TTL and health-check convergence case study)<br>`finalize-before-ttl` (L64, DNS cutover TTL and health-check convergence case study) |
| `no_draining_all_replicas` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  |  |  | `east` |  |
| `service_min_available` | `case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md` | `edge-sre` | `checkout` |  |  |  |  |  | `east` |  |

## Unverified prose obligations

None.

## Coverage gaps

Every modeled service, database, queue, alert, DNS record, region, and prose obligation is linked to a current invariant template.
