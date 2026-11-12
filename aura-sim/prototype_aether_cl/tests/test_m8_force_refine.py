"""Second-stage dose-plan/retention fixtures; no native force proof."""

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from aether_cl import m8_force_refine as refine


class RefinementTests(unittest.TestCase):
    def test_fixed24_plan_only_reuses100101_with_eight_repeat_slots(self):
        plan = refine.plan()
        self.assertEqual(len(plan), 24)
        self.assertEqual({p["seed"] for p in plan}, {100, 101})
        self.assertEqual([sum(p["kind"] == k for p in plan)
                          for k in ("original", "main", "repeat")], [2, 14, 8])
        self.assertEqual(len({(p["kind"], p["point_id"], p["seed"]) for p in plan}), 24)
        for seed in (True, 99, 140, 159, 160, 179, 2022):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                refine.validate_child(seed, "main", "force-probe-1")
        with self.assertRaises(ValueError):
            refine.validate_child(100, "original", "force-probe-1")
        with self.assertRaises(ValueError):
            refine.validate_child(100, "main", "arbitrary-force")

    def test_force_grid_extends_measured_v1_max_without_state_or_timing_targets(self):
        points = refine.candidate_points()
        self.assertEqual(len(points), 7)
        self.assertEqual(points[0]["command_force_y_n"], 0.)
        maximum = refine.response_review()["next_development_plan"]["existing_reference_max_force_n"]
        self.assertEqual(points[2]["command_force_y_n"], maximum)
        for k, point in enumerate(points[3:], 1):
            self.assertEqual(point["command_force_y_n"], float(np.float32(maximum * 1.25**k)))
        self.assertTrue(all(a["command_force_y_n"] < b["command_force_y_n"]
                            for a, b in zip(points, points[1:])))
        for point in points:
            self.assertIsNone(point["estimated_drift_m"])
            self.assertEqual(point["command_force_world_n"], [0., point["command_force_y_n"], 0.])
            self.assertEqual(point["torque_world_nm"], [0., 0., 0.])
            self.assertEqual(point["planned_nominal_duration_s"], .05)

    def test_changed_review_receipt_blocks_before_installed_native_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed.json"
            review = refine.response_review()
            review["all_audit_checks_passed"] = False
            changed.write_text(json.dumps(review))
            with patch.object(refine, "RESPONSE_REVIEW", changed), \
                    patch.object(refine, "installed_preflight") as native, \
                    patch.object(refine.subprocess, "run") as child, \
                    redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "independently audited"):
                    refine.preflight("fixture-head")
                output = Path(directory) / "study"; archive = Path(directory) / "archive.tar.gz"
                with self.assertRaises(SystemExit):
                    refine.run_suite(output, archive, "fixture-head")
                native.assert_not_called()
                child.assert_not_called()
                retained = json.loads((output / "suite.json").read_text())
                self.assertEqual(retained["state"], "error_retained")
                self.assertEqual(retained["trials"], [])
                self.assertTrue(archive.exists())

    def test_parent_launches_all_fixed_children_and_indexes_both_receipts(self):
        commands = []
        def child(command, **kwargs):
            commands.append(command)
            case = Path(command[command.index("--output") + 1])
            refine.write_json(case / "m8_result.json", {"state": "finished_valid_development_evidence"})
            return subprocess.CompletedProcess(command, 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); output = root / "study"; archive = root / "archive.tar.gz"
            with patch.object(refine, "preflight", return_value={"software": {}}), \
                    patch.object(refine.subprocess, "run", side_effect=child), \
                    patch.object(refine, "compare", return_value={"passed": True, "checks": {}}), \
                    redirect_stdout(io.StringIO()):
                report = refine.run_suite(output, archive, "fixture-head")
            self.assertEqual(report["state"], "valid_development_evidence")
            self.assertFalse(report["fresh_study_started"])
            self.assertFalse(report["force_family_frozen_for_fresh_study"])
            self.assertEqual(len(report["comparisons"]), 22)
            self.assertEqual(len(commands), 24)
            for command, slot in zip(commands, refine.plan()):
                self.assertEqual(command[command.index("-m") + 1], "aether_cl.m8_force_refine")
                self.assertEqual(command[command.index("--seed") + 1], str(slot["seed"]))
                self.assertEqual(command[command.index("--point") + 1], slot["point_id"])
            with tarfile.open(archive) as bundle:
                index = json.load(bundle.extractfile("m8-force-commission/file_index.json"))
                for receipt in (refine.RECEIPT, refine.RESPONSE_REVIEW):
                    relative = "sources/" + receipt.name
                    self.assertIn(relative, index)
                    self.assertEqual(bundle.extractfile("m8-force-commission/" + relative).read(), receipt.read_bytes())

    def test_failed_child_is_retained_once_without_advancing_or_replacing(self):
        commands = []
        def failed(command, **kwargs):
            commands.append(command)
            case = Path(command[command.index("--output") + 1])
            (case / "partial-native.jsonl").write_text('{"event":"reset","seed":100}\n')
            return subprocess.CompletedProcess(command, 2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); output = root / "study"; archive = root / "archive.tar.gz"
            with patch.object(refine, "preflight", return_value={"software": {}}), \
                    patch.object(refine.subprocess, "run", side_effect=failed), \
                    redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    refine.run_suite(output, archive, "fixture-head")
            self.assertEqual(len(commands), 1)
            report = json.loads((output / "suite.json").read_text())
            self.assertEqual(len(report["trials"]), 1)
            self.assertEqual(report["trials"][0]["returncode"], 2)
            self.assertEqual(report["state"], "error_retained")
            with tarfile.open(archive) as bundle:
                relative = report["trials"][0]["directory"] + "/partial-native.jsonl"
                index = json.load(bundle.extractfile("m8-force-commission/file_index.json"))
                self.assertIn(relative, index)
            with self.assertRaises(FileExistsError):
                refine.run_suite(output, archive, "fixture-head")

    def test_no_new_force_api_or_cube_setter_is_added(self):
        tree = ast.parse(Path(refine.__file__).read_text())
        forbidden = {"set_pose", "set_linear_velocity", "set_angular_velocity", "set_velocity",
                     "add_force_torque", "apply_impulse", "shift_native"}
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertFalse(any(isinstance(n.func, ast.Attribute) and n.func.attr in forbidden for n in calls))
        configs = [n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "M6RConfig"]
        self.assertEqual(len(configs), 1)
        values = {k.arg: ast.literal_eval(k.value) for k in configs[0].keywords
                  if k.arg in ("system", "verification", "render", "disturbance")}
        self.assertEqual(values, {"system": "baseline", "verification": False,
                                  "render": False, "disturbance": "none"})


if __name__ == "__main__":
    unittest.main()
