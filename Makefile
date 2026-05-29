.PHONY: test smoke verify export benchmark benchmark-reproduce
PYTHONPATH := src
export PYTHONPATH

test:
	python3 -m unittest discover -s tests

smoke:
	python3 -m runbook_verify.cli check examples/safe_runbook.json
	python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations
	python3 -m runbook_verify.cli benchmark --format json

verify:
	python3 -m runbook_verify.cli check examples/safe_runbook.json
	python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations
	python3 -m runbook_verify.cli check examples/cache_flush_safe.json
	python3 -m runbook_verify.cli check examples/cache_flush_unsafe.json --expect-violations
	python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations
	python3 -m runbook_verify.cli check case_studies/current/dnsswitch_dns_failover/dnsswitch_dns_failover_reconstructed.md --expect-violations
	python3 -m runbook_verify.cli audit case_studies/current/redis_cache_flush --format json --expect-findings
	python3 -m runbook_verify.cli ci-gate case_studies/current/grafana_tempo --format json --expect-blocks
	python3 -m runbook_verify.cli annotate case_studies/current/grafana_tempo --format json --fail-on none
	python3 -m runbook_verify.cli scan case_studies/current/grafana_tempo --format json
	python3 -m runbook_verify.cli diff case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md case_studies/github_oct21_2018/github_oct21_reconstructed_with_quorum_guard.md --format json
	python3 -m runbook_verify.cli owner-scorecard case_studies/current/grafana_tempo --as-of 2026-05-29 --format json --fail-on none
	python3 -m runbook_verify.cli coverage case_studies/current/grafana_tempo --format json
	python3 -m runbook_verify.cli formal-objects case_studies/current/grafana_tempo --format json
	python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format json

export:
	python3 -m runbook_verify.cli export examples/safe_runbook.json --format tla

benchmark:
	python3 -m runbook_verify.cli benchmark --format markdown

benchmark-reproduce:
	python3 scripts/reproduce_benchmarks.py
