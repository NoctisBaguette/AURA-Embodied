"""M5 invocation ablation: no verifier input; unchanged retry execution."""

from .policies import FixedPickCube, vector
from .recovery import RecoveryController


FIRST_ACTION = {"shift": 128, "drop": 184}


class ScheduledRecoveryController(RecoveryController):
    """Replace only invocation; inherited action primitives/observe stay frozen.

    Family is preregistered experiment metadata, including normal controls.
    No failure verdict, magnitude, evaluator/contact label or disturbance event
    is accepted by this controller. Local retry feedback remains unchanged.
    """

    def __init__(self, policy, base_pose, max_steps, family):
        super().__init__(policy, base_pose, max_steps)
        if family not in FIRST_ACTION or max_steps != 360:
            raise ValueError("Scheduled recovery requires shift/drop family and 360 actions")
        self.family = family
        self.first_scheduled_action = FIRST_ACTION[family]

    def manifest(self):
        return {**super().manifest(), "version": "m5-scheduled-v0.1",
                "supported_failures": [], "trigger": "preregistered_clock_only",
                "family": self.family, "first_scheduled_action": self.first_scheduled_action,
                "inputs": ["step", "obj_pose", "goal_pos", "tcp_pose", "qpos"],
                "verifier_inputs": False, "magnitude_inputs": False,
                "retry_feedback": "unchanged_inherited_attachment_arrival_and_budget_checks"}

    def action(self, observation, step):
        if self.state == "nominal" and step == self.first_scheduled_action:
            # Same startup as frozen V2 after its gate. SCHEDULED is metadata,
            # not a fabricated diagnosis; the superclass never receives a verdict.
            self.reason = "SCHEDULED"
            self.trigger_step = step - 1
            if self.max_steps - step + 1 < self.settings.minimum_remaining_steps:
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
        return super().action(observation, step, {})
