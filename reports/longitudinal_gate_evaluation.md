# Longitudinal semantic-gate evaluation

- Config: `benchmarks/builtin.json`
- Pass: `True`
- Revision pairs: 1
- Would block before merge: 1
- Resolved counterexamples: 2

| Revision pair | Old safe | New safe | Would block before merge | Reason | Summary |
| --- | --- | --- | --- | --- | --- |
| github-oct21-quorum-guard-remediation | `False` | `True` | `True` | pre-existing counterexample debt, remediation resolved counterexamples | `{"assumption_changes": 0, "assumption_weakenings": 0, "behavior_preserving_changes": 0, "changes": 1, "effect_changes": 0, "introduced_counterexamples": 0, "invariant_changes": 0, "new_states_explored": 6, "old_states_explored": 6, "persisting_counterexamples": 0, "proof_obligation_strengthenings": 0, "resolved_counterexamples": 2, "safety_relevant_changes": 1, "waiver_changes": 0}` |
