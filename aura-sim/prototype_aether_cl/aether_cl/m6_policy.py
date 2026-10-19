"""Task-specific placement extension; original PickCube primitives stay unchanged."""

from dataclasses import asdict, dataclass

import numpy as np

from .policies import FixedPickCube, PickCubeSettings, pose_rotation, vector
from .m6_task import SETTINGS, geometry


PHASES = ("approach", "descend", "close", "lift", "transport", "lower", "release", "retract", "settle")
NOMINAL_DURATIONS = (60, 40, 25, 45, 60, 40, 25, 35, 30)
NOMINAL_STEPS = sum(NOMINAL_DURATIONS)
INJECTION_STEP = sum(NOMINAL_DURATIONS[:7]) + 1
MAX_STEPS = 800


class FixedPlacement:
    def __init__(self, observation, base_pose):
        self.primitive = FixedPickCube(observation, base_pose)
        self.cube, self.goal = self.primitive.cube.copy(), self.primitive.goal.copy()
        self.targets = {k: v.copy() for k, v in self.primitive.targets.items()}
        lower = self.goal + [0, 0, .002]
        self.targets.update(lower=lower, release=lower.copy(),
                            retract=self.goal + [0, 0, PickCubeSettings().clearance_m],
                            settle=self.goal + [0, 0, PickCubeSettings().clearance_m])

    def manifest(self):
        return {"name": "fixed_support_placement", "version": "m6-preregistered-v0.1",
                "primitive": self.primitive.manifest(), "phases": list(PHASES),
                "durations": list(NOMINAL_DURATIONS), "scheduled_steps": NOMINAL_STEPS,
                "release_tcp_clearance_m": .002, "step_inputs": ["tcp_pose"],
                "phase_transition": "elapsed_steps_only", "verification": False, "recovery": False}

    def phase(self, index):
        start = 0
        for phase, duration in zip(PHASES, NOMINAL_DURATIONS):
            if index < start + duration:
                return phase, index - start + 1
            start += duration
        return "settle", index - sum(NOMINAL_DURATIONS[:-1]) + 1

    def command(self, observation, phase, phase_step, recovery=False, target=None):
        # The existing servo performs all coordinate/rotation/bound handling.
        open_gripper = phase in ("approach", "descend", "release", "retract", "settle", "retry_retract")
        primitive_phase = "approach" if open_gripper else "close"
        start = 0 if open_gripper else PickCubeSettings().approach_steps + PickCubeSettings().descend_steps
        prior = self.primitive.targets[primitive_phase]
        self.primitive.targets[primitive_phase] = self.targets.get(phase) if target is None else target
        try:
            action, decision = self.primitive.action(observation, start)
        finally:
            self.primitive.targets[primitive_phase] = prior
        return action, {**decision, "phase": ("recovery_" if recovery else "") + phase,
                        "phase_step": phase_step, "schedule_complete": not recovery and phase == "settle" and phase_step >= 30}

    def action(self, observation, index):
        phase, local = self.phase(index)
        return self.command(observation, phase, local)


@dataclass(frozen=True)
class PlacementRecoverySettings:
    durations: tuple = (35, 60, 35, 25, 35, 80, 40, 25, 35, 30)
    action_budget: int = 400
    maximum_attempts: int = 1
    minimum_remaining_steps: int = 100
    minimum_motion_steps: int = 3
    minimum_close_steps: int = 10
    arrival_tolerance_m: float = .02
    lower_vertical_tolerance_m: float = .003
    arrival_rotation_tolerance_rad: float = .15


RETRY_PHASES = ("retry_retract", *PHASES)
SUPPORTED_FAILURES = ("GRASP_FAILURE", "OBJECT_LOST", "LIFT_NOT_ACHIEVED", "PLACEMENT_TARGET_NOT_REACHED",
                      "RELEASE_NOT_ACHIEVED", "UNSUPPORTED_PLACEMENT", "RETRACTION_NOT_ACHIEVED", "POST_RELEASE_INSTABILITY")


class PlacementRecovery:
    def __init__(self, nominal, base_pose, max_steps=MAX_STEPS):
        self.nominal, self.base_pose, self.max_steps = nominal, base_pose, max_steps
        self.settings = PlacementRecoverySettings()
        self.state = "nominal"
        self.attempts = self.steps = self.stage = self.stage_steps = self.candidate_steps = self.stable_steps = 0
        self.reason = self.trigger_step = self.first_action_step = self.failure_detail = None
        self.retry = self.previous_tcp = self.previous_pose = self.last_action = self.last_decision = None
        self.max_lift = self.path = 0.
        self.action_budget = self.settings.action_budget

    def manifest(self):
        return {"settings": asdict(self.settings), "phases": list(RETRY_PHASES),
                "supported_failures": list(SUPPORTED_FAILURES), "maximum_attempts": 1,
                "trigger": "preceding_confirmed_geometry_verdict", "targets": "refresh_once_at_attempt_start",
                "inputs": ["observation", "step", "verifier_verdict"], "evaluator_inputs": False,
                "terminal_behavior": "repeat_last_absolute_command_without_new_attempt"}

    def snapshot(self):
        return {"state": self.state, "attempts": self.attempts, "reason": self.reason,
                "trigger_step": self.trigger_step, "first_action_step": self.first_action_step,
                "phase": RETRY_PHASES[self.stage] if self.retry else None, "phase_step": self.stage_steps,
                "action_steps": self.steps, "action_budget": self.action_budget, "observed_tcp_path_m": self.path,
                "candidate_persistence_steps": self.candidate_steps, "attempt_max_cube_lift_m": self.max_lift,
                "failure_detail": self.failure_detail,
                "cached_cube_world_m": self.retry.cube.tolist() if self.retry else None}

    def abort(self, reason):
        self.state, self.failure_detail = "aborted", reason

    def action(self, observation, step, verdict):
        if self.state == "nominal" and verdict.get("status") == "failed":
            self.reason, self.trigger_step = verdict["failure"], step - 1
            if self.reason not in SUPPORTED_FAILURES:
                self.abort("unsupported_failure")
            elif self.max_steps - step + 1 < self.settings.minimum_remaining_steps:
                self.abort("insufficient_remaining_budget")
            else:
                self.retry = FixedPlacement(observation, self.base_pose)
                g = geometry(observation)
                self.previous_tcp, self.previous_pose = g["tcp"], g["pose"]
                self.retract_target = g["tcp"].copy()
                self.retract_target[2] = max(g["tcp"][2], self.retry.targets["approach"][2])
                self.action_budget = min(self.settings.action_budget, self.max_steps - step + 1)
                self.attempts, self.first_action_step, self.state = 1, step, "attempting"
        if self.state == "nominal":
            action, decision = self.nominal.action(observation, step - 1)
        elif self.state == "attempting":
            phase = RETRY_PHASES[self.stage]
            self.stage_steps += 1
            self.steps += 1
            action, decision = self.retry.command(observation, phase, self.stage_steps, True,
                                                 self.retract_target if phase == "retry_retract" else None)
        else:
            action = self.last_action.copy()
            decision = {**self.last_decision, "phase": "recovery_" + self.state,
                        "schedule_complete": self.state == "attempt_complete"}
        self.last_action, self.last_decision = action.copy(), decision.copy()
        return action, decision

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
                    ready &= abs(g["tcp"][2] - target[2]) <= self.settings.lower_vertical_tolerance_m
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


def rotation_angle(matrix):
    return np.arccos(np.clip((np.trace(matrix) - 1) / 2, -1, 1))
