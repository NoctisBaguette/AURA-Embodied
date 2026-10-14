"""Guard checks for M8 inspection: retained provenance and no fresh execution."""

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "m8_physics_inspection.py"
SPEC = importlib.util.spec_from_file_location("m8_physics_inspection", SCRIPT)
INSPECTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSPECTION)


class InspectionGuards(unittest.TestCase):
    def history(self, directory, records):
        root = Path(directory)
        path = root / "failed_or_stopped" / "events.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in records))
        return INSPECTION.inspect_history(root)

    def test_retains_failed_resets_and_does_not_treat_step_seed_as_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.history(directory, [
                {"event": "reset", "seed": 100},
                {"event": "controller_reset", "seed": 159},
                {"event": "step", "seed": 160},
                {"event": "run_failed", "error": "retained"},
            ])
            self.assertEqual(report["recorded_reset_seeds"], [100, 159])
            self.assertEqual(report["preferred_overlap"], [])
            self.assertEqual(report["first_unused_contiguous20_from160"], list(range(160, 180)))
            self.assertFalse(report["selection_frozen"])
            self.assertTrue(report["fresh_entry_must_recheck"])

    def test_seed_collision_is_reported_and_does_not_select_evaluation_seeds(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.history(directory, [{"event": "reset", "seed": s} for s in (100, 160, 175)])
            self.assertEqual(report["preferred_overlap"], [160, 175])
            self.assertEqual(report["first_unused_contiguous20_from160"], list(range(176, 196)))
            self.assertFalse(report["selection_frozen"])

    def test_original_controller_reset_without_seed_matches_later_native_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.history(directory, [
                {"event": "controller_reset", "episode": 0, "policy": {"name": "fixed_pick_cube"}},
                {"event": "reset", "episode": 0, "seed": 100},
                {"event": "controller_reset", "episode": 1, "policy": {}},
                {"event": "reset", "episode": 1, "seed": 160},
                {"event": "run_failed", "error": "retained"},
            ])
            self.assertEqual(report["preferred_overlap"], [160])
            self.assertEqual(report["reset_records"], 4)
            matched = report["legacy_controller_resets_matched"]
            self.assertEqual([r["seed"] for r in matched], [100, 160])
            self.assertEqual([r["seed_source_reset_line"] for r in matched], [2, 4])

    def test_unresolved_or_ambiguous_legacy_controller_reset_blocks(self):
        cases = [
            [{"event": "controller_reset", "episode": 0, "policy": {}}],
            [{"event": "controller_reset", "episode": 0, "policy": {}}, {"event": "reset", "episode": 1, "seed": 100}],
            [{"event": "controller_reset", "episode": 0, "policy": {}}, {"event": "reset", "episode": 0, "seed": 100}, {"event": "reset", "episode": 0, "seed": 160}],
            [{"event": "controller_reset", "episode": True, "policy": {}}],
            [{"event": "controller_reset", "episode": 0}],
        ]
        for records in cases:
            with self.subTest(records=records), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "Unresolved legacy"):
                    self.history(directory, [{"event": "reset", "seed": 100}] + records)

    def test_missing_real_reset_seed_still_blocks_and_explicit_bad_controller_seed_blocks(self):
        for bad in ({"event": "reset", "episode": 0}, {"event": "controller_reset", "episode": 0, "policy": {}, "seed": None}):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "reset seed"):
                    self.history(directory, [{"event": "reset", "seed": 100}, bad])

    def test_missing_native_history_and_unobserved_development_seed_block(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                INSPECTION.inspect_history(Path(directory))
            with self.assertRaisesRegex(ValueError, "seed100"):
                self.history(directory, [{"event": "reset", "seed": 159}])

    def test_malformed_reset_seed_cannot_pass_history(self):
        for seed in (True, None, "160", -1, 2**32):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "reset seed"):
                    self.history(directory, [{"event": "reset", "seed": 100}, {"event": "reset", "seed": seed}])

    def test_unknown_constructor_seed_is_blocked_before_environment_creation(self):
        template = "class BaseEnv:\n    def __init__(self):\n        self.reset(seed={})\n"
        self.assertEqual(INSPECTION.constructor_reset_seeds(template.format("2022")), [2022])
        self.assertEqual(INSPECTION.constructor_reset_seeds(template.format("[2022 + i for i in range(self.num_envs)]")), [2022])
        for seed in ("160", "selected_seed", "True", "[2022]"):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, "initialization reset"):
                INSPECTION.constructor_reset_seeds(template.format(seed))

    def test_binding_descriptor_inspection_does_not_invoke_property_or_force(self):
        class FakeRigidBody:
            @property
            def mass(self):
                raise AssertionError("Descriptor invoked")

            def add_force_at_point(self, force, point):
                """World-frame external force, inspector must only read this doc."""
                raise AssertionError("Force invoked")

        record = INSPECTION.interface(FakeRigidBody)
        self.assertEqual(record["force_or_impulse_names"], ["add_force_at_point"])
        self.assertIn("World-frame", record["members"]["add_force_at_point"]["doc"])

    def test_inspection_entry_has_no_rollout_or_pose_velocity_force_mutation(self):
        tree = ast.parse(SCRIPT.read_text())
        calls = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        forbidden = {"step", "set_pose", "set_linear_velocity", "set_angular_velocity",
                     "add_force_at_point", "add_force_torque", "apply_impulse", "set_velocity"}
        self.assertEqual(sorted(set(calls) & forbidden), [])
        targets = [n.attr for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                   for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
                   for n in ast.walk(target) if isinstance(n, ast.Attribute)]
        self.assertEqual(set(targets) & {"linear_velocity", "angular_velocity", "pose"}, set())
        resets = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "reset"]
        self.assertEqual(len(resets), 1)
        self.assertEqual(ast.unparse(resets[0].keywords[0].value), "DEVELOPMENT_SEED")

    def test_error_bundle_is_retained_indexed_and_never_overwrites_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "inspection"
            output.mkdir()
            archive = root / "inspection.tar.gz"
            INSPECTION.write_bundle(output, archive, {"status": "error_retained_no_fresh_execution"})
            first_hash = INSPECTION.sha256_file(archive)
            report_hash = INSPECTION.sha256_file(output / "inspection.json")
            with tarfile.open(archive) as tar:
                index = json.load(tar.extractfile("m8-physics-inspection/file_index.json"))
                for name, record in index.items():
                    raw = tar.extractfile("m8-physics-inspection/" + name).read()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), record["sha256"])
                    self.assertEqual(len(raw), record["bytes"])
            with self.assertRaises(FileExistsError):
                INSPECTION.write_bundle(output, archive, {"status": "another_run"})
            self.assertEqual(first_hash, INSPECTION.sha256_file(archive))
            self.assertEqual(report_hash, INSPECTION.sha256_file(output / "inspection.json"))


if __name__ == "__main__":
    unittest.main()
