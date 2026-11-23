"""Prevent previous-episode recovery from entering a paired reset."""

import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from aether_cl.m3_isolated_screening import PROTOCOL_PATH, run_screening
from aether_cl.m3_runtime import M3Config, run
from aether_cl.m3_screening import compare_recovery
from test_m2 import inject
from test_m3_screening import VariedEnvironment


class CarryoverEnvironment(VariedEnvironment):
    def snapshot(self):
        obs = super().snapshot()
        obs["extra"]["is_grasped"] = [self.held]
        return obs

    def reset(self, seed):
        previous_grasp = getattr(self, "held", False)
        super().reset(seed)
        if seed == 58:
            self.goal = self.cube.pose.raw_pose[0, :3].copy()
        obs = self.snapshot()
        # Reproduce the observed native stale contact flag after a successful
        # preceding recovery. A new environment has no previous grasp.
        obs["extra"]["is_grasped"] = [previous_grasp]
        return obs, {"success": [seed == 58], "is_grasped": [previous_grasp],
                     "is_robot_static": [True], "is_obj_placed": [seed == 58]}


class IsolatedScreeningTests(unittest.TestCase):
    def setUp(self):
        software = patch("aether_cl.m3_runtime.software_manifest", return_value={"git_commit": "fixture", "git_dirty": False})
        software.start()
        self.addCleanup(software.stop)

    def runner(self, config):
        return run(config, env_factory=lambda _: CarryoverEnvironment(), disturbance_fn=inject)

    def test_reused_environment_exposes_reset_carryover_without_weakening_pair_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = {}
            for system in ("v1", "v2"):
                result = self.runner(M3Config(system=system, verification=True, disturbance="object_shift",
                                             seed=40, episodes=2, render=False, output=Path(temporary) / system))
                paths[system] = Path(result["run_directory"])
            checked = compare_recovery(paths["v1"], paths["v2"])
            self.assertFalse(checked["passed"])
            self.assertFalse(checked["checks"]["same_resets"])
            self.assertTrue(checked["checks"]["causal_prefixes"])

    def test_180_one_episode_calls_eliminate_carryover_and_preserve_excluded_seed_and_hashes(self):
        calls, environments = [], []
        def child(config, environment, module):
            self.assertEqual(module, "aether_cl.m3")
            self.assertEqual(config.episodes, 1)
            self.assertEqual(config.fps, 5)
            calls.append((config.disturbance, config.seed, config.system))
            environments.append(environment.copy())
            return self.runner(config)
        with tempfile.TemporaryDirectory() as temporary, patch("aether_cl.m3_isolated_screening.run_in_process", side_effect=child):
            report = run_screening(Path(temporary) / "runs")
            self.assertEqual(report["state"], "passed")
            self.assertEqual(len(calls), 180)
            self.assertEqual(len(set(calls)), 180)
            self.assertEqual(calls[:6], [("none", seed, system) for seed in (40, 41) for system in ("baseline", "v1", "v2")])
            self.assertTrue(all(e == environments[0] for e in environments))
            self.assertEqual(len(report["pairs"]), 60)
            self.assertEqual(len(report["recovery_pairs"]), 60)
            self.assertTrue(all(c["excluded_seeds"] == [58] and c["eligible_episodes"] == 19 for c in report["cells"]))
            self.assertTrue(all(p["complete_valid_pairing"] and p["eligible_pairs"] == 19 for p in report["paired_outcomes"]))
            for t in report["episode_trials"]:
                self.assertEqual(t["episodes"][0]["episode"], 0)
                self.assertEqual(t["requested_seed_index"], t["seed"] - 40)
                self.assertEqual(t["episodes"][0]["steps"], 0 if t["seed"] == 58 else 360)
            with tarfile.open(report["archive"]) as bundle:
                index = json.load(bundle.extractfile("m3-isolated-screening/archive_index.json"))
                self.assertEqual(set(bundle.getnames()), {e["path"] for e in index["files"]} | {"m3-isolated-screening/archive_index.json"})
                for item in index["files"]:
                    data = bundle.extractfile(item["path"]).read()
                    self.assertEqual(len(data), item["bytes"])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            before = hashlib.sha256(Path(report["archive"]).read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "new path"):
                run_screening(Path(temporary) / "again", report["archive"])
            self.assertEqual(hashlib.sha256(Path(report["archive"]).read_bytes()).hexdigest(), before)

    def test_interrupt_or_errors_archive_partial_trials_and_null_incomplete_rates(self):
        for error, expected in ((KeyboardInterrupt(), "interrupted"), (RuntimeError("native fixture failure"), "failed")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                def fail(config):
                    raise error
                report = run_screening(Path(temporary) / "runs", run_fn=fail)
                self.assertEqual(report["state"], expected)
                self.assertTrue(all(c["task_success_rate_at_end"] is None for c in report["cells"]))
                self.assertTrue(all(p["success_rate_difference_v2_minus_v1"] is None for p in report["paired_outcomes"]))
                with tarfile.open(report["archive"]) as bundle:
                    self.assertEqual(json.load(bundle.extractfile("m3-isolated-screening/suite.json"))["state"], expected)

    def test_changed_guard_or_execution_protocol_stops_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "runs"
            with patch.dict("aether_cl.m3_isolated_screening.SOURCES", {"m3_screening.py": "wrong"}), patch("aether_cl.m3_isolated_screening.run_in_process") as child:
                with self.assertRaisesRegex(ValueError, "m3_screening.py"):
                    run_screening(output)
                child.assert_not_called()
            value = json.loads(PROTOCOL_PATH.read_text())
            value["child_episodes"] = 20
            changed = Path(temporary) / "protocol.json"
            changed.write_text(json.dumps(value))
            with patch("aether_cl.m3_isolated_screening.PROTOCOL_PATH", changed), patch("aether_cl.m3_isolated_screening.run_in_process") as child:
                with self.assertRaisesRegex(ValueError, "amendment"):
                    run_screening(output)
                child.assert_not_called()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
