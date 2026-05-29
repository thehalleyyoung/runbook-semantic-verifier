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


if __name__ == "__main__":
    unittest.main()
