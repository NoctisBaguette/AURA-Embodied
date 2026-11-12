"""Fixed state-based PickCube controller; no verification or recovery decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.spatial.transform import Rotation


@dataclass(frozen=True)
class PickCubeSettings:
    # Durations are in control steps, independent of browser wall-clock pacing.
    approach_steps: int = 60
    descend_steps: int = 40
    close_steps: int = 25
    lift_steps: int = 45
    transport_steps: int = 60
    lower_steps: int = 40
    hold_steps: int = 50
    clearance_m: float = 0.12
    goal_clearance_m: float = 0.06
    max_translation_m: float = 0.012
    max_rotation_rad: float = 0.08

    @property
    def scheduled_steps(self):
        return sum(getattr(self, phase + "_steps") for phase in PHASES)


PHASES = ("approach", "descend", "close", "lift", "transport", "lower", "hold")


def vector(value, size, name):
    """Read exactly one batched or unbatched state vector, copying its storage."""
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    array = np.asarray(value, dtype=np.float64)
    if array.shape == (1, size):
        array = array[0]
    if array.shape != (size,) or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite single-environment vector of length {size}")
    return array.copy()


def pose_rotation(pose):
    # ManiSkill stores quaternions as wxyz; SciPy's input order is xyzw.
    if np.linalg.norm(pose[3:]) < 1e-8:
        raise ValueError("Pose quaternion has zero norm")
    return Rotation.from_quat(pose[[4, 5, 6, 3]]).as_matrix()


def bounded(vector, maximum):
    length = np.linalg.norm(vector)
    return vector * min(1.0, maximum / length) if length else vector


class FixedPickCube:
    """Execute a fixed schedule using cached reset targets and TCP servo feedback.

    Object pose and goal are privileged simulator-state observations. Only the
    current TCP pose is reread during execution. No evaluator info, grasp flag,
    success flag, or failure label enters this controller. Phase changes depend
    only on elapsed control steps, including when the grasp fails.
    """

    name = "fixed_pick_cube"
    control_mode = "pd_ee_pose"
    version = "0.1-candidate"

    def __init__(self, observation, base_pose):
        self.settings = PickCubeSettings()
        extra = observation["extra"]
        cube_pose = vector(extra["obj_pose"], 7, "obj_pose")
        self.cube = cube_pose[:3].copy()
        self.goal = vector(extra["goal_pos"], 3, "goal_pos")
        tcp = vector(extra["tcp_pose"], 7, "tcp_pose")
        base = vector(base_pose, 7, "base_pose")
        self.base_position = base[:3]
        self.base_rotation = pose_rotation(base)

        # Top-down grasp aligned to a cube edge. Four equivalent cube yaw
        # orientations exist; pick the one nearest the initial TCP x axis.
        cube_rotation = pose_rotation(cube_pose)
        cube_yaw = np.arctan2(cube_rotation[1, 0], cube_rotation[0, 0])
        tcp_rotation = pose_rotation(tcp)
        tcp_yaw = np.arctan2(tcp_rotation[1, 0], tcp_rotation[0, 0])
        offset = (cube_yaw - tcp_yaw + np.pi / 4) % (np.pi / 2) - np.pi / 4
        yaw = tcp_yaw + offset
        c, s = np.cos(yaw), np.sin(yaw)
        self.grasp_rotation = np.array([[c, s, 0], [s, -c, 0], [0, 0, -1]])

        above_cube = self.cube + [0, 0, self.settings.clearance_m]
        above_goal = self.goal.copy()
        above_goal[2] = max(above_cube[2], self.goal[2] + self.settings.goal_clearance_m)
        self.targets = {
            "approach": above_cube,
            "descend": self.cube,
            "close": self.cube,
            "lift": above_cube,
            "transport": above_goal,
            "lower": self.goal,
            "hold": self.goal,
        }

    def manifest(self):
        return {
            "name": self.name, "version": self.version,
            "settings": asdict(self.settings),
            "scheduled_steps": self.settings.scheduled_steps,
            "input_source": "privileged_simulator_state",
            "reset_inputs": ["obj_pose", "goal_pos", "tcp_pose", "robot_base_pose"],
            "step_inputs": ["tcp_pose"],
            "phase_transition": "elapsed_control_steps_only",
            "verification": False, "recovery": False,
        }

    def phase(self, step_index):
        if step_index < 0:
            raise ValueError("step_index must be nonnegative")
        end = 0
        for phase in PHASES:
            end += getattr(self.settings, phase + "_steps")
            if step_index < end:
                return phase
        return "hold"

    def action(self, observation, step_index):
        phase = self.phase(step_index)
        tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")
        target = self.targets[phase]
        next_position = tcp[:3] + bounded(
            target - tcp[:3], self.settings.max_translation_m,
        )
        current_rotation = pose_rotation(tcp)
        rotation_error = Rotation.from_matrix(
            self.grasp_rotation @ current_rotation.T,
        ).as_rotvec()
        next_rotation = Rotation.from_rotvec(
            bounded(rotation_error, self.settings.max_rotation_rad),
        ).as_matrix() @ current_rotation

        # pd_ee_pose takes absolute position and intrinsic XYZ Euler angles
        # in the robot base frame. Its arm action is NOT normalized. Gripper
        # remains normalized: +1 opens, -1 closes, as in Panda's config.
        base_position = self.base_rotation.T @ (next_position - self.base_position)
        base_rotation = self.base_rotation.T @ next_rotation
        angles = Rotation.from_matrix(base_rotation).as_euler("XYZ")
        gripper = 1.0 if phase in ("approach", "descend") else -1.0
        action = np.concatenate([base_position, angles, [gripper]])
        metadata = {
            "phase": phase,
            "expected_tcp_position_world_m": target.tolist(),
            "commanded_tcp_position_world_m": next_position.tolist(),
            "gripper": "open" if gripper > 0 else "closed",
            "schedule_complete": step_index + 1 >= self.settings.scheduled_steps,
        }
        return action.astype(np.float32)[None, :], metadata


def task_diagnostics(observation, info):
    """Evaluator-only state diagnostics. Never passed to the controller."""
    extra = observation["extra"]
    cube = vector(extra["obj_pose"], 7, "obj_pose")[:3]
    goal = vector(extra["goal_pos"], 3, "goal_pos")
    return {
        "cube_position_world_m": cube.tolist(),
        "goal_position_world_m": goal.tolist(),
        "cube_goal_distance_m": float(np.linalg.norm(cube - goal)),
    }
