from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runbook_verify.parser import RunbookParseError, load_runbook, parse_runbook

ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_loads_safe_example(self):
        runbook = load_runbook(ROOT / "examples" / "safe_runbook.json")
        self.assertEqual(runbook.name, "Safe regional database failover")
        self.assertEqual(len(runbook.steps), 6)
        self.assertIn("api", runbook.state.services)

    def test_rejects_duplicate_step_ids(self):
        with self.assertRaises(RunbookParseError):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "toggle_flag"}, {"id": "x", "action": "toggle_flag"}]})

    def test_rejects_unknown_dependency(self):
        with self.assertRaises(RunbookParseError):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "toggle_flag", "after": ["missing"]}]})

    def test_rejects_dependency_cycles(self):
        with self.assertRaisesRegex(RunbookParseError, "dependency cycle"):
            parse_runbook({
                "system": {},
                "steps": [
                    {"id": "a", "action": "wait", "params": {"minutes": 1}, "after": ["b"]},
                    {"id": "b", "action": "wait", "params": {"minutes": 1}, "after": ["a"]},
                ],
            })

class ParserValidationTests(unittest.TestCase):
    def test_rejects_unknown_action_and_params(self):
        with self.assertRaisesRegex(RunbookParseError, "unsupported action"):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "rm_rf", "params": {}}]})
        with self.assertRaisesRegex(RunbookParseError, "unknown field"):
            parse_runbook({"system": {}, "steps": [{"id": "x", "action": "wait", "params": {"minutes": 1, "extra": True}}]})

    def test_rejects_unknown_entity_references(self):
        doc = {
            "system": {"regions": {"a": {}}, "services": {}, "databases": {}, "queues": {}, "alerts": {}, "feature_flags": {}, "deployments": {}},
            "steps": [{"id": "x", "action": "suppress_alert", "params": {"alert": "missing", "expires_after_minutes": 5}}],
        }
        with self.assertRaisesRegex(RunbookParseError, "unknown alert"):
            parse_runbook(doc)

    def test_rejects_invalid_numeric_bounds(self):
        with self.assertRaisesRegex(RunbookParseError, "positive integer"):
            parse_runbook({
                "system": {"alerts": {"a": {}}},
                "steps": [{"id": "x", "action": "suppress_alert", "params": {"alert": "a", "expires_after_minutes": 0}}],
            })
        with self.assertRaisesRegex(RunbookParseError, "non-negative integer"):
            parse_runbook({
                "system": {},
                "steps": [{"id": "x", "action": "wait", "params": {"minutes": -1}}],
            })

    def test_rejects_descriptor_type_errors(self):
        with self.assertRaisesRegex(RunbookParseError, "must be a string"):
            parse_runbook({
                "system": {"queues": {"jobs": {}}},
                "steps": [{"id": "pause", "action": "pause_queue", "params": {"queue": 7}}],
            })
        with self.assertRaisesRegex(RunbookParseError, "must be a boolean"):
            parse_runbook({
                "system": {"feature_flags": {"brownout": {}}},
                "steps": [{"id": "flag", "action": "toggle_flag", "params": {"flag": "brownout", "enabled": "yes"}}],
            })
        with self.assertRaisesRegex(RunbookParseError, "must contain only strings"):
            parse_runbook({
                "system": {"regions": {"a": {}}, "services": {"api": {"min_available": 0, "replicas": []}}},
                "steps": [{"id": "drain", "action": "drain_region", "params": {"region": "a", "services": ["api", 1]}}],
            })

    def test_source_path_is_attached_to_steps(self):
        runbook = load_runbook(ROOT / "examples" / "safe_runbook.json")
        self.assertTrue(runbook.steps[0].source_path.endswith("safe_runbook.json"))
        self.assertIsInstance(runbook.steps[0].source_line, int)

    def test_rejects_duplicate_replica_ids(self):
        with self.assertRaisesRegex(RunbookParseError, "duplicate replica id"):
            parse_runbook({
                "system": {
                    "regions": {"a": {}},
                    "services": {
                        "api": {
                            "replicas": [
                                {"id": "api-0", "region": "a"},
                                {"id": "api-0", "region": "a"},
                            ]
                        }
                    },
                },
                "steps": [],
            })

    def test_rejects_unachievable_min_available_unless_waived(self):
        doc = {
            "system": {
                "regions": {"a": {}},
                "services": {"api": {"min_available": 3, "replicas": [{"id": "api-a", "region": "a"}]}},
            },
            "steps": [],
        }
        with self.assertRaisesRegex(RunbookParseError, "not achievable"):
            parse_runbook(doc)
        doc["system"]["services"]["api"]["allow_unachievable_min_available"] = True
        self.assertEqual(parse_runbook(doc).state.services["api"].min_available, 3)

    def test_rejects_generated_scale_replica_collisions(self):
        with self.assertRaisesRegex(RunbookParseError, "generate duplicate replica id"):
            parse_runbook({
                "system": {
                    "regions": {"a": {}},
                    "services": {"api": {"replicas": [{"id": "api-1", "region": "a"}]}},
                },
                "steps": [{"id": "scale", "action": "scale_service", "params": {"service": "api", "replicas": 2}}],
            })
        with self.assertRaisesRegex(RunbookParseError, "would both generate replica id"):
            parse_runbook({
                "system": {
                    "regions": {"a": {}},
                    "services": {"api": {"replicas": [{"id": "api-base", "region": "a"}]}},
                },
                "steps": [
                    {"id": "scale-a", "action": "scale_service", "params": {"service": "api", "replicas": 2}},
                    {"id": "scale-b", "action": "scale_service", "params": {"service": "api", "replicas": 2}},
                ],
            })

    def test_rejects_deployment_service_mismatch(self):
        with self.assertRaisesRegex(RunbookParseError, "does not match"):
            parse_runbook({
                "system": {
                    "services": {"api": {"deployment": "v2", "min_available": 0, "replicas": []}},
                    "deployments": {"api": {"service": "api", "current": "v1"}},
                },
                "steps": [],
            })

    def test_parse_error_exposes_structured_diagnostic(self):
        try:
            load_runbook(ROOT / "tests" / "fixtures" / "invalid_unknown_alert.json")
        except RunbookParseError as exc:
            diagnostic = exc.to_dict()
        else:
            self.fail("invalid fixture unexpectedly parsed")
        self.assertEqual(diagnostic["severity"], "error")
        self.assertTrue(diagnostic["path"].endswith("invalid_unknown_alert.json"))
        self.assertIsInstance(diagnostic["line"], int)
        self.assertIn("alert", diagnostic["field"])
        self.assertIn("Declare the referenced entity", diagnostic["remediation"])

    def test_complete_schema_example_fixture_validates(self):
        runbook = load_runbook(ROOT / "docs" / "schema" / "examples" / "complete_runbook.json")
        self.assertEqual(runbook.name, "Complete documented DSL fixture")
        self.assertEqual(len(runbook.steps), 13)
        self.assertIn("api-artifacts", runbook.state.object_buckets)
        self.assertEqual(runbook.safety["fairness"], "dependency")

    def test_parses_and_validates_traffic_route_references(self):
        runbook = parse_runbook({
            "system": {
                "regions": {"east": {}, "west": {}},
                "services": {"api": {"min_available": 1, "replicas": [{"id": "api-east", "region": "east"}]}},
                "traffic_routes": {"api-public": {"service": "api", "weights": {"east": 100, "west": 0}}},
            },
            "steps": [{"id": "shift", "action": "shift_traffic", "params": {"route": "api-public", "region": "west", "percent": 25}}],
        })
        self.assertEqual(runbook.state.traffic_routes["api-public"].weights["east"], 100)

        with self.assertRaisesRegex(RunbookParseError, "unknown traffic route"):
            parse_runbook({
                "system": {"regions": {"west": {}}},
                "steps": [{"id": "shift", "action": "shift_traffic", "params": {"route": "missing", "region": "west", "percent": 25}}],
            })

    def test_rejects_invalid_traffic_weight_percentages(self):
        with self.assertRaisesRegex(RunbookParseError, "less than or equal to 100"):
            parse_runbook({
                "system": {
                    "regions": {"east": {}},
                    "services": {"api": {"min_available": 0, "replicas": []}},
                    "traffic_routes": {"api-public": {"service": "api", "weights": {"east": 101}}},
                },
                "steps": [],
            })
        with self.assertRaisesRegex(RunbookParseError, "less than or equal to 100"):
            parse_runbook({
                "system": {"regions": {"east": {}}, "traffic_routes": {}},
                "steps": [{"id": "shift", "action": "shift_traffic", "params": {"route": "api-public", "region": "east", "percent": 101}}],
            })

    def test_parses_and_validates_dns_record_references(self):
        runbook = parse_runbook({
            "system": {
                "regions": {"east": {}, "west": {}},
                "services": {"api": {"min_available": 1, "replicas": [{"id": "api-east", "region": "east"}]}},
                "dns_records": {"api.example.com": {
                    "service": "api",
                    "region": "east",
                    "ttl_minutes": 5,
                    "health_check_converged_regions": ["east"],
                }},
            },
            "steps": [{"id": "dns", "action": "update_dns_record", "params": {"record": "api.example.com", "target_region": "west"}}],
        })
        self.assertEqual(runbook.state.dns_records["api.example.com"].ttl_minutes, 5)

        with self.assertRaisesRegex(RunbookParseError, "unknown DNS record"):
            parse_runbook({
                "system": {"regions": {"west": {}}},
                "steps": [{"id": "dns", "action": "update_dns_record", "params": {"record": "missing", "target_region": "west"}}],
            })

    def test_rejects_invalid_dns_entity_references(self):
        with self.assertRaisesRegex(RunbookParseError, "unknown service"):
            parse_runbook({
                "system": {"regions": {"east": {}}, "dns_records": {"api.example.com": {"service": "api", "region": "east"}}},
                "steps": [],
            })
        with self.assertRaisesRegex(RunbookParseError, "unknown region"):
            parse_runbook({
                "system": {
                    "regions": {"east": {}},
                    "services": {"api": {"min_available": 0, "replicas": []}},
                    "dns_records": {"api.example.com": {"service": "api", "region": "west"}},
                },
                "steps": [],
            })

    def test_parses_queue_replay_state_and_references(self):
        runbook = parse_runbook({
            "system": {"queues": {"jobs": {"dead_letter_depth": 2, "dedupe_window_minutes": 30, "duplicate_risk": False, "consumer_group_stable": True}}},
            "steps": [{"id": "replay", "action": "replay_messages", "params": {"queue": "jobs", "count": 1, "from_dead_letter": True, "dedupe_key": "message_id"}}],
        })
        self.assertEqual(runbook.state.queues["jobs"].dead_letter_depth, 2)
        self.assertEqual(runbook.steps[0].params["dedupe_key"], "message_id")

        with self.assertRaisesRegex(RunbookParseError, "unknown queue"):
            parse_runbook({
                "system": {"queues": {}},
                "steps": [{"id": "replay", "action": "replay_messages", "params": {"queue": "missing", "count": 1}}],
            })

    def test_parses_and_validates_cache_references(self):
        runbook = parse_runbook({
            "system": {
                "services": {"api": {"min_available": 0, "replicas": []}},
                "caches": {"redis": {"service": "api", "entries": 100, "warmup_entries": 50, "capacity_entries": 200}},
            },
            "steps": [{"id": "flush", "action": "flush_cache", "params": {"cache": "redis"}}],
        })
        self.assertEqual(runbook.state.caches["redis"].service, "api")
        self.assertEqual(runbook.state.caches["redis"].capacity_entries, 200)

    def test_parses_and_validates_object_bucket_references(self):
        runbook = parse_runbook({
            "system": {
                "regions": {"east": {}, "west": {}},
                "object_buckets": {"artifacts": {
                    "region": "east",
                    "replicated_regions": ["east"],
                    "min_replicated_regions": 1,
                    "snapshot_available": True,
                    "rpo_minutes": 30,
                    "rto_minutes": 60,
                }},
            },
            "steps": [{"id": "freeze", "action": "freeze_bucket_writes", "params": {"bucket": "artifacts"}}],
        })
        self.assertEqual(runbook.state.object_buckets["artifacts"].region, "east")
        with self.assertRaisesRegex(RunbookParseError, "unknown object bucket"):
            parse_runbook({
                "system": {"regions": {"east": {}}},
                "steps": [{"id": "restore", "action": "restore_bucket_snapshot", "params": {"bucket": "missing", "snapshot_age_minutes": 1}}],
            })

        with self.assertRaisesRegex(RunbookParseError, "unknown cache"):
            parse_runbook({
                "system": {"services": {"api": {"min_available": 0, "replicas": []}}, "caches": {}},
                "steps": [{"id": "flush", "action": "flush_cache", "params": {"cache": "missing"}}],
            })

        with self.assertRaisesRegex(RunbookParseError, "unknown service"):
            parse_runbook({
                "system": {"caches": {"redis": {"service": "api"}}},
                "steps": [],
            })

    def test_parses_credentials_effect_annotations_and_waivers(self):
        runbook = parse_runbook({
            "metadata": {
                "waivers": [{
                    "id": "waive-rotation-doc",
                    "owner": "security-oncall",
                    "expiry": "2099-12-31",
                    "scope": "step:rotate-api-key",
                    "rationale": "Fixture documents a visible waiver for benchmark triage.",
                    "invariant": "effect_annotation_required",
                    "benchmark_visibility": "visible",
                }]
            },
            "system": {"credentials": {"api-key": {"owner": "payments", "rotation_due_minute": 10}}},
            "steps": [{
                "id": "rotate-api-key",
                "action": "rotate_credential",
                "params": {"credential": "api-key"},
                "effect_annotations": {
                    "effect_types": ["credential_revocation"],
                    "idempotency": "idempotent",
                    "reversibility": "reversible",
                    "retry_safety": "safe",
                    "blast_radius": "single service credential",
                    "expected_user_impact": "no expected customer impact after staged rotation",
                    "reviewed_by": ["security-oncall"],
                },
                "effects": [{"kind": "credential_active", "credential": "api-key"}],
            }],
        })
        self.assertEqual(runbook.state.credentials["api-key"].owner, "payments")
        self.assertEqual(runbook.steps[0].effect_annotations["idempotency"], "idempotent")
        self.assertEqual(runbook.waivers[0].benchmark_visibility, "visible")

    def test_rejects_invalid_effect_annotations_and_waivers(self):
        with self.assertRaisesRegex(RunbookParseError, "effect_types"):
            parse_runbook({
                "system": {"credentials": {"api-key": {}}},
                "steps": [{
                    "id": "revoke",
                    "action": "revoke_credential",
                    "params": {"credential": "api-key"},
                    "effect_annotations": {"idempotency": "idempotent"},
                }],
            })

        with self.assertRaisesRegex(RunbookParseError, "benchmark_visibility"):
            parse_runbook({
                "metadata": {"waivers": [{
                    "id": "w1",
                    "owner": "owner",
                    "expiry": "2099-12-31",
                    "scope": "*",
                    "rationale": "test",
                    "invariant": "effect_annotation_required",
                    "benchmark_visibility": "private",
                }]},
                "system": {},
                "steps": [],
            })

        with self.assertRaisesRegex(RunbookParseError, "unknown credential"):
            parse_runbook({
                "system": {"credentials": {}},
                "steps": [{"id": "revoke", "action": "revoke_credential", "params": {"credential": "missing"}}],
            })


if __name__ == "__main__":
    unittest.main()
