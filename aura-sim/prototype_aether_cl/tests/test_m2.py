"""Matched-budget runtime contracts; fixtures do not model native contacts."""

import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

import numpy as np

from aether_cl.disturbances import apply_disturbance, disturbance_spec
from aether_cl.runtime import RunConfig, config_from_args, parser, run
from test_policy import Actions, BASE
from test_verification import state


def pose_factory(p, q, device):
    return SimpleNamespace(raw_pose=np.array([[*p, *q]]))


class Cube:
    def __init__(self, env):
        self.env = env
        self.pose = SimpleNamespace(raw_pose=np.array([[0., 0, .02, 1, 0, 0, 0]]))
        self.linear_velocity = self.angular_velocity = np.ones(3)

    def set_pose(self, pose):
        self.pose = pose
        self.env.held = False


class Environment:
    def __init__(self, stop=None):
        self.unwrapped = self
        self.device = "cpu"
        self.gpu_sim_enabled = False
        self.agent = SimpleNamespace(robot=SimpleNamespace(pose=SimpleNamespace(raw_pose=BASE)))
        self.action_space = Actions()
        self.cube = Cube(self)
        self.closed = False
        self.stop = stop
        self.timeline = []

    def snapshot(self):
        return state(cube=tuple(self.cube.pose.raw_pose[0, :3]), tcp=tuple(self.tcp),
                     goal=tuple(self.goal), aperture=self.aperture)

    def reset(self, seed):
        self.step_number = 0
        self.held = False
        self.cube.pose.raw_pose[0, :3] = [0, 0, .02]
        self.goal = np.array([0, 0, .02] if seed == 8 else [.08, 0, .2])
        self.tcp = np.array([0., 0, .25])
        self.aperture = .08
        # A deliberately stale reset flag must never establish attachment.
        return self.snapshot(), {"success": [seed == 8], "is_grasped": [True],
                                 "is_robot_static": [True], "is_obj_placed": [seed == 8]}

    def step(self, action):
        self.step_number += 1
        self.timeline.append(("step", self.step_number))
        self.tcp = action[:3] + BASE[0, :3]
        if action[-1] > 0:
            self.held = False
            self.aperture = .08
        elif np.linalg.norm(self.cube.pose.raw_pose[0, :3] - self.tcp) <= .04:
            self.held = True
            self.aperture = .0366
        elif not self.held:
            self.aperture = 0
        if self.held:
            self.cube.pose.raw_pose[0, :3] = self.tcp
        placed = bool(np.linalg.norm(self.cube.pose.raw_pose[0, :3] - self.goal) <= .025)
        observation = self.snapshot()
        if self.stop and self.step_number == 2:
            self.stop.set()
        action[:] = 99
        return observation, [0], [placed], [self.step_number == 360], {
            "success": [placed], "is_grasped": [self.held],
            "is_robot_static": [True], "is_obj_placed": [placed]}

    def close(self):
        self.closed = True


def inject(env, name, step, initial_cube, magnitude):
    record = apply_disturbance(env, name, step, initial_cube, magnitude, pose_factory=pose_factory)
    if record:
        env.timeline.append(("disturbance", step))
    return record


class M2Tests(unittest.TestCase):
    def test_baseline_and_v1_execute_identical_actions_and_full_budget(self):
        for condition, expected_failure in [("none", None), ("object_shift", "GRASP_FAILURE"),
                                             ("object_drop", "OBJECT_LOST")]:
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as temporary:
                results = []
                logs = []
                for enabled in (False, True):
                    env = Environment()
                    result = run(RunConfig(controller="fixed_pick_cube", protocol="m2",
                                           verification=enabled, disturbance=condition,
                                           max_steps=360, render=False, output=Path(temporary)),
                                 env_factory=lambda _: env, disturbance_fn=inject)
                    results.append(result)
                    events = [json.loads(line) for line in
                              (Path(result["run_directory"]) / "events.jsonl").read_text().splitlines()]
                    logs.append(events)
                    self.assertTrue(env.closed)
                    self.assertEqual(result["episodes"][0]["steps"], 360)
                    if condition != "none":
                        step = disturbance_spec(condition, .12)["step"]
                        index = env.timeline.index(("disturbance", step))
                        self.assertEqual(env.timeline[index + 1], ("step", step))
                        self.assertEqual(len([e for e in events if e["event"] == "disturbance_applied"]), 1)
                steps = [[e for e in events if e["event"] == "step"] for events in logs]
                self.assertEqual([e["action"] for e in steps[0]], [e["action"] for e in steps[1]])
                self.assertEqual([e["observation"] for e in steps[0]], [e["observation"] for e in steps[1]])
                self.assertEqual(results[0]["evaluation"]["task_success_rate_at_end"],
                                 results[1]["evaluation"]["task_success_rate_at_end"])
                episode = results[1]["episodes"][0]
                if expected_failure:
                    self.assertEqual(episode["first_detected_failure"]["failure"], expected_failure)
                    self.assertEqual(episode["first_failure_latency_steps"], 2)
                    self.assertEqual(results[1]["evaluation"]["task_success_rate_at_end"], 0)
                else:
                    self.assertIsNone(episode["first_detected_failure"])
                    self.assertEqual(results[1]["evaluation"]["task_success_rate_at_end"], 1)
                    # Raw task termination occurs earlier but cannot end M2.
                    self.assertTrue(any(e["terminated"] for e in steps[1][:-1]))
                self.assertFalse(any(e["action"][0] == 99 for e in steps[1]))

    def test_excluded_resets_remain_recorded_without_actions_or_failure_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment()
            result = run(RunConfig(controller="fixed_pick_cube", protocol="m2", verification=True,
                                   seed=8, disturbance="object_shift", max_steps=360,
                                   render=False, output=Path(temporary)),
                         env_factory=lambda _: env, disturbance_fn=inject)
            episode = result["episodes"][0]
            self.assertTrue(episode["excluded"])
            self.assertEqual(episode["steps"], 0)
            self.assertEqual(env.timeline, [])
            self.assertEqual(result["evaluation"]["completed_episodes"], 0)
            self.assertIsNone(result["evaluation"]["task_success_rate_at_end"])
            self.assertEqual(result["verification"]["status"], "excluded")

    def test_stopped_m2_has_no_complete_task_or_verification_rates(self):
        with tempfile.TemporaryDirectory() as temporary:
            stop = threading.Event()
            env = Environment(stop)
            result = run(RunConfig(controller="fixed_pick_cube", protocol="m2", verification=True,
                                   max_steps=360, render=False, output=Path(temporary)),
                         env_factory=lambda _: env, disturbance_fn=inject, stop=stop)
            self.assertEqual(result["state"], "stopped")
            self.assertIsNone(result["evaluation"]["task_success_rate_at_end"])
            self.assertIsNone(result["evaluation"]["verification_metrics"]["observation_coverage"])

    def test_mixed_exclusions_use_only_eligible_episodes_in_task_denominator(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment()
            result = run(RunConfig(controller="fixed_pick_cube", protocol="m2", verification=True,
                                   episodes=2, seed=7, disturbance="object_shift", max_steps=360,
                                   render=False, output=Path(temporary)),
                         env_factory=lambda _: env, disturbance_fn=inject)
            evaluation = result["evaluation"]
            self.assertTrue(evaluation["complete"])
            self.assertEqual(evaluation["recorded_episodes"], 2)
            self.assertEqual(evaluation["eligible_episodes"], 1)
            self.assertEqual(evaluation["excluded_episodes"], 1)
            self.assertEqual(evaluation["completed_episodes"], 1)
            self.assertEqual(evaluation["task_success_rate_at_end"], 0)

    def test_missing_verifier_sensor_stays_uncertain_without_reference_leakage(self):
        class MissingVelocity(Environment):
            def step(self, action):
                observation, *outputs = super().step(action)
                del observation["agent"]["qvel"]
                return observation, *outputs

        with tempfile.TemporaryDirectory() as temporary:
            result = run(RunConfig(controller="fixed_pick_cube", protocol="m2", verification=True,
                                   max_steps=360, render=False, output=Path(temporary)),
                         env_factory=lambda _: MissingVelocity(), disturbance_fn=inject)
            self.assertEqual(result["episodes"][0]["final_verification"]["failure"], "UNCERTAIN")
            self.assertEqual(result["evaluation"]["task_success_rate_at_end"], 1)
            self.assertEqual(result["evaluation"]["verification_metrics"]["uncertain_steps"], 360)
            self.assertEqual(result["evaluation"]["verification_metrics"]["observation_coverage"], 0)

    def test_disturbance_exception_remains_execution_error_and_closes_environment(self):
        def failed_injection(*args):
            raise RuntimeError("pose mutation failed")
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment()
            with self.assertRaisesRegex(RuntimeError, "pose mutation failed"):
                run(RunConfig(controller="fixed_pick_cube", protocol="m2", max_steps=360,
                              disturbance="object_shift", render=False, output=Path(temporary)),
                    env_factory=lambda _: env, disturbance_fn=failed_injection)
            self.assertTrue(env.closed)
            result_path = next(Path(temporary).glob("*/result.json"))
            self.assertEqual(json.loads(result_path.read_text())["state"], "error")

    def test_invalid_protocol_and_budget_fail_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "absent"
            invalid = [RunConfig(verification=True),
                       RunConfig(protocol="m2"),
                       RunConfig(controller="fixed_pick_cube", protocol="m2", max_steps=320),
                       RunConfig(controller="fixed_pick_cube", protocol="m2", max_steps=360,
                                 disturbance_magnitude=float("nan"))]
            for config in invalid:
                from dataclasses import replace
                with self.subTest(config=config), self.assertRaises(ValueError):
                    run(replace(config, output=output))
            self.assertFalse(output.exists())

    def test_parser_preserves_protocol_and_intervention(self):
        config = config_from_args(parser("test").parse_args([
            "--controller", "fixed_pick_cube", "--protocol", "m2", "--verification",
            "--max-steps", "360", "--disturbance", "object_drop", "--disturbance-magnitude", ".08"]))
        config.validate()
        self.assertTrue(config.verification)
        self.assertEqual(config.disturbance, "object_drop")
        self.assertEqual(config.disturbance_magnitude, .08)


class DisturbanceTests(unittest.TestCase):
    def test_relocation_preserves_orientation_zeros_velocities_and_has_fixed_timing(self):
        for name, step in [("object_shift", 81), ("object_drop", 181)]:
            with self.subTest(name=name):
                env = Environment()
                env.cube.pose.raw_pose[0] = [.01, .02, .14, .7, 0, 0, .7]
                before = env.cube.pose.raw_pose.copy()
                self.assertIsNone(apply_disturbance(env, name, step - 1, [0, 0, .02], .12,
                                                   pose_factory=pose_factory))
                np.testing.assert_array_equal(env.cube.pose.raw_pose, before)
                record = apply_disturbance(env, name, step, [0, 0, .02], .12, pose_factory=pose_factory)
                after = env.cube.pose.raw_pose[0]
                self.assertAlmostEqual(after[1], .14)
                self.assertAlmostEqual(after[2], .02 if name == "object_drop" else .14)
                np.testing.assert_array_equal(after[3:], before[0, 3:])
                np.testing.assert_array_equal(env.cube.linear_velocity, np.zeros(3))
                np.testing.assert_array_equal(env.cube.angular_velocity, np.zeros(3))
                self.assertEqual(record["step"], step)

    def test_unsupported_gpu_adapter_fails_instead_of_silently_ignoring_intervention(self):
        env = Environment()
        env.gpu_sim_enabled = True
        with self.assertRaisesRegex(RuntimeError, "CPU physics"):
            apply_disturbance(env, "object_shift", 81, [0, 0, .02], .12, pose_factory=pose_factory)


if __name__ == "__main__":
    unittest.main()
