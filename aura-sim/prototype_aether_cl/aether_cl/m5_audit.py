"""M5 strict invocation/capability checks; performance is not an acceptance gate."""

from dataclasses import asdict
import numpy as np

from .acceptance import STEP_FIELDS, load_trial
from .m3_isolated_screening import check_episode
from .m5_scheduled import ScheduledRecoveryController, FIRST_ACTION
from .policies import FixedPickCube
from .recovery import RecoveryController
from .runtime import json_value


CAPABILITY_FIELDS = ("settings", "attempt_action_budget", "ground_truth_inputs",
                     "nominal_policy_changed", "retry_targets", "retry_motion_primitives",
                     "transport_gate", "failure_action")


def check_trial(directory, config, software):
    checked = check_episode(directory, config)
    manifest, result, events = load_trial(directory)
    checks = checked["checks"]
    checks["suite_software_matches"] = manifest["software"] == software
    checks["declared_system_matches"] = (manifest["system"] == config.system
        and manifest["verification"] == config.verification
        and manifest["recovery"] == (config.system in ("v2", "v3")))
    checks["actions_and_controller_replay"] = True
    checks["scheduled_contract"] = True
    maximum = 0.0
    for episode in checked["episodes"]:
        reset = next(e for e in events if e["event"] == "reset" and e["episode"] == episode["episode"])
        steps = [e for e in events if e["event"] == "step" and e["episode"] == episode["episode"]]
        # Original frozen M3 does not log base pose: Panda calibration is fixed.
        base = manifest.get("robot_base_pose", np.array([-.615, 0, 0, 1, 0, 0, 0], dtype=np.float32))
        observation = reset["observation"]
        policy = FixedPickCube(observation, base)
        controller = (ScheduledRecoveryController(policy, base, 360, config.family) if config.system == "v3"
                      else RecoveryController(policy, base, 360) if config.system == "v2" else None)
        if controller:
            checks["actions_and_controller_replay"] &= manifest["recovery_controller"] == controller.manifest()
        verdict = {"status": "waiting_for_post_action_observation", "failure": None, "confidence": None}
        for e in steps:
            if config.system == "v3":
                action, decision = controller.action(observation, e["step"])
                checks["scheduled_contract"] &= e["verification"] == {"status": "disabled", "failure": None}
            elif controller:
                action, decision = controller.action(observation, e["step"], verdict)
            else:
                action, decision = policy.action(observation, e["step"] - 1)
            error = float(np.max(np.abs(action.reshape(-1) - np.asarray(e["action"]).reshape(-1))))
            maximum = max(maximum, error)
            checks["actions_and_controller_replay"] &= error < 3e-7 and decision == e["controller_decision"]
            observation = e["observation"]
            verdict = e["verification"]
            if controller:
                controller.observe(observation)
                checks["actions_and_controller_replay"] &= controller.snapshot() == e["recovery"]
        if controller and not episode["excluded"]:
            checks["actions_and_controller_replay"] &= episode["recovery"] == controller.snapshot()
        if config.system == "v3":
            checks["scheduled_contract"] &= (manifest["config"] == json_value(asdict(config))
                and "verifier" not in manifest and result["evaluation"]["verification_metrics"] is None
                and episode.get("first_detected_failure") is None)
            if not episode["excluded"]:
                r = episode["recovery"]
                checks["scheduled_contract"] &= (r["reason"] == "SCHEDULED" and r["attempts"] == 1
                    and r["trigger_step"] == FIRST_ACTION[config.family] - 1
                    and r["first_action_step"] == FIRST_ACTION[config.family]
                    and r["action_budget"] == min(230, 361 - FIRST_ACTION[config.family])
                    and r["state"] in ("attempt_complete", "aborted")
                    and episode["recovery_task_success"] == episode["task_success_at_end"])
                rm = result["evaluation"].get("recovery_metrics", {})
                checks["scheduled_contract"] &= (rm.get("attempted_episodes") == 1
                    and rm.get("detected_failure_episodes") == 0
                    and rm.get("recovery_successes") == int(episode["task_success_at_end"])
                    and rm.get("aborted_attempts") == int(r["state"] == "aborted")
                    and rm.get("mean_attempt_action_steps") == r["action_steps"]
                    and rm.get("mean_attempt_observed_tcp_path_m") == r["observed_tcp_path_m"])
            else:
                checks["scheduled_contract"] &= not steps and reset["eligibility"]["eligible"] is False
    checked.update(passed=all(checks.values()), failed_checks=[k for k,v in checks.items() if not v],
                   max_action_replay_error=maximum)
    return checked


def compare_scheduled(left_directory, right_directory, attribution=False):
    left, lr, le = load_trial(left_directory)
    right, rr, re = load_trial(right_directory)
    a = [e for e in le if e["event"] == "step"]
    b = [e for e in re if e["event"] == "step"]
    reset_a = [{k:e[k] for k in ("seed", "observation", "eligibility")} for e in le if e["event"] == "reset"]
    reset_b = [{k:e[k] for k in ("seed", "observation", "eligibility")} for e in re if e["event"] == "reset"]
    schedule = FIRST_ACTION[right["config"]["family"]] - 1
    left_trigger = lr["episodes"][0].get("recovery", {}).get("trigger_step")
    prefix = min(schedule, left_trigger if left_trigger is not None else 360) if attribution else schedule
    checks = {"shared_software_policy_task_disturbance": all(left.get(k)==right.get(k)
              for k in ("software", "policy_details", "task_contract", "disturbance")),
              "full_reset_equal": reset_a == reset_b,
              "same_exclusion": lr["episodes"][0]["excluded"] == rr["episodes"][0]["excluded"],
              "physical_causal_prefix": len(a)==len(b) and all(all(x[k]==y[k] for k in STEP_FIELDS)
                 for x,y in zip(a[:prefix], b[:prefix])),
              "same_preintervention_injection": [{k:e[k] for k in ("step", "disturbance")} for e in le
                 if e["event"]=="disturbance_applied" and e["step"]<=prefix] ==
                 [{k:e[k] for k in ("step", "disturbance")} for e in re
                 if e["event"]=="disturbance_applied" and e["step"]<=prefix]}
    if attribution:
        checks["same_recovery_capability"] = all(left["recovery_controller"].get(k)==right["recovery_controller"].get(k)
                                                  for k in CAPABILITY_FIELDS)
        checks["aligned_trigger_full_physical_trace"] = (left_trigger != schedule
            or all(all(x[k]==y[k] for k in STEP_FIELDS) for x,y in zip(a,b)))
    return {"passed": all(checks.values()), "checks": checks, "matched_steps": min(prefix,len(a)),
            "v2_trigger_step": left_trigger if attribution else None,
            "scheduled_trigger_step": schedule, "aligned_triggers": attribution and left_trigger==schedule}
