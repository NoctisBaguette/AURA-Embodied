"""Task-specific development insertion controller and one effect-gated backout/retry."""

from dataclasses import asdict, dataclass

import numpy as np
from scipy.spatial.transform import Rotation

from .policies import bounded, pose_rotation, vector
from .m7_task import SETTINGS, geometry, fixed_target_check, PoseStability

PHASES = ("approach", "descend", "close", "lift", "carry", "prealign", "offset", "insert", "settle")
DURATIONS = (80, 60, 30, 60, 100, 100, 60, 140, 80)
INJECTION_STEP = sum(DURATIONS[:6]) + 1
MAX_STEPS = 1200
SLOW_AXIAL_STEP_M = .004
SLOW_TRANSVERSE_STEP_M = .004
GRIPPER_LOWER_M = -.01
GRIPPER_UPPER_M = .04


@dataclass(frozen=True)
class TrackingSettings:
    integral_gain_per_step: float = .1
    maximum_correction_m: float = .006
    learning_error_limit_m: float = .006


class TransverseTracking:
    """Bounded TCP-only load compensation; never integrate blocked axial travel."""

    def __init__(self):
        self.settings = TrackingSettings()
        self.offset = np.zeros(3)

    def correct(self, observation, target, axis):
        tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp")[:3]
        error = target - tcp
        transverse = error - axis * float(error @ axis)
        self.offset -= axis * float(self.offset @ axis)
        eligible = np.linalg.norm(transverse) <= self.settings.learning_error_limit_m
        if eligible:
            self.offset = bounded(self.offset + self.settings.integral_gain_per_step * transverse,
                                  self.settings.maximum_correction_m)
        return target + self.offset, {"tcp_tracking_offset_world_m": self.offset.tolist(),
            "transverse_tcp_tracking_error_world_m": transverse.tolist(),
            "tracking_integral_updated": bool(eligible)}


def command(observation, base_pose, position, rotation, gripper=-1., slow=False, axis_world=None):
    tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")
    base = vector(base_pose, 7, "robot_base_pose")
    delta = position - tcp[:3]
    if slow and axis_world is not None:
        axis = np.asarray(axis_world, dtype=float)
        axial_error = float(delta @ axis)
        transverse_error = delta - axial_error * axis
        # Long remaining insertion travel must not scale away height/alignment correction.
        delta = axis * np.clip(axial_error, -SLOW_AXIAL_STEP_M, SLOW_AXIAL_STEP_M) + bounded(
            transverse_error, SLOW_TRANSVERSE_STEP_M)
    else:
        delta = bounded(delta, .004 if slow else .012)
    next_p = tcp[:3] + delta
    current_r = pose_rotation(tcp)
    error = Rotation.from_matrix(rotation @ current_r.T).as_rotvec()
    next_r = Rotation.from_rotvec(bounded(error, .06)).as_matrix() @ current_r
    rb = pose_rotation(base)
    action = np.r_[rb.T @ (next_p - base[:3]), Rotation.from_matrix(rb.T @ next_r).as_euler("XYZ"), gripper]
    return action.astype(np.float32)[None, :], {"expected_tcp_position_world_m": position.tolist(),
        "commanded_tcp_position_world_m": next_p.tolist(), "expected_tcp_rotation_world": rotation.tolist(),
        "gripper": "open" if gripper == 1 else "closed" if gripper == -1 else "holding",
        "gripper_action": float(gripper)}


class FixedInsertion:
    """Timed nominal sequence, one post-lift grasp transform calibration, cached targets.

    Only TCP servo feedback is consumed after calibration. A separate experiment
    injector may bias the cached offset/insert/settle waypoints before contact.
    Neither evaluator data nor verifier labels enter this nominal controller.
    """

    def __init__(self, observation, base_pose):
        g = geometry(observation)
        self.base = vector(base_pose, 7, "base_pose")
        self.hole, self.half = g["hole"].copy(), g["half"].copy()
        self.rh = pose_rotation(self.hole)
        self.grasp_rotation = pose_rotation(g["pose"]) @ np.diag([1., -1., -1.])
        self.grasp_position = g["pose"][:3] + pose_rotation(g["pose"]) @ [-SETTINGS.grasp_tail_offset_m, 0, 0]
        self.calibrated = False
        self.targets = {"approach": self.grasp_position + [0, 0, .15], "descend": self.grasp_position.copy(),
                        "close": self.grasp_position.copy(), "lift": self.grasp_position + [0, 0, .15]}
        self.rotations = {p: self.grasp_rotation.copy() for p in self.targets}
        self.bias_world = np.zeros(3)
        self.tracking = TransverseTracking()
        self.hold_gripper = -1.

    def manifest(self):
        return {"name": "fixed_side_insertion_development", "phases": PHASES, "durations": DURATIONS,
                "total_nominal_steps": sum(DURATIONS), "status": "development_not_frozen",
                "grasp_tail_offset_m": SETTINGS.grasp_tail_offset_m, "precontact_head_gap_m": .06,
                "maximum_translation_m": .012, "insertion_axial_translation_m": SLOW_AXIAL_STEP_M,
                "insertion_transverse_translation_m": SLOW_TRANSVERSE_STEP_M,
                "insertion_maximum_translation_norm_m": float(np.hypot(SLOW_AXIAL_STEP_M, SLOW_TRANSVERSE_STEP_M)),
                "insertion_servo": "independent_axial_and_transverse_error_bounds_in_cached_target_frame",
                "transverse_tcp_tracking": asdict(self.tracking.settings),
                "hold_gripper": {"command": "sustained_full_close_after_acquisition",
                    "normalized_action": -1.,
                    "installed_joint_target_range_m": [GRIPPER_LOWER_M, GRIPPER_UPPER_M]},
                "maximum_rotation_rad": .06,
                "phase_transition": "elapsed_steps_only", "post_lift_calibration": "once_actual_tcp_in_peg_transform",
                "after_calibration_inputs": ["tcp_pose"], "evaluator_inputs": False, "verifier_inputs": False}

    @staticmethod
    def phase(index):
        start = 0
        for phase, duration in zip(PHASES, DURATIONS):
            if index < start + duration:
                return phase, index - start + 1
            start += duration
        return "settle", index - sum(DURATIONS[:-1]) + 1

    def calibrate(self, observation):
        g = geometry(observation)
        rp = pose_rotation(g["pose"])
        self.tcp_in_peg = rp.T @ (g["tcp"][:3] - g["pose"][:3])
        self.tcp_rotation_in_peg = rp.T @ pose_rotation(g["tcp"])
        pre_peg = self.hole[:3] + self.rh @ [-2 * self.half[0] - .06, 0, 0]
        inserted_peg = self.hole[:3] + self.rh @ [-self.half[0], 0, 0]
        pre_tcp = pre_peg + self.rh @ self.tcp_in_peg
        insert_tcp = inserted_peg + self.rh @ self.tcp_in_peg
        carry = pre_tcp.copy(); carry[2] = max(.35, pre_tcp[2] + .15)
        self.targets.update(carry=carry, prealign=pre_tcp, offset=pre_tcp.copy(), insert=insert_tcp, settle=insert_tcp.copy())
        self.rotations.update({p: self.rh @ self.tcp_rotation_in_peg for p in ("carry", "prealign", "offset", "insert", "settle")})
        self.calibrated = True

    def bias_insertion_waypoints(self, world_offset):
        if not self.calibrated or np.linalg.norm(self.bias_world) != 0:
            raise ValueError("Waypoint perturbation requires calibrated, unperturbed nominal path")
        self.bias_world = np.asarray(world_offset, dtype=float).copy()
        for phase in ("offset", "insert", "settle"):
            self.targets[phase] += self.bias_world

    def action(self, observation, index):
        phase, local = self.phase(index)
        if phase == "carry" and not self.calibrated:
            self.calibrate(observation)
        target = self.targets[phase]
        tracking = {"tcp_tracking_offset_world_m": [0., 0., 0.], "tracking_integral_updated": False}
        if phase in ("prealign", "offset", "insert", "settle"):
            target, tracking = self.tracking.correct(observation, target, self.rh[:, 0])
        gripper = 1. if phase in ("approach", "descend") else -1. if phase == "close" else self.hold_gripper
        action, detail = command(observation, self.base, target, self.rotations[phase],
                                 gripper, phase in ("insert", "settle"),
                                 self.rh[:, 0])
        return action, {**detail, **tracking, "expected_tcp_position_world_m": self.targets[phase].tolist(),
                        "phase": phase, "phase_step": local,
                        "schedule_complete": index + 1 >= sum(DURATIONS)}


@dataclass(frozen=True)
class RecoverySettings:
    maximum_attempts: int = 1
    action_budget: int = 420
    minimum_remaining_steps: int = 80
    stage_caps: tuple = (120, 120, 140, 40)
    minimum_stage_steps: int = 3
    safe_head_gap_m: float = .04


RETRY_PHASES = ("backout", "realign", "reinsert", "verify")


class InsertionRecovery:
    def __init__(self, nominal, max_steps=MAX_STEPS):
        self.nominal, self.max_steps = nominal, max_steps
        self.settings = RecoverySettings()
        self.state = "nominal"
        self.attempts = self.steps = self.stage = self.stage_steps = self.stable_steps = self.missing = 0
        self.reason = self.trigger_step = self.first_action_step = self.failure_detail = None
        self.completed_stages = []
        self.path = 0.
        self.previous_tcp = self.previous_pose = self.last_action = self.last_decision = None
        self.target = self.target_rotation = None
        self.refresh_record = None
        self.target_check = None
        self.tracking = TransverseTracking()
        self.pose_stability = None
        self.motion = None

    def manifest(self):
        return {"name": "one_bounded_insertion_recovery", "settings": asdict(self.settings),
                "phases": RETRY_PHASES, "trigger": "preceding_confirmed_geometry_verdict",
                "backout_readiness": "entire_peg_before_channel_entry_with_safe_head_gap",
                "realign_readiness": "object_axis_and_projected_cross_section_fit_channel",
                "reinsert_readiness": "object_target_depth_orientation_and_clipped_volume_clearance",
                "verify_readiness": "consecutive_stable_object_target_relation",
                "refresh": "object_target_and_grasp_transform_after_safe_backout",
                "transverse_tcp_tracking": asdict(self.tracking.settings),
                "hold_gripper": "same_sustained_full_close_as_nominal",
                "verify_stability": "same_complete_physics_sampled_pose_window_as_verifier",
                "slow_servo": {"axis": "cached_hole_local_x", "axial_step_m": SLOW_AXIAL_STEP_M,
                    "transverse_step_m": SLOW_TRANSVERSE_STEP_M,
                    "maximum_step_norm_m": float(np.hypot(SLOW_AXIAL_STEP_M, SLOW_TRANSVERSE_STEP_M))},
                "evaluator_inputs": False, "terminal": "repeat_last_absolute_command_no_second_attempt"}

    def snapshot(self):
        return {"state": self.state, "attempts": self.attempts, "reason": self.reason,
                "trigger_step": self.trigger_step, "first_action_step": self.first_action_step,
                "phase": RETRY_PHASES[self.stage] if self.attempts else None, "phase_step": self.stage_steps,
                "action_steps": self.steps, "observed_tcp_path_m": self.path,
                "completed_stages": self.completed_stages.copy(), "failure_detail": self.failure_detail,
                "stable_steps": self.stable_steps, "refresh_record": self.refresh_record,
                "fixed_target_check": self.target_check,
                "pose_stability": self.motion,
                "tcp_tracking_offset_world_m": self.tracking.offset.tolist()}

    def abort(self, reason):
        self.state, self.failure_detail = "aborted", reason

    def start(self, observation, step, verdict):
        self.attempts, self.trigger_step, self.first_action_step = 1, step - 1, step
        self.reason = verdict["failure"]
        g = geometry(observation)
        self.previous_tcp, self.previous_pose = g["tcp"][:3].copy(), g["pose"].copy()
        self.pose_stability = PoseStability(observation)
        if self.max_steps - step + 1 < self.settings.minimum_remaining_steps:
            self.abort("insufficient_remaining_budget"); return
        if not g["attachment_proxy"]:
            self.abort("acquisition_or_attachment_unavailable_consumes_single_episode"); return
        self.hole = g["hole"].copy(); self.rh = pose_rotation(self.hole)
        current_head = g["head_position_hole_m"][0]
        distance = max(0., current_head + g["half"][0] + .06)
        self.target = g["tcp"][:3] - self.rh[:, 0] * distance
        self.target_rotation = pose_rotation(g["tcp"])
        self.state = "attempting"

    def refresh(self, observation):
        g = geometry(observation)
        self.hole, self.rh = g["hole"].copy(), pose_rotation(g["hole"])
        rp = pose_rotation(g["pose"])
        offset = rp.T @ (g["tcp"][:3] - g["pose"][:3])
        rel_r = rp.T @ pose_rotation(g["tcp"])
        pre_peg = self.hole[:3] + self.rh @ [-2 * g["half"][0] - .06, 0, 0]
        inserted_peg = self.hole[:3] + self.rh @ [-g["half"][0], 0, 0]
        self.pre_target, self.insert_target = pre_peg + self.rh @ offset, inserted_peg + self.rh @ offset
        self.target_rotation = self.rh @ rel_r
        self.refresh_record = {"peg_pose_world": g["pose"].tolist(), "hole_pose_world": self.hole.tolist(),
                               "tcp_in_peg_m": offset.tolist(), "tcp_rotation_in_peg": rel_r.tolist()}

    def action(self, observation, step, verdict):
        if self.state == "nominal" and verdict.get("status") == "failed":
            self.start(observation, step, verdict)
        if self.state == "nominal":
            action, decision = self.nominal.action(observation, step - 1)
        elif self.state == "attempting":
            phase = RETRY_PHASES[self.stage]
            self.stage_steps += 1; self.steps += 1
            target, tracking = self.tracking.correct(observation, self.target, self.rh[:, 0])
            action, detail = command(observation, self.nominal.base, target, self.target_rotation,
                                     gripper=self.nominal.hold_gripper,
                                     slow=phase in ("backout", "reinsert", "verify"), axis_world=self.rh[:, 0])
            decision = {**detail, **tracking, "expected_tcp_position_world_m": self.target.tolist(),
                        "phase": "recovery_" + phase, "phase_step": self.stage_steps, "schedule_complete": False}
        elif self.last_action is not None:
            action, decision = self.last_action.copy(), {**self.last_decision, "phase": "recovery_" + self.state,
                                                       "schedule_complete": self.state == "attempt_complete"}
        else:
            action, detail = command(observation, self.nominal.base,
                vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")[:3],
                pose_rotation(vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")))
            decision = {**detail, "phase": "recovery_aborted", "phase_step": 0, "schedule_complete": False}
        self.last_action, self.last_decision = action.copy(), decision.copy()
        return action, decision

    def observe(self, observation, physics_samples=None):
        if self.state != "attempting":
            return
        g = geometry(observation, self.previous_pose)
        self.target_check = fixed_target_check(g["hole"], self.hole)
        if not self.target_check["passed"]:
            self.abort("target_changed_during_recovery"); return
        self.motion = self.pose_stability.observe(observation, physics_samples)
        self.path += float(np.linalg.norm(g["tcp"][:3] - self.previous_tcp))
        self.previous_tcp, self.previous_pose = g["tcp"][:3].copy(), g["pose"].copy()
        self.missing = self.missing + 1 if not g["attachment_proxy"] else 0
        if self.missing >= SETTINGS.failure_persistence_steps:
            self.abort("attachment_lost_during_episode"); return
        phase = RETRY_PHASES[self.stage]
        if phase == "backout":
            ready = g["maximum_vertex_axial_m"] <= -g["half"][0] - self.settings.safe_head_gap_m
        elif phase == "realign":
            ready = (g["orientation_error_rad"] <= SETTINGS.orientation_tolerance_rad and
                     g["alignment_margin_m"] >= -SETTINGS.collision_slop_m and
                     g["maximum_vertex_axial_m"] <= -g["half"][0] - self.settings.safe_head_gap_m)
        elif phase == "reinsert":
            ready = g["relation_ready"]
        else:
            self.stable_steps = self.stable_steps + 1 if (g["relation_ready"] and self.motion["stable_frame"]
                and self.motion["relation_all_substeps"]) else 0
            ready = self.stable_steps >= SETTINGS.stable_steps and self.motion["window_ready"]
        ready = bool(ready and self.stage_steps >= self.settings.minimum_stage_steps and g["attachment_proxy"])
        if ready:
            self.completed_stages.append(phase)
            if phase == "verify":
                self.state = "attempt_complete"
            else:
                self.stage += 1; self.stage_steps = 0
                if phase == "backout":
                    self.refresh(observation); self.target = self.pre_target.copy()
                elif phase == "realign":
                    self.target = self.insert_target.copy()
        elif self.stage_steps >= self.settings.stage_caps[self.stage]:
            self.abort(phase + "_physical_effect_not_completed")
        if self.state == "attempting" and self.steps >= self.settings.action_budget:
            self.abort("one_episode_action_budget_exhausted")
