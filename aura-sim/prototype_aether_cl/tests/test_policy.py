"""Controller input boundaries, coordinate conventions, and evaluation records."""

import copy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from aether_cl.policies import FixedPickCube, PickCubeSettings, pose_rotation
from aether_cl.runtime import RunConfig, config_from_args, fixed_action_for_space, parser, run


def observation():
    return {"extra": {
        "obj_pose": np.array([[0.03, 0.02, 0.02, 1, 0, 0, 0]]),
        "goal_pos": np.array([[0.08, -0.04, 0.2]]),
        "tcp_pose": np.array([[0.0, 0.0, 0.25, 0, 1, 0, 0]]),
    }}


BASE = np.array([[-0.615, 0, 0, 1, 0, 0, 0]])


class PolicyTests(unittest.TestCase):
    def test_absolute_base_frame_action_round_trips_to_world_command(self):
        obs = observation()
        # A rotated base catches accidentally treating world deltas/positions
        # as absolute base-frame commands. A real Panda uses an identity base.
        q = Rotation.from_euler("z", 0.7).as_quat()
        base = np.array([[-0.615, 0.1, 0.02, q[3], *q[:3]]])
        policy = FixedPickCube(obs, base)
        action, decision = policy.action(obs, 0)
        base_rotation = pose_rotation(base[0])
        world_position = base_rotation @ action[0, :3] + base[0, :3]
        np.testing.assert_allclose(world_position, decision["commanded_tcp_position_world_m"], atol=1e-7)
        world_rotation = base_rotation @ Rotation.from_euler("XYZ", action[0, 3:6]).as_matrix()
        np.testing.assert_allclose(world_rotation, policy.grasp_rotation, atol=1e-7)
        self.assertEqual(action.shape, (1, 7))
        self.assertEqual(action.dtype, np.float32)
        self.assertEqual(action[0, 6], 1)

    def test_only_tcp_feedback_is_read_after_reset(self):
        initial = observation()
        policy = FixedPickCube(initial, BASE)
        reference = policy.action(initial, 180)
        changed = copy.deepcopy(initial)
        # Remove all future object/goal/evaluator data. The controller must
        # still produce the exact same action from the remaining TCP pose.
        changed["extra"] = {"tcp_pose": changed["extra"]["tcp_pose"]}
        changed["success"] = True
        changed["failure"] = "GRASP_FAILURE"
        actual = policy.action(changed, 180)
        np.testing.assert_array_equal(reference[0], actual[0])
        self.assertEqual(reference[1], actual[1])
        initial["extra"]["obj_pose"][:] = 99
        initial["extra"]["goal_pos"][:] = 99
        self.assertLess(np.linalg.norm(policy.cube), 1)
        self.assertLess(np.linalg.norm(policy.goal), 1)

    def test_fixed_schedule_cannot_retry_or_reopen_after_closing(self):
        obs = observation()
        policy = FixedPickCube(obs, BASE)
        phases = []
        for step in range(360):
            action, decision = policy.action(obs, step)
            if not phases or phases[-1] != decision["phase"]:
                phases.append(decision["phase"])
            self.assertEqual(action[0, 6], 1 if step < 100 else -1)
        self.assertEqual(phases, ["approach", "descend", "close", "lift", "transport", "lower", "hold"])
        self.assertFalse(policy.action(obs, 318)[1]["schedule_complete"])
        self.assertTrue(policy.action(obs, 319)[1]["schedule_complete"])
        self.assertEqual(policy.phase(1000), "hold")

    def test_translation_and_rotation_changes_are_bounded(self):
        obs = observation()
        obs["extra"]["tcp_pose"][0, 3:] = [1, 0, 0, 0]
        policy = FixedPickCube(obs, BASE)
        action, decision = policy.action(obs, 0)
        self.assertLessEqual(np.linalg.norm(np.array(decision["commanded_tcp_position_world_m"]) - obs["extra"]["tcp_pose"][0, :3]), 0.012 + 1e-9)
        change = Rotation.from_euler("XYZ", action[0, 3:6]).magnitude()
        self.assertLessEqual(change, 0.08 + 1e-7)

    def test_invalid_pose_and_insufficient_budget_fail_before_output(self):
        obs = observation()
        obs["extra"]["obj_pose"][0, 3:] = 0
        with self.assertRaisesRegex(ValueError, "zero norm"):
            FixedPickCube(obs, BASE)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "absent"
            with self.assertRaisesRegex(ValueError, "320"):
                run(RunConfig(controller="fixed_pick_cube", max_steps=50, output=output))
            self.assertFalse(output.exists())
        with self.assertRaisesRegex(ValueError, "PickCube-v1"):
            RunConfig(controller="fixed_pick_cube", max_steps=360, env_id="Other-v1").validate()

    def test_parser_preserves_explicit_policy_and_path(self):
        args = parser("test").parse_args(["--controller", "fixed_pick_cube", "--max-steps", "360", "--output", "runs/test"])
        config = config_from_args(args)
        self.assertEqual(config.controller, "fixed_pick_cube")
        self.assertEqual(config.control_mode, "pd_ee_pose")
        self.assertEqual(config.output, Path("runs/test"))
        self.assertEqual(PickCubeSettings().scheduled_steps, 320)


class Actions:
    def __init__(self, shape=(7,)):
        self.shape = shape

    def seed(self, seed):
        pass

    def contains(self, action):
        return (action.shape == self.shape and np.isfinite(action).all()
                and abs(action.reshape(-1)[-1]) <= 1)

    def sample(self):
        raise AssertionError("Fixed controller must never sample random actions")


class Environment:
    """Fixture for logging contracts, not a substitute for native physics."""

    def __init__(self, stop=None, action_shape=(7,)):
        self.unwrapped = self
        self.action_space = Actions(action_shape)
        self.agent = SimpleNamespace(robot=SimpleNamespace(pose=SimpleNamespace(raw_pose=BASE)))
        self.closed = False
        self.stop = stop

    def reset(self, seed):
        self.seed = seed
        self.step_number = 0
        self.obs = observation()
        return copy.deepcopy(self.obs), {"success": [False], "is_grasped": [False]}

    def step(self, action):
        if not self.action_space.contains(action):
            raise AssertionError("Action must match the declared environment space")
        self.step_number += 1
        # Emulate absolute Cartesian pose updates to exercise state flow.
        command = action.reshape(7)
        self.obs["extra"]["tcp_pose"][0, :3] = command[:3] + BASE[0, :3]
        q = Rotation.from_euler("XYZ", command[3:6]).as_quat()
        self.obs["extra"]["tcp_pose"][0, 3:] = [q[3], *q[:3]]
        success = self.step_number == 359 or (self.step_number == 360 and self.seed % 2 == 0)
        self.obs["extra"]["obj_pose"][0, :3] = self.obs["extra"]["goal_pos"][0] if success else [0.03, 0.02, 0.02]
        if self.stop is not None and self.step_number == 2:
            self.stop.set()
        action[:] = 99
        return copy.deepcopy(self.obs), [0], [False], [self.step_number == 360], {"success": [success], "is_grasped": [success]}

    def close(self):
        self.closed = True


class IntegrationTests(unittest.TestCase):
    def test_evaluation_and_logs_distinguish_final_from_ever_success(self):
        for shape in ((7,), (1, 7)):
            with self.subTest(action_space_shape=shape):
                self.check_evaluation_and_logs(shape)

    def check_evaluation_and_logs(self, shape):
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment(action_shape=shape)
            config = RunConfig(controller="fixed_pick_cube", max_steps=360,
                               episodes=2, render=False, output=Path(temporary))
            result = run(config, env_factory=lambda _: env)
            self.assertTrue(env.closed)
            self.assertEqual(result["evaluation"]["success_rate_at_end"], 0.5)
            self.assertEqual(result["evaluation"]["success_rate_ever"], 1.0)
            self.assertTrue(result["evaluation"]["complete"])
            self.assertTrue(all(e["schedule_complete"] for e in result["episodes"]))
            directory = Path(result["run_directory"])
            manifest = json.loads((directory / "manifest.json").read_text())
            self.assertEqual(manifest["policy_details"]["step_inputs"], ["tcp_pose"])
            self.assertEqual(manifest["control_mode"], "pd_ee_pose")
            self.assertEqual(manifest["action_space_shape"], list(shape))
            self.assertFalse(manifest["verification"])
            events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
            steps = [e for e in events if e["event"] == "step"]
            self.assertEqual(len(steps), 720)
            self.assertEqual(steps[0]["controller_decision"]["phase"], "approach")
            self.assertEqual(np.asarray(steps[0]["action"]).shape, shape)
            self.assertLess(np.asarray(steps[0]["action"]).reshape(-1)[0], 2)  # storage mutation was snapshotted
            self.assertIn("cube_goal_distance_m", steps[-1]["evaluator"])
            self.assertEqual(json.loads((directory / "result.json").read_text()), result)

    def test_stopped_baseline_does_not_report_complete_success_rate(self):
        with tempfile.TemporaryDirectory() as temporary:
            stop = threading.Event()
            env = Environment(stop)
            result = run(RunConfig(controller="fixed_pick_cube", max_steps=360,
                                   render=False, output=Path(temporary)),
                         env_factory=lambda _: env, stop=stop)
            self.assertEqual(result["state"], "stopped")
            self.assertFalse(result["evaluation"]["complete"])
            self.assertEqual(result["evaluation"]["completed_episodes"], 0)
            self.assertIsNone(result["evaluation"]["success_rate_at_end"])
            self.assertFalse(result["episodes"][0]["schedule_complete"])

    def test_action_adapter_preserves_commands_for_both_spaces(self):
        command, _ = FixedPickCube(observation(), BASE).action(observation(), 0)
        for shape in ((7,), (1, 7)):
            with self.subTest(action_space_shape=shape):
                actual = fixed_action_for_space(command, Actions(shape))
                self.assertEqual(actual.shape, shape)
                self.assertEqual(actual.dtype, np.float32)
                np.testing.assert_array_equal(actual.reshape(1, 7), command)

    def test_action_adapter_rejects_malformed_nonfinite_and_out_of_bounds(self):
        command, _ = FixedPickCube(observation(), BASE).action(observation(), 0)
        with self.assertRaisesRegex(RuntimeError, "controller action shape"):
            fixed_action_for_space(command.reshape(7), Actions())
        with self.assertRaisesRegex(RuntimeError, "Panda pd_ee_pose action shape"):
            fixed_action_for_space(command, Actions((2, 7)))
        for shape in ((7,), (1, 7)):
            for bad_value in (float("nan"), 2):
                with self.subTest(action_space_shape=shape, gripper=bad_value):
                    invalid = command.copy()
                    invalid[0, -1] = bad_value
                    with self.assertRaisesRegex(RuntimeError, "invalid action"):
                        fixed_action_for_space(invalid, Actions(shape))

    def test_unsupported_space_fails_before_any_step_and_closes_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment(action_shape=(2, 7))
            with self.assertRaisesRegex(RuntimeError, "Panda pd_ee_pose action shape"):
                run(RunConfig(controller="fixed_pick_cube", max_steps=360,
                              render=False, output=Path(temporary)),
                    env_factory=lambda _: env)
            self.assertEqual(env.step_number, 0)
            self.assertTrue(env.closed)
            result_path = next(Path(temporary).glob("*/result.json"))
            self.assertEqual(json.loads(result_path.read_text())["state"], "error")


if __name__ == "__main__":
    unittest.main()
