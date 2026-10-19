"""Passive, privileged-state checks. No evaluator info or action selection."""

from dataclasses import asdict, dataclass

import numpy as np

from .policies import PickCubeSettings, vector


@dataclass(frozen=True)
class TaskSettings:
    goal_tolerance_m: float = 0.025
    minimum_lift_m: float = 0.05
    stable_steps: int = 5
    robot_static_threshold: float = 0.2


@dataclass(frozen=True)
class VerificationSettings:
    cube_tcp_tolerance_m: float = 0.04
    minimum_aperture_m: float = 0.01
    maximum_aperture_m: float = 0.06
    attachment_lift_m: float = 0.01
    failure_persistence_steps: int = 3


def initial_task(observation):
    extra = observation["extra"]
    cube = vector(extra["obj_pose"], 7, "obj_pose")[:3]
    goal = vector(extra["goal_pos"], 3, "goal_pos")
    distance = float(np.linalg.norm(cube - goal))
    eligible = distance > TaskSettings().goal_tolerance_m
    return cube, goal, {
        "eligible": eligible,
        "exclusion_reason": None if eligible else "initially_at_goal",
        "initial_cube_goal_distance_m": distance,
    }


def single_bool(value, name):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    array = np.asarray(value)
    if array.size != 1 or array.dtype != np.bool_:
        raise ValueError(f"{name} must be one boolean")
    return bool(array.reshape(-1)[0])


def checkpoint_steps():
    p = PickCubeSettings()
    close = p.approach_steps + p.descend_steps + p.close_steps
    return close, close + p.lift_steps, p.scheduled_steps


class TaskReference:
    """Shared task/reference evaluator using fresh simulator contact info.

    This reference never reaches the policy or verifier. It is a simulator
    agreement reference, not an independent perception benchmark.
    """

    def __init__(self, observation):
        self.cube, self.goal, self.eligibility = initial_task(observation)
        self.settings = TaskSettings()
        self.max_lift = 0.0
        self.ever_attached = False
        self.stable_count = 0
        self.first_failure = None
        self.last_step = 0

    def observe(self, observation, info, step, final=False):
        if step <= self.last_step:
            raise ValueError("Reference requires increasing post-action step numbers")
        if step != self.last_step + 1:
            self.stable_count = 0
        self.last_step = step
        extra = observation["extra"]
        cube = vector(extra["obj_pose"], 7, "obj_pose")[:3]
        goal = vector(extra["goal_pos"], 3, "goal_pos")
        grasped = single_bool(info["is_grasped"], "is_grasped")
        static = single_bool(info["is_robot_static"], "is_robot_static")
        self.max_lift = max(self.max_lift, float(cube[2] - self.cube[2]))
        distance = float(np.linalg.norm(cube - self.goal))
        self.ever_attached |= grasped and self.max_lift >= VerificationSettings().attachment_lift_m
        ready = (self.eligibility["eligible"] and grasped and static
                 and self.max_lift >= self.settings.minimum_lift_m
                 and distance <= self.settings.goal_tolerance_m
                 and np.linalg.norm(goal - self.goal) <= 1e-6)
        self.stable_count = self.stable_count + 1 if ready else 0
        success = self.stable_count >= self.settings.stable_steps
        close, lift, target = checkpoint_steps()
        failure = None
        if np.linalg.norm(goal - self.goal) > 1e-6:
            failure = "STATE_MISMATCH"
        elif self.ever_attached and not grasped:
            failure = "OBJECT_LOST"
        elif step >= close and not grasped:
            failure = "GRASP_FAILURE"
        elif step >= lift and self.max_lift < self.settings.minimum_lift_m:
            failure = "STATE_MISMATCH"
        elif step >= target and distance > self.settings.goal_tolerance_m:
            failure = "TARGET_NOT_REACHED"
        elif final and not success:
            failure = "STATE_MISMATCH"
        if failure and self.first_failure is None:
            self.first_failure = {"step": step, "failure": failure}
        return {"task_success": success, "failure": failure,
                "max_cube_lift_m": self.max_lift, "stable_steps": self.stable_count,
                "cube_goal_distance_m": distance, "is_grasped": grasped,
                "is_robot_static": static}


class StateVerifier:
    """Compare expected grasp/lift/goal outcomes with geometry and joint state.

    Reset grasp flags, extra.is_grasped, info.success, contact flags, reference
    labels, and disturbance identities are intentionally not inputs. Small
    per-episode counters are temporal checks, not experience memory.
    """

    def __init__(self, observation):
        self.cube, self.goal, self.eligibility = initial_task(observation)
        self.task = TaskSettings()
        self.settings = VerificationSettings()
        self.last_step = 0
        self.max_lift = 0.0
        self.attachment_count = 0
        self.ever_attached = False
        self.stable_count = 0
        self.failure_count = 0
        self.previous_failure = None
        self.first_failure = None

    def manifest(self):
        return {"name": "geometric_state_verifier", "version": "0.1",
                "task": asdict(self.task), "settings": asdict(self.settings),
                "inputs": ["obj_pose", "goal_pos", "tcp_pose", "qpos", "qvel", "post_action_step"],
                "excluded_inputs": ["reset_grasp_flags", "is_grasped", "info", "disturbance", "reference"],
                "confidence": "not_calibrated", "changes_actions": False}

    def observe(self, observation, step, final=False):
        if step <= self.last_step:
            return self._uncertain("stale_or_repeated_step")
        if step != self.last_step + 1:
            self.stable_count = self.attachment_count = self.failure_count = 0
            self.previous_failure = None
        # Mark the step consumed even if its sensors are invalid; a later fresh
        # observation can resume checking without accepting a duplicate frame.
        self.last_step = step
        try:
            extra = observation["extra"]
            cube = vector(extra["obj_pose"], 7, "obj_pose")[:3]
            goal = vector(extra["goal_pos"], 3, "goal_pos")
            tcp = vector(extra["tcp_pose"], 7, "tcp_pose")[:3]
            qpos = vector(observation["agent"]["qpos"], 9, "qpos")
            qvel = vector(observation["agent"]["qvel"], 9, "qvel")
        except (KeyError, ValueError, TypeError) as error:
            return self._uncertain(str(error))
        self.max_lift = max(self.max_lift, float(cube[2] - self.cube[2]))
        gap = float(np.linalg.norm(cube - tcp))
        aperture = float(qpos[-2:].sum())
        close, lift, target = checkpoint_steps()
        candidate = (step >= PickCubeSettings().approach_steps + PickCubeSettings().descend_steps
                     and gap <= self.settings.cube_tcp_tolerance_m
                     and self.settings.minimum_aperture_m <= aperture <= self.settings.maximum_aperture_m)
        self.attachment_count = self.attachment_count + 1 if candidate else 0
        self.ever_attached |= (self.attachment_count >= self.settings.failure_persistence_steps
                               and self.max_lift >= self.settings.attachment_lift_m)
        distance = float(np.linalg.norm(cube - self.goal))
        static = bool(np.max(np.abs(qvel[:7])) <= self.task.robot_static_threshold)
        ready = (self.eligibility["eligible"] and candidate and self.ever_attached
                 and self.max_lift >= self.task.minimum_lift_m and static
                 and distance <= self.task.goal_tolerance_m
                 and np.linalg.norm(goal - self.goal) <= 1e-6)
        self.stable_count = self.stable_count + 1 if ready else 0
        success = self.stable_count >= self.task.stable_steps
        failure = None
        if np.linalg.norm(goal - self.goal) > 1e-6:
            failure = "STATE_MISMATCH"
        elif self.ever_attached and not candidate:
            failure = "OBJECT_LOST"
        elif step >= close and not candidate:
            failure = "GRASP_FAILURE"
        elif step >= lift and self.max_lift < self.task.minimum_lift_m:
            failure = "STATE_MISMATCH"
        elif step >= target and distance > self.task.goal_tolerance_m:
            failure = "TARGET_NOT_REACHED"
        elif final and not success:
            failure = "STATE_MISMATCH"
        self.failure_count = self.failure_count + 1 if failure and failure == self.previous_failure else int(failure is not None)
        self.previous_failure = failure
        confirmed_failure = failure if self.failure_count >= self.settings.failure_persistence_steps or final else None
        if confirmed_failure and self.first_failure is None:
            self.first_failure = {"step": step, "failure": confirmed_failure}
        expected = ("grasp_and_goal_stability" if step >= target else
                    "grasp_and_lift" if step >= close else "approach_and_close")
        return {"status": "failed" if confirmed_failure else "passed" if success else "pending",
                "success": success, "failure": confirmed_failure, "confidence": None,
                "expected_outcome": expected, "evidence": {
                    "cube_tcp_distance_m": gap, "gripper_aperture_m": aperture,
                    "max_cube_lift_m": self.max_lift, "cube_goal_distance_m": distance,
                    "robot_static": static, "stable_steps": self.stable_count,
                    "failure_persistence_steps": self.failure_count}}

    def _uncertain(self, reason):
        self.stable_count = self.attachment_count = self.failure_count = 0
        self.previous_failure = None
        return {"status": "uncertain", "success": False, "failure": "UNCERTAIN",
                "confidence": None, "reason": reason}


class VerificationMetrics:
    """Explicit agreement counts against the separate simulator reference."""

    def __init__(self):
        self.steps = self.uncertain = self.tp = self.fp = self.fn = self.tn = 0
        self.uncertain_on_negative = 0
        self.correct_diagnoses = 0
        self.confusion = {}

    def observe(self, reference, verdict):
        truth = reference["failure"]
        prediction = verdict["failure"]
        self.steps += 1
        self.uncertain += prediction == "UNCERTAIN"
        predicted_failure = prediction is not None and prediction != "UNCERTAIN"
        if truth:
            if predicted_failure:
                self.tp += 1
                self.correct_diagnoses += truth == prediction
            else:
                self.fn += 1
        elif predicted_failure:
            self.fp += 1
        elif prediction == "UNCERTAIN":
            self.uncertain_on_negative += 1
        else:
            self.tn += 1
        key = (truth or "NONE") + "->" + (prediction or "NONE")
        self.confusion[key] = self.confusion.get(key, 0) + 1

    def result(self, complete):
        def rate(numerator, denominator):
            return numerator / denominator if complete and denominator else None
        return {"scope": "privileged_state_simulator_reference_agreement",
                "complete": complete, "steps": self.steps, "uncertain_steps": self.uncertain,
                "true_positive": self.tp, "false_positive": self.fp,
                "false_negative": self.fn, "true_negative": self.tn,
                "uncertain_on_negative": self.uncertain_on_negative,
                "failure_detection_precision": rate(self.tp, self.tp + self.fp),
                "failure_detection_recall": rate(self.tp, self.tp + self.fn),
                "diagnosis_accuracy_when_failure_detected": rate(self.correct_diagnoses, self.tp),
                "observation_coverage": rate(self.steps - self.uncertain, self.steps),
                "confusion": self.confusion}
