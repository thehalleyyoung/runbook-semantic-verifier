from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

FieldType = Literal["string", "integer", "boolean", "string_list"]


@dataclass(frozen=True)
class FieldDescriptor:
    name: str
    type: FieldType
    required: bool = True
    minimum: int | None = None
    description: str = ""

    def json_schema(self) -> dict[str, Any]:
        if self.type == "integer":
            schema: dict[str, Any] = {"type": "integer"}
            if self.minimum is not None:
                schema["minimum"] = self.minimum
            return schema
        if self.type == "boolean":
            return {"type": "boolean"}
        if self.type == "string_list":
            return {"type": "array", "items": {"type": "string"}}
        return {"type": "string"}

    def validate(self, value: Any) -> str | None:
        if self.type == "integer":
            if type(value) is not int:
                return f"must be an integer"
            if self.minimum is not None and value < self.minimum:
                if self.minimum == 0:
                    return "must be a non-negative integer"
                if self.minimum == 1:
                    return "must be a positive integer"
                return f"must be an integer greater than or equal to {self.minimum}"
            return None
        if self.type == "boolean":
            return None if type(value) is bool else "must be a boolean"
        if self.type == "string_list":
            if not isinstance(value, list):
                return "must be a list"
            if any(not isinstance(item, str) for item in value):
                return "must contain only strings"
            return None
        return None if isinstance(value, str) else "must be a string"

    @property
    def type_label(self) -> str:
        if self.type == "integer" and self.minimum is not None:
            return f"integer>={self.minimum}"
        if self.type == "string_list":
            return "string[]"
        return self.type


@dataclass(frozen=True)
class OperationDescriptor:
    name: str
    fields: tuple[FieldDescriptor, ...]
    summary: str

    @property
    def required(self) -> set[str]:
        return {field.name for field in self.fields if field.required}

    @property
    def optional(self) -> set[str]:
        return {field.name for field in self.fields if not field.required}

    @property
    def field_map(self) -> dict[str, FieldDescriptor]:
        return {field.name: field for field in self.fields}

    def signature(self) -> str:
        chunks = []
        for field in self.fields:
            optional = "?" if not field.required else ""
            chunks.append(f"{field.name}{optional}:{field.type_label}")
        return ", ".join(chunks) if chunks else "(none)"


def F(name: str, type: FieldType = "string", *, required: bool = True, minimum: int | None = None, description: str = "") -> FieldDescriptor:
    return FieldDescriptor(name=name, type=type, required=required, minimum=minimum, description=description)


ACTION_DESCRIPTORS: dict[str, OperationDescriptor] = {
    "restart_service": OperationDescriptor("restart_service", (F("service"),), "Reasserts the modeled service without changing capacity."),
    "drain_replica": OperationDescriptor("drain_replica", (F("service"), F("replica")), "Marks one service replica drained and unavailable."),
    "restore_replica": OperationDescriptor("restore_replica", (F("service"), F("replica")), "Marks one drained service replica available again."),
    "drain_region": OperationDescriptor("drain_region", (F("region"), F("services", "string_list", required=False)), "Drains replicas in a region, optionally limited to named services."),
    "rollback_deployment": OperationDescriptor("rollback_deployment", (F("service"), F("to", required=False)), "Moves a service deployment pointer to a previous or named version."),
    "failover_database": OperationDescriptor("failover_database", (F("database"), F("target_region"), F("data_loss_risk", "boolean", required=False)), "Changes database primary region and records data-loss risk for invariants."),
    "confirm_quorum": OperationDescriptor("confirm_quorum", (F("database"),), "Marks database quorum/data-safety confirmation complete."),
    "suppress_alert": OperationDescriptor("suppress_alert", (F("alert"), F("expires_after_minutes", "integer", minimum=1)), "Suppresses an alert until the bounded expiry minute."),
    "scale_service": OperationDescriptor("scale_service", (F("service"), F("replicas", "integer", minimum=0), F("region", required=False)), "Resizes a service replica set using deterministic generated replica ids."),
    "toggle_flag": OperationDescriptor("toggle_flag", (F("flag"), F("enabled", "boolean")), "Sets a feature flag to the requested boolean value."),
    "run_migration": OperationDescriptor("run_migration", (F("database"), F("in_progress", "boolean", required=False), F("compatible", "boolean", required=False)), "Updates database migration progress and compatibility flags."),
    "finish_migration": OperationDescriptor("finish_migration", (F("database"),), "Clears the database migration-in-progress flag."),
    "pause_queue": OperationDescriptor("pause_queue", (F("queue"),), "Pauses queue consumption/processing."),
    "resume_queue": OperationDescriptor("resume_queue", (F("queue"),), "Resumes queue consumption/processing."),
    "wait": OperationDescriptor("wait", (F("minutes", "integer", minimum=0),), "Advances the model clock by a non-negative number of minutes."),
    "mark_region_health": OperationDescriptor("mark_region_health", (F("region"), F("healthy", "boolean")), "Sets a region health flag used by failover checks."),
}

CONDITION_DESCRIPTORS: dict[str, OperationDescriptor] = {
    "service_available_at_least": OperationDescriptor("service_available_at_least", (F("service"), F("count", "integer", minimum=0)), "Requires or asserts minimum available service replicas."),
    "database_quorum_confirmed": OperationDescriptor("database_quorum_confirmed", (F("database"),), "Requires or asserts confirmed database quorum."),
    "database_primary_region": OperationDescriptor("database_primary_region", (F("database"), F("region")), "Requires or asserts a database primary region."),
    "region_healthy": OperationDescriptor("region_healthy", (F("region"),), "Requires or asserts a healthy region."),
    "flag_enabled": OperationDescriptor("flag_enabled", (F("flag"), F("enabled", "boolean")), "Requires or asserts a feature flag value."),
    "alert_active": OperationDescriptor("alert_active", (F("alert"), F("active", "boolean")), "Requires or asserts an alert activity value."),
    "alert_suppressed_for_at_most": OperationDescriptor("alert_suppressed_for_at_most", (F("alert"), F("minutes", "integer", minimum=0)), "Requires or asserts bounded alert suppression duration."),
    "queue_depth_at_most": OperationDescriptor("queue_depth_at_most", (F("queue"), F("depth", "integer", minimum=0)), "Requires or asserts bounded queue depth."),
    "queue_has_consumers": OperationDescriptor("queue_has_consumers", (F("queue"), F("count", "integer", minimum=0)), "Requires or asserts minimum queue consumers."),
    "queue_resumed": OperationDescriptor("queue_resumed", (F("queue"),), "Requires or asserts an unpaused queue."),
    "service_deployment_is": OperationDescriptor("service_deployment_is", (F("service"), F("deployment")), "Requires or asserts a service deployment version."),
    "replica_not_drained": OperationDescriptor("replica_not_drained", (F("service"), F("replica")), "Requires or asserts a replica is not drained."),
}

ACTION_SCHEMAS = {name: {"required": desc.required, "optional": desc.optional} for name, desc in ACTION_DESCRIPTORS.items()}
CONDITION_SCHEMAS = {name: {"required": desc.required, "optional": desc.optional} for name, desc in CONDITION_DESCRIPTORS.items()}


def render_action_reference_markdown() -> str:
    lines = [
        "# Action semantics reference",
        "",
        "This table is generated from the typed action descriptors used by parser validation, JSON Schema generation, and formal exporters.",
        "",
        "| Action | Parameters | Semantics |",
        "| --- | --- | --- |",
    ]
    for name in sorted(ACTION_DESCRIPTORS):
        desc = ACTION_DESCRIPTORS[name]
        lines.append(f"| `{name}` | `{desc.signature()}` | {desc.summary} |")
    lines.extend([
        "",
        "## Condition descriptors",
        "",
        "| Condition kind | Fields | Meaning |",
        "| --- | --- | --- |",
    ])
    for name in sorted(CONDITION_DESCRIPTORS):
        desc = CONDITION_DESCRIPTORS[name]
        lines.append(f"| `{name}` | `{desc.signature()}` | {desc.summary} |")
    return "\n".join(lines) + "\n"
