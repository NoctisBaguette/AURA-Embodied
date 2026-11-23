"""Fixed, logged CPU-physics interventions shared by baseline and V1."""

import numpy as np

from .policies import vector


def disturbance_spec(name, magnitude):
    return {"name": name, "step": {"none": None, "object_shift": 81, "object_drop": 181}[name],
            "magnitude_m": magnitude, "axis": "world_y",
            "timing": "after_action_computation_before_physics_step",
            "implementation": "one_time_pose_relocation_with_zero_velocity"}


def apply_disturbance(env, name, step, initial_cube, magnitude, pose_factory=None):
    spec = disturbance_spec(name, magnitude)
    if step != spec["step"]:
        return None
    base = env.unwrapped
    if bool(getattr(base, "gpu_sim_enabled", False)):
        raise RuntimeError("M2 disturbance adapter supports CPU physics only")
    before = vector(base.cube.pose.raw_pose, 7, "cube_pose")
    after = before.copy()
    after[1] += magnitude
    if name == "object_drop":
        after[2] = initial_cube[2]
    if pose_factory is None:
        from mani_skill.utils.structs.pose import Pose
        pose_factory = Pose.create_from_pq
    base.cube.set_pose(pose_factory(p=after[:3], q=after[3:], device=base.device))
    base.cube.linear_velocity = np.zeros(3, dtype=np.float32)
    base.cube.angular_velocity = np.zeros(3, dtype=np.float32)
    return {**spec, "before_pose_world": before.tolist(), "after_pose_world": after.tolist(),
            "velocities_zeroed": True}
