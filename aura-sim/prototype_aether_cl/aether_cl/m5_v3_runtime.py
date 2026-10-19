"""V3-only execution; scoring and physics mirror the frozen M3 runtime.

Baseline/V1/V2 continue to execute the original M3 runner, never this module.
Only controller construction/invocation and explicitly marked metadata differ.
"""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from typing import Callable
from uuid import uuid4

from .runtime import (RunConfig, build_env, encode_frame, fixed_action_for_space,
                      json_value, scalar, software_manifest)
from .m5_scheduled import ScheduledRecoveryController, FIRST_ACTION


@dataclass(frozen=True)
class V3Config(RunConfig):
    controller: str = "fixed_pick_cube"
    protocol: str = "m3"
    max_steps: int = 360
    verification: bool = False
    system: str = "v3"
    render: bool = False
    family: str = "shift"

    @property
    def purpose(self):
        return "m5_scheduled_recovery_control"

    def validate(self):
        RunConfig.validate(replace(self, protocol="m2"))
        if (self.protocol != "m3" or self.system != "v3" or self.verification
                or self.max_steps != 360 or self.episodes != 1
                or self.controller != "fixed_pick_cube" or self.family not in FIRST_ACTION):
            raise ValueError("V3 requires one fixed-policy episode, no verifier, 360 actions and a frozen family")
        expected = "object_shift" if self.family == "shift" else "object_drop"
        if self.disturbance not in ("none", expected):
            raise ValueError("V3 disturbance and attribution family disagree")


def run(config: V3Config, publish: Callable | None = None,
        stop: threading.Event | None = None, env_factory=build_env,
        disturbance_fn=None):
    config.validate()
    stop = stop if stop is not None else threading.Event()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = config.output / f"{stamp}-{uuid4().hex[:8]}"
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": 4, "purpose": config.purpose,
        "config": json_value(asdict(config)), "software": software_manifest(),
        "physics_backend": "cpu", "observation_mode": "state_dict",
        "control_mode": config.control_mode,
        "policy": "fixed_pick_cube" if config.controller == "fixed_pick_cube" else "seeded_random_actions",
        "verification": config.verification, "recovery": config.system == "v3",
        "protocol": config.protocol, "system": config.system,
    }
    metrics = None
    if config.protocol == "m3":
        from .disturbances import apply_disturbance, disturbance_spec
        from .verification import TaskReference, TaskSettings
        disturbance_fn = disturbance_fn or apply_disturbance
        metrics = None
        manifest["disturbance"] = disturbance_spec(config.disturbance, config.disturbance_magnitude)
        manifest["task_contract"] = {**asdict(TaskSettings()),
            "reset_eligibility": "initial_cube_goal_distance_above_goal_tolerance",
            "requires_fresh_contact_grasp": True,
            "termination": "full_action_budget_or_time_limit",
            "release_required": False,
            "interpretation": "held_cube_target_stability_after_lift"}
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    env = None
    result = {"state": "starting", "run_directory": str(directory),
              "purpose": manifest["purpose"], "controller": config.controller,
              "protocol": config.protocol, "verification_enabled": config.verification,
              "system": config.system, "recovery_enabled": config.system == "v3",
              "disturbance": config.disturbance,
              "episodes": []}
    with (directory / "events.jsonl").open("w", encoding="utf-8", buffering=1) as log:
        def event(kind, **fields):
            record = {"event": kind, "time_utc": datetime.now(timezone.utc).isoformat(),
                      **json_value(fields)}
            log.write(json.dumps(record, allow_nan=False) + "\n")

        def update(**fields):
            result.update(fields)
            if publish:
                publish(json_value(result), None)

        def capture():
            if config.render:
                jpeg = encode_frame(env.render())
                (directory / "latest.jpg").write_bytes(jpeg)
                if publish:
                    publish(json_value(result), jpeg)

        try:
            event("run_started", manifest=manifest)
            update(state="initializing")
            env = env_factory(config)
            backend = getattr(env.unwrapped, "backend", None)
            event("environment_created", render_device=str(
                getattr(backend, "render_device", "unknown")))
            for episode in range(config.episodes):
                if stop.is_set():
                    break
                seed = config.seed + episode
                observation, info = env.reset(seed=seed)
                env.action_space.seed(seed)
                policy = None
                diagnostics = {}
                decision = {"phase": "random", "schedule_complete": False}
                reference = verifier = recovery = None
                reference_state = {}
                verification_state = {"status": "disabled", "failure": None}
                eligibility = {"eligible": True, "exclusion_reason": None}
                disturbance_record = None
                if config.controller == "fixed_pick_cube":
                    from .policies import FixedPickCube, task_diagnostics
                    policy = FixedPickCube(observation, env.unwrapped.agent.robot.pose.raw_pose)
                    if env.action_space.shape not in ((7,), (1, 7)):
                        raise RuntimeError(f"Unexpected Panda pd_ee_pose action shape: {env.action_space.shape}")
                    diagnostics = task_diagnostics(observation, info)
                    manifest["policy_details"] = policy.manifest()
                    manifest["action_space_shape"] = list(env.action_space.shape)
                    if config.system == "v3":
                        recovery = ScheduledRecoveryController(policy, env.unwrapped.agent.robot.pose.raw_pose, config.max_steps, config.family)
                        manifest["recovery_controller"] = recovery.manifest()
                        manifest["robot_base_pose"] = json_value(env.unwrapped.agent.robot.pose.raw_pose)
                    if config.protocol == "m3":
                        reference = TaskReference(observation)
                        eligibility = reference.eligibility
                        if not eligibility["eligible"]:
                            verification_state = {"status": "excluded", "failure": None,
                                                  "reason": eligibility["exclusion_reason"]}
                    (directory / "manifest.json").write_text(
                        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8",
                    )
                    event("controller_reset", episode=episode, policy=policy.manifest(),
                          initial_cube_position_world_m=policy.cube.tolist(),
                          initial_goal_position_world_m=policy.goal.tolist())
                event("reset", episode=episode, seed=seed,
                      observation=observation, info=info, eligibility=eligibility)
                update(state="running", episode=episode, step=0,
                       phase="approach" if policy else "random",
                       success=bool(scalar(info.get("success", False))),
                       eligibility=eligibility, task_success=False,
                       verification=verification_state, disturbance_applied=False,
                       reference={}, recovery=recovery.snapshot() if recovery else {"state": "disabled"}, **diagnostics)
                capture()
                if config.protocol == "m3" and not eligibility["eligible"]:
                    summary = {"episode": episode, "seed": seed, "steps": 0,
                               "excluded": True, "exclusion_reason": eligibility["exclusion_reason"],
                               "success_at_end": result["success"], "success_ever": result["success"],
                               "task_success_at_end": False, "stopped": False,
                               "seconds": 0.0, "disturbance_applied": False}
                    result["episodes"].append(summary)
                    event("episode_excluded", **summary)
                    continue
                success_ever = result["success"]
                terminated = truncated = False
                steps = 0
                start = time.monotonic()
                for step in range(1, config.max_steps + 1):
                    if stop.is_set():
                        break
                    tick = time.monotonic()
                    if policy:
                        before = recovery.snapshot() if recovery else None
                        action, decision = (recovery.action(observation, step) if recovery
                                            else policy.action(observation, step - 1))
                        if recovery and (before["state"], before["phase"]) != (recovery.state, recovery.snapshot()["phase"]):
                            event("recovery_transition", episode=episode, step=step, timing="before_action",
                                  recovery=recovery.snapshot())
                        action = fixed_action_for_space(action, env.action_space)
                    else:
                        action = env.action_space.sample()
                    logged_action = json_value(action)
                    if reference is not None:
                        record = disturbance_fn(env, config.disturbance, step,
                                                reference.cube, config.disturbance_magnitude)
                        if record is not None:
                            if disturbance_record is not None:
                                raise RuntimeError("Disturbance was applied more than once")
                            disturbance_record = record
                            event("disturbance_applied", episode=episode, step=step, disturbance=record)
                    observation, reward, term, trunc, info = env.step(action)
                    terminated, truncated = bool(scalar(term)), bool(scalar(trunc))
                    success = bool(scalar(info.get("success", False)))
                    success_ever = success_ever or success
                    steps = step
                    if policy:
                        diagnostics = task_diagnostics(observation, info)
                    if reference is not None:
                        final = step == config.max_steps or truncated
                        reference_state = reference.observe(observation, info, step, final=final)
                    if recovery:
                        before = recovery.snapshot()
                        recovery.observe(observation)
                        after = recovery.snapshot()
                        if (before["state"], before["phase"]) != (after["state"], after["phase"]):
                            event("recovery_transition", episode=episode, step=step, timing="after_observation",
                                  recovery=after)
                    event("step", episode=episode, step=step, action=logged_action,
                          observation=observation, reward=reward,
                          terminated=terminated, truncated=truncated, info=info,
                          controller_decision=decision, evaluator=diagnostics,
                          reference=reference_state, verification=verification_state,
                          recovery=recovery.snapshot() if recovery else {"state": "disabled"})
                    update(step=step, success=success, phase=decision["phase"],
                           task_success=reference_state.get("task_success", False),
                           reference=reference_state, verification=verification_state,
                           recovery=recovery.snapshot() if recovery else {"state": "disabled"},
                           disturbance_applied=disturbance_record is not None, **diagnostics)
                    capture()
                    if truncated or (terminated and config.protocol == "m1"):
                        break
                    if publish:
                        stop.wait(max(0, 1 / config.fps - (time.monotonic() - tick)))
                summary = {
                    "episode": episode, "seed": seed, "steps": steps,
                    "success_at_end": result["success"], "success_ever": success_ever,
                    "terminated": terminated, "truncated": truncated,
                    "stopped": stop.is_set(), "seconds": time.monotonic() - start,
                }
                if policy:
                    summary.update(final_phase=decision["phase"],
                                   schedule_complete=decision["schedule_complete"],
                                   final_cube_goal_distance_m=diagnostics["cube_goal_distance_m"],
                                   final_is_grasped=bool(scalar(info.get("is_grasped", False))),
                                   final_is_obj_placed=bool(scalar(info.get("is_obj_placed", False))),
                                   final_is_robot_static=bool(scalar(info.get("is_robot_static", False))))
                if reference is not None:
                    detected = verifier.first_failure if verifier else None
                    truth = reference.first_failure
                    latency = None
                    if (detected and truth and detected["failure"] == truth["failure"]
                            and detected["step"] >= truth["step"]):
                        latency = detected["step"] - truth["step"]
                    summary.update(excluded=False, task_success_at_end=reference_state.get("task_success", False),
                                   first_reference_failure=truth, first_detected_failure=detected,
                                   first_failure_latency_steps=latency,
                                   final_verification=verification_state,
                                   max_cube_lift_m=reference_state.get("max_cube_lift_m", 0.0),
                                   disturbance_applied=disturbance_record is not None)
                if recovery:
                    summary["recovery"] = recovery.snapshot()
                    summary["recovery_task_success"] = bool(recovery.attempts and summary["task_success_at_end"])
                result["episodes"].append(summary)
                event("episode_finished", **summary)
            update(state="stopped" if stop.is_set() else "finished")
            if config.controller == "fixed_pick_cube":
                complete = result["state"] == "finished" and len(result["episodes"]) == config.episodes
                evaluation = {
                    "requested_episodes": config.episodes,
                    "recorded_episodes": len(result["episodes"]),
                    "completed_episodes": sum(not e["stopped"] for e in result["episodes"]),
                    "complete": complete,
                    "success_rate_at_end": (sum(e["success_at_end"] for e in result["episodes"]) / config.episodes) if complete else None,
                    "success_rate_ever": (sum(e["success_ever"] for e in result["episodes"]) / config.episodes) if complete else None,
                    "verification": config.verification, "recovery": config.system == "v3",
                    "input_source": "privileged_simulator_state",
                }
                if config.protocol == "m3":
                    eligible = [e for e in result["episodes"] if not e["excluded"]]
                    evaluation.update(
                        protocol="m3", system=config.system, eligible_episodes=len(eligible),
                        excluded_episodes=len(result["episodes"]) - len(eligible),
                        task_success_rate_at_end=(sum(e["task_success_at_end"] for e in eligible) / len(eligible))
                            if complete and eligible else None,
                        environment_success_rate_eligible=(sum(e["success_at_end"] for e in eligible) / len(eligible))
                            if complete and eligible else None,
                        verification_metrics=metrics.result(complete) if metrics else None)
                    # An excluded reset is recorded but is not an executed,
                    # completed manipulation episode.
                    evaluation["completed_episodes"] = sum(not e["stopped"] for e in eligible)
                if config.system == "v3":
                    attempted = [e for e in eligible if e["recovery"]["attempts"]]
                    evaluation["recovery_metrics"] = {
                        "scope": "final_shared_task_success_after_one_attempt",
                        "complete": complete, "attempted_episodes": len(attempted),
                        "detected_failure_episodes": sum(e["first_detected_failure"] is not None for e in eligible),
                        "aborted_attempts": sum(e["recovery"]["state"] == "aborted" for e in attempted),
                        "recovery_successes": sum(e["recovery_task_success"] for e in attempted),
                        "recovery_success_rate": sum(e["recovery_task_success"] for e in attempted) / len(attempted)
                            if complete and attempted else None,
                        "mean_attempt_action_steps": sum(e["recovery"]["action_steps"] for e in attempted) / len(attempted)
                            if complete and attempted else None,
                        "mean_attempt_observed_tcp_path_m": sum(e["recovery"]["observed_tcp_path_m"] for e in attempted) / len(attempted)
                            if complete and attempted else None,
                    }
                update(evaluation=evaluation)
            event("run_finished", result=result)
        except BaseException as error:
            update(state="error", error=f"{type(error).__name__}: {error}")
            event("run_failed", error=result["error"])
            raise
        finally:
            try:
                if env is not None:
                    env.close()
            except BaseException as error:
                update(state="error", error=f"Environment cleanup failed: {type(error).__name__}: {error}")
                event("cleanup_failed", error=result["error"])
                raise
            finally:
                (directory / "result.json").write_text(
                    json.dumps(result, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8",
                )
    return result
