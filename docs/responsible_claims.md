# Responsible claims guide

The verifier is useful because it makes runbook assumptions executable and reviewable. It must not be described as proving live cloud safety.

## Claim categories

| Claim | Acceptable wording | Required evidence | Bound |
| --- | --- | --- | --- |
| Checked model safety | No modeled property failed for this runbook within `max_depth`. | `frv check` or `frv audit` output. | Only the DSL abstraction and bounded exploration. |
| Concrete counterexample | The modeled trace violates a named property. | Finding with trace, small-step rule, source span, and remediation hint. | The trace may depend on reconstructed assumptions. |
| Prose audit coverage | Dangerous prose lacks a matching executable guard, effect, or explicit limitation. | `frv lint-markdown`, `frv audit`, `frv coverage`, or `frv scan`. | Pattern-based linting; not natural-language proof. |
| Runtime conformance | Observed logs/events matched or deviated from modeled traces. | Future runtime-verification report. | Does not prove unobserved executions safe. |
| Live infrastructure safety | Avoid making this claim. | Requires production telemetry, system design review, and operator judgment outside this repo. | Out of scope for this artifact. |

## Public case-study wording

- Use "derived public-document fixture", "bounded reconstruction", or "defensive documentation analysis".
- Do not state that a public project is vulnerable unless there is direct, responsible-disclosure-reviewed evidence outside this repository.
- Clearly separate public facts, reconstructed assumptions, and synthetic mutants.

## Benchmark wording

- Use "expected labels" and "oracle-review metadata" only for entries that record those fields.
- Use "operator time saved" only as triage metadata unless a benchmark entry records measured usability data.
- Keep validity threats and responsible-disclosure status adjacent to benchmark results.

## Suppressions and waivers

An `frv-suppress` comment is evidence that a limitation was reviewed with owner/expiry/reason/link metadata. It is not evidence that the operation is safe. Readiness, coverage, scorecards, and CI reports should keep the suppression visible.
