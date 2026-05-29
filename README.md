# Formal Runbook Verification for Cloud Incident Response

A standalone, engineering prototype that turns incident runbooks into executable, bounded-model-checkable specifications. The thesis is that production runbooks should be treated like critical programs: parsed, simulated, checked against safety properties, and exportable to a formal model before an incident happens.

Current roadmap status: **44/100** items in the local roadmap are complete. The
implemented artifact includes parser/schema validation, bounded checking,
small-step semantic rule traces, denotational action contracts, Hoare-style
finding obligations, weakest-precondition templates, JSON explanation traces,
editor-friendly diagnostic examples, formal object maps, Markdown audits,
semantic diffs, explanations, readiness reports, owner
scorecards, property-coverage reports, repository/wiki runbook-priority scans,
CI gates and pull-request annotations for high-risk operations prose, auditable prose suppressions, Markdown autofix suggestions for reviewable
runbook edits, named configuration profiles for production/advisory/docs-only/benchmark workflows,
inventory-refinement checks for stale service, owner, alert, dependency, and
replica-count assumptions,
queue replay/DLQ/consumer-group semantics, DNS cutover semantics,
cache flush/warmup/cold-start/capacity semantics, and checked-in
historical/current public case-study evidence.

## Quickstart

```bash
cd /Users/halleyyoung/Documents/repo/formal-runbook-verification-repo
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m runbook_verify.cli check examples/safe_runbook.json
PYTHONPATH=src python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli check examples/queue_replay_safe.json
PYTHONPATH=src python3 -m runbook_verify.cli check examples/queue_replay_unsafe.json --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli check examples/cache_flush_safe.json
PYTHONPATH=src python3 -m runbook_verify.cli check examples/cache_flush_unsafe.json --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli export examples/safe_runbook.json --format tla
PYTHONPATH=src python3 -m runbook_verify.cli schema
PYTHONPATH=src python3 -m runbook_verify.cli validate examples/safe_runbook.json
PYTHONPATH=src python3 -m runbook_verify.cli validate docs/schema/examples/complete_runbook.json
PYTHONPATH=src python3 -m runbook_verify.cli validate tests/fixtures/invalid_json_syntax.json --diagnostics-format json
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations --format json
PYTHONPATH=src python3 -m runbook_verify.cli audit examples/real_world --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format markdown --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format sarif --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format junit --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli coverage case_studies/current/dnsswitch_dns_failover --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/redis_cache_flush --format markdown --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli explain case_studies/current/grafana_tempo finding-001 --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli diff case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --service tempo-query --region prod --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli readiness case_studies/current/grafana_tempo --service tempo-query --region prod --inventory case_studies/current/grafana_tempo/tempo_inventory_current_impact.json --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli owner-scorecard case_studies/current/grafana_tempo --as-of 2026-05-29 --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli coverage case_studies/current/grafana_tempo --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli lint-markdown case_studies/current/grafana_tempo --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli scan case_studies/current/grafana_tempo --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate case_studies/current/grafana_tempo --format markdown --expect-blocks
PYTHONPATH=src python3 -m runbook_verify.cli profiles --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate case_studies/current/grafana_tempo --format markdown --profile advisory-research
PYTHONPATH=src python3 -m runbook_verify.cli annotate case_studies/current/grafana_tempo --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli formal-objects case_studies/current/grafana_tempo --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/current_impact.json --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown --profile benchmark-reproduction
```

Optional editable install:

```bash
python3 -m pip install -e .
frv check examples/safe_runbook.json
```

## Example output

The unsafe example intentionally contains: draining all service replicas, failover to an unhealthy region, data-loss-risk failover before quorum confirmation, rollback during an incompatible migration, and an unbounded alert suppression. The checker explores dependency-respecting action orders and reports concrete traces plus mirrored small-step rule names such as:

```text
[service_min_available] rule=ActionPreserves.ServiceAvailability trace=drain-api-1 -> drain-api-2: service api has 0 available replicas; requires 1
[quorum_before_data_loss_action] rule=ActionGuard.DatabaseFailoverQuorum trace=failover-orders-west: database orders failover has data-loss risk before quorum confirmation
```

## DSL

Executable examples use JSON so the repository runs with the Python standard library. YAML files are accepted only when `PyYAML` is installed; otherwise the parser raises a clear error rather than silently falling back. Markdown files are also accepted when they contain one fenced `runbook-json` block, which lets teams audit wiki-style runbooks without abandoning prose documentation.

Top-level fields:

- `system`: regions, services/replicas, databases, queues, caches, alerts, feature flags, deployments, traffic routes, DNS records.
- `steps`: runbook actions with `id`, `action`, `params`, optional `after`, `requires`, and `effects`.
- `allow_reordering`: when true, the checker explores any order satisfying `after` dependencies.
- `max_depth`: bound for state-space exploration.
- `safety`: checker configuration such as maximum alert suppression duration.
- `metadata.labels`: optional benchmark labels such as `expected_safe`,
  `expected_violation_properties`, and `expected_prose_rules`.

The parser validates supported actions using typed field descriptors shared by
parser checks, JSON Schema generation, the action semantics reference, and
formal exporter comments. It rejects missing/unknown parameters, type errors,
numeric bounds, condition kinds, duplicate step ids, duplicate replica ids,
unachievable `min_available` targets unless explicitly waived, acyclic
dependencies, entity references, generated scale-replica id collisions, and
deployment/service version inconsistency before checking. `frv validate` runs
these parse/schema/entity checks without state-space exploration. Parse failures
can be emitted as structured JSON diagnostics with `path`, `line`, `field`,
`severity`, `message`, and `remediation` for editor and CI annotations. `frv
schema` prints the JSON Schema for editor, registry, and CI integration; the
canonical checked-in artifact lives at `docs/schema/runbook.schema.json`. See
`docs/schema/examples.md`, `docs/schema/examples/complete_runbook.json`,
`docs/schema/compatibility_policy.md`, `docs/action_semantics.md`,
`docs/small_step_semantics.md`, `docs/weakest_preconditions.md`, and
`docs/diagnostic_examples.md` for a commented prose walkthrough, strict JSON
fixture covering every supported top-level field, schema versioning/deprecation
guarantees, generated action/condition semantics tables with denotational state
transformers, scheduling / action / wait / failure / budget rules mirrored in
traces, weakest-precondition templates, and editor-ready diagnostic payloads:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli schema
PYTHONPATH=src python3 -m runbook_verify.cli validate examples/safe_runbook.json
PYTHONPATH=src python3 -m runbook_verify.cli validate docs/schema/examples/complete_runbook.json
PYTHONPATH=src python3 -m runbook_verify.cli validate tests/fixtures/invalid_json_syntax.json --diagnostics-format json
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations --format json
```
Supported actions include `restart_service`, `drain_replica`, `restore_replica`,
`drain_region`, `rollback_deployment`, `failover_database`, `confirm_quorum`,
`suppress_alert`, `scale_service`, `toggle_flag`, `run_migration`,
`finish_migration`, `pause_queue`, `resume_queue`, `replay_messages`,
`drain_dead_letter_queue`, `rebalance_consumers`, `freeze_cache_writes`,
`resume_cache_writes`, `flush_cache`, `warm_cache`, `wait`, and
`mark_region_health`, plus traffic actions `shift_traffic`,
`failover_traffic`, `drain_load_balancer`, and `restore_load_balancer`, and
DNS actions `update_dns_record`, `mark_dns_health_check`, and
`finalize_dns_record`.

## Safety properties

The prototype checks pragmatic cloud-operations hazards:

- no service below `min_available` replicas;
- no draining all replicas of a service;
- no rollback during an incompatible schema migration;
- no alert suppression without a bounded positive expiry;
- no data-loss-risk database action before quorum confirmation;
- no failover to an unhealthy target region;
- no pausing a backlog-heavy queue without a drain/consumer plan;
- no replaying messages without a dedupe key, idempotency proof, or positive
  dedupe window; no draining/replaying from an empty or undersized DLQ; no
  backlog left with zero consumers or an unstable consumer group; and no
  duplicate-processing risk after unsafe replay;
- no weighted traffic to unhealthy regions, drained load balancers, or regions
  lacking available service capacity, and route weights must remain normalized
  to 100%;
- no DNS cutover to unhealthy or capacity-less regions, no cutover before target
  health-check convergence, no premature DNS finalization before the TTL window
  elapses, and no stateful split-brain DNS window unless explicitly modeled as
  active-active safe;
- no destructive shared-cache flush without write freeze, no resuming traffic or
  writes before modeled cache warmup reaches threshold, no warmup beyond modeled
  cache capacity, and no stale-read-risk state left after a flush;
- declared step preconditions and effects must hold.

## Architecture

```text
src/runbook_verify/
  model.py      immutable domain model for systems and runbooks
  parser.py     JSON loader plus optional YAML support
  actions.py    operational semantics for runbook actions
  contracts.py  denotational action contracts, Hoare triples, weakest preconditions
  checker.py    bounded state-space explorer and safety checker
  explanation.py finding ids plus rule/source/state-delta explanations
  markdown_lint.py static/prose linter for dangerous unmodeled Markdown
  exporter.py   TLA+/Alloy-like text exporters
  benchmark.py  benchmark harness and JSON/Markdown result renderers
  semantic_diff.py PR-oriented semantic diff and counterexample delta
  readiness.py  incident-readiness aggregation over checks, audits, freshness
  owner_scorecard.py  owner/team scorecards for hazards, waivers, and remediation history
  coverage.py   property-to-entity/owner/Markdown-section coverage reports
  repository_scan.py  Markdown/wiki runbook discovery and model-first prioritization
  ci_gate.py    CI gate for new high-risk operations prose and owner-approved waivers
  pr_annotations.py  pull-request annotations grouped by obligation and source span
  formal_objects.py  object-to-CLI map for syntax, stores, traces, hazards, diagnostics, waivers, and benchmark labels
  profiles.py   named CLI exit-policy profiles for production/advisory/docs/benchmark use
  cli.py        command-line interface
examples/       safe, unsafe, and real-world-style benchmark runbooks
case_studies/   public historical reconstructed executable fixtures
benchmarks/     reusable benchmark suite config files
docs/           claims, evidence, and reproducibility notes
tests/          parser, checker, CLI, exporter, and example tests
```

The checker is deliberately small: it models a runbook as a finite set of steps,
enumerates all dependency-respecting traces up to `max_depth`, applies action
semantics to immutable system states, deduplicates canonical states, and records
safety violations with shortest traces and remediation hints.

`frv check --format json` emits the same counterexamples as structured
explanation records. Each finding includes the small-step trace, source line,
causal dependencies, state delta, Hoare triple, and weakest-precondition hint
needed by editor integrations or review bots:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli check \
  case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md \
  --expect-violations --format json
```

## Real-world finding workflow

The repo is designed to audit real operational material, not only toy JSON examples. For a Markdown runbook in a wiki, incident-response repo, or service catalog, add a single executable `runbook-json` block that models the system state and operational steps, then run:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli audit path/to/runbooks --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli lint-markdown path/to/runbooks --expect-findings
```

`examples/real_world/kubernetes_region_failover.md` is a case-study fixture modeled on common cloud failover mistakes. The audit confirms three concrete bugs: suppressing an alert for longer than policy allows, draining all available API replicas in a region before replacement capacity exists, and performing a data-loss-risk database failover before quorum confirmation.

`frv scan` ranks repository/wiki Markdown files by dangerous-effect vocabulary,
uncovered semantic obligations, and whether a fenced executable model is already
present. This helps teams decide which operational docs need `runbook-json`
models first before relying on audit/check results:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli scan path/to/runbooks --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli scan case_studies/current/grafana_tempo --format json
```

The checked-in outputs `reports/current_impact_scan.md` and
`reports/current_impact_scan.json` rank the Grafana Tempo-derived public fixture
as `critical` (score 52) because destructive-delete, data-deletion, and
backfill/replay prose map to uncovered blast-radius, restore-path, queue,
consumer, deduplication, and explicit-limitation obligations. The scan is a
triage signal, not proof of live-service risk.

`frv audit` now combines executable checking with severity-ranked Markdown/wiki
prose findings. Each prose rule links to a semantic obligation or explicit
limitation. Reports can be emitted as terminal text, JSON, Markdown, SARIF 2.1.0
for GitHub code scanning, or JUnit XML for CI test dashboards; CI thresholds are
tunable:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format json --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format sarif --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli audit case_studies/current/grafana_tempo --format junit --fail-on error
PYTHONPATH=src python3 -m runbook_verify.cli explain case_studies/current/grafana_tempo finding-001 --format json
PYTHONPATH=src python3 -m runbook_verify.cli lint-markdown path/to/runbooks --fail-on error
```

Audit JSON and Markdown reports include deterministic `finding-NNN` ids. `frv
explain` recomputes the same ordered finding set for a file or directory and
expands one id into the relevant small-step rule, shortest trace, declared
causal dependencies, mirrored `semantic_trace`, source line/excerpt, state delta
before/after the failing step when executable, weakest-precondition hint, and bounded remediation
examples. This is intended for review comments and incident-readiness drills,
not for claiming unsound proof beyond the modeled DSL abstraction.

`frv ci-gate` is the CI-facing policy layer for high-risk operations docs. With a
`--baseline`, matching prose findings are treated as existing debt while new
unsafe deletion, credential, traffic/capacity, failover, manual SQL, cache, and
data-restoration instructions block unless the linter sees an auditable
owner/expiry/reason waiver. Without a baseline, all high-risk findings are
treated as new:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate path/to/changed/runbooks --baseline path/to/main/runbooks
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate case_studies/current/grafana_tempo --format markdown --expect-blocks
```

The checked-in `reports/current_impact_ci_gate.md` and
`reports/current_impact_ci_gate.json` validate the gate on the Tempo-derived
public fixture: two destructive/data-restoration findings block, while the
ring-forget excerpt is reported as owner-approved waiver evidence rather than
silently skipped.

`frv annotate` emits pull-request-review annotations from the same audit/check
finding set, grouped by semantic obligation and source span. GitHub Actions
format uses workflow annotation commands; JSON and Markdown keep the grouping
explicit for bots and reviewer summaries:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli annotate \
  case_studies/current/grafana_tempo --format github --fail-on error
PYTHONPATH=src python3 -m runbook_verify.cli annotate \
  case_studies/current/grafana_tempo --format markdown --fail-on none
```

The checked-in `reports/current_impact_annotations.md`,
`reports/current_impact_annotations.json`, and
`reports/current_impact_annotations.github.txt` validate this on the
Tempo-derived public fixture: 10 annotations are grouped into 10
obligation/source-span groups, including queue replay small-step violations,
destructive-data prose obligations, and the audited limitation suppression.

`frv profiles` makes those policy choices reproducible. Profiles set default
exit policies only when `--fail-on` is not explicitly supplied; they do not
change parser validation, action semantics, bounded exploration, or finding
content:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli profiles --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli ci-gate \
  case_studies/current/grafana_tempo --format markdown \
  --profile advisory-research
PYTHONPATH=src python3 -m runbook_verify.cli benchmark \
  benchmarks/builtin.json --format markdown --profile benchmark-reproduction
```

The checked-in `reports/current_impact_ci_gate_advisory_profile.md` shows the
Tempo-derived fixture retains the same two blocking findings and one waiver
while exiting successfully for non-blocking advisory review. The checked-in
`reports/builtin_benchmark_profile.md` records the benchmark-reproduction
profile alongside the public benchmark metrics. See
`docs/configuration_profiles.md`.

`frv formal-objects` makes the verifier's mathematical boundary inspectable. It
maps syntax, entity universe, immutable store, bounded traces, hazards, prose
observations, diagnostics, waivers, and benchmark labels to concrete CLI JSON
fields so reviewers can see which public-case evidence is a checked semantic
object and which evidence is advisory metadata:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli formal-objects \
  case_studies/current/grafana_tempo --format markdown
```

The checked-in `reports/current_impact_formal_objects.md` and
`reports/current_impact_formal_objects.json` validate this on the
Tempo-derived public fixture: one executable runbook maps two queue-action
steps, one `tenant-index-fallback-scan` queue, six bounded hazard
counterexamples, four prose observations, and one auditable limitation waiver to
the same JSON-field families consumed by audit, readiness, coverage, and
benchmark workflows.

`frv readiness` turns validation, bounded checking, Markdown audit, service and
region coverage, rollback/restore coverage, source freshness, optional inventory
refinement, and Hoare-style proof-obligation counters into a service- or
region-scoped incident-readiness report:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli readiness \
  case_studies/current/grafana_tempo \
  --service tempo-query --region prod --as-of 2026-05-29 \
  --format markdown --fail-on none
PYTHONPATH=src python3 -m runbook_verify.cli readiness \
  case_studies/current/grafana_tempo \
  --service tempo-query --region prod \
  --inventory case_studies/current/grafana_tempo/tempo_inventory_current_impact.json \
  --as-of 2026-05-29 --format markdown --fail-on none
```

The checked-in outputs `reports/current_impact_readiness.md` and
`reports/current_impact_readiness.json` report `not_ready` for the derived Tempo
fixture because the model has six bounded queue replay/consumer-group
counterexamples, three unsuppressed destructive/data-deletion/backfill prose
claims, and one audited explicit-limitation suppression. With
`--inventory`, readiness also checks the runbook as a refinement of a configured
service inventory: modeled services must be present, owner/alert/dependency names
must match configured identifiers, and modeled replica counts must match the
declared current assumption. The checked-in
`reports/current_impact_inventory_readiness.md` and
`reports/current_impact_inventory_readiness.json` validate this on the bounded
Tempo fixture inventory by reporting a `replica_count_mismatch`,
`missing_service_alert`, and `missing_dependency` under the formal
`inventory_refinement_precondition` obligation.

`frv owner-scorecard` groups the same bounded semantic and prose-audit evidence
by owner metadata (`metadata.owners`, `metadata.owner`, `metadata.team`, or
`metadata.service_owners`) and reports verified runbooks, open hazards, stale
assumptions, waiver debt, proof-obligation failures, and recent remediation
history:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli owner-scorecard \
  case_studies/current/grafana_tempo --as-of 2026-05-29 \
  --format markdown --fail-on none
```

The checked-in outputs `reports/current_impact_owner_scorecard.md` and
`reports/current_impact_owner_scorecard.json` assign the derived Tempo fixture to
`grafana-tempo-public-fixture`, report `not_ready`, and show six bounded queue
counterexamples plus destructive-data/backfill prose obligations and one audited
prose suppression as
owner-visible remediation debt.

`frv coverage` maps each current invariant template to the services, databases,
queues, caches, alerts, DNS records, credentials (currently no credential state in the
DSL), owners, regions, and Markdown sections it covers:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli coverage \
  case_studies/current/grafana_tempo --format markdown
```

The checked-in coverage outputs `reports/current_impact_coverage.md` and
`reports/current_impact_coverage.json` show that the Tempo-derived fixture's
`tempo-query` service, `tenant-index-fallback-scan` queue, `prod` region, owner,
and executable DSL section are covered by eleven invariant/proof-obligation
templates, while three destructive-data/backfill prose obligations and one
explicit-limitation suppression remain coverage gaps.

The checked-in DNS case-study reports (`reports/dnsswitch_dns_audit.md`,
`reports/dnsswitch_dns_audit.json`, and `reports/dnsswitch_dns_coverage.md`)
show the same report surfaces on a bounded DNS failover fixture.

The checked-in Redis cache-flush reports (`reports/redis_cache_flush_audit.md`,
`reports/redis_cache_flush_audit.json`,
`reports/redis_cache_flush_coverage.md`, and
`reports/redis_cache_flush_coverage.json`) validate the cache semantics on a
bounded fixture derived from a public Redis runbook template that mentions flush
procedures and capacity operations. The model intentionally reports missing
write-freeze, insufficient warmup, over-capacity warmup, and stale-read-risk
obligations; it is not a claim about a live deployment.

Expanded prose rules cover destructive data deletion, data restore from backups
or snapshots, manual SQL, backfills or
replays, cache flush/invalidation, credential handling, customer-notification
gaps, rollback ambiguity, alert suppression, failover, draining, unmodeled
escalation paths, ambiguous operator instructions, stale owner placeholders, and
unsafe copy-paste shell snippets. Backfill or replay prose is tied to executable
backlog, consumer, and deduplication obligations; cache-flush prose is tied to
executable write-freeze, warmup, and capacity obligations. Findings now carry
machine-readable `autofix_suggestions` in JSON and a Markdown summary column for
manual edits such as inserting a `runbook-json` block, adding missing
preconditions/effects, replacing stale owners, tightening vague criteria, or
scoping unsafe shell commands. These suggestions are review aids, not automatic
proof repair. Severity levels are `audit-only`, `warning`, `error`, and
`responsible-disclosure`, with `info` reserved for future advisory checks.

Markdown prose suppressions are supported only when the suppression itself is
auditable:

```markdown
<!-- frv-suppress rule=destructive-delete-needs-targeting owner=team-sre expires=2099-12-31 reason="public excerpt retained as an explicit limitation" link=limitation:ring-forget-targeting -->
```

Missing or malformed `owner`, `expires`, `reason`, or `link` metadata produces
an `invalid-prose-suppression` error and does not hide the original prose
finding. Valid suppressions are emitted as `prose-suppression-applied`
`audit-only` findings so reviews, readiness reports, scorecards, and coverage
reports can see the waiver/limitation contract.

## Current public-doc case study

`case_studies/current/grafana_tempo/tempo_runbook_current_impact.md` analyzes
short, attributed excerpts from Grafana Tempo's public runbook at commit
`ef18cc176e44dea795543f50cb2341f5ea9e7827` (retrieved 2026-05-29). The prose
linter flags destructive `forget/remove/delete`, data-deletion, and replay or
backfill operations that lack executable blast-radius/capacity, restore-path,
consumer, or deduplication preconditions; `reports/current_impact_lint.*` now
includes bounded autofix suggestions for those missing preconditions. The
derived executable model reports
bounded queue fallback replay hazards: replay without dedupe, duplicate
processing risk, rebalancing to zero consumers, and an unstable consumer group
with backlog. One public ring-forget excerpt is intentionally retained with an
auditable `frv-suppress` limitation link, demonstrating that suppressions are
reviewable artifacts rather than silent skips. The
combined audit report is checked in as `reports/current_impact_audit.md` and
`reports/current_impact_audit.json`, with code-scanning/CI equivalents in
`reports/current_impact_audit.sarif` and `reports/current_impact_audit.junit.xml`;
the high-risk prose gate outputs are checked in as
`reports/current_impact_ci_gate.md` and `reports/current_impact_ci_gate.json`;
the pull-request annotation outputs are checked in as
`reports/current_impact_annotations.md`, `reports/current_impact_annotations.json`,
and `reports/current_impact_annotations.github.txt`;
the first finding's explain report is checked in as `reports/current_impact_explain.md` and
`reports/current_impact_explain.json`. The repository scan outputs are checked in as
`reports/current_impact_scan.md` and `reports/current_impact_scan.json`. The
service/region-scoped readiness report is checked in as `reports/current_impact_readiness.md` and
`reports/current_impact_readiness.json`; inventory-refinement readiness evidence
for the bounded fixture inventory in
`case_studies/current/grafana_tempo/tempo_inventory_current_impact.json` is
checked in as `reports/current_impact_inventory_readiness.md` and
`reports/current_impact_inventory_readiness.json`; the owner-facing scorecard is checked in
as `reports/current_impact_owner_scorecard.md` and
`reports/current_impact_owner_scorecard.json`; and the advisory CI profile
evidence is checked in as `reports/current_impact_ci_gate_advisory_profile.md`.

## DNS failover public-pattern case study

`case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md`
is an independently authored bounded model derived from public DNS failover
guidance in `Hotpirsch/dnsswitch` (retrieved 2026-05-29). It demonstrates the
new DNS semantics by reporting a cutover before target health-check convergence,
before west-region service capacity exists, during a stateful TTL split-brain
window, and with premature finalization before TTL expiry. This is a defensive
artifact-level validation, not a claim about a live deployment.

## Redis cache-flush public-template case study

`case_studies/current/redis_cache_flush/redis_cache_flush_public_runbook_derived.md`
is an independently authored bounded model derived from short attributed
excerpts in OneUptime's public Redis operations runbook template (retrieved
2026-05-29). It demonstrates cache flush, write-freeze, warmup threshold,
capacity, and stale-read-risk semantics by reporting an intentionally unsafe
mutant. This validates the checker/report surfaces against public operational
documentation while keeping the claim bounded to the modeled artifact.

## Historical public case study

`case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md`
contains a reconstructed executable fixture derived from GitHub's public
October 21, 2018 post-incident analysis:
<https://github.blog/news-insights/company-news/oct21-post-incident-analysis/>.

This is **not** original GitHub runbook text. It transparently models public
facts from the incident: a brief network partition, MySQL/Orchestrator failover
to US West, unreplicated writes in US East, pausing webhook and Pages work to
protect data integrity, and a recovery plan based on backup restoration and
replica synchronization. The modeled safety failure is a data-loss-risk
database failover before the DSL's explicit quorum/data-safety precondition has
been confirmed. `reports/github_oct21_check_explanations.json` and
`reports/github_oct21_check_explanations.md` show the same bounded finding as
review-tool-ready JSON/Markdown with source line, state delta, Hoare triple, and
weakest-precondition evidence.

Run it directly:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations
```

For pull-request review, `frv diff old new` compares two executable runbook
models as programs rather than as text. It classifies changed step order,
actions, preconditions, effects, state assumptions, and verification settings;
then it reports introduced, resolved, and persisting counterexample traces plus
proof-obligation deltas. By default it exits non-zero only for semantic
regressions, so it can gate unsafe changes while allowing remediation diffs:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli diff \
  case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md \
  case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md \
  --format markdown
```

The bounded remediation fixture is not original GitHub procedure text; it is a
public-data-derived variant that moves the quorum/data-safety confirmation
before the modeled failover. Checked-in reports live at
`reports/github_oct21_semantic_diff.md` and
`reports/github_oct21_semantic_diff.json`.

## Benchmark harness

The benchmark command runs the built-in fixtures or a user-provided corpus and
emits JSON or Markdown. Metrics include number of runbooks, states explored,
terminal traces explored, checker performance counters (transitions, branch
factor, reductions, symbolic splits, minimized counterexample trace length, and
proof-obligation outcomes), violations by property, prose findings by rule,
expected labels when present, public benchmark metadata, runtime, and pass/fail.

Built-in suite:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format markdown
```

Reusable config:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown --profile benchmark-reproduction
```

The checked-in `reports/builtin_benchmark.md` records the Markdown output for
the reusable public benchmark config; `reports/builtin_benchmark_profile.md`
records the same suite with the benchmark-reproduction profile metadata.

External corpus:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli benchmark path/to/runbook-or-directory --format markdown
```

Benchmark config files are JSON. Version `1.0` configs are validated against the
public benchmark contract documented by `docs/schema/benchmark.schema.json` and
`docs/schema/benchmark_config.md`; each entry records provenance, license,
abstraction level, expected result, responsible-disclosure status, validity
threats, and semantic feature coverage.

The built-in benchmark currently contains eleven runbooks: safe/unsafe
synthetic regressions, safe/unsafe queue replay mutants, safe/unsafe cache-flush
mutants, one real-world-style Kubernetes failover fixture, the GitHub Oct. 21
2018 reconstructed failover case, the Grafana Tempo current public
runbook-derived replay case, a public DNS-failover-pattern reconstruction, and a
public Redis runbook-template-derived cache-flush mutant.

```json
{
  "benchmark_schema_version": "1.0",
  "name": "my runbook corpus",
  "runbooks": [
    {
      "path": "../case_studies/github_oct21_2018",
      "provenance": { "kind": "public-historical", "source_url": "https://github.blog/news-insights/company-news/oct21-post-incident-analysis/" },
      "license": { "status": "excerpted" },
      "abstraction_level": "reconstructed-public-facts",
      "expected_result": { "safe": false, "violation_properties": ["quorum_before_data_loss_action"], "prose_rules": [] },
      "responsible_disclosure": { "status": "public-information" },
      "validity_threats": ["Reconstructed assumptions may differ from original procedures."],
      "semantic_features": ["database_quorum", "public_historical_case"]
    }
  ]
}
```

## Paper angle

A paper titled _Verifying Incident Runbooks for Cloud-Native Systems_ could evaluate how many injected runbook bugs are caught, how much modeling effort is needed, which production hazards are expressible, and whether operators can understand the DSL. The exporter gives a bridge to TLA+/Alloy-style artifacts for formal-methods credibility while the Python checker keeps experiments reproducible locally.

## LLM-process separation note

This repository is intentionally a non-AI artifact. LLMs may help draft prose, generate synthetic runbooks, or propose adversarial scenarios, but verification results come from explicit parsers, operational semantics, and deterministic state-space exploration. Any future `llm-process/` material should document assistance separately from the verifier's trusted core.

## Limitations

- Bounded exploration is not a full temporal model checker.
- Action semantics are abstract and conservative, not cloud-provider APIs.
- Concurrency is represented as permissible step reordering, not real-time interleavings.
- The TLA+/Alloy exporters are formal-ish starting points, not complete proof obligations.
- The benchmark corpus is small: it includes synthetic examples plus bounded
  public historical/current fixtures for database failover, queue replay/fallback,
  DNS failover patterns, and cache-flush warmup/capacity hazards, and should be
  expanded before empirical claims.
- The historical GitHub fixture is reconstructed from public facts, not exact
  internal runbook text.
- The Markdown workflow requires an embedded executable model; fully automatic extraction from prose is intentionally out of scope for the trusted verifier.

## Claims and evidence

See `docs/claims_evidence.md` for bounded claims, what is and is not proven, and
a reproduction protocol. The repository records exact public artifacts and
commands used for evidence; it does not claim live-infrastructure safety or a
universal proof of novelty.

## License

MIT.
