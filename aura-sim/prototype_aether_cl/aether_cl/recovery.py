"""One bounded observed-state retry, using the unchanged M1 motion primitives."""

from dataclasses import asdict, dataclass

import numpy as np

from .policies import FixedPickCube, PickCubeSettings, pose_rotation, vector
from .verification import TaskSettings, VerificationSettings


@dataclass(frozen=True)
class RecoverySettings:
    retract_steps: int = 35
    approach_steps: int = 60
    descend_steps: int = 35
    close_steps: int = 25
    lift_steps: int = 35
    transport_steps: int = 80
    lower_steps: int = 30
    hold_steps: int = 10
    arrival_tolerance_m: float = 0.02
    arrival_rotation_tolerance_rad: float = 0.15
    maximum_attempts: int = 1

    action_budget: int = 230
    minimum_remaining_steps: int = 40
    minimum_close_steps: int = 10
    minimum_motion_steps: int = 3


RETRY_PHASES = ("retract", "approach", "descend", "close", "lift", "transport", "lower", "hold")
SUPPORTED_FAILURES = ("GRASP_FAILURE", "OBJECT_LOST")


class RecoveryController:
    """Reads observations and the preceding verifier verdict, never evaluator info.

    The nominal policy object is untouched. A retry caches fresh cube/goal
    targets once and reuses FixedPickCube.action at the selected phase index.
    The original verifier continues running, with its original task clock.
    Local candidate checks gate retry transport; they are not contact truth.
    """

    def __init__(self, policy, base_pose, max_steps):
        self.policy = policy
        self.base_pose = vector(base_pose, 7, "base_pose")
        self.max_steps = max_steps
        self.settings = RecoverySettings()
        self.verification_settings = VerificationSettings()
        self.state = "nominal"
        self.reason = None
        self.trigger_step = self.first_action_step = None
        self.attempts = self.steps = 0
        self.action_budget = self.settings.action_budget
        self.stage_index = self.stage_steps = 0
        self.candidate_steps = self.missing_steps = 0
        self.max_lift = 0.0
        self.observed_path_m = 0.0
        self.previous_tcp = None
        self.last_action = None
        self.last_decision = None
        self.retry = None
        self.failure_detail = None
        self.phase_starts = {}
        start = 0
        for phase in ("approach", "descend", "close", "lift", "transport", "lower", "hold"):
            self.phase_starts[phase] = start
            start += getattr(PickCubeSettings(), phase + "_steps")

    def manifest(self):
        return {"version": "0.1-candidate", "settings": asdict(self.settings),
                "attempt_action_budget": self.settings.action_budget,
                "supported_failures": list(SUPPORTED_FAILURES),
                "trigger": "preceding_confirmed_verifier_failure",
                "inputs": ["verifier_verdict", "obj_pose", "goal_pos", "tcp_pose", "qpos"],
                "ground_truth_inputs": False,
                "nominal_policy_changed": False,
                "retry_targets": "cached_from_observation_at_trigger",
                "retry_motion_primitives": "unchanged_FixedPickCube_action",
                "transport_gate": "three_fresh_geometry_candidates_and_0.05m_attempt_lift",
                "failure_action": "repeat_last_absolute_command_no_nominal_resumption"}

    def snapshot(self):
        return {"state": self.state, "reason": self.reason, "attempts": self.attempts,
                "trigger_step": self.trigger_step, "first_action_step": self.first_action_step,
                "phase": RETRY_PHASES[self.stage_index] if self.retry else None,
                "action_steps": self.steps, "action_budget": self.action_budget,
                "observed_tcp_path_m": self.observed_path_m,
                "candidate_persistence_steps": self.candidate_steps,
                "attempt_max_cube_lift_m": self.max_lift,
                "attempt_cube_position_world_m": self.retry.cube.tolist() if self.retry else None,
                "attempt_goal_position_world_m": self.retry.goal.tolist() if self.retry else None,
                "failure_detail": self.failure_detail}

    def abort(self, reason):
        self.state = "aborted"
        self.failure_detail = reason

    def action(self, observation, step, verdict):
        if self.state == "nominal" and verdict.get("status") == "failed":
            self.reason = verdict.get("failure")
            self.trigger_step = step - 1
            if self.reason not in SUPPORTED_FAILURES:
                self.abort("unsupported_failure")
            elif self.max_steps - step + 1 < self.settings.minimum_remaining_steps:
                self.abort("insufficient_remaining_budget")
            else:
                self.retry = FixedPickCube(observation, self.base_pose)
                tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")[:3]
                self.retract_target = tcp.copy()
                self.retract_target[2] = max(tcp[2], self.retry.targets["approach"][2])
                self.previous_tcp = tcp
                self.action_budget = min(self.settings.action_budget, self.max_steps - step + 1)
                self.attempts = 1
                self.first_action_step = step
                self.state = "attempting"
        if self.state == "nominal":
            action, decision = self.policy.action(observation, step - 1)
        elif self.state == "attempting":
            phase = RETRY_PHASES[self.stage_index]
            primitive = "approach" if phase == "retract" else phase
            target = self.retry.targets[primitive].copy()
            if phase == "retract":
                self.retry.targets[primitive] = self.retract_target
            try:
                action, decision = self.retry.action(observation, self.phase_starts[primitive])
            finally:
                self.retry.targets[primitive] = target
            decision = {**decision, "phase": "recovery_" + phase, "schedule_complete": False}
            self.stage_steps += 1
            self.steps += 1
        else:
            # A diagnosis always follows a nominal action, so a command exists.
            action = self.last_action.copy()
            decision = {**self.last_decision, "phase": "recovery_" + self.state,
                        "schedule_complete": self.state == "attempt_complete"}
        self.last_action = action.copy()
        self.last_decision = decision.copy()
        return action, decision

    def observe(self, observation):
        if self.state != "attempting":
            return
        try:
            extra = observation["extra"]
            cube = vector(extra["obj_pose"], 7, "obj_pose")[:3]
            tcp_pose = vector(extra["tcp_pose"], 7, "tcp_pose")
            tcp = tcp_pose[:3]
            qpos = vector(observation["agent"]["qpos"], 9, "qpos")
            goal = vector(extra["goal_pos"], 3, "goal_pos")
            if np.linalg.norm(goal - self.retry.goal) > 1e-6:
                self.abort("goal_changed_during_attempt")
                return
            self.observed_path_m += float(np.linalg.norm(tcp - self.previous_tcp))
            self.previous_tcp = tcp
            self.max_lift = max(self.max_lift, float(cube[2] - self.retry.cube[2]))
            vs = self.verification_settings
            candidate = (np.linalg.norm(cube - tcp) <= vs.cube_tcp_tolerance_m
                         and vs.minimum_aperture_m <= qpos[-2:].sum() <= vs.maximum_aperture_m)
            self.candidate_steps = self.candidate_steps + 1 if candidate else 0
            self.missing_steps = 0 if candidate else self.missing_steps + 1
            phase = RETRY_PHASES[self.stage_index]
            if phase in ("transport", "lower", "hold") and self.missing_steps >= vs.failure_persistence_steps:
                self.abort("attachment_lost_during_retry")
                return
            timed_out = self.stage_steps >= getattr(self.settings, phase + "_steps")
            ready = False
            if phase == "close":
                ready = (self.stage_steps >= self.settings.minimum_close_steps
                         and self.candidate_steps >= vs.failure_persistence_steps)
                timeout_reason = "retry_grasp_not_established"
            elif phase == "hold":
                ready = timed_out
                timeout_reason = "retry_hold_not_completed"
            else:
                target = self.retract_target if phase == "retract" else self.retry.targets[phase]
                rotation_error = pose_rotation(tcp_pose) @ self.retry.grasp_rotation.T
                angle = float(np.arccos(np.clip((np.trace(rotation_error) - 1) / 2, -1, 1)))
                ready = (self.stage_steps >= self.settings.minimum_motion_steps
                         and np.linalg.norm(tcp - target) <= self.settings.arrival_tolerance_m
                         and angle <= self.settings.arrival_rotation_tolerance_rad)
                timeout_reason = "retry_" + phase + "_target_not_reached"
                if phase == "retract":
                    ready &= qpos[-2:].sum() >= vs.maximum_aperture_m
                if phase == "lift":
                    ready &= (self.candidate_steps >= vs.failure_persistence_steps
                              and self.max_lift >= TaskSettings().minimum_lift_m)
            if ready:
                if phase == "hold":
                    # Completion is not success. Shared final task scoring decides.
                    self.state = "attempt_complete"
                else:
                    self.stage_index += 1
                    self.stage_steps = 0
            elif timed_out:
                self.abort(timeout_reason)
            if self.state == "attempting" and self.steps >= self.action_budget:
                self.abort("remaining_action_budget_exhausted")
        except (KeyError, TypeError, ValueError):
            self.abort("invalid_recovery_observation")
