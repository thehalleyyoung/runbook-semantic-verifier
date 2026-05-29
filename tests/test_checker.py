from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify import Checker, load_runbook
from runbook_verify.parser import parse_runbook

ROOT = Path(__file__).resolve().parents[1]


class CheckerTests(unittest.TestCase):
    def test_safe_example_has_no_violations(self):
        result = Checker(load_runbook(ROOT / "examples" / "safe_runbook.json")).check()
        self.assertTrue(result.safe)
        self.assertEqual(result.violations, [])
        self.assertGreater(result.states_explored, 1)

    def test_unsafe_example_finds_multiple_property_classes(self):
        result = Checker(load_runbook(ROOT / "examples" / "unsafe_runbook.json")).check()
        props = {v.property for v in result.violations}
        self.assertFalse(result.safe)
        self.assertIn("service_min_available", props)
        self.assertIn("no_rollback_during_incompatible_migration", props)
        self.assertIn("no_failover_to_unhealthy_region", props)
        self.assertIn("quorum_before_data_loss_action", props)
        self.assertIn("bounded_alert_suppression", props)
        self.assertTrue(all(v.small_step_rule for v in result.violations))
        self.assertTrue(all(v.semantic_trace for v in result.violations))
        self.assertTrue(all(v.hoare_triple for v in result.violations))

    def test_dependency_order_prevents_premature_failover(self):
        result = Checker(load_runbook(ROOT / "examples" / "safe_runbook.json")).check()
        traces = [v.trace for v in result.violations]
        self.assertNotIn(("failover-orders-west",), traces)

    def test_small_step_rule_counts_cover_choice_wait_and_budget(self):
        runbook = parse_runbook({
            "allow_reordering": True,
            "max_depth": 1,
            "system": {
                "regions": {"east": {"healthy": True}},
                "services": {"api": {"min_available": 0, "replicas": []}},
            },
            "steps": [
                {"id": "wait-clock", "action": "wait", "params": {"minutes": 5}},
                {"id": "restart", "action": "restart_service", "params": {"service": "api"}},
            ],
        })
        result = Checker(runbook).check()
        counters = result.performance_counters()["semantic_rule_counts"]
        self.assertEqual(counters["Schedule.OperatorChoice"], 2)
        self.assertEqual(counters["Action.Wait"], 1)
        self.assertEqual(counters["Action.Execute"], 1)
        self.assertEqual(counters["Explore.BudgetReached"], 2)

class CheckerExplanationTests(unittest.TestCase):
    def test_queue_pause_hazard_has_remediation(self):
        runbook = parse_runbook({
            "system": {
                "regions": {}, "services": {}, "databases": {}, "alerts": {}, "feature_flags": {}, "deployments": {},
                "queues": {"q": {"depth": 10, "consumers": 1}}
            },
            "steps": [{"id": "pause", "action": "pause_queue", "params": {"queue": "q"}}]
        })
        result = Checker(runbook).check()
        props = {v.property for v in result.violations}
        self.assertIn("no_queue_pause_without_drain_plan", props)
        self.assertIn("no_paused_queue_with_backlog", props)
        self.assertTrue(all(v.remediation for v in result.violations))

    def test_safe_weighted_regional_traffic_failover(self):
        runbook = parse_runbook({
            "system": {
                "regions": {"east": {"healthy": True}, "west": {"healthy": True}},
                "services": {"api": {"min_available": 1, "replicas": [
                    {"id": "api-east", "region": "east"},
                    {"id": "api-west", "region": "west"},
                ]}},
                "traffic_routes": {"api-public": {"service": "api", "weights": {"east": 100, "west": 0}}},
            },
            "steps": [
                {"id": "shift-west", "action": "failover_traffic", "params": {"route": "api-public", "target_region": "west"},
                 "requires": [{"kind": "region_healthy", "region": "west"}],
                 "effects": [{"kind": "traffic_weight_is", "route": "api-public", "region": "west", "percent": 100}]},
                {"id": "drain-east-lb", "action": "drain_load_balancer", "after": ["shift-west"], "params": {"route": "api-public", "region": "east"},
                 "effects": [{"kind": "load_balancer_active", "route": "api-public", "region": "west"}]},
            ],
        })
        result = Checker(runbook).check()
        self.assertTrue(result.safe, result.violations)

    def test_unsafe_traffic_shift_and_load_balancer_drain_are_reported(self):
        runbook = parse_runbook({
            "system": {
                "regions": {"east": {"healthy": True}, "west": {"healthy": False}},
                "services": {"api": {"min_available": 1, "replicas": [{"id": "api-east", "region": "east"}]}},
                "traffic_routes": {"api-public": {"service": "api", "weights": {"east": 100, "west": 0}, "drained_regions": ["west"]}},
            },
            "steps": [
                {"id": "drain-east-lb", "action": "drain_load_balancer", "params": {"route": "api-public", "region": "east"}},
                {"id": "shift-west", "action": "failover_traffic", "params": {"route": "api-public", "target_region": "west"}},
            ],
        })
        result = Checker(runbook).check()
        props = {v.property for v in result.violations}
        self.assertIn("no_draining_load_balancer_with_traffic", props)
        self.assertIn("no_traffic_to_drained_load_balancer", props)
        self.assertIn("no_traffic_to_unhealthy_region", props)
        self.assertIn("traffic_requires_regional_capacity", props)

    def test_safe_dns_cutover_requires_health_capacity_and_ttl_wait(self):
        runbook = parse_runbook({
            "allow_reordering": False,
            "system": {
                "regions": {"east": {}, "west": {}},
                "services": {"api": {"min_available": 1, "replicas": [
                    {"id": "api-east", "region": "east"},
                    {"id": "api-west", "region": "west"},
                ]}},
                "dns_records": {"api.example.com": {
                    "service": "api",
                    "region": "east",
                    "ttl_minutes": 5,
                    "health_check_converged_regions": ["east", "west"],
                    "allow_split_brain": True,
                }},
            },
            "steps": [
                {"id": "cutover", "action": "update_dns_record", "params": {"record": "api.example.com", "target_region": "west"},
                 "requires": [{"kind": "dns_health_check_converged", "record": "api.example.com", "region": "west"}]},
                {"id": "wait-ttl", "action": "wait", "after": ["cutover"], "params": {"minutes": 5}},
                {"id": "finalize", "action": "finalize_dns_record", "after": ["wait-ttl"], "params": {"record": "api.example.com"},
                 "requires": [{"kind": "dns_ttl_elapsed", "record": "api.example.com"}],
                 "effects": [{"kind": "dns_points_to", "record": "api.example.com", "region": "west"}]},
            ],
        })
        result = Checker(runbook).check()
        self.assertTrue(result.safe, result.violations)

    def test_unsafe_dns_cutover_reports_operator_readable_ttl_and_health_hazards(self):
        runbook = parse_runbook({
            "allow_reordering": True,
            "max_depth": 2,
            "system": {
                "regions": {"east": {}, "west": {}},
                "services": {"api": {"min_available": 1, "replicas": [{"id": "api-east", "region": "east"}]}},
                "dns_records": {"api.example.com": {
                    "service": "api",
                    "region": "east",
                    "ttl_minutes": 5,
                    "health_check_converged_regions": ["east"],
                    "allow_split_brain": False,
                }},
            },
            "steps": [
                {"id": "cutover", "action": "update_dns_record", "params": {"record": "api.example.com", "target_region": "west"}},
                {"id": "finalize", "action": "finalize_dns_record", "after": ["cutover"], "params": {"record": "api.example.com"}},
            ],
        })
        result = Checker(runbook).check()
        props = {v.property for v in result.violations}
        self.assertIn("dns_health_check_converged_before_cutover", props)
        self.assertIn("dns_requires_regional_capacity", props)
        self.assertIn("dns_no_split_brain_during_ttl", props)
        self.assertIn("dns_ttl_elapsed_before_finalize", props)
        self.assertTrue(any("until minute 5" in v.message for v in result.violations))

    def test_safe_message_replay_uses_dead_letter_bound_dedupe_and_stable_consumers(self):
        runbook = parse_runbook({
            "allow_reordering": False,
            "system": {
                "queues": {
                    "jobs": {
                        "depth": 0,
                        "consumers": 2,
                        "dead_letter_depth": 25,
                        "dedupe_window_minutes": 60,
                    }
                }
            },
            "steps": [
                {"id": "replay-dlq", "action": "replay_messages", "params": {"queue": "jobs", "count": 10, "from_dead_letter": True, "dedupe_key": "event_id"}},
                {"id": "rebalance", "action": "rebalance_consumers", "after": ["replay-dlq"], "params": {"queue": "jobs", "consumers": 3, "stable": True},
                 "effects": [{"kind": "consumer_group_stable", "queue": "jobs"}, {"kind": "queue_replay_deduplicated", "queue": "jobs"}]},
            ],
        })
        result = Checker(runbook).check()
        self.assertTrue(result.safe, result.violations)

    def test_unsafe_message_replay_reports_dedupe_dlq_and_consumer_group_hazards(self):
        runbook = parse_runbook({
            "allow_reordering": True,
            "max_depth": 2,
            "system": {
                "queues": {
                    "jobs": {
                        "depth": 3,
                        "consumers": 1,
                        "dead_letter_depth": 5,
                    }
                }
            },
            "steps": [
                {"id": "oversized-dlq-replay", "action": "replay_messages", "params": {"queue": "jobs", "count": 7, "from_dead_letter": True}},
                {"id": "unsafe-replay", "action": "replay_messages", "params": {"queue": "jobs", "count": 4}},
                {"id": "rebalance-zero", "action": "rebalance_consumers", "after": ["unsafe-replay"], "params": {"queue": "jobs", "consumers": 0}},
            ],
        })
        result = Checker(runbook).check()
        props = {v.property for v in result.violations}
        self.assertIn("dead_letter_replay_has_messages", props)
        self.assertIn("no_replay_without_dedupe", props)
        self.assertIn("no_duplicate_processing_risk", props)
        self.assertIn("no_rebalance_to_zero_consumers", props)
        self.assertIn("queue_backlog_requires_consumers", props)
        self.assertIn("no_unstable_consumer_group_with_backlog", props)

    def test_safe_cache_flush_freezes_writes_and_warms_before_resume(self):
        runbook = parse_runbook({
            "allow_reordering": False,
            "system": {
                "services": {"api": {"min_available": 0, "replicas": []}},
                "caches": {"redis": {"service": "api", "entries": 100, "warmup_entries": 80, "capacity_entries": 120}},
            },
            "steps": [
                {"id": "freeze", "action": "freeze_cache_writes", "params": {"cache": "redis"},
                 "effects": [{"kind": "cache_writes_frozen", "cache": "redis"}]},
                {"id": "flush", "action": "flush_cache", "after": ["freeze"], "params": {"cache": "redis"},
                 "requires": [{"kind": "cache_writes_frozen", "cache": "redis"}]},
                {"id": "warm", "action": "warm_cache", "after": ["flush"], "params": {"cache": "redis", "entries": 100},
                 "requires": [{"kind": "cache_capacity_at_least", "cache": "redis", "entries": 100}],
                 "effects": [{"kind": "cache_warm", "cache": "redis"}, {"kind": "cache_no_stale_read_risk", "cache": "redis"}]},
                {"id": "resume", "action": "resume_cache_writes", "after": ["warm"], "params": {"cache": "redis"}},
            ],
        })
        result = Checker(runbook).check()
        self.assertTrue(result.safe, result.violations)

    def test_unsafe_cache_flush_reports_cold_start_capacity_and_stale_read_hazards(self):
        runbook = parse_runbook({
            "allow_reordering": True,
            "max_depth": 2,
            "system": {
                "services": {"api": {"min_available": 0, "replicas": []}},
                "caches": {"redis": {"service": "api", "entries": 100, "warmup_entries": 80, "capacity_entries": 120}},
            },
            "steps": [
                {"id": "flush", "action": "flush_cache", "params": {"cache": "redis"}},
                {"id": "underwarm", "action": "warm_cache", "after": ["flush"], "params": {"cache": "redis", "entries": 40}},
                {"id": "overwarm", "action": "warm_cache", "after": ["flush"], "params": {"cache": "redis", "entries": 130}},
            ],
        })
        result = Checker(runbook).check()
        props = {v.property for v in result.violations}
        self.assertIn("cache_flush_requires_write_freeze", props)
        self.assertIn("cache_warmup_before_traffic", props)
        self.assertIn("cache_warmup_within_capacity", props)
        self.assertIn("no_stale_reads_after_cache_flush", props)

    def test_missing_high_risk_effect_annotation_warns_without_failing_safety(self):
        runbook = parse_runbook({
            "system": {"credentials": {"api-key": {"owner": "security"}}},
            "steps": [{"id": "revoke", "action": "revoke_credential", "params": {"credential": "api-key"}}],
        })
        result = Checker(runbook).check()
        self.assertTrue(result.safe, result.violations)
        self.assertIn("effect_annotation_required", {warning.property for warning in result.annotation_warnings})
        self.assertEqual(result.performance_counters()["annotation_warnings"], 1)

    def test_active_waiver_records_suppressed_effect_annotation_warning(self):
        runbook = parse_runbook({
            "metadata": {"waivers": [{
                "id": "w-effect",
                "owner": "security",
                "expiry": "2099-12-31",
                "scope": "step:revoke",
                "rationale": "Fixture exercises visible waiver reporting.",
                "invariant": "effect_annotation_required",
                "benchmark_visibility": "visible",
            }]},
            "system": {"credentials": {"api-key": {"owner": "security"}}},
            "steps": [{"id": "revoke", "action": "revoke_credential", "params": {"credential": "api-key"}}],
        })
        result = Checker(runbook).check()
        self.assertEqual(result.annotation_warnings, [])
        self.assertEqual(len(result.waivers_applied), 1)
        self.assertEqual(result.waivers_applied[0]["waiver"]["id"], "w-effect")

    def test_credential_rotation_and_revocation_conditions(self):
        runbook = parse_runbook({
            "system": {"credentials": {"api-key": {"owner": "security", "revoked": False}}},
            "steps": [
                {"id": "revoke", "action": "revoke_credential", "params": {"credential": "api-key"},
                 "effects": [{"kind": "credential_revoked", "credential": "api-key"}],
                 "effect_annotations": {
                     "effect_types": ["credential_revocation"],
                     "idempotency": "idempotent",
                     "reversibility": "irreversible",
                     "retry_safety": "unknown",
                     "blast_radius": "single API key",
                     "expected_user_impact": "dependent clients must refresh credentials",
                 }},
                {"id": "rotate", "action": "rotate_credential", "after": ["revoke"], "params": {"credential": "api-key"},
                 "effects": [{"kind": "credential_active", "credential": "api-key"}]},
            ],
        })
        result = Checker(runbook).check()
        self.assertTrue(result.safe, result.violations)

    def test_safe_object_storage_restore_checks_rpo_rto_and_replication(self):
        result = Checker(load_runbook(ROOT / "examples" / "object_storage_restore_safe.json")).check()
        self.assertTrue(result.safe, result.violations)
        self.assertIn("exploration_strategy", result.performance_counters())

    def test_unsafe_object_storage_restore_reports_durability_and_recovery_objectives(self):
        result = Checker(load_runbook(ROOT / "examples" / "object_storage_restore_unsafe.json")).check()
        props = {v.property for v in result.violations}
        self.assertIn("object_restore_requires_write_freeze", props)
        self.assertIn("object_restore_requires_snapshot", props)
        self.assertIn("object_restore_within_rpo", props)
        self.assertIn("object_restore_within_rto", props)
        self.assertIn("object_bucket_replication_min_regions", props)
        self.assertIn("object_replication_target_region_healthy", props)

    def test_reproducible_exploration_strategies_are_recorded_and_seeded(self):
        runbook = parse_runbook({
            "allow_reordering": True,
            "max_depth": 2,
            "safety": {"exploration_strategy": "randomized_bounded", "exploration_seed": 7},
            "system": {"regions": {"a": {}}, "services": {"api": {"min_available": 0, "replicas": []}}},
            "steps": [
                {"id": "wait-a", "action": "wait", "params": {"minutes": 1}},
                {"id": "wait-b", "action": "wait", "params": {"minutes": 2}},
            ],
        })
        first = Checker(runbook).check().performance_counters()
        second = Checker(runbook).check().performance_counters()
        self.assertEqual(first["exploration_strategy"], "randomized_bounded")
        self.assertEqual(first["exploration_seed"], 7)
        self.assertEqual(first["semantic_rule_counts"], second["semantic_rule_counts"])

    def test_bounded_model_checking_reports_inconclusive_state_budget(self):
        runbook = parse_runbook({
            "allow_reordering": True,
            "safety": {"max_states": 1, "fairness": "dependency"},
            "system": {"regions": {"a": {}}, "services": {"api": {"min_available": 0, "replicas": []}}},
            "steps": [
                {"id": "wait-a", "action": "wait", "params": {"minutes": 1}},
                {"id": "wait-b", "action": "wait", "params": {"minutes": 2}},
            ],
        })
        result = Checker(runbook).check()
        self.assertTrue(result.inconclusive)
        self.assertIn("max_states", result.inconclusive_reason)
        self.assertEqual(result.performance_counters()["fairness_model"], "dependency")

    def test_bounded_model_checking_reports_inconclusive_timeout_budget(self):
        runbook = parse_runbook({
            "allow_reordering": True,
            "safety": {"timeout_seconds": 0},
            "system": {"regions": {"a": {}}, "services": {"api": {"min_available": 0, "replicas": []}}},
            "steps": [
                {"id": "wait-a", "action": "wait", "params": {"minutes": 1}},
                {"id": "wait-b", "action": "wait", "params": {"minutes": 2}},
            ],
        })
        result = Checker(runbook).check()
        counters = result.performance_counters()
        self.assertTrue(result.inconclusive)
        self.assertIn("timeout_seconds=0", result.inconclusive_reason)
        self.assertEqual(counters["timeout_seconds"], 0)

    def test_markdown_nested_precondition_source_mapping_and_patch_synthesis(self):
        runbook = load_runbook(ROOT / "tests" / "fixtures" / "source_mapping_runbook.md")
        result = Checker(runbook).check()
        precondition = next(v for v in result.violations if v.property == "precondition")
        self.assertEqual(precondition.source_field, "requires[0]")
        self.assertGreater(precondition.source_line or 0, runbook.steps[0].source_line or 0)
        self.assertEqual(precondition.source_path, str(ROOT / "tests" / "fixtures" / "source_mapping_runbook.md"))

        quorum = next(v for v in result.violations if v.property == "quorum_before_data_loss_action")
        # The failover checker can synthesize a reviewable JSON-patch candidate for a missing guard.
        self.assertIn({"kind": "database_quorum_confirmed", "database": "orders"}, list(quorum.suggested_preconditions))
        self.assertTrue(quorum.json_patches)

    def test_partial_order_reduction_preserves_safe_trace_equivalence_for_independent_actions(self):
        base = {
            "allow_reordering": True,
            "system": {
                "regions": {"east": {}},
                "services": {
                    "api": {"min_available": 0, "replicas": []},
                    "worker": {"min_available": 0, "replicas": []},
                },
            },
            "steps": [
                {"id": "restart-api", "action": "restart_service", "params": {"service": "api"}},
                {"id": "restart-worker", "action": "restart_service", "params": {"service": "worker"}},
            ],
        }
        reduced = Checker(parse_runbook({**base, "safety": {"partial_order_reduction": True}})).check()
        exhaustive = Checker(parse_runbook({**base, "safety": {"partial_order_reduction": False}})).check()
        self.assertEqual({v.property for v in reduced.violations}, {v.property for v in exhaustive.violations})
        self.assertEqual(reduced.safe, exhaustive.safe)
        self.assertGreater(reduced.reductions_applied, 0)
        self.assertLess(reduced.transitions_explored, exhaustive.transitions_explored)


if __name__ == "__main__":
    unittest.main()
