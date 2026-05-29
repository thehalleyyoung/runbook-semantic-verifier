from __future__ import annotations

import json
from typing import Any

from .actions import ACTION_SCHEMAS, CONDITION_SCHEMAS


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
            "metadata": {"type": "object", "additionalProperties": True},
            "allow_reordering": {"type": "boolean"},
            "max_depth": {"type": "integer", "minimum": 0},
            "safety": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "max_alert_suppression_minutes": {"type": "integer", "minimum": 1},
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
        },
    }


def _step_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "action", "params"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "action": {"type": "string", "enum": sorted(ACTION_SCHEMAS)},
            "params": {"type": "object"},
            "after": {"type": "array", "items": {"type": "string"}},
            "requires": {"type": "array", "items": {"$ref": "#/$defs/condition"}},
            "effects": {"type": "array", "items": {"$ref": "#/$defs/condition"}},
        },
        "allOf": [_tagged_object_schema("action", "params", name, schema) for name, schema in sorted(ACTION_SCHEMAS.items())],
    }


def _condition_schema() -> dict[str, Any]:
    return {
        "oneOf": [
            _inline_tagged_object_schema("kind", name, schema)
            for name, schema in sorted(CONDITION_SCHEMAS.items())
        ]
    }


def _tagged_object_schema(tag_field: str, payload_field: str, tag: str, schema: dict[str, set[str]]) -> dict[str, Any]:
    return {
        "if": {"properties": {tag_field: {"const": tag}}, "required": [tag_field]},
        "then": {"properties": {payload_field: _object_payload_schema(schema)}},
    }


def _inline_tagged_object_schema(tag_field: str, tag: str, schema: dict[str, set[str]]) -> dict[str, Any]:
    required = sorted(schema["required"] | {tag_field})
    properties = {key: _field_schema(key) for key in sorted(schema["required"] | schema["optional"])}
    properties[tag_field] = {"const": tag}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _object_payload_schema(schema: dict[str, set[str]]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(schema["required"]),
        "properties": {key: _field_schema(key) for key in sorted(schema["required"] | schema["optional"])},
    }


def _field_schema(name: str) -> dict[str, Any]:
    integer_minimums = {
        "count": 0,
        "depth": 0,
        "expires_after_minutes": 1,
        "minutes": 0,
        "replicas": 0,
    }
    if name in integer_minimums:
        return {"type": "integer", "minimum": integer_minimums[name]}
    if name in {"enabled", "healthy", "active", "data_loss_risk", "compatible", "in_progress"}:
        return {"type": "boolean"}
    if name == "services":
        return {"type": "array", "items": {"type": "string"}}
    return {"type": "string"}
