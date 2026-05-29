# Formal Runbook Verification for Cloud Incident Response

A standalone, engineering prototype that turns incident runbooks into executable, bounded-model-checkable specifications. The thesis is that production runbooks should be treated like critical programs: parsed, simulated, checked against safety properties, and exportable to a formal model before an incident happens.

## Quickstart

```bash
cd /Users/halleyyoung/Documents/repo/formal-runbook-verification-repo
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m runbook_verify.cli check examples/safe_runbook.json
PYTHONPATH=src python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations
PYTHONPATH=src python3 -m runbook_verify.cli export examples/safe_runbook.json --format tla
PYTHONPATH=src python3 -m runbook_verify.cli audit examples/real_world --expect-findings
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format markdown
```

Optional editable install:

```bash
python3 -m pip install -e .
frv check examples/safe_runbook.json
```

## Example output

The unsafe example intentionally contains: draining all service replicas, failover to an unhealthy region, data-loss-risk failover before quorum confirmation, rollback during an incompatible migration, and an unbounded alert suppression. The checker explores dependency-respecting action orders and reports concrete traces such as:

```text
[service_min_available] trace=drain-api-1 -> drain-api-2: service api has 0 available replicas; requires 1
[quorum_before_data_loss_action] trace=failover-orders-west: database orders failover has data-loss risk before quorum confirmation
```

## DSL

Executable examples use JSON so the repository runs with the Python standard library. YAML files are accepted only when `PyYAML` is installed; otherwise the parser raises a clear error rather than silently falling back. Markdown files are also accepted when they contain one fenced `runbook-json` block, which lets teams audit wiki-style runbooks without abandoning prose documentation.

Top-level fields:

- `system`: regions, services/replicas, databases, queues, alerts, feature flags, deployments.
- `steps`: runbook actions with `id`, `action`, `params`, optional `after`, `requires`, and `effects`.
- `allow_reordering`: when true, the checker explores any order satisfying `after` dependencies.
- `max_depth`: bound for state-space exploration.
- `safety`: checker configuration such as maximum alert suppression duration.
- `metadata.labels`: optional benchmark labels such as `expected_safe` and
  `expected_violation_properties`.

Supported actions include `restart_service`, `drain_replica`, `drain_region`, `rollback_deployment`, `failover_database`, `confirm_quorum`, `suppress_alert`, `scale_service`, `toggle_flag`, `run_migration`, `finish_migration`, `pause_queue`, and `resume_queue`.

## Safety properties

The prototype checks pragmatic cloud-operations hazards:

- no service below `min_available` replicas;
- no draining all replicas of a service;
- no rollback during an incompatible schema migration;
- no alert suppression without a bounded positive expiry;
- no data-loss-risk database action before quorum confirmation;
- no failover to an unhealthy target region;
- declared step preconditions and effects must hold.

## Architecture

```text
src/runbook_verify/
  model.py      immutable domain model for systems and runbooks
  parser.py     JSON loader plus optional YAML support
  actions.py    operational semantics for runbook actions
  checker.py    bounded state-space explorer and safety checker
  exporter.py   TLA+/Alloy-like text exporters
  benchmark.py  benchmark harness and JSON/Markdown result renderers
  cli.py        command-line interface
examples/       safe, unsafe, and real-world-style benchmark runbooks
case_studies/   public historical reconstructed executable fixtures
benchmarks/     reusable benchmark suite config files
docs/           claims, evidence, and reproducibility notes
tests/          parser, checker, CLI, exporter, and example tests
```

The checker is deliberately small: it models a runbook as a finite set of steps, enumerates all dependency-respecting traces up to `max_depth`, applies action semantics to immutable system states, and records safety violations with traces.

## Real-world finding workflow

The repo is designed to audit real operational material, not only toy JSON examples. For a Markdown runbook in a wiki, incident-response repo, or service catalog, add a single executable `runbook-json` block that models the system state and operational steps, then run:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli audit path/to/runbooks --expect-findings
```

`examples/real_world/kubernetes_region_failover.md` is a case-study fixture modeled on common cloud failover mistakes. The audit confirms three concrete bugs: suppressing an alert for longer than policy allows, draining all available API replicas in a region before replacement capacity exists, and performing a data-loss-risk database failover before quorum confirmation.

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
been confirmed.

Run it directly:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations
```

## Benchmark harness

The benchmark command runs the built-in fixtures or a user-provided corpus and
emits JSON or Markdown. Metrics include number of runbooks, states explored,
terminal traces explored, violations by property, expected labels when present,
runtime, and pass/fail.

Built-in suite:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format json
PYTHONPATH=src python3 -m runbook_verify.cli benchmark --format markdown
```

Reusable config:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format json
```

External corpus:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli benchmark path/to/runbook-or-directory --format markdown
```

Benchmark config files are JSON:

```json
{
  "name": "my runbook corpus",
  "runbooks": [
    { "path": "../examples/safe_runbook.json" },
    { "path": "../case_studies/github_oct21_2018" }
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
- The benchmark examples are synthetic and should be expanded before empirical claims.
- The historical GitHub fixture is reconstructed from public facts, not exact
  internal runbook text.
- The Markdown workflow requires an embedded executable model; fully automatic extraction from prose is intentionally out of scope for the trusted verifier.

## Claims and evidence

See `docs/claims_evidence.md` for the precise novelty claim, what is and is not
proven, and a reproduction protocol. In short: we are not aware of an existing
open-source benchmark that converts public outage narratives into executable
runbook safety models and reproduces the safety failure with model checking, but
we do not claim a universal proof that no unpublished or private system exists.

## License

MIT.
