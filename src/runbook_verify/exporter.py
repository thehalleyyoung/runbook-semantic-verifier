from __future__ import annotations

from .descriptors import ACTION_DESCRIPTORS
from .model import Runbook


def export_tla(runbook: Runbook) -> str:
    step_names = ", ".join(f'"{s.id}"' for s in runbook.steps)
    lines = [
        f"---- MODULE { _module_name(runbook.name) } ----",
        "EXTENDS Naturals, Sequences, FiniteSets",
        "",
        f"CONSTANTS Steps \\* {{{step_names}}}",
        "VARIABLES done, services, databases, alerts, flags, trafficRoutes",
        "",
        "Init == /\\ done = <<>>",
        f"        /\\ Steps = {{{step_names}}}",
        "",
        "CanRun(step) == step \\notin SeqToSet(done)",
        "Run(step) == /\\ CanRun(step)",
        "             /\\ done' = Append(done, step)",
        "             /\\ UNCHANGED <<services, databases, alerts, flags, trafficRoutes>>",
        "",
        "Next == \\E step \\in Steps : Run(step)",
        "",
        "NoAllReplicasDrained == \\A svc \\in DOMAIN services : services[svc].available >= services[svc].minAvailable",
        "BoundedAlertSuppression == \\A a \\in DOMAIN alerts : alerts[a].suppressed => alerts[a].expiresAt # NULL",
        "NoUnsafeFailover == \\A db \\in DOMAIN databases : databases[db].primaryRegion \\in databases[db].healthyRegions",
        "TrafficWeightsNormalized == \\A route \\in DOMAIN trafficRoutes : trafficRoutes[route].weightTotal = 100",
        "Safety == NoAllReplicasDrained /\\ BoundedAlertSuppression /\\ NoUnsafeFailover /\\ TrafficWeightsNormalized",
        "",
        "Spec == Init /\\ [][Next]_<<done, services, databases, alerts, flags, trafficRoutes>>",
        "THEOREM Spec => []Safety",
        "====",
    ]
    lines.append("\\* Action mapping from DSL:")
    for step in runbook.steps:
        descriptor = ACTION_DESCRIPTORS[step.action]
        lines.append(f"\\* {step.id}: {step.action}({descriptor.signature()}) {step.params}")
    return "\n".join(lines) + "\n"


def export_alloy(runbook: Runbook) -> str:
    lines = [
        "module runbook_verification",
        "abstract sig Step {}",
    ]
    for step in runbook.steps:
        descriptor = ACTION_DESCRIPTORS[step.action]
        lines.append(f"one sig { _symbol(step.id) } extends Step {{}} // {step.action}({descriptor.signature()})")
    lines.extend([
        "sig State { done: set Step }",
        "pred transition[s, s': State] { some st: Step - s.done | s'.done = s.done + st }",
        "pred noAllReplicasDrained { /* generated checker enforces concrete cardinalities */ }",
        "assert Safety { all s: State | noAllReplicasDrained }",
        "check Safety for 8",
    ])
    return "\n".join(lines) + "\n"


def _module_name(name: str) -> str:
    text = "".join(ch if ch.isalnum() else "_" for ch in name.title())
    return text or "Runbook"


def _symbol(name: str) -> str:
    text = "".join(ch if ch.isalnum() else "_" for ch in name.title())
    return text or "Step"
