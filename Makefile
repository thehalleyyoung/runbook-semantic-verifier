.PHONY: test smoke verify export benchmark
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
	python3 -m runbook_verify.cli check case_studies/github_oct21_2018/github_oct21_reconstructed_runbook.md --expect-violations
	python3 -m runbook_verify.cli benchmark benchmarks/builtin.json --format json

export:
	python3 -m runbook_verify.cli export examples/safe_runbook.json --format tla

benchmark:
	python3 -m runbook_verify.cli benchmark --format markdown
