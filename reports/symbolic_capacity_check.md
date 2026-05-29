# Symbolic bounded check

- Path: `tests/fixtures/symbolic_capacity_runbook.json`
- Pass: `True`
- Variants: 8
- Symbolic splits: 7

| Bindings | Pass | Safe | States | Violations |
| --- | --- | --- | ---: | --- |
| `{"steps[scale].params.replicas": 1, "steps[wait].params.minutes": 0, "system.services.api.min_available": 1}` | `True` | `True` | 3 | `{}` |
| `{"steps[scale].params.replicas": 1, "steps[wait].params.minutes": 0, "system.services.api.min_available": 2}` | `True` | `False` | 3 | `{"service_min_available": 3}` |
| `{"steps[scale].params.replicas": 1, "steps[wait].params.minutes": 5, "system.services.api.min_available": 1}` | `True` | `True` | 3 | `{}` |
| `{"steps[scale].params.replicas": 1, "steps[wait].params.minutes": 5, "system.services.api.min_available": 2}` | `True` | `False` | 3 | `{"service_min_available": 3}` |
| `{"steps[scale].params.replicas": 2, "steps[wait].params.minutes": 0, "system.services.api.min_available": 1}` | `True` | `True` | 3 | `{}` |
| `{"steps[scale].params.replicas": 2, "steps[wait].params.minutes": 0, "system.services.api.min_available": 2}` | `True` | `True` | 3 | `{}` |
| `{"steps[scale].params.replicas": 2, "steps[wait].params.minutes": 5, "system.services.api.min_available": 1}` | `True` | `True` | 3 | `{}` |
| `{"steps[scale].params.replicas": 2, "steps[wait].params.minutes": 5, "system.services.api.min_available": 2}` | `True` | `True` | 3 | `{}` |
