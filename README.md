# frv: bounded model checking for operational runbooks

`frv` checks an operational procedure (drain, failover, rollback, restore,
rotate, silence, replay, cutover) before anyone runs it. The procedure is
written as a small typed model: system state, steps, dependencies between
steps, and the checks the runbook tells the operator to make. `frv` explores
dependency-respecting step orders, checks preconditions and post-state safety
invariants, and reports each violation with a minimized trace. A safe verdict
requires a completed search. Budget-limited searches return inconclusive.

```text
$ frv check evaluation/incidents/heroku-redis-credentials-2014-06-23/as_performed.json
Runbook: heroku-redis-credentials-2014-06-23 (as performed)
States explored: 31; terminal traces: 1; max depth reached: False
Violations:
- [service_min_available] ... trace=rotate-redis-1 -> rotate-redis-2:
  step rotate-redis-2 would leave service control-redis with 2 available replicas; requires 3
```

## What it checks

* 36 actions with a state-transformer semantics (`drain_replica`,
  `failover_database`, `rollback_deployment`, `run_migration`, `suppress_alert`,
  `replay_messages`, `flush_cache`, `restore_bucket_snapshot`, `shift_traffic`,
  `update_dns_record`, `rotate_credential`, and others) and 37 condition kinds
  for preconditions and promised effects.
* Built-in invariants: minimum available replicas, no draining all replicas,
  quorum before a lossy failover, no failover to an unhealthy region, no
  rollback across an incompatible migration, bounded alert suppression, write
  freeze before restore, RPO/RTO, traffic and DNS only to regions with
  capacity, DNS TTL and split-brain windows, queue replay deduplication, cache
  write freeze and warm-up.
* Per-runbook assume/guarantee contracts and rely/guarantee entries for
  external actors (for example an autoscaler that may act between steps).
* Breadth-first exploration with state deduplication, restricted
  partial-order reduction for disjoint restart, flag-toggle and alert-suppression steps, and greedy counterexample minimization.

Models are JSON, YAML (with PyYAML) or a Markdown runbook containing one fenced
`runbook-json` block, so the model can sit next to the prose it encodes.
Output is text, JSON, Markdown, SARIF or JUnit. `docs/feature_reference.md`
documents every command (`validate`, `explain`, `diff`, `export` to TLA+/Alloy,
`lint-markdown`, `ci-gate`, and the rest).

## Install and use

```bash
python3 -m pip install -e .          # Python 3.10+, no runtime dependencies
frv check examples/unsafe_runbook.json --expect-violations
frv validate examples/safe_runbook.json
frv explain case_studies/current/grafana_tempo finding-001 --format markdown
```

Without installing: `PYTHONPATH=src python3 -m runbook_verify.cli check <model>`.
Tests: `python3 -m unittest discover -s tests` (129 tests).

## Evaluation

The evaluation lives in `evaluation/`; every number below is produced by a
script listed in `REPRODUCE.md` and stored under `results/`.

**Real incidents.** We screened 42 first-party postmortems of outages caused
or worsened by an operator procedure (`evaluation/incidents/candidates.json`);
39 met the inclusion criteria and 12 are expressible in `frv`'s vocabulary.
Each of the 12 is modeled twice, as performed and with only the safeguards the
postmortem announces, under a translation guide written before modeling and
with the semantics files frozen by hash. The hazard label comes from the
postmortem.

| Method (12 incident pairs) | documented hazard found | remediated accepted | pairs separated |
|---|---|---|---|
| frv (bounded exploration) | 12 | 10 | 10 |
| same semantics, written order only | 12 | 10 | 10 |
| same semantics, each step from the initial state | 5 | 11 | 4 |
| frv prose linter on the procedure text | 2 | 9 | 0 |
| Claude Sonnet 5.5 reviewer | 12 | 11 | 11 |
| Gemini 3.8 Flash reviewer | 12 | 11 | 11 |
| GPT-5.4 mini reviewer | 11 | 7 | 7 |

The two remediated procedures `frv` rejects drain every machine of a pool whose
minimum is zero, which the no-draining-all-replicas invariant flags. Source:
`results/incident_study.json`, `results/llm_reviewer_scores.json`.

**Concurrent maintenance (synthetic).** 50 procedures in which up to 16
operators drain, patch and restore replicas with random cross-dependencies; the
ground truth is the width of the precedence order, computed independently with
Dilworth's theorem. Reanalysis of the saved executions gives 44 correct decisive verdicts and
6 inconclusive results. Exhaustive antichain enumeration independently checks
all 50 recorded width labels. Results: `results/scaling_checkers.json`,
`results/scaling_llm.json` (see the paper for the table).

**Public runbook corpus.** 1,358 Markdown runbooks from GitLab, OpenShift,
prometheus-operator, Grafana Mimir, etcd and kubespray, pinned by commit and
hashed per file (`evaluation/corpus/`). In a seeded sample of 21 files flagged
by the prose linter, 13 contain an operator step of the flagged class and 6 of
those are expressible; `frv` reports one missing obligation (a dead-letter
replay with no stated deduplication). ShellCheck and ansible-lint results on
the same corpus are in `results/static_linters_corpus.json`.

Models and corpus classifications were produced by an LLM-based coding agent
following `evaluation/TRANSLATION_GUIDE.md`; corpus labels are LLM-assisted.
Blinded packets for two human annotators, with a guide and an agreement
script, are in `evaluation/annotation/`.

LLM calls (OpenRouter) are cached in `results/llm_raw/` and logged with cost
in `results/api_costs.jsonl`.

## Verdict boundaries

`check` returns exit code 0 for safe, 1 for a witnessed hazard, and 2 for an
inconclusive search. Depth, state and time budgets are reported in the JSON
performance counters. Preconditions are obligations checked at enabled steps;
step dependencies determine feasible schedules.

A separate stress test covers seven small scenarios across four search
strategies with reduction enabled and disabled. The 56 runs include safe and
unsafe maintenance, dependency-excluded schedules, indirect traffic/capacity
dependence and search cutoffs. Results and the independent small-state oracle
are in `results/journal_audit/` and `audit/journal/stress.py`.

## Paper

`paper/tool_paper.tex` (tables and numbers are generated from `results/` by
`paper/make_tables.py`).

## Citing

```bibtex
@misc{frv2026,
  title  = {Checking Concurrent Operational Procedures by Bounded Exploration of a Typed Runbook Model},
  note   = {Preprint and software, https://github.com/thehalleyyoung/runbook-semantic-verifier},
  year   = {2026}
}
```

## License

MIT (see `LICENSE`). Corpus files are not redistributed; `evaluation/corpus/fetch_corpus.py`
fetches them from their sources under their own licenses.

## Publication artifact and semantic audit

The canonical preprint is [tool_paper.pdf](tool_paper.pdf), built from [paper/tool_paper.tex](paper/tool_paper.tex). The local [research site](index.html) presents scoped results and open gates; `python3 scripts/build_site.py` checks links and stages the Pages artifact. [ZENODO_VERDICT.md](ZENODO_VERDICT.md) records NOT_YET separately from journal readiness. New finite semantic controls and source-worktree provenance are under [audit/wave2](audit/wave2/improvement-report.md).
