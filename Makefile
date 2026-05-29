.PHONY: test smoke verify export
PYTHONPATH := src
export PYTHONPATH

test:
	python3 -m unittest discover -s tests

smoke:
	python3 -m runbook_verify.cli check examples/safe_runbook.json
	python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations

verify:
	python3 -m runbook_verify.cli check examples/safe_runbook.json
	python3 -m runbook_verify.cli check examples/unsafe_runbook.json --expect-violations

export:
	python3 -m runbook_verify.cli export examples/safe_runbook.json --format tla
