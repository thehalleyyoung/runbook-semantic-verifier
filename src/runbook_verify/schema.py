from __future__ import annotations

import json
from typing import Any

from .contracts import action_denotation
from .descriptors import ACTION_DESCRIPTORS, CONDITION_DESCRIPTORS, FieldDescriptor, OperationDescriptor


def build_json_schema() -> dict[str, Any]:
    """Return the repository's machine-readable runbook DSL schema."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://formal-runbook-verification.local/schema/runbook.schema.json",
        "title": "Formal Runbook Verification DSL",
        "type": "object",
        "additionalProperties": False,
        "required": ["system", "steps"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "metadata": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "owner": {"type": "string"},
                    "owners": {"type": "array", "items": {"oneOf": [{"type": "string"}, {"type": "object", "additionalProperties": True}]}},
                    "service_owners": {"type": "object", "additionalProperties": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]}},
                    "waivers": {"type": "array", "items": {"$ref": "#/$defs/waiver"}},
                    "assume_guarantee_contracts": {"type": "array", "items": {"$ref": "#/$defs/assume_guarantee_contract"}},
                    "rely_guarantee": {"type": "array", "items": {"$ref": "#/$defs/rely_guarantee"}},
                },
            },
            "allow_reordering": {"type": "boolean"},
            "max_depth": {"type": "integer", "minimum": 0},
            "safety": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "max_alert_suppression_minutes": {"type": "integer", "minimum": 1},
                    "exploration_strategy": {"type": "string", "enum": ["breadth_first", "depth_first", "shortest_counterexample", "randomized_bounded", "seeded_chaos_style"]},
                    "exploration_seed": {"type": "integer"},
                    "max_states": {"type": "integer", "minimum": 1},
                    "timeout_seconds": {"type": "integer", "minimum": 0},
                    "fairness": {"type": "string", "enum": ["dependency", "fifo"]},
                    "dominance_pruning": {"type": "boolean"},
                },
            },
            "symbolic": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "choices": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": ["string", "integer", "boolean", "array", "object", "null"]},
                        },
                    },
                },
            },
            "system": {"$ref": "#/$defs/system"},
            "steps": {
                "type": "array",
                "items": {"$ref": "#/$defs/step"},
            },
        },
        "$defs": {
            "system": _system_schema(),
            "step": _step_schema(),
            "condition": _condition_schema(),
            "waiver": _waiver_schema(),
            "assume_guarantee_contract": _assume_guarantee_contract_schema(),
            "rely_guarantee": _rely_guarantee_schema(),
            "effect_annotations": _effect_annotation_schema(),
        },
    }


def render_json_schema() -> str:
    return json.dumps(build_json_schema(), indent=2, sort_keys=True) + "\n"


def _system_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "clock_minute": {"type": "integer", "minimum": 0},
            "regions": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"healthy": {"type": "boolean"}},
                },
            },
            "services": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "min_available": {"type": "integer", "minimum": 0},
                        "allow_unachievable_min_available": {"type": "boolean"},
                        "deployment": {"type": "string"},
                        "replicas": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["region"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "region": {"type": "string"},
                                    "healthy": {"type": "boolean"},
                                    "drained": {"type": "boolean"},
                                },
                            },
                        },
                    },
                },
            },
            "databases": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["primary_region"],
                    "properties": {
                        "primary_region": {"type": "string"},
                        "healthy_regions": {"type": "array", "items": {"type": "string"}},
                        "quorum_confirmed": {"type": "boolean"},
                        "migration_in_progress": {"type": "boolean"},
                        "migration_compatible": {"type": "boolean"},
                    },
                },
            },
            "queues": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "depth": {"type": "integer", "minimum": 0},
                        "consumers": {"type": "integer", "minimum": 0},
                        "paused": {"type": "boolean"},
                        "dead_letter_depth": {"type": "integer", "minimum": 0},
                        "dedupe_window_minutes": {"type": "integer", "minimum": 0},
                        "duplicate_risk": {"type": "boolean"},
                        "consumer_group_stable": {"type": "boolean"},
                    },
                },
            },
            "caches": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["service"],
                    "properties": {
                        "service": {"type": "string"},
                        "warm": {"type": "boolean"},
                        "entries": {"type": "integer", "minimum": 0},
                        "warmup_entries": {"type": "integer", "minimum": 0},
                        "capacity_entries": {"type": "integer", "minimum": 0},
                        "stale_read_risk": {"type": "boolean"},
                        "write_frozen": {"type": "boolean"},
                    },
                },
            },
            "object_buckets": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["region"],
                    "properties": {
                        "region": {"type": "string"},
                        "replicated_regions": {"type": "array", "items": {"type": "string"}},
                        "min_replicated_regions": {"type": "integer", "minimum": 1},
                        "writes_frozen": {"type": "boolean"},
                        "snapshot_available": {"type": "boolean"},
                        "last_snapshot_minute": {"type": "integer", "minimum": 0},
                        "rpo_minutes": {"type": "integer", "minimum": 0},
                        "rto_minutes": {"type": "integer", "minimum": 0},
                        "restore_completed": {"type": "boolean"},
                        "last_restore_minute": {"type": ["integer", "null"], "minimum": 0},
                    },
                },
            },
            "alerts": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "active": {"type": "boolean"},
                        "suppressed_until_minute": {"type": ["integer", "null"], "minimum": 0},
                    },
                },
            },
            "feature_flags": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"enabled": {"type": "boolean"}},
                },
            },
            "deployments": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "service": {"type": "string"},
                        "current": {"type": "string"},
                        "previous": {"type": ["string", "null"]},
                    },
                },
            },
            "traffic_routes": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["service", "weights"],
                    "properties": {
                        "service": {"type": "string"},
                        "weights": {
                            "type": "object",
                            "additionalProperties": {"type": "integer", "minimum": 0, "maximum": 100},
                        },
                        "drained_regions": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "dns_records": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["service", "region"],
                    "properties": {
                        "service": {"type": "string"},
                        "region": {"type": "string"},
                        "ttl_minutes": {"type": "integer", "minimum": 0},
                        "last_changed_minute": {"type": "integer", "minimum": 0},
                        "previous_region": {"type": ["string", "null"]},
                        "health_check_converged_regions": {"type": "array", "items": {"type": "string"}},
                        "allow_split_brain": {"type": "boolean"},
                    },
                },
            },
            "credentials": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "owner": {"type": "string"},
                        "revoked": {"type": "boolean"},
                        "rotation_due_minute": {"type": ["integer", "null"], "minimum": 0},
                    },
                },
            },
        },
    }


def _step_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "action", "params"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "action": {"type": "string", "enum": sorted(ACTION_DESCRIPTORS)},
            "params": {"type": "object"},
            "after": {"type": "array", "items": {"type": "string"}},
            "requires": {"type": "array", "items": {"$ref": "#/$defs/condition"}},
            "effects": {"type": "array", "items": {"$ref": "#/$defs/condition"}},
            "effect_annotations": {"$ref": "#/$defs/effect_annotations"},
        },
        "allOf": [_tagged_object_schema("action", "params", name, descriptor) for name, descriptor in sorted(ACTION_DESCRIPTORS.items())],
    }


def _waiver_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "owner", "expiry", "scope", "rationale", "invariant", "benchmark_visibility"],
        "properties": {
            "id": {"type": "string"},
            "owner": {"type": "string"},
            "expiry": {"type": "string", "format": "date"},
            "scope": {"type": "string"},
            "rationale": {"type": "string"},
            "invariant": {"type": "string"},
            "benchmark_visibility": {"type": "string", "enum": ["blocking", "hidden", "visible"]},
        },
    }


def _assume_guarantee_contract_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "provider", "consumer", "guarantees"],
        "properties": {
            "id": {"type": "string"},
            "provider": {"type": "string"},
            "consumer": {"type": "string"},
            "assumptions": {"type": "array", "items": {"$ref": "#/$defs/condition"}},
            "guarantees": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/condition"}},
            "evidence": {"type": "string"},
            "source_url": {"type": "string"},
            "notes": {"type": "string"},
        },
    }


def _rely_guarantee_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "actor", "action", "params", "preserves"],
        "properties": {
            "id": {"type": "string"},
            "actor": {"type": "string"},
            "action": {"type": "string", "enum": sorted(ACTION_DESCRIPTORS)},
            "params": {"type": "object"},
            "preserves": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/condition"}},
            "applies_before": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": "string"},
        },
        "allOf": [_tagged_object_schema("action", "params", name, descriptor) for name, descriptor in sorted(ACTION_DESCRIPTORS.items())],
    }


def _effect_annotation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["effect_types", "idempotency", "reversibility", "retry_safety", "blast_radius", "expected_user_impact"],
        "properties": {
            "effect_types": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "enum": ["credential_revocation", "customer_visible_degradation", "deletion", "irreversible_state_change", "manual_sql", "queue_replay", "traffic_drain"]},
            },
            "idempotency": {"type": "string", "enum": ["idempotent", "non_idempotent", "unknown"]},
            "reversibility": {"type": "string", "enum": ["irreversible", "reversible", "unknown"]},
            "retry_safety": {"type": "string", "enum": ["safe", "unsafe", "unknown"]},
            "blast_radius": {"type": "string"},
            "expected_user_impact": {"type": "string"},
            "reviewed_by": {"type": "array", "items": {"type": "string"}},
        },
    }


def _condition_schema() -> dict[str, Any]:
    return {
        "oneOf": [
            _inline_tagged_object_schema("kind", name, descriptor)
            for name, descriptor in sorted(CONDITION_DESCRIPTORS.items())
        ]
    }


def _tagged_object_schema(tag_field: str, payload_field: str, tag: str, descriptor: OperationDescriptor) -> dict[str, Any]:
    return {
        "if": {"properties": {tag_field: {"const": tag}}, "required": [tag_field]},
        "then": {
            "$comment": f"{descriptor.summary} Denotation: {action_denotation(tag)}",
            "properties": {payload_field: _object_payload_schema(descriptor)},
        },
    }


def _inline_tagged_object_schema(tag_field: str, tag: str, descriptor: OperationDescriptor) -> dict[str, Any]:
    required = sorted(descriptor.required | {tag_field})
    properties = {field.name: _field_schema(field) for field in descriptor.fields}
    properties[tag_field] = {"const": tag}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _object_payload_schema(descriptor: OperationDescriptor) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(descriptor.required),
        "properties": {field.name: _field_schema(field) for field in descriptor.fields},
    }


def _field_schema(field: FieldDescriptor | str) -> dict[str, Any]:
    if isinstance(field, FieldDescriptor):
        return field.json_schema()
    name = field
    integer_minimums = {
        "count": 0,
        "depth": 0,
        "expires_after_minutes": 1,
        "minutes": 0,
        "replicas": 0,
        "percent": 0,
        "entries": 0,
    }
    if name in integer_minimums:
        schema = {"type": "integer", "minimum": integer_minimums[name]}
        if name == "percent":
            schema["maximum"] = 100
        return schema
    if name in {"enabled", "healthy", "active", "data_loss_risk", "compatible", "in_progress", "converged", "allow_split_brain", "from_dead_letter", "idempotent", "stable"}:
        return {"type": "boolean"}
    if name == "services":
        return {"type": "array", "items": {"type": "string"}}
    return {"type": "string"}
