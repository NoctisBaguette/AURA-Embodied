"""Meaningful provenance and non-execution guards for the M9a source probe."""

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "m9_sensor_inspection.py"
SPEC = importlib.util.spec_from_file_location("m9_sensor_inspection", SCRIPT)
INSPECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSPECTOR)


class SensorInspectionGuards(unittest.TestCase):
    def test_no_native_import_environment_creation_reset_or_action(self):
        tree = ast.parse(SCRIPT.read_text())
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertFalse(any(name and name.split(".")[0] in ("mani_skill", "sapien", "gymnasium", "torch") for name in imports))
        calls = [n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertFalse(set(calls).intersection({"make", "reset", "step", "set_pose",
            "set_velocity", "set_linear_velocity", "set_angular_velocity", "add_force_torque", "apply_impulse"}))

    def test_seed_collision_is_reported_without_replacing_or_allocating_scenes(self):
        report = INSPECTOR.candidate_banks({"recorded_reset_seeds": [100, 181, 203]})
        self.assertEqual(report["calibration"]["retained_history_overlap"], [181])
        self.assertEqual(report["evaluation"]["retained_history_overlap"], [203])
        self.assertEqual(report["evaluation"]["proposed_seeds"], list(range(200, 240)))
        self.assertFalse(report["evaluation"]["unused_in_retained_history"])
        self.assertFalse(report["evaluation"]["allocation_frozen"])

    def test_observed_development_scenes_do_not_collide_with_proposed_banks(self):
        report = INSPECTOR.candidate_banks({"recorded_reset_seeds": [100, 101, *range(160, 180), 2022]})
        self.assertTrue(all(bank["unused_in_retained_history"] for bank in report.values()))
        self.assertTrue(all(not bank["allocation_frozen"] for bank in report.values()))

    def test_storage_budget_includes_raw_depth_both_rgb_views_and_validity(self):
        report = INSPECTOR.storage_budget()
        self.assertEqual(report["bytes_per_observation_set"], 2764800)
        self.assertEqual(report["bytes_per_second"], 55296000)
        self.assertEqual(report["matrix_bytes_including_masks"], 3185049600000)
        self.assertEqual(report["matrix_bytes_excluding_masks"], 2831155200000)
        self.assertIsNone(report["compression_ratio"])

    def test_camera_outline_does_not_evaluate_imports_properties_or_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "camera.py"
            path.write_text("raise AssertionError('source executed')\nclass Camera:\n"
                "    @property\n    def pose(self):\n        raise AssertionError('property invoked')\n"
                "    def capture(self, output=missing()):\n        pass\n")
            result = INSPECTOR.source_outline(path)
            self.assertEqual(result[0]["class"], "Camera")
            self.assertEqual([x["name"] for x in result[0]["methods"]], ["pose", "capture"])

    def test_frozen_native_sources_and_receipts_match_accepted_protocol(self):
        paths = INSPECTOR.check_frozen_sources()
        self.assertGreaterEqual(len(paths), 20)
        self.assertIn("tools/m8_physics_inspection.py", paths)

    def test_changed_frozen_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = INSPECTOR.check_frozen_sources()
            names = [*paths, "docs/research/experiments/evidence/AETHER_CL_M8_Placement_Protocol.json"]
            for name in names:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(INSPECTOR.ROOT / name, target)
            changed = root / "aura-sim/prototype_aether_cl/aether_cl/m6r_policy.py"
            changed.write_bytes(changed.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "Frozen M8"):
                INSPECTOR.check_frozen_sources(root)

    def test_protocol_cannot_rewrite_the_preserved_source_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "docs/research/experiments/evidence" / INSPECTOR.PROTOCOL.name
            target.parent.mkdir(parents=True)
            changed = json.loads(INSPECTOR.PROTOCOL.read_text())
            changed["sources_sha256"]["m6r_policy.py"] = "0" * 64
            target.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "protocol changed"):
                INSPECTOR.check_frozen_sources(root)

    def test_failed_inspection_retains_sources_and_recursive_hash_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "inspection"
            output.mkdir()
            source = output / "installed/mani_skill/sensors/camera.py"
            source.parent.mkdir(parents=True)
            source.write_text("retained partial source\n")
            archive = Path(temporary) / "evidence.tar.gz"
            INSPECTOR.write_bundle(output, archive, {"status": "error_retained_no_native_execution"})
            original = archive.read_bytes()
            with tarfile.open(archive) as tar:
                index = json.load(tar.extractfile("m9-sensor-inspection/file_index.json"))
                self.assertIn("installed/mani_skill/sensors/camera.py", index)
                for name, record in index.items():
                    raw = tar.extractfile("m9-sensor-inspection/" + name).read()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), record["sha256"])
                    self.assertEqual(len(raw), record["bytes"])
            with self.assertRaises(FileExistsError):
                INSPECTOR.write_bundle(output, archive, {"status": "another_run"})
            self.assertEqual(archive.read_bytes(), original)

    def test_output_must_not_modify_checkout_or_self_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "checkout"
            outside = Path(temporary) / "outside"
            with self.assertRaisesRegex(ValueError, "outside"):
                INSPECTOR.check_paths(root / "inspection", outside / "archive.tar.gz", root)
            with self.assertRaisesRegex(ValueError, "inside"):
                INSPECTOR.check_paths(outside, outside / "archive.tar.gz", root)
            outside.mkdir()
            with self.assertRaises(FileExistsError):
                INSPECTOR.check_paths(outside, Path(temporary) / "archive.tar.gz", root)

    def test_missing_external_tool_is_reported_not_installed(self):
        result = INSPECTOR.tool_probe(["m9_intentionally_missing_external_binary"])
        self.assertFalse(result["available"])


if __name__ == "__main__":
    unittest.main()
