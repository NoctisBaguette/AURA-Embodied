"""Development insertion contract; geometric verification and contact acquisition reference."""

from dataclasses import asdict, dataclass
from itertools import product

import numpy as np
from scipy.spatial.transform import Rotation

from .policies import pose_rotation, vector
from .verification import single_bool


@dataclass(frozen=True)
class InsertionSettings:
    # Development candidates, NOT a fresh-native preregistration.
    minimum_lift_m: float = .03
    minimum_depth_half_length_ratio: float = .8
    maximum_depth_half_length_ratio: float = 1.2
    orientation_tolerance_rad: float = .05
    collision_slop_m: float = .0002
    stable_steps: int = 10
    failure_persistence_steps: int = 3
    maximum_linear_speed_m_s: float = .01
    maximum_angular_speed_rad_s: float = .15
    maximum_frame_translation_m: float = .0005
    maximum_frame_rotation_rad: float = .01
    grasp_tail_offset_m: float = .06
    attachment_position_tolerance_m: float = .025


SETTINGS = InsertionSettings()
SIGNS = np.array(list(product((-1, 1), repeat=3)))
EDGES = [(i, j) for i in range(8) for j in range(i + 1, 8)
         if np.count_nonzero(SIGNS[i] != SIGNS[j]) == 1]

# Fixed-target identity only: independent of insertion success and paired traces.
TARGET_TRANSLATION_ROUNDOFF_M = 1e-6
TARGET_ROTATION_ROUNDOFF_RAD = 1e-6


def fixed_target_check(current, expected):
    translation = float(np.linalg.norm(current[:3] - expected[:3]))
    rotation = float(Rotation.from_matrix(
        pose_rotation(current) @ pose_rotation(expected).T).magnitude())
    return {"raw_pose_equal": bool(np.array_equal(current, expected)),
            "translation_delta_m": translation, "rotation_delta_rad": rotation,
            "maximum_translation_delta_m": TARGET_TRANSLATION_ROUNDOFF_M,
            "maximum_rotation_delta_rad": TARGET_ROTATION_ROUNDOFF_RAD,
            "passed": translation <= TARGET_TRANSLATION_ROUNDOFF_M
                      and rotation <= TARGET_ROTATION_ROUNDOFF_RAD}


def channel_section(vertices, low, high):
    """Vertices of a box clipped to the channel's axial slab, including cut edges."""
    points = [v for v in vertices if low <= v[0] <= high]
    for i, j in EDGES:
        a, b = vertices[i], vertices[j]
        for plane in (low, high):
            if (a[0] - plane) * (b[0] - plane) < 0:
                points.append(a + (b - a) * ((plane - a[0]) / (b[0] - a[0])))
    return np.asarray(points, dtype=float).reshape(-1, 3)


def geometry(observation, previous=None):
    e = observation["extra"]
    peg = vector(e["peg_pose"], 7, "peg_pose")
    hole = vector(e["box_hole_pose"], 7, "box_hole_pose")
    half = vector(e["peg_half_size"], 3, "peg_half_size")
    radius = float(np.asarray(e["box_hole_radius"], dtype=float).reshape(-1)[0])
    if np.asarray(e["box_hole_radius"]).size != 1 or not np.isfinite(radius):
        raise ValueError("One finite hole radius required")
    if (not .085 - 1e-6 <= half[0] <= .125 + 1e-6 or
            not .015 - 1e-6 <= half[1] <= .025 + 1e-6 or
            abs(half[1] - half[2]) > 1e-6 or abs(radius - half[1] - .003) > 1e-6):
        raise ValueError("Unexpected installed peg/channel geometry")
    tcp = vector(e["tcp_pose"], 7, "tcp_pose")
    rp, rh = pose_rotation(peg), pose_rotation(hole)
    rel_r = rh.T @ rp
    rel_p = rh.T @ (peg[:3] - hole[:3])
    vertices = (SIGNS * half) @ rel_r.T + rel_p
    section = channel_section(vertices, -half[0], half[0])
    margin = float(radius - np.max(np.abs(section[:, 1:]))) if len(section) else None
    head = rel_p + rel_r[:, 0] * half[0]
    depth = float(head[0] + half[0])
    # Square cross section permits equivalent quarter-turn roll, not reversed entry.
    orientation = min(float(Rotation.from_matrix(rel_r @ Rotation.from_rotvec(
        [k * np.pi / 2, 0, 0]).as_matrix().T).magnitude()) for k in range(4))
    alignment_margin = float(radius - np.max(np.abs(rel_p[1:]) + np.abs(rel_r[1:]) @ half))
    qpos = vector(observation["agent"]["qpos"], 9, "qpos")
    aperture = float(qpos[-2:].sum())
    tail_tcp = rp.T @ (tcp[:3] - peg[:3])
    attached = (np.linalg.norm(tail_tcp - [-SETTINGS.grasp_tail_offset_m, 0, 0]) <= SETTINGS.attachment_position_tolerance_m
                and 2 * half[1] - .01 <= aperture <= 2 * half[1] + .01)
    linear = vector(e["peg_linear_velocity"], 3, "peg_linear_velocity")
    angular = vector(e["peg_angular_velocity"], 3, "peg_angular_velocity")
    delta = float(np.linalg.norm(peg[:3] - previous[:3])) if previous is not None else None
    angle = float(Rotation.from_matrix(rp @ pose_rotation(previous).T).magnitude()) if previous is not None else None
    stable = (previous is not None and np.linalg.norm(linear) <= SETTINGS.maximum_linear_speed_m_s
              and np.linalg.norm(angular) <= SETTINGS.maximum_angular_speed_rad_s
              and delta <= SETTINGS.maximum_frame_translation_m and angle <= SETTINGS.maximum_frame_rotation_rad)
    relation = (SETTINGS.minimum_depth_half_length_ratio * half[0] <= depth <= SETTINGS.maximum_depth_half_length_ratio * half[0]
                and orientation <= SETTINGS.orientation_tolerance_rad and margin is not None
                and margin >= -SETTINGS.collision_slop_m)
    return {"pose": peg, "hole": hole, "half": half, "radius": radius, "tcp": tcp,
            "relative_position": rel_p, "relative_rotation": rel_r, "vertices": vertices,
            "depth_m": depth, "orientation_error_rad": orientation,
            "lateral_error_m": float(np.linalg.norm(head[1:])), "channel_margin_m": margin,
            "alignment_margin_m": alignment_margin, "head_position_hole_m": head,
            "maximum_vertex_axial_m": float(vertices[:, 0].max()),
            "aperture_m": aperture, "attachment_proxy": bool(attached),
            "linear_speed_m_s": float(np.linalg.norm(linear)), "angular_speed_rad_s": float(np.linalg.norm(angular)),
            "frame_translation_m": delta, "frame_rotation_rad": angle,
            "stable_frame": bool(stable), "relation_ready": bool(relation)}


def diagnostics(g):
    names = ("depth_m", "orientation_error_rad", "lateral_error_m", "channel_margin_m",
             "alignment_margin_m", "aperture_m", "attachment_proxy", "linear_speed_m_s",
             "angular_speed_rad_s", "frame_translation_m", "frame_rotation_rad", "stable_frame", "relation_ready")
    return {**{n: g[n] for n in names}, "peg_head_position_hole_m": g["head_position_hole_m"].tolist(),
            "object_target_relative_pose": {"position_m": g["relative_position"].tolist(),
                                            "rotation_matrix": g["relative_rotation"].tolist()}}


def failure_label(g, decision, acquired, max_lift, success, final=False):
    phase, local = decision["phase"], decision["phase_step"]
    if phase.startswith("recovery_"):
        return None if not final or success else "RECOVERY_TASK_NOT_ACHIEVED"
    if (phase == "close" and local >= 28 or phase in ("lift", "carry", "prealign", "offset", "insert", "settle")) and not acquired:
        return "GRASP_FAILURE"
    if phase in ("carry", "prealign", "offset", "insert", "settle") and max_lift < SETTINGS.minimum_lift_m:
        return "LIFT_NOT_ACHIEVED"
    if acquired and phase in ("lift", "carry", "prealign", "offset", "insert", "settle") and not g["attached"]:
        return "OBJECT_LOST"
    if (phase == "insert" and local >= 140) or (phase == "settle" and local >= 10) or final:
        if not g["relation_ready"]:
            if g["orientation_error_rad"] > SETTINGS.orientation_tolerance_rad:
                return "INSERTION_ORIENTATION_ERROR"
            if g["channel_margin_m"] is not None and g["channel_margin_m"] < -SETTINGS.collision_slop_m:
                return "INSERTION_LATERAL_INTERFERENCE"
            return "INSERTION_DEPTH_NOT_ACHIEVED"
        if not success:
            return "INSERTION_UNSTABLE"
    return None


class InsertionReference:
    """Independent of built-in success; fresh contact acquisition and physical state."""

    def __init__(self, observation):
        g = geometry(observation)
        self.initial_z = g["pose"][2]
        self.previous = g["pose"].copy()
        self.hole, self.half = g["hole"].copy(), g["half"].copy()
        self.radius = g["radius"]
        self.last_step = self.stable_count = 0
        self.ever_attached = False
        self.acquired = False
        self.max_lift = 0.
        self.first_failure = self.first_success_step = None

    def observe(self, observation, info, step, decision, final=False):
        if step != self.last_step + 1:
            raise ValueError("Fresh consecutive insertion reference observations required")
        g = geometry(observation, self.previous)
        target_check = fixed_target_check(g["hole"], self.hole)
        target_check.update(half_size_equal=bool(np.array_equal(g["half"], self.half)),
                            hole_radius_equal=g["radius"] == self.radius)
        if not (target_check["passed"] and target_check["half_size_equal"] and target_check["hole_radius_equal"]):
            raise ValueError(f"Insertion target/geometry changed: {target_check}")
        self.previous, self.last_step = g["pose"].copy(), step
        held = single_bool(info["contact_grasped"], "contact_grasped")
        self.ever_attached |= held
        self.max_lift = max(self.max_lift, float(g["pose"][2] - self.initial_z))
        self.acquired |= held and g["pose"][2] - self.initial_z >= SETTINGS.minimum_lift_m
        ready = self.acquired and g["relation_ready"] and g["stable_frame"]
        self.stable_count = self.stable_count + 1 if ready else 0
        success = self.stable_count >= SETTINGS.stable_steps
        g["attached"] = held
        failure = failure_label(g, decision, self.ever_attached, self.max_lift, success, final)
        if failure and self.first_failure is None:
            self.first_failure = {"step": step, "failure": failure}
        if success and self.first_success_step is None:
            self.first_success_step = step
        return {**diagnostics(g), "fixed_target_check": target_check, "task_success": success, "failure": failure,
                "stable_steps": self.stable_count, "valid_acquisition": self.acquired,
                "ever_contact_grasped": self.ever_attached, "current_contact_grasped": held, "max_lift_m": self.max_lift}


class InsertionVerifier:
    """Passive geometry/velocity verifier; evaluator contacts/success never enter it."""

    def __init__(self, observation):
        g = geometry(observation)
        self.initial_z, self.previous = g["pose"][2], g["pose"].copy()
        self.last_step = self.stable_count = self.persistence = 0
        self.ever_attached = False
        self.acquired = False
        self.max_lift = 0.
        self.pending = self.first_failure = None

    def observe(self, observation, step, decision, final=False):
        if step != self.last_step + 1:
            raise ValueError("Fresh consecutive verifier observations required")
        g = geometry(observation, self.previous)
        self.previous, self.last_step = g["pose"].copy(), step
        self.ever_attached |= g["attachment_proxy"]
        self.max_lift = max(self.max_lift, float(g["pose"][2] - self.initial_z))
        self.acquired |= g["attachment_proxy"] and g["pose"][2] - self.initial_z >= SETTINGS.minimum_lift_m
        ready = self.acquired and g["relation_ready"] and g["stable_frame"]
        self.stable_count = self.stable_count + 1 if ready else 0
        success = self.stable_count >= SETTINGS.stable_steps
        g["attached"] = g["attachment_proxy"]
        label = failure_label(g, decision, self.ever_attached, self.max_lift, success, final)
        self.persistence = self.persistence + 1 if label and label == self.pending else int(label is not None)
        self.pending = label
        confirmed = label is not None and self.persistence >= SETTINGS.failure_persistence_steps
        if confirmed and self.first_failure is None:
            self.first_failure = {"step": step, "failure": label}
        return {**diagnostics(g), "status": "failed" if confirmed else "succeeded" if success else "monitoring",
                "failure": label if confirmed else None, "pending_failure": label,
                "failure_persistence_steps": self.persistence, "stable_steps": self.stable_count,
                "max_lift_m": self.max_lift}


def task_manifest():
    return {"name": "validly_acquired_peg_stably_inserted_in_designated_square_channel",
            "status": "development_only_not_frozen", **asdict(SETTINGS),
            "fixed_target_identity": {"translation_roundoff_m": TARGET_TRANSLATION_ROUNDOFF_M,
                "rotation_roundoff_rad": TARGET_ROTATION_ROUNDOFF_RAD,
                "anchor": "reset_pose_no_cumulative_drift", "dimensions": "exact",
                "paired_raw_observations": "exact_no_tolerance"},
            "depth": "peg_head_center_x_in_hole_frame_plus_channel_half_length",
            "clearance": "all_vertices_of_peg_volume_clipped_to_channel_axial_slab_inside_square_channel",
            "final_release_required": False, "historical_contact_grasp_and_lift_required": True,
            "built_in_success": "logged_only_never_controller_or_sole_reference"}
