"""M6R changes only the lower-to-release contract; M6 V2 stays frozen."""

import numpy as np

from .policies import pose_rotation, vector
from .m6_policy import PlacementRecovery, RETRY_PHASES, rotation_angle
from .m6_task import SETTINGS, geometry


LOWER_CONTRACT = {
    "phase": "lower", "removed": "abs(tcp_z - lower_target_z) <= 0.003",
    "replacement": "supported_geometry and horizontal_error_m <= 0.025",
    "retained": ["minimum_motion_steps", "tcp_distance_0.02m", "rotation_0.15rad", "attachment_loss_monitoring"],
    "inputs": ["obj_pose", "goal_pos", "tcp_pose", "qpos", "obj_linear_velocity", "obj_angular_velocity"],
    "excluded_inputs": ["info", "is_grasped", "contact_force", "reference", "environment_success", "disturbance_identity"],
}


class EffectAlignedRecovery(PlacementRecovery):
    def manifest(self):
        return {**super().manifest(), "m6r_lower_transition": LOWER_CONTRACT,
                "lower_vertical_tolerance_setting": "retained_in_settings_for_identity_unused_by_v2r"}

    def observe(self, observation):
        if self.state != "attempting":
            return
        try:
            g = geometry(observation, self.previous_pose)
            self.previous_pose = g["pose"]
            if np.linalg.norm(g["goal"] - self.retry.goal) > 1e-6:
                self.abort("goal_changed_during_attempt")
                return
            self.path += float(np.linalg.norm(g["tcp"] - self.previous_tcp))
            self.previous_tcp = g["tcp"]
            self.max_lift = max(self.max_lift, float(g["pose"][2] - self.retry.cube[2]))
            self.candidate_steps = self.candidate_steps + 1 if g["candidate"] else 0
            phase = RETRY_PHASES[self.stage]
            timed_out = self.stage_steps >= self.settings.durations[self.stage]
            if phase in ("transport", "lower") and self.candidate_steps == 0:
                self.missing_steps = getattr(self, "missing_steps", 0) + 1
                if self.missing_steps >= SETTINGS.failure_persistence_steps:
                    self.abort("attachment_lost_during_retry")
                    return
            else:
                self.missing_steps = 0
            if phase == "close":
                ready = self.stage_steps >= self.settings.minimum_close_steps and self.candidate_steps >= SETTINGS.failure_persistence_steps
            elif phase == "release":
                ready = self.stage_steps >= 10 and g["released_geometry"]
            elif phase == "settle":
                valid = (g["released_geometry"] and g["supported_geometry"] and g["retracted"] and g["stable_frame"]
                         and g["horizontal_error_m"] <= SETTINGS.horizontal_tolerance_m)
                self.stable_steps = self.stable_steps + 1 if valid else 0
                ready = self.stable_steps >= SETTINGS.stable_steps
            else:
                target = self.retract_target if phase == "retry_retract" else self.retry.targets[phase]
                tcp_pose = vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")
                angle = float(rotation_angle(pose_rotation(tcp_pose) @ self.retry.primitive.grasp_rotation.T))
                ready = (self.stage_steps >= self.settings.minimum_motion_steps and np.linalg.norm(g["tcp"] - target) <= self.settings.arrival_tolerance_m
                         and angle <= self.settings.arrival_rotation_tolerance_rad)
                if phase == "retry_retract":
                    ready &= g["aperture_m"] >= SETTINGS.released_aperture_m
                if phase == "lift":
                    ready &= self.max_lift >= SETTINGS.minimum_lift_m and self.candidate_steps >= SETTINGS.failure_persistence_steps
                if phase == "lower":
                    ready &= g["supported_geometry"] and g["horizontal_error_m"] <= SETTINGS.horizontal_tolerance_m
                if phase == "retract":
                    ready &= g["retracted"]
            if ready:
                if phase == "settle":
                    self.state = "attempt_complete"
                else:
                    self.stage += 1
                    self.stage_steps = 0
            elif timed_out:
                self.abort("retry_" + phase + "_not_completed")
            if self.state == "attempting" and self.steps >= self.action_budget:
                self.abort("remaining_action_budget_exhausted")
        except (KeyError, TypeError, ValueError):
            self.abort("invalid_recovery_observation")
