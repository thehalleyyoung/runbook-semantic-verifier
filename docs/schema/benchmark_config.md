# Public benchmark config schema

`frv benchmark` accepts JSON benchmark configs that conform to
`docs/schema/benchmark.schema.json`. Version `1.0` requires every runbook entry
to declare:

- provenance (`synthetic`, `real-world-style`, `public-historical`,
  `public-current`, or `sanitized`), including source URL/commit/date where
  available;
- license status and notes;
- abstraction level, distinguishing toy fixtures from reconstructed public facts
  and derived public runbook models;
- expected safety result, violation properties, and prose-lint rules;
- responsible-disclosure status;
- validity threats; and
- semantic feature coverage.

The benchmark runner validates these fields without adding a JSON Schema runtime
dependency and includes the normalized metadata in JSON and Markdown reports.
This keeps public-data claims bounded and reproducible: results describe the
checked model and its declared evidence limits, not live infrastructure safety.
