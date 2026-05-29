# Security and privacy guidance

Runbooks and counterexample traces can expose sensitive operational details. Treat this verifier as a review aid that must preserve secrets, private incident facts, and responsible-disclosure obligations.

## Inputs

- Do not commit credentials, tokens, private hostnames, customer identifiers, or unpublished incident details.
- Prefer sanitized fixtures with stable pseudonyms for services, owners, alerts, and regions.
- For public case studies, store short attributed excerpts or independently authored reconstructions, not copied private runbooks.

## Reports and traces

- `frv check`, `frv audit`, `frv explain`, `frv annotate`, and `frv benchmark` can echo step ids, owner metadata, source excerpts, and counterexample traces. Review outputs before posting them to public issues, pull requests, or papers.
- If a trace reveals a sensitive gap, replace the fixture with a sanitized model and record responsible-disclosure status in benchmark metadata.
- Keep suppressions visible; do not use them to hide sensitive risks from maintainers.

## Credentials and destructive commands

- Model credential rotation or deletion with abstract names only.
- Do not paste runnable destructive shell commands unless they are clearly scoped placeholders and the Markdown linter can treat them as review targets.
- Avoid storing real backup locations, bucket names, database DSNs, or chatops tokens.

## Public disclosure

- Public-current case studies in this repo are defensive documentation analyses. They should be worded as bounded artifact findings, not claims of exploitable live vulnerabilities.
- If future evidence suggests a non-public vulnerability, follow the affected project's disclosure process before publishing detailed traces.

## Data retention

- Keep generated reports that support public claims under version control only after sanitization review.
- Remove local scratch artifacts that contain private source material.
- Ensure benchmark metadata records source license, retrieval date, abstraction level, and validity threats.
