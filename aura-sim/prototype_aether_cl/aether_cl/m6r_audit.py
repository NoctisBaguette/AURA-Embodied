"""Reconstruct every M6R decision, verifier/reference state and terminal metric."""

from dataclasses import asdict
import math
from pathlib import Path

import numpy as np

from .acceptance import load_trial
from .runtime import json_value, scalar
from .policies import pose_rotation, vector
from .verification import VerificationMetrics, single_bool
from .m6_task import PlacementReference, PlacementVerifier, geometry, task_manifest
from .m6_policy import FixedPlacement, PlacementRecovery, INJECTION_STEP
from .m6r_runtime import UPSTREAM_SOURCE_MODULES, evaluation, summarize_episode, recovery_class, progress_record


PHYSICAL_FIELDS = ("step", "action", "observation", "info", "reward", "terminated", "truncated", "controller_decision", "reference", "total_observed_tcp_path_m")


def check_trial(directory, config, software=None):
    manifest, result, events = load_trial(directory)
    checks = {"config_and_task": manifest["config"] == json_value(asdict(config)) and manifest["task_contract"] == task_manifest(),
              "software": software is None or manifest["software"] == software,
              "complete_terminal": result["state"] == "finished" and len(result["episodes"]) == 1,
              "single_reset": False, "source_provenance": (set(manifest.get("upstream_sources_sha256", {})) == set(UPSTREAM_SOURCE_MODULES)
                    and all(isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)
                            for v in manifest.get("upstream_sources_sha256", {}).values())),
              "action_replay": True, "decision_replay": True, "reference_replay": True,
              "verifier_replay": True, "recovery_replay": True, "path_replay": True,
              "injection_provenance": True, "summary_replay": True}
    checks["m6r_identity"] = (manifest.get("schema_version") == 7 and manifest.get("purpose") == config.purpose
                              and result.get("purpose") == config.purpose and result.get("protocol") == "m6r")
    resets = [e for e in events if e["event"] == "reset"]
    checks["single_reset"] = len(resets) == 1 and resets[0]["seed"] == config.seed and resets[0]["episode"] == 0
    if not checks["single_reset"]:
        return finish(checks, result, 0., manifest)
    reset = resets[0]
    obs = reset["observation"]
    policy = FixedPlacement(obs, manifest["robot_base_pose"])
    reference = PlacementReference(obs)
    verifier = PlacementVerifier(obs) if config.verification else None
    recovery = recovery_class(config.system)(policy, manifest["robot_base_pose"], config.max_steps) if config.system in ("v2-old", "v2r") else None
    metrics = VerificationMetrics() if verifier else None
    checks["config_and_task"] &= (manifest["policy_details"] == policy.manifest() and manifest["system"] == config.system
        and manifest["verification"] == config.verification and manifest["recovery"] == (config.system in ("v2-old", "v2r"))
        and manifest["verifier"] == (verifier.manifest() if verifier else None)
        and manifest["recovery_controller"] == json_value(recovery.manifest() if recovery else None)
        and reset["eligibility"] == reference.eligibility
        and abs(vector(obs["extra"]["goal_pos"], 3, "goal_pos")[2] - .02) < 1e-7)
    support = manifest["support_geometry"]
    checks["support_geometry_and_goal_projection"] = (support["support_actor"] == "table-workspace"
            and support["cube_half_size_m"] == .02
            and np.allclose(support["table_pose_world"][:3], [-.12, 0, -.9196429], atol=1e-6, rtol=0)
            and np.allclose(pose_rotation(np.asarray(support["table_pose_world"])), [[0, -1, 0], [1, 0, 0], [0, 0, 1]], atol=1e-6, rtol=0)
            and np.allclose(support["original_sampled_goal_world_m"][:2], vector(obs["extra"]["goal_pos"], 3, "goal_pos")[:2], atol=1e-7, rtol=0)
            and support["goal_projection"] == "retain_sampled_xy_project_z_to_cube_center_on_table")
    steps = [e for e in events if e["event"] == "step"]
    excluded = not reference.eligibility["eligible"]
    checks["full_budget_and_step_sequence"] = [e["step"] for e in steps] == ([] if excluded else list(range(1, config.max_steps + 1)))
    checks["no_unassigned_steps"] = all(e["episode"] == 0 for e in steps)
    verdict = {"status": "waiting" if verifier else "disabled", "failure": None}
    truth = {}
    path = max_error = 0.
    previous_tcp = geometry(obs)["tcp"]
    nominal_complete = False
    progress = []
    injections = [e for e in events if e["event"] == "disturbance_attempted"]
    expected_count = int(not excluded and config.disturbance != "none")
    checks["injection_provenance"] &= len(injections) == expected_count
    injection = injections[0]["disturbance"] if len(injections) == 1 else None
    for e in steps:
        action, decision = recovery.action(obs, e["step"], verdict) if recovery else policy.action(obs, e["step"] - 1)
        recorded = np.asarray(e["action"], dtype=np.float64)
        expected = action[0] if manifest["action_space_shape"] == [7] else action
        error = float(np.max(np.abs(recorded - expected))) if recorded.shape == expected.shape else float("inf")
        max_error = max(max_error, error)
        checks["action_replay"] &= math.isfinite(error) and error <= 3e-7
        checks["decision_replay"] &= decision == e["controller_decision"]
        if e["step"] == INJECTION_STEP and injection is not None:
            g = geometry(obs)
            released = (not single_bool((reset["info"] if e["step"] == 1 else steps[e["step"] - 2]["info"])["is_grasped"], "is_grasped")
                        and g["released_geometry"] and g["supported_geometry"] and decision["phase"] == "retract")
            checks["injection_provenance"] &= (injection["release_precondition"] == released and injection["applied"] == released
                and injection["step"] == INJECTION_STEP and injection["name"] == "post_release_shift"
                and injection["magnitude_m"] == config.disturbance_magnitude and injection["axis"] == "world_y"
                and injection["timing"] == "after_action_computation_before_physics_step"
                and injection["implementation"] == "synthetic_lateral_pose_relocation_zero_velocities_not_force_disturbance")
            if released:
                before = vector(obs["extra"]["obj_pose"], 7, "obj_pose")
                after = before.copy(); after[1] += config.disturbance_magnitude
                checks["injection_provenance"] &= (injection["before_pose_world"] == before.tolist()
                    and injection["after_pose_world"] == after.tolist() and injection["velocities_zeroed"] is True)
            else:
                checks["injection_provenance"] &= injection.get("reason") == "release_precondition_not_satisfied"
            entry = injections[0]
            position = events.index(entry)
            checks["injection_provenance"] &= events[position + 1] is e
        obs = e["observation"]
        final = e["step"] == config.max_steps or bool(scalar(e["truncated"]))
        truth = reference.observe(obs, e["info"], e["step"], decision, final)
        checks["reference_replay"] &= truth == e["reference"]
        if verifier:
            verdict = verifier.observe(obs, e["step"], decision, final)
            metrics.observe(truth, verdict)
        checks["verifier_replay"] &= verdict == e["verification"]
        if recovery:
            recovery.observe(obs)
        progress.append(progress_record(e["step"], decision, recovery))
        checks["recovery_replay"] &= e["recovery"] == (recovery.snapshot() if recovery else {"state": "disabled"})
        tcp = geometry(obs)["tcp"]
        path += float(np.linalg.norm(tcp - previous_tcp)); previous_tcp = tcp
        checks["path_replay"] &= path == e["total_observed_tcp_path_m"]
        nominal_complete |= decision["phase"] == "settle" and decision["schedule_complete"]
    episode = result["episodes"][0]
    expected_summary = summarize_episode(config, reference, verifier, truth, verdict, recovery, len(steps), False, path,
                                         nominal_complete, injection, episode["seconds"], progress)
    summaries = [{k: v for k, v in e.items() if k not in ("event", "time_utc")} for e in events if e["event"] in ("episode_finished", "episode_excluded")]
    checks["summary_replay"] = expected_summary == episode and summaries == [episode]
    checks["evaluation_replay"] = result["evaluation"] == evaluation(config, episode, metrics, True)
    checks["final_result_log"] = [e["result"] for e in events if e["event"] == "run_finished"] == [result]
    checks["run_manifest_log"] = [e["manifest"] for e in events if e["event"] == "run_started"] == [manifest]
    checks["no_error_events"] = not any(e["event"] in ("run_failed", "cleanup_failed") for e in events)
    return finish(checks, result, max_error, manifest)


def finish(checks, result, max_error, manifest):
    return {"passed": all(checks.values()), "checks": checks, "failed_checks": [k for k, v in checks.items() if not v],
            "episodes": result["episodes"], "evaluation": result.get("evaluation"), "max_action_replay_error": max_error,
            "native_sources_sha256": manifest.get("upstream_sources_sha256")}


def lower_predicates(event, manifest, attempt_observation):
    """Independently inspect the two predicates on the same post-action state."""
    from .m6_policy import PlacementRecoverySettings, rotation_angle
    from .m6_task import SETTINGS
    g = geometry(event["observation"])
    decision = event["controller_decision"]
    target = np.asarray(decision["expected_tcp_position_world_m"])
    primitive = FixedPlacement(attempt_observation, manifest["robot_base_pose"]).primitive
    pose = vector(event["observation"]["extra"]["tcp_pose"], 7, "tcp_pose")
    angle = float(rotation_angle(pose_rotation(pose) @ primitive.grasp_rotation.T))
    settings = PlacementRecoverySettings()
    common = (decision["phase_step"] >= settings.minimum_motion_steps
              and np.linalg.norm(g["tcp"] - target) <= settings.arrival_tolerance_m
              and angle <= settings.arrival_rotation_tolerance_rad)
    return {"common_gates": bool(common), "rotation_error_rad": angle,
            "tcp_distance_m": float(np.linalg.norm(g["tcp"] - target)),
            "vertical_residual_m": float(abs(g["tcp"][2] - target[2])),
            "supported_geometry": g["supported_geometry"], "horizontal_error_m": g["horizontal_error_m"],
            "old_ready": bool(common and abs(g["tcp"][2] - target[2]) <= settings.lower_vertical_tolerance_m),
            "repair_ready": bool(common and g["supported_geometry"] and g["horizontal_error_m"] <= SETTINGS.horizontal_tolerance_m)}


def compare(left_directory, right_directory, kind):
    if kind not in ("passive", "recovery", "repair", "control"):
        raise ValueError("Unknown M6R comparison kind")
    lm, lr, le = load_trial(left_directory)
    rm, rr, re = load_trial(right_directory)
    a = [e for e in le if e["event"] == "step"]
    b = [e for e in re if e["event"] == "step"]
    checks = {"shared_software_policy_task_support": all(lm[k] == rm[k] for k in
              ("software", "policy_details", "task_contract", "support_geometry", "upstream_sources_sha256", "robot_base_pose", "action_space_shape")),
              "exact_reset_including_contact": [{k: e[k] for k in ("seed", "observation", "info", "eligibility")} for e in le if e["event"] == "reset"] ==
                  [{k: e[k] for k in ("seed", "observation", "info", "eligibility")} for e in re if e["event"] == "reset"]}
    divergence = predicates = None
    if kind == "control":
        prefix = INJECTION_STEP - 1
        checks["system_and_condition"] = lm["system"] == rm["system"] == "baseline" and lm["config"]["disturbance"] == "none" and rm["config"]["disturbance"] == "post_release_shift"
        checks["same_control_config"] = {k: v for k, v in lm["config"].items() if k not in ("disturbance", "disturbance_magnitude", "output")} == {k: v for k, v in rm["config"].items() if k not in ("disturbance", "disturbance_magnitude", "output")}
    else:
        trigger = rr["episodes"][0]["recovery"].get("trigger_step") if kind == "recovery" else None
        prefix = trigger if trigger is not None else len(b)
        checks["same_config_except_system"] = {k: v for k, v in lm["config"].items() if k not in ("system", "verification", "output")} == {k: v for k, v in rm["config"].items() if k not in ("system", "verification", "output")}
        checks["system_contract"] = (lm["system"], rm["system"]) == {"passive": ("baseline", "v1"), "recovery": ("v1", "v2-old"), "repair": ("v2-old", "v2r")}[kind]
    if kind == "repair":
        divergence = next((x["step"] for x, y in zip(a, b) if x["recovery"] != y["recovery"]), None)
        prefix = divergence if divergence is not None else len(b)
        checks["identical_verifier_and_trigger_before_divergence"] = (lr["episodes"][0]["recovery"].get("trigger_step") == rr["episodes"][0]["recovery"].get("trigger_step")
              and lr["episodes"][0]["recovery"].get("first_action_step") == rr["episodes"][0]["recovery"].get("first_action_step"))
        checks["exact_common_recovery_states"] = all(x["recovery"] == y["recovery"] for x, y in zip(a, b) if divergence is None or x["step"] < divergence)
        if divergence is not None:
            x, y = a[divergence - 1], b[divergence - 1]
            trigger = lr["episodes"][0]["recovery"].get("trigger_step")
            attempt_observation = a[trigger - 1]["observation"] if trigger else next(e["observation"] for e in le if e["event"] == "reset")
            predicates = lower_predicates(x, lm, attempt_observation)
            checks["first_difference_is_lower_transition"] = (x["controller_decision"]["phase"] == y["controller_decision"]["phase"] == "recovery_lower"
                and predicates["old_ready"] != predicates["repair_ready"]
                and (x["recovery"]["phase"] == "release") == predicates["old_ready"]
                and (y["recovery"]["phase"] == "release") == predicates["repair_ready"])
        else:
            checks["no_divergence_full_recovery_equality"] = len(a) == len(b) and all(x["recovery"] == y["recovery"] for x, y in zip(a, b))
    fields = (*PHYSICAL_FIELDS, "verification") if kind in ("recovery", "repair") else PHYSICAL_FIELDS
    aa = [e for e in a if e["step"] <= prefix]
    bb = [e for e in b if e["step"] <= prefix]
    checks["exact_physical_prefix"] = len(a) == len(b) and len(aa) == len(bb) and all(all(x[k] == y[k] for k in fields) for x, y in zip(aa, bb))
    if kind != "control":
        checks["exact_preintervention_injections"] = [e["disturbance"] for e in le if e["event"] == "disturbance_attempted" and e["step"] <= prefix] == [e["disturbance"] for e in re if e["event"] == "disturbance_attempted" and e["step"] <= prefix]
    return json_value({"passed": all(checks.values()), "checks": checks, "matched_steps": len(aa),
                       "first_lower_state_divergence_step": divergence,
                       "first_possible_action_divergence_step": divergence + 1 if divergence is not None else None,
                       "lower_predicates_at_divergence": predicates})
