# Native/exported trace-equivalence report

- Pass: `True`
- Cases: 4
- Matched counterexamples: 17
- Missing from export projection: 0

The exported-model side is the checker-derived conformance projection used by the TLA+/Alloy starters: action ids, enabledness edges, and property labels must preserve every native counterexample key. It does not claim TLC/Alloy discharged concrete arithmetic invariants.

| Case | Pass | Native CEX | Exported CEX | Matched | Missing | Unexpected |
| --- | --- | ---: | ---: | ---: | --- | --- |
| github_oct21_reconstructed_runbook.md | `True` | 2 | 2 | 2 | `[]` | `[]` |
| tempo_runbook_current_impact.md | `True` | 6 | 6 | 6 | `[]` | `[]` |
| object_storage_restore_unsafe.json | `True` | 9 | 9 | 9 | `[]` | `[]` |
| credential_rotation_runbook.json | `True` | 0 | 0 | 0 | `[]` | `[]` |
