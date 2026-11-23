"""Matched episode evidence, measured failures, and frozen recovery screening."""

import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from aether_cl.m3_runtime import M3Config, run
from aether_cl.m3_screening import (PROTOCOL_PATH, check_cell, compare_recovery,
                                    frozen_protocol, paired_outcomes, run_screening)
from test_m2 import inject
from test_recovery import RetryEnvironment


class VariedEnvironment(RetryEnvironment):
    def reset(self, seed):
        self.seed = seed
        super().reset(seed)
        self.cube.pose.raw_pose[0, 0] = (seed % 20) * .0005
        self.goal[1] = (seed % 20) * .0003
        return self.snapshot(), {"success": [False], "is_grasped": [False],
                                 "is_robot_static": [True], "is_obj_placed": [False]}


class M3ScreeningTests(unittest.TestCase):
    def setUp(self):
        software = patch("aether_cl.m3_runtime.software_manifest", return_value={"git_commit": "fixture", "git_dirty": False})
        software.start()
        self.addCleanup(software.stop)

    def runner(self, config, env_type=VariedEnvironment):
        return run(config, env_factory=lambda _: env_type(), disturbance_fn=inject)

    def execute(self, output, system="v2", condition="object_shift", seed=40, episodes=2, env_type=VariedEnvironment):
        config = M3Config(system=system, verification=system != "baseline", disturbance=condition,
                          seed=seed, episodes=episodes, render=False, output=output)
        result = self.runner(config, env_type)
        return config, Path(result["run_directory"]), result

    def test_frozen_180_episode_matrix_pairs_and_every_archive_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = run_screening(Path(temporary) / "runs", run_fn=self.runner)
            self.assertEqual(report["state"], "passed", [(t["condition"], t["system"], t.get("failed_checks"), t.get("error")) for t in report["trials"]])
            self.assertEqual(sum(len(t["episodes"]) for t in report["trials"]), 180)
            self.assertEqual(len(report["pairs"]), 3)
            self.assertEqual(len(report["recovery_pairs"]), 3)
            for trial in report["trials"]:
                self.assertEqual([e["seed"] for e in trial["episodes"]], list(range(40, 60)))
                self.assertEqual(trial["config"]["fps"], 5)
                self.assertEqual(trial["config"]["disturbance"], trial["condition"])
                self.assertEqual(trial["config"]["system"], trial["system"])
                self.assertEqual(trial["evaluation"]["eligible_episodes"], 20)
            for pair in report["paired_outcomes"]:
                self.assertEqual(pair["eligible_pairs"], 20)
                self.assertEqual(pair["both_succeeded"] if pair["condition"] == "none" else pair["recovery_only_success"], 20)
            with tarfile.open(report["archive"]) as bundle:
                index = json.load(bundle.extractfile("m3-screening/archive_index.json"))
                self.assertEqual(set(bundle.getnames()), {e["path"] for e in index["files"]} | {"m3-screening/archive_index.json"})
                self.assertEqual(json.load(bundle.extractfile("m3-screening/protocol.json")), frozen_protocol())
                for entry in index["files"]:
                    data = bundle.extractfile(entry["path"]).read()
                    self.assertEqual(len(data), entry["bytes"])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
            digest = hashlib.sha256(Path(report["archive"]).read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "new path"):
                run_screening(Path(temporary) / "another", report["archive"], run_fn=self.runner)
            self.assertEqual(hashlib.sha256(Path(report["archive"]).read_bytes()).hexdigest(), digest)

    def test_normal_natural_failure_and_failed_retry_are_valid_measured_outcomes(self):
        class MissedRetry(VariedEnvironment):
            def step(self, action):
                if self.step_number == 80:
                    self.cube.pose.raw_pose[0, 1] += .12
                closing = action[-1] < 0
                result = super().step(action)
                if self.step_number > 127:
                    self.held = False
                    self.aperture = 0 if closing else .08
                    self.cube.pose.raw_pose[0, :3] = [0, .24, .02]
                    result = (self.snapshot(), *result[1:-1],
                              {**result[-1], "is_grasped": [False], "success": [False]})
                return result
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, passive, left = self.execute(root / "v1", system="v1", condition="none", env_type=MissedRetry)
            config, active, result = self.execute(root / "v2", condition="none", env_type=MissedRetry)
            checked = check_cell(active, config)
            self.assertTrue(checked["passed"], checked["failed_checks"])
            self.assertEqual(result["evaluation"]["task_success_rate_at_end"], 0)
            self.assertEqual(result["evaluation"]["recovery_metrics"]["aborted_attempts"], 2)
            self.assertTrue(compare_recovery(passive, active)["passed"])
            self.assertEqual(paired_outcomes({"episodes": left["episodes"]}, checked)["both_failed"], 2)

    def test_excluded_reset_remains_in_order_and_zero_attempt_metrics_are_null(self):
        class Excluded(VariedEnvironment):
            def reset(self, seed):
                super().reset(seed)
                if seed == 40:
                    self.goal = self.cube.pose.raw_pose[0, :3].copy()
                return self.snapshot(), {"success": [seed == 40], "is_grasped": [False],
                                         "is_robot_static": [True], "is_obj_placed": [seed == 40]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, passive, left = self.execute(root / "v1", system="v1", condition="none", env_type=Excluded)
            config, active, result = self.execute(root / "v2", condition="none", env_type=Excluded)
            checked = check_cell(active, config)
            self.assertTrue(checked["passed"], checked["failed_checks"])
            self.assertEqual([e["seed"] for e in checked["episodes"]], [40, 41])
            self.assertEqual(result["evaluation"]["eligible_episodes"], 1)
            self.assertIsNone(result["evaluation"]["recovery_metrics"]["recovery_success_rate"])
            self.assertTrue(compare_recovery(passive, active)["passed"])
            paired = paired_outcomes({"episodes": left["episodes"]}, checked)
            self.assertEqual(paired["excluded_seeds"], [40])
            self.assertEqual(paired["eligible_pairs"], 1)

    def test_corrupted_cost_budget_summary_or_transport_evidence_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, directory, _ = self.execute(Path(temporary))
            original = (directory / "result.json").read_text()
            for field, value in (("action_steps", 231), ("observed_tcp_path_m", 999)):
                changed = json.loads(original)
                changed["episodes"][0]["recovery"][field] = value
                (directory / "result.json").write_text(json.dumps(changed))
                checked = check_cell(directory, config)
                self.assertFalse(checked["passed"])
                self.assertIn("episode_summaries_match_logs", checked["failed_checks"])
                self.assertIn("recovery_contracts", checked["failed_checks"])
            (directory / "result.json").write_text(original)
            events_path = directory / "events.jsonl"
            events = [json.loads(l) for l in events_path.read_text().splitlines()]
            transport = next(e for e in events if e["event"] == "step" and e["controller_decision"]["phase"] == "recovery_transport")
            previous = next(e for e in events if e["event"] == "step" and e["episode"] == transport["episode"] and e["step"] == transport["step"] - 1)
            previous["recovery"]["candidate_persistence_steps"] = 0
            events_path.write_text(''.join(json.dumps(e) + '\n' for e in events))
            self.assertIn("recovery_contracts", check_cell(directory, config)["failed_checks"])

    def test_changed_pretrigger_action_breaks_pair_without_requiring_full_v2_equality(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, passive, _ = self.execute(root / "v1", system="v1")
            _, active, _ = self.execute(root / "v2")
            self.assertTrue(compare_recovery(passive, active)["passed"])
            file = active / "events.jsonl"
            events = [json.loads(l) for l in file.read_text().splitlines()]
            next(e for e in events if e["event"] == "step")["action"][0] += .01
            file.write_text(''.join(json.dumps(e) + '\n' for e in events))
            checked = compare_recovery(passive, active)
            self.assertFalse(checked["passed"])
            self.assertFalse(checked["checks"]["causal_prefixes"])

    def test_source_or_protocol_change_stops_before_output_and_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "runs"
            with patch.dict("aether_cl.m3_screening.FROZEN_SOURCES", {"recovery.py": "wrong"}), patch("aether_cl.m3_screening.run_in_process") as child:
                with self.assertRaisesRegex(ValueError, "recovery.py"):
                    run_screening(output)
                child.assert_not_called()
            wrong = Path(temporary) / "protocol.json"
            protocol = json.loads(PROTOCOL_PATH.read_text())
            protocol["seeds"] = list(range(20, 40))
            wrong.write_text(json.dumps(protocol))
            with patch("aether_cl.m3_screening.PROTOCOL_PATH", wrong), patch("aether_cl.m3_screening.run_in_process") as child:
                with self.assertRaisesRegex(ValueError, "preregistration"):
                    run_screening(output)
                child.assert_not_called()
            self.assertFalse(output.exists())

    def test_early_natural_failure_allows_different_later_injection_pose(self):
        class EarlyMiss(VariedEnvironment):
            def step(self, action):
                if self.step_number == 80:
                    self.cube.pose.raw_pose[0, 1] += .12
                return super().step(action)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, passive, _ = self.execute(root / "v1", system="v1", condition="object_drop", env_type=EarlyMiss)
            config, active, _ = self.execute(root / "v2", condition="object_drop", env_type=EarlyMiss)
            checked = check_cell(active, config)
            self.assertTrue(checked["passed"], checked["failed_checks"])
            paired = compare_recovery(passive, active)
            self.assertTrue(paired["passed"], paired)
            self.assertTrue(all(e["trigger_step"] < 181 for e in paired["episode_prefixes"]))
            def injection(directory):
                return next(json.loads(l)["disturbance"] for l in (directory / "events.jsonl").read_text().splitlines()
                            if json.loads(l)["event"] == "disturbance_applied")
            self.assertNotEqual(injection(passive)["before_pose_world"], injection(active)["before_pose_world"])

    def test_unsupported_diagnosis_without_attempt_is_valid_and_corrupt_metrics_fail(self):
        class ChangedGoal(VariedEnvironment):
            def step(self, action):
                if self.step_number == 1:
                    self.goal[1] += .1
                return super().step(action)
        with tempfile.TemporaryDirectory() as temporary:
            config, directory, result = self.execute(Path(temporary), condition="none", env_type=ChangedGoal)
            checked = check_cell(directory, config)
            self.assertTrue(checked["passed"], checked["failed_checks"])
            self.assertTrue(all(e["recovery"]["attempts"] == 0 and e["recovery"]["failure_detail"] == "unsupported_failure"
                                for e in result["episodes"]))
            result["evaluation"]["verification_metrics"]["true_positive"] += 1
            (directory / "result.json").write_text(json.dumps(result))
            checked = check_cell(directory, config)
            self.assertIn("verification_metrics_match_replay", checked["failed_checks"])

    def test_missing_tcp_aborts_retry_and_uncertainty_remains_measured(self):
        class MissingTCP(VariedEnvironment):
            def step(self, action):
                observation, *outputs = super().step(action)
                if self.step_number == 130:
                    del observation["extra"]["tcp_pose"]
                return observation, *outputs
        with tempfile.TemporaryDirectory() as temporary:
            config, directory, result = self.execute(Path(temporary), env_type=MissingTCP)
            checked = check_cell(directory, config)
            self.assertTrue(checked["passed"], checked["failed_checks"])
            self.assertEqual(result["evaluation"]["verification_metrics"]["uncertain_steps"], 2)
            self.assertTrue(all(e["recovery"]["failure_detail"] == "invalid_recovery_observation" for e in result["episodes"]))

    def test_error_or_interruption_retains_partial_hashed_evidence(self):
        for error, state in ((RuntimeError("fixture child error"), "failed"), (KeyboardInterrupt(), "interrupted")):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temporary:
                def fail(config):
                    raise error
                report = run_screening(Path(temporary) / "runs", run_fn=fail)
                self.assertEqual(report["state"], state)
                self.assertEqual(report["paired_outcomes"], [])
                self.assertTrue(Path(report["archive"]).is_file())
                with tarfile.open(report["archive"]) as bundle:
                    self.assertEqual(json.load(bundle.extractfile("m3-screening/suite.json"))["state"], state)


if __name__ == "__main__":
    unittest.main()
