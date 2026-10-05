"""Fresh-seed screening checks completeness, not favorable task outcomes."""

import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from aether_cl.acceptance import check_screening, run_acceptance, trace
from aether_cl.runtime import RunConfig, run
from test_m2 import Environment, inject


def fixture_run(config):
    return run(config, env_factory=lambda _: Environment(), disturbance_fn=inject)


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        software = patch("aether_cl.runtime.software_manifest", return_value={
            "git_commit": "fixture-revision", "git_dirty": False})
        software.start()
        self.addCleanup(software.stop)

    def test_frozen_twenty_seed_matrix_has_120_episodes_and_paired_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(temporary, screening=True, run_fn=fixture_run)
            self.assertEqual(report["state"], "passed")
            self.assertEqual(report["seed"], 20)
            self.assertEqual(report["episodes_per_cell"], 20)
            self.assertEqual(sum(len(t["episodes"]) for t in report["trials"]), 120)
            self.assertTrue(all(p["passed"] for p in report["pairs"]))
            for trial in report["trials"]:
                self.assertEqual([e["seed"] for e in trial["episodes"]], list(range(20, 40)))
                self.assertEqual(trial["config"]["max_steps"], 360)
            self.assertEqual(set(report["frozen_files_sha256"]),
                             {"policies.py", "verification.py", "disturbances.py", "runtime.py"})
            with tarfile.open(report["archive"]) as bundle:
                self.assertIn("screening/suite.json", bundle.getnames())
                index = json.load(bundle.extractfile("screening/archive_index.json"))
                self.assertEqual(index["scope"], "frozen_seed20_39_screening")

    def test_eligible_denominator_retains_excluded_reset_without_resampling(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = RunConfig(controller="fixed_pick_cube", protocol="m2", seed=7,
                               episodes=2, max_steps=360, render=False, output=Path(temporary))
            result = fixture_run(config)
            checked = check_screening(Path(result["run_directory"]), config)
            self.assertTrue(checked["passed"], checked["failed_checks"])
            self.assertEqual(checked["evaluation"]["eligible_episodes"], 1)
            self.assertEqual(checked["evaluation"]["excluded_episodes"], 1)
            self.assertEqual(checked["evaluation"]["task_success_rate_at_end"], 1)
            self.assertEqual([e["seed"] for e in checked["episodes"]], [7, 8])

    def test_natural_policy_failure_is_a_measured_outcome_not_invalid_evidence(self):
        class MissedGrasp(Environment):
            def reset(self, seed):
                self.seed = seed
                return super().reset(seed)
            def step(self, action):
                if self.seed == 20 and self.step_number == 80:
                    self.cube.pose.raw_pose[0, 1] += .12
                return super().step(action)
        with tempfile.TemporaryDirectory() as temporary:
            config = RunConfig(controller="fixed_pick_cube", protocol="m2", verification=True,
                               seed=20, episodes=2, max_steps=360, render=False, output=Path(temporary))
            result = run(config, env_factory=lambda _: MissedGrasp(), disturbance_fn=inject)
            checked = check_screening(Path(result["run_directory"]), config)
            self.assertTrue(checked["passed"], checked["failed_checks"])
            self.assertEqual(checked["evaluation"]["task_success_rate_at_end"], .5)
            self.assertEqual(checked["episodes"][0]["first_detected_failure"]["failure"], "GRASP_FAILURE")

    def test_changed_seed_or_wrong_denominator_fails_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = RunConfig(controller="fixed_pick_cube", protocol="m2", seed=20,
                               episodes=2, max_steps=360, render=False, output=Path(temporary))
            result = fixture_run(config)
            directory = Path(result["run_directory"])
            result["episodes"][1]["seed"] = 99
            result["evaluation"]["eligible_episodes"] = 1
            (directory / "result.json").write_text(json.dumps(result))
            checked = check_screening(directory, config)
            self.assertFalse(checked["passed"])
            self.assertIn("exact_requested_seeds", checked["failed_checks"])
            self.assertIn("eligible_denominator", checked["failed_checks"])

    def test_trace_omits_reset_info_but_compares_full_reset_observation(self):
        event = {"event": "reset", "seed": 20, "eligibility": {"eligible": True},
                 "observation": {"extra": {"is_grasped": [False]}},
                 "info": {"is_grasped": [False]}}
        original = trace([event])
        event["info"]["is_grasped"] = [True]
        self.assertEqual(trace([event]), original)
        changed = json.loads(json.dumps(event))
        changed["observation"]["extra"]["is_grasped"] = [True]
        self.assertNotEqual(trace([changed]), original)

    def test_changed_frozen_source_hash_stops_before_any_trial_or_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "runs"
            with patch.dict("aether_cl.acceptance.FROZEN_FILES_SHA256", {"policies.py": "incorrect-fingerprint"}), \
                    patch("aether_cl.acceptance.run_in_process") as child:
                with self.assertRaisesRegex(ValueError, "policies.py"):
                    run_acceptance(output, screening=True)
                child.assert_not_called()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
