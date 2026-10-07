# Reproducing the evaluation

All commands run from the repository root with Python 3.10+ and no third-party
packages, except where noted. Every number in `paper/tool_paper.tex` and the
README comes from a file under `results/` written by one of these commands.

## 0. Tests

```bash
python3 -m unittest discover -s tests          # 122 tests; log: results/tests_after_fix.log
python3 evaluation/check_frozen.py             # semantics files match evaluation/FROZEN_SEMANTICS.json
```

## 1. Public runbook corpus

```bash
python3 evaluation/corpus/fetch_corpus.py      # clones 6 repositories at pinned commits; writes manifest.csv
python3 evaluation/run_corpus_lint.py          # results/corpus_lint_summary.json, corpus_lint_findings.jsonl
```

Static linters (needs `pip install ansible-lint shellcheck-py`; versions used:
ansible-lint 26.9.0, ShellCheck 0.11.0):

```bash
python3 evaluation/baselines/run_static_linters.py --bin-dir <venv>/bin
# results/static_linters_corpus.json, shellcheck_findings.jsonl, ansible_lint_findings.json
```

## 2. RQ1: postmortem-grounded incidents

```bash
python3 evaluation/incidents/build_incidents.py    # writes evaluation/incidents/<id>/ and not_expressible.json
python3 evaluation/run_incident_study.py           # results/incident_study.json, incident_study.csv
```

The screened candidate list (42 first-party reports, with verification notes)
is `evaluation/incidents/candidates.json`.

## 3. LLM baselines (OpenRouter; cached)

```bash
export OPENROUTER_API_KEY=...                      # only needed for uncached calls
python3 evaluation/baselines/llm_reviewer.py       # results/llm_reviewer_incidents.json
python3 evaluation/score_llm_reviewer.py           # results/llm_reviewer_scores.json
python3 evaluation/annotation/llm_label_packet.py  # results/llm_labels_findings_*.csv (LLM-assisted labels)
python3 evaluation/annotation/score_packet.py      # results/packet_a_scores.json
```

Every response is cached in `results/llm_raw/` under the hash of its request,
so re-running replays the recorded responses at no cost. Every paid call is
logged with model and cost in `results/api_costs.jsonl`.

## 4. RQ3: applicability on a random sample of public runbooks

```bash
python3 evaluation/sample_modeling_set.py          # seeded sample (seed 2026): evaluation/modeled_runbooks/sample.json
python3 evaluation/modeled_runbooks/build_and_check.py   # results/corpus_models_check.json
```

## 5. RQ4: concurrent maintenance (synthetic)

```bash
python3 evaluation/scaling/generate.py             # 50 instances with width oracle (seed 11)
python3 evaluation/scaling/run_checkers.py         # results/scaling_checkers.json
python3 evaluation/scaling/run_llm.py              # results/scaling_llm.json
```

## 6. Human annotation (not yet performed)

```bash
python3 evaluation/annotation/build_finding_packet.py   # packet A (217 items, blinded; key kept separately)
python3 evaluation/annotation/build_model_packet.py     # packet B (model faithfulness, finding validity)
python3 evaluation/annotation/agreement.py A1.csv A2.csv --column label
```

See `evaluation/annotation/ANNOTATION_GUIDE.md`.

## 7. Paper tables

```bash
python3 paper/make_tables.py                       # paper/tables.tex from results/*.json
cd paper && pdflatex tool_paper && bibtex tool_paper && pdflatex tool_paper && pdflatex tool_paper
```
