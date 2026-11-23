"""Recovery contracts and matched traces. Fixtures are not native physics."""

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest

import numpy as np

from aether_cl.acceptance import FROZEN_FILES_SHA256, trace
from aether_cl.m3 import config_from_args, parser
from aether_cl.m3_runtime import M3Config, run
from aether_cl.policies import FixedPickCube
from aether_cl.recovery import RecoveryController, RecoverySettings
from aether_cl.runtime import RunConfig, run as m2_run
from test_m2 import Environment, inject
from test_policy import BASE
from test_verification import state


class RetryEnvironment(Environment):
    def snapshot(self):
        observation = super().snapshot()
        observation["extra"]["tcp_pose"][0, 3:] = [0, 1, 0, 0]
        return observation


def logs(result):
    return [json.loads(line) for line in
            (Path(result["run_directory"]) / "events.jsonl").read_text().splitlines()]


class RecoveryTests(unittest.TestCase):
    def execute(self, system="v2", disturbance="none", env_type=RetryEnvironment, **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        env = env_type()
        result = run(M3Config(system=system, verification=system != "baseline",
                              disturbance=disturbance, render=False,
                              output=Path(temporary.name), **kwargs),
                     env_factory=lambda _: env, disturbance_fn=inject)
        self.assertTrue(env.closed)
        return result, logs(result)

    def test_frozen_m2_sources_remain_identical(self):
        root = Path(__file__).parents[1] / "aether_cl"
        for name, expected in FROZEN_FILES_SHA256.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected)

    def test_passive_traces_match_frozen_m2_and_normal_v2_is_unchanged(self):
        for condition in ("none", "object_shift", "object_drop"):
            with tempfile.TemporaryDirectory() as temporary:
                result = m2_run(RunConfig(controller="fixed_pick_cube", protocol="m2", verification=True,
                                         disturbance=condition, max_steps=360, render=False, output=Path(temporary)),
                                env_factory=lambda _: RetryEnvironment(), disturbance_fn=inject)
                original = trace(logs(result))
            for system in (("baseline", "v1", "v2") if condition == "none" else ("baseline", "v1")):
                with self.subTest(condition=condition, system=system):
                    result, events = self.execute(system, condition)
                    self.assertEqual(trace(events), original)
                    self.assertEqual(result["evaluation"]["task_success_rate_at_end"], int(condition == "none"))
                    self.assertEqual(result["episodes"][0]["steps"], 360)
                    if system == "v2":
                        self.assertEqual(result["episodes"][0]["recovery"]["attempts"], 0)
                        self.assertIsNone(result["evaluation"]["recovery_metrics"]["recovery_success_rate"])

    def test_shift_and_drop_recover_with_one_attempt_and_unchanged_prefix(self):
        for condition, trigger in (("object_shift", 127), ("object_drop", 183)):
            with self.subTest(condition=condition):
                passive, left = self.execute("v1", condition)
                active, right = self.execute("v2", condition)
                self.assertEqual(passive["evaluation"]["task_success_rate_at_end"], 0)
                self.assertEqual(active["evaluation"]["task_success_rate_at_end"], 1)
                before = [e for e in left if e["event"] == "step"]
                after = [e for e in right if e["event"] == "step"]
                for field in ("action", "observation", "controller_decision", "reference", "verification"):
                    self.assertEqual([e[field] for e in before[:trigger]], [e[field] for e in after[:trigger]])
                ep = active["episodes"][0]
                self.assertEqual(ep["steps"], 360)
                self.assertEqual(ep["recovery"]["attempts"], 1)
                self.assertEqual(ep["recovery"]["trigger_step"], trigger)
                self.assertEqual(ep["recovery"]["first_action_step"], trigger + 1)
                self.assertLessEqual(ep["recovery"]["action_steps"], ep["recovery"]["action_budget"])
                self.assertEqual(ep["recovery"]["state"], "attempt_complete")
                self.assertEqual(after[trigger]["action"][-1], 1)
                self.assertEqual(after[trigger]["controller_decision"]["phase"], "recovery_retract")
                self.assertEqual(len([e for e in right if e["event"] == "disturbance_applied"]), 1)

    def test_failed_retry_grasp_aborts_before_lift_or_transport(self):
        class MissedRetry(RetryEnvironment):
            def step(self, action):
                closing = action[-1] < 0
                result = super().step(action)
                if self.step_number > 127:
                    self.held = False
                    self.aperture = 0 if closing else .08
                    self.cube.pose.raw_pose[0, :3] = [0, .12, .02]
                    result = (self.snapshot(), *result[1:-1],
                              {**result[-1], "is_grasped": [False], "success": [False]})
                return result
        result, events = self.execute(disturbance="object_shift", env_type=MissedRetry)
        ep = result["episodes"][0]
        self.assertEqual(ep["recovery"]["state"], "aborted")
        self.assertEqual(ep["recovery"]["failure_detail"], "retry_grasp_not_established")
        phases = [e["controller_decision"]["phase"] for e in events if e["event"] == "step"]
        self.assertNotIn("recovery_lift", phases)
        self.assertNotIn("recovery_transport", phases)
        self.assertEqual(ep["recovery"]["attempts"], 1)
        self.assertEqual(ep["steps"], 360)
        self.assertEqual(result["evaluation"]["recovery_metrics"]["recovery_success_rate"], 0)

    def test_reference_contact_flags_cannot_change_recovery_actions(self):
        class PoisonReference(RetryEnvironment):
            def step(self, action):
                observation, reward, term, trunc, info = super().step(action)
                return observation, reward, term, trunc, {**info, "is_grasped": [False], "success": [False]}
        _, clean = self.execute(disturbance="object_shift")
        _, poison = self.execute(disturbance="object_shift", env_type=PoisonReference)
        for field in ("action", "controller_decision", "verification", "recovery"):
            self.assertEqual([e[field] for e in clean if e["event"] == "step"],
                             [e[field] for e in poison if e["event"] == "step"])

    def test_arrival_phases_tolerate_lag_without_extending_episode(self):
        class LaggedServo(RetryEnvironment):
            def reset(self, seed):
                super().reset(seed)
                self.cube.pose.raw_pose[0, :3] = [-.0007477, .053642, .02]
                self.goal = np.array([.0268157, -.0019813, .2889335])
                return self.snapshot(), {"success": [False], "is_grasped": [False],
                                         "is_robot_static": [True], "is_obj_placed": [False]}

            def step(self, action):
                command = action.copy()
                desired = command[:3] + BASE[0, :3]
                command[:3] = self.tcp + .4 * (desired - self.tcp) - BASE[0, :3]
                return super().step(command)

        # A lagged contact fixture, not a model or validation of native physics.
        for condition in ("object_shift", "object_drop"):
            result, _ = self.execute(disturbance=condition, env_type=LaggedServo)
            ep = result["episodes"][0]
            self.assertEqual(ep["steps"], 360)
            self.assertTrue(ep["task_success_at_end"])
            self.assertEqual(ep["recovery"]["state"], "attempt_complete")
            self.assertLessEqual(ep["recovery"]["action_steps"], ep["recovery"]["action_budget"])

    def controller(self):
        observation = state(tcp=(0, 0, .14), aperture=.08)
        observation["extra"]["tcp_pose"][0, 3:] = [0, 1, 0, 0]
        return RecoveryController(FixedPickCube(observation, BASE), BASE, 360), observation

    def test_late_failure_holds_without_increasing_budget_or_starting_attempt(self):
        controller, observation = self.controller()
        prior, _ = controller.action(observation, 349, {"status": "pending"})
        action, _ = controller.action(observation, 350, {"status": "failed", "failure": "GRASP_FAILURE"})
        np.testing.assert_array_equal(action, prior)
        self.assertEqual(controller.attempts, 0)
        self.assertEqual(controller.failure_detail, "insufficient_remaining_budget")

    def test_unsupported_failure_holds_and_uncertainty_does_not_start_retry(self):
        controller, observation = self.controller()
        controller.action(observation, 1, {"status": "uncertain", "failure": "UNCERTAIN"})
        self.assertEqual(controller.state, "nominal")
        controller.action(observation, 2, {"status": "failed", "failure": "STATE_MISMATCH"})
        self.assertEqual(controller.state, "aborted")
        self.assertEqual(controller.failure_detail, "unsupported_failure")
        self.assertEqual(controller.attempts, 0)

    def test_goal_change_and_missing_state_abort_active_attempt(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                controller, observation = self.controller()
                controller.action(observation, 128, {"status": "failed", "failure": "GRASP_FAILURE"})
                invalid = copy.deepcopy(observation)
                if missing:
                    del invalid["agent"]["qpos"]
                else:
                    invalid["extra"]["goal_pos"][0, 0] += .1
                controller.observe(invalid)
                self.assertEqual(controller.state, "aborted")
                self.assertEqual(controller.failure_detail, "invalid_recovery_observation" if missing else "goal_changed_during_attempt")

    def test_motion_timeout_and_remaining_budget_are_bounded(self):
        controller, observation = self.controller()
        observation["extra"]["tcp_pose"][0, 2] = .02
        verdict = {"status": "failed", "failure": "GRASP_FAILURE"}
        for step in range(128, 163):
            controller.action(observation, step, verdict)
            controller.observe(observation)  # TCP deliberately never follows.
        self.assertEqual(controller.state, "aborted")
        self.assertEqual(controller.failure_detail, "retry_retract_target_not_reached")
        self.assertEqual(controller.steps, 35)
        action, _ = controller.action(observation, 163, verdict)
        np.testing.assert_array_equal(action, controller.last_action)

        controller, observation = self.controller()
        controller.action(observation, 300, verdict)
        self.assertEqual(controller.action_budget, 61)
        # Exhaustion is independent of per-phase timeout.
        controller.steps = 60
        controller.action(observation, 360, verdict)
        controller.observe(observation)
        self.assertEqual(controller.failure_detail, "remaining_action_budget_exhausted")
        self.assertEqual(controller.steps, 61)

    def test_lost_attachment_during_transport_stops_after_persistence(self):
        controller, observation = self.controller()
        verdict = {"status": "failed", "failure": "GRASP_FAILURE"}
        controller.action(observation, 128, verdict)
        controller.stage_index = 5  # Isolate the transport monitoring boundary.
        missed = state(cube=(0, .12, .02), tcp=(0, 0, .14), aperture=0)
        missed["extra"]["tcp_pose"][0, 3:] = [0, 1, 0, 0]
        for step in (129, 130, 131):
            controller.action(missed, step, verdict)
            controller.observe(missed)
        self.assertEqual(controller.state, "aborted")
        self.assertEqual(controller.failure_detail, "attachment_lost_during_retry")

    def test_all_excluded_and_stopped_runs_keep_rates_null(self):
        result, _ = self.execute(seed=8)
        self.assertEqual(result["evaluation"]["eligible_episodes"], 0)
        self.assertIsNone(result["evaluation"]["task_success_rate_at_end"])
        self.assertIsNone(result["evaluation"]["recovery_metrics"]["recovery_success_rate"])
        stop = threading.Event()
        with tempfile.TemporaryDirectory() as temporary:
            env = RetryEnvironment(stop)
            result = run(M3Config(render=False, output=Path(temporary)), stop=stop,
                         env_factory=lambda _: env, disturbance_fn=inject)
        self.assertEqual(result["state"], "stopped")
        self.assertIsNone(result["evaluation"]["recovery_metrics"]["recovery_success_rate"])

    def test_error_closes_environment_and_records_error_without_success_metrics(self):
        def fail(*args):
            raise RuntimeError("injection failed")
        with tempfile.TemporaryDirectory() as temporary:
            env = RetryEnvironment()
            with self.assertRaisesRegex(RuntimeError, "injection failed"):
                run(M3Config(render=False, output=Path(temporary)), env_factory=lambda _: env, disturbance_fn=fail)
            result = json.loads(next(Path(temporary).glob("*/result.json")).read_text())
            self.assertEqual(result["state"], "error")
            self.assertNotIn("evaluation", result)
            self.assertTrue(env.closed)

    def test_cli_preserves_system_live_and_fixed_budget(self):
        args = parser().parse_args(["--system", "v2", "--live", "--disturbance", "object_drop", "--port", "8765"])
        config = config_from_args(args)
        config.validate()
        self.assertEqual(config.protocol, "m3")
        self.assertEqual(config.system, "v2")
        self.assertTrue(config.render)
        self.assertEqual(config.max_steps, 360)
        self.assertEqual(RecoverySettings().action_budget, 230)
        for bad in (replace(config, max_steps=525), replace(config, verification=False), replace(config, protocol="m1")):
            with self.assertRaises(ValueError):
                bad.validate()


if __name__ == "__main__":
    unittest.main()
