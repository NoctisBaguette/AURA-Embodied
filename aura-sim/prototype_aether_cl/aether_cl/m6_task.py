"""Frozen M6 placement state, independent contact reference and geometric verifier."""

from dataclasses import asdict, dataclass

import numpy as np
from scipy.spatial.transform import Rotation

from .policies import pose_rotation, vector
from .verification import VerificationSettings, single_bool


@dataclass(frozen=True)
class PlacementSettings:
    horizontal_tolerance_m: float = .025
    minimum_lift_m: float = .05
    cube_half_size_m: float = .02
    support_height_m: float = 0.
    support_region_half_extent_m: float = .40
    support_height_tolerance_m: float = .004
    minimum_support_force_n: float = .01
    retraction_clearance_m: float = .08
    released_aperture_m: float = .06
    maximum_linear_speed_m_s: float = .01
    maximum_angular_speed_rad_s: float = .2
    maximum_frame_translation_m: float = .001
    maximum_frame_rotation_rad: float = .02
    stable_steps: int = 5
    failure_persistence_steps: int = 3
    settle_grace_steps: int = 10


SETTINGS = PlacementSettings()


def task_manifest():
    return {**asdict(SETTINGS), "name": "released_cube_supported_on_designated_table",
            "support_actor": "table-workspace", "support_region": "world_xy_square_centered_at_origin",
            "reference_support": "fresh_cube_table_pairwise_vertical_contact_force_and_bottom_geometry",
            "verifier_support": "privileged_pose_geometry_and_velocity_proxy_no_contact_labels",
            "requires_historical_contact_grasp_and_lift": True,
            "requires_release_command_and_current_non_grasp": True,
            "requires_open_gripper_and_vertical_and_euclidean_tcp_clearance": True,
            "requires_consecutive_fresh_stability": True, "termination": "full_frozen_action_budget",
            "environment_success_is_not_task_success": True}


def geometry(observation, previous_pose=None):
    extra = observation["extra"]
    pose = vector(extra["obj_pose"], 7, "obj_pose")
    goal = vector(extra["goal_pos"], 3, "goal_pos")
    tcp = vector(extra["tcp_pose"], 7, "tcp_pose")[:3]
    qpos = vector(observation["agent"]["qpos"], 9, "qpos")
    linear = vector(extra["obj_linear_velocity"], 3, "obj_linear_velocity")
    angular = vector(extra["obj_angular_velocity"], 3, "obj_angular_velocity")
    rotation = pose_rotation(pose)
    extent = SETTINGS.cube_half_size_m * np.abs(rotation).sum(axis=1)
    bottom = float(pose[2] - extent[2])
    supported = (abs(bottom - SETTINGS.support_height_m) <= SETTINGS.support_height_tolerance_m
                 and bool(np.all(np.abs(pose[:2]) + extent[:2] <= SETTINGS.support_region_half_extent_m)))
    aperture = float(qpos[-2:].sum())
    gap = float(np.linalg.norm(tcp - pose[:3]))
    candidate = (gap <= VerificationSettings().cube_tcp_tolerance_m
                 and VerificationSettings().minimum_aperture_m <= aperture <= VerificationSettings().maximum_aperture_m)
    delta = float(np.linalg.norm(pose[:3] - previous_pose[:3])) if previous_pose is not None else None
    angle = float(Rotation.from_matrix(rotation @ pose_rotation(previous_pose).T).magnitude()) if previous_pose is not None else None
    still = (previous_pose is not None and np.linalg.norm(linear) <= SETTINGS.maximum_linear_speed_m_s
             and np.linalg.norm(angular) <= SETTINGS.maximum_angular_speed_rad_s
             and delta <= SETTINGS.maximum_frame_translation_m and angle <= SETTINGS.maximum_frame_rotation_rad)
    clear = gap >= SETTINGS.retraction_clearance_m and tcp[2] - pose[2] >= SETTINGS.retraction_clearance_m
    return {"pose": pose, "goal": goal, "tcp": tcp, "candidate": bool(candidate),
            "released_geometry": aperture >= SETTINGS.released_aperture_m and not candidate,
            "supported_geometry": bool(supported), "retracted": bool(clear), "stable_frame": bool(still),
            "horizontal_error_m": float(np.linalg.norm(pose[:2] - goal[:2])),
            "bottom_height_m": bottom, "aperture_m": aperture, "tcp_distance_m": gap,
            "linear_speed_m_s": float(np.linalg.norm(linear)), "angular_speed_rad_s": float(np.linalg.norm(angular)),
            "frame_translation_m": delta, "frame_rotation_rad": angle}


def eligibility(observation):
    g = geometry(observation)
    distance = g["horizontal_error_m"]
    # Do not select a replacement when a fresh seed starts in the target region.
    return {"eligible": distance > SETTINGS.horizontal_tolerance_m,
            "exclusion_reason": "initially_in_horizontal_target_region" if distance <= SETTINGS.horizontal_tolerance_m else None,
            "initial_horizontal_error_m": distance}


def classify(g, goal, phase, phase_step, held, ever_attached, max_lift, success, final):
    phase = phase.removeprefix("recovery_")
    if np.linalg.norm(g["goal"] - goal) > 1e-6:
        return "STATE_MISMATCH"
    if phase == "close" and phase_step >= 25 and not held:
        return "GRASP_FAILURE"
    if phase in ("lift", "transport", "lower") and ever_attached and not held:
        return "OBJECT_LOST"
    if phase == "transport" and max_lift < SETTINGS.minimum_lift_m:
        return "LIFT_NOT_ACHIEVED"
    if phase == "release" and phase_step >= 25 and (held or not g["released_geometry"]):
        return "RELEASE_NOT_ACHIEVED"
    if (phase == "settle" and phase_step >= SETTINGS.settle_grace_steps) or final:
        if held or not g["released_geometry"]:
            return "RELEASE_NOT_ACHIEVED"
        if g["horizontal_error_m"] > SETTINGS.horizontal_tolerance_m:
            return "PLACEMENT_TARGET_NOT_REACHED"
        if not g["supported"]:
            return "UNSUPPORTED_PLACEMENT"
        if not g["retracted"]:
            return "RETRACTION_NOT_ACHIEVED"
        if not success:
            return "POST_RELEASE_INSTABILITY"
    return None


class PlacementReference:
    """Contact labels are evaluator-only; the controller never receives this object."""

    def __init__(self, observation):
        g = geometry(observation)
        self.initial_cube = g["pose"][:3].copy()
        self.goal = g["goal"].copy()
        self.eligibility = eligibility(observation)
        self.previous_pose = g["pose"]
        self.last_step = self.stable_count = 0
        self.support_stable_count = 0
        self.max_lift = 0.
        self.ever_attached = self.release_commanded = False
        self.first_failure = self.first_success_step = None

    def observe(self, observation, info, step, decision, final=False):
        if step != self.last_step + 1:
            raise ValueError("Placement reference requires consecutive fresh observations")
        g = geometry(observation, self.previous_pose)
        self.previous_pose, self.last_step = g["pose"], step
        held = single_bool(info["is_grasped"], "is_grasped")
        force = vector(info["cube_table_contact_force_world_n"], 3, "support_force")
        g["supported"] = g["supported_geometry"] and abs(force[2]) >= SETTINGS.minimum_support_force_n
        self.max_lift = max(self.max_lift, float(g["pose"][2] - self.initial_cube[2]))
        self.ever_attached |= held
        self.release_commanded |= decision["phase"].removeprefix("recovery_") == "release" and decision["gripper"] == "open"
        released = self.ever_attached and self.release_commanded and not held and g["released_geometry"]
        support_ready = released and g["supported"] and g["retracted"] and g["stable_frame"]
        self.support_stable_count = self.support_stable_count + 1 if support_ready else 0
        ready = (self.eligibility["eligible"] and support_ready
                 and self.max_lift >= SETTINGS.minimum_lift_m and g["horizontal_error_m"] <= SETTINGS.horizontal_tolerance_m
                 and np.linalg.norm(g["goal"] - self.goal) <= 1e-6)
        self.stable_count = self.stable_count + 1 if ready else 0
        success = self.stable_count >= SETTINGS.stable_steps
        if success and self.first_success_step is None:
            self.first_success_step = step
        failure = classify(g, self.goal, decision["phase"], decision["phase_step"], held,
                           self.ever_attached, self.max_lift, success, final)
        if failure and self.first_failure is None:
            self.first_failure = {"step": step, "failure": failure}
        return {"task_success": bool(success), "failure": failure, "release_success": bool(released),
                "supported": bool(g["supported"]), "stable_frame": g["stable_frame"],
                "support_stability_success": bool(self.support_stable_count >= SETTINGS.stable_steps),
                "support_stable_steps": self.support_stable_count,
                "retracted": g["retracted"], "is_grasped": held, "stable_steps": self.stable_count,
                "max_cube_lift_m": self.max_lift, "horizontal_error_m": g["horizontal_error_m"],
                "cube_table_contact_force_world_n": force.tolist(), "bottom_height_m": g["bottom_height_m"],
                "linear_speed_m_s": g["linear_speed_m_s"], "angular_speed_rad_s": g["angular_speed_rad_s"]}


class PlacementVerifier:
    """Privileged geometry/velocity checks, excluding contact/evaluator/injection labels."""

    def __init__(self, observation):
        g = geometry(observation)
        self.initial_cube, self.goal = g["pose"][:3].copy(), g["goal"].copy()
        self.previous_pose = g["pose"]
        self.last_step = self.stable_count = self.attachment_count = self.failure_count = 0
        self.max_lift = 0.
        self.ever_attached = self.release_commanded = False
        self.previous_failure = self.first_failure = None

    def manifest(self):
        return {"name": "m6_privileged_geometry_velocity_verifier", "settings": asdict(SETTINGS),
                "inputs": ["obj_pose", "goal_pos", "tcp_pose", "qpos", "obj_linear_velocity", "obj_angular_velocity", "step", "controller_phase_clock"],
                "excluded_inputs": ["is_grasped", "info", "cube_table_contact_force", "reference", "disturbance_identity"],
                "confidence": "not_calibrated", "sensor_verifier_closure": False}

    def observe(self, observation, step, decision, final=False):
        if step != self.last_step + 1:
            raise ValueError("Placement verifier requires consecutive fresh observations")
        self.last_step = step
        try:
            g = geometry(observation, self.previous_pose)
        except (ValueError, KeyError, TypeError):
            self.stable_count = self.attachment_count = self.failure_count = 0
            self.previous_failure = None
            self.previous_pose = None
            return {"status": "uncertain", "success": False, "failure": "UNCERTAIN", "confidence": None}
        self.previous_pose = g["pose"]
        g["supported"] = g["supported_geometry"]
        self.max_lift = max(self.max_lift, float(g["pose"][2] - self.initial_cube[2]))
        self.attachment_count = self.attachment_count + 1 if g["candidate"] else 0
        self.ever_attached |= self.attachment_count >= SETTINGS.failure_persistence_steps
        self.release_commanded |= decision["phase"].removeprefix("recovery_") == "release" and decision["gripper"] == "open"
        ready = (self.ever_attached and self.release_commanded and g["released_geometry"] and g["supported"]
                 and g["retracted"] and g["stable_frame"] and self.max_lift >= SETTINGS.minimum_lift_m
                 and g["horizontal_error_m"] <= SETTINGS.horizontal_tolerance_m and np.linalg.norm(g["goal"] - self.goal) <= 1e-6)
        self.stable_count = self.stable_count + 1 if ready else 0
        success = self.stable_count >= SETTINGS.stable_steps
        failure = classify(g, self.goal, decision["phase"], decision["phase_step"], g["candidate"],
                           self.ever_attached, self.max_lift, success, final)
        self.failure_count = self.failure_count + 1 if failure and failure == self.previous_failure else int(failure is not None)
        self.previous_failure = failure
        confirmed = failure if self.failure_count >= SETTINGS.failure_persistence_steps or final else None
        if confirmed and self.first_failure is None:
            self.first_failure = {"step": step, "failure": confirmed}
        return {"status": "failed" if confirmed else "passed" if success else "pending", "success": bool(success),
                "failure": confirmed, "confidence": None,
                "evidence": {k: g[k] for k in ("horizontal_error_m", "released_geometry", "supported_geometry", "retracted", "stable_frame", "bottom_height_m", "aperture_m")},
                "stable_steps": self.stable_count, "failure_persistence_steps": self.failure_count}
