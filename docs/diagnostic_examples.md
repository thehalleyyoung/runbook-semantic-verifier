# Editor-friendly JSON diagnostics

`frv validate --diagnostics-format json` emits stable diagnostic objects that can be shown inline by editors, language servers, GitHub annotations, or CI review bots. Diagnostics are syntax/entity obligations only; run `frv check --format json` for semantic counterexamples.

Example command:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli validate tests/fixtures/invalid_json_syntax.json --diagnostics-format json
```

Example payload:

```json
{
  "diagnostics": [
    {
      "field": null,
      "line": 4,
      "message": "invalid JSON in tests/fixtures/invalid_json_syntax.json: Expecting ',' delimiter: line 4 column 5 (char 50)",
      "path": "tests/fixtures/invalid_json_syntax.json",
      "remediation": "Fix the JSON syntax and rerun `frv validate`.",
      "severity": "error"
    }
  ]
}
```

Fields:

- `path` and `line` identify the editor span when available, including lines inside Markdown `runbook-json` blocks.
- `field` names the DSL field for schema/entity errors when the parser can isolate one.
- `severity` is currently `error` for parse/validation failures.
- `remediation` is concise text suitable for an inline quick-fix hint.

For semantic findings, use:

```bash
PYTHONPATH=src python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations --format json
```

Each finding includes `source`, `semantic_trace`, `state_delta`, `causal_dependencies`, `hoare_triple`, and `weakest_precondition_hint`, so review tools can show both the failing line and the proof obligation that failed.
