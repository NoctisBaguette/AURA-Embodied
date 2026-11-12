"""Isolated M6 placement runs with full-budget logs and separate contact scoring."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import threading
import time
from uuid import uuid4

import numpy as np

from .runtime import RunConfig, build_env, encode_frame, fixed_action_for_space, json_value, scalar, software_manifest
from .policies import pose_rotation, vector
from .verification import VerificationMetrics, single_bool
from .m6_task import SETTINGS, PlacementReference, PlacementVerifier, geometry, task_manifest
from .m6_policy import FixedPlacement, PlacementRecovery, INJECTION_STEP, MAX_STEPS


@dataclass(frozen=True)
class M6Config(RunConfig):
    controller: str = "fixed_pick_cube"
    protocol: str = "m6"
    system: str = "v2"
    verification: bool = True
    episodes: int = 1
    max_steps: int = MAX_STEPS
    render: bool = False
    render_device: str = "cuda:0"
    disturbance: str = "none"
    disturbance_magnitude: float = .08

    def validate(self):
        if (self.env_id != "PickCube-v1" or self.controller != "fixed_pick_cube" or self.protocol != "m6"
                or self.system not in ("baseline", "v1", "v2") or self.verification != (self.system != "baseline")
                or self.episodes != 1 or self.max_steps != MAX_STEPS):
            raise ValueError("M6 requires the frozen single-episode Panda placement configuration")
        if not 0 <= self.seed < 2**32 or not 0 < self.fps <= 60:
            raise ValueError("Invalid seed or FPS")
        if self.disturbance not in ("none", "post_release_shift") or self.disturbance_magnitude not in (.01, .04, .08, .12, .20):
            raise ValueError("M6 disturbance must use a frozen magnitude")

    @property
    def purpose(self):
        return "m6_support_placement_" + self.system


UPSTREAM_SOURCE_MODULES = ("mani_skill.envs.tasks.tabletop.pick_cube", "mani_skill.utils.scene_builder.table.scene_builder",
                         "mani_skill.envs.scene", "mani_skill.utils.structs.actor", "mani_skill.agents.robots.panda.panda")


def upstream_sources():
    result = {}
    for name in UPSTREAM_SOURCE_MODULES:
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            raise RuntimeError("Required native source is unavailable: " + name)
        result[name] = hashlib.sha256(Path(spec.origin).read_bytes()).hexdigest()
    return result


def observe_native(env, observation, info):
    base = env.unwrapped
    extra = dict(observation["extra"])
    extra["goal_pos"] = base.goal_site.pose.p
    extra["obj_to_goal_pos"] = base.goal_site.pose.p - base.cube.pose.p
    extra["obj_linear_velocity"] = base.cube.linear_velocity
    extra["obj_angular_velocity"] = base.cube.angular_velocity
    return {**observation, "extra": extra}, {**info,
        "cube_table_contact_force_world_n": base.scene.get_pairwise_contact_forces(base.cube, base.table_scene.table)}


def reset_native(env, seed, pose_factory=None):
    observation, info = env.reset(seed=seed)
    base = env.unwrapped
    if bool(getattr(base, "gpu_sim_enabled", False)):
        raise RuntimeError("M6 supports CPU physics only")
    if abs(float(base.cube_half_size) - SETTINGS.cube_half_size_m) > 1e-7:
        raise RuntimeError("Unexpected native cube geometry")
    table_pose = vector(base.table_scene.table.pose.raw_pose, 7, "table_pose")
    if not np.allclose(table_pose[:3], [-.12, 0, -.9196429], atol=1e-6, rtol=0):
        raise RuntimeError("Designated table pose differs from ManiSkill 3.0.1 geometry")
    if not np.allclose(pose_rotation(table_pose), [[0, -1, 0], [1, 0, 0], [0, 0, 1]], atol=1e-6, rtol=0):
        raise RuntimeError("Designated table orientation differs from ManiSkill 3.0.1 geometry")
    if pose_factory is None:
        from mani_skill.utils.structs.pose import Pose
        pose_factory = Pose.create_from_pq
    goal = vector(base.goal_site.pose.p, 3, "goal_pos")
    original_goal = goal.copy()
    goal[2] = SETTINGS.support_height_m + SETTINGS.cube_half_size_m
    base.goal_site.set_pose(pose_factory(p=goal, device=base.device))
    info = {**info, **base.evaluate()}
    observation, info = observe_native(env, observation, info)
    return observation, info, {"support_actor": base.table_scene.table.name,
                               "table_pose_world": table_pose.tolist(), "cube_half_size_m": float(base.cube_half_size),
                               "original_sampled_goal_world_m": original_goal.tolist(),
                               "goal_projection": "retain_sampled_xy_project_z_to_cube_center_on_table"}


def shift_native(env, magnitude, observation, info, decision, pose_factory=None):
    g = geometry(observation)
    released = (not single_bool(info["is_grasped"], "is_grasped") and g["released_geometry"]
                and g["supported_geometry"] and decision["phase"] == "retract")
    record = {"name": "post_release_shift", "step": INJECTION_STEP, "magnitude_m": magnitude,
              "axis": "world_y", "timing": "after_action_computation_before_physics_step",
              "release_precondition": bool(released), "applied": bool(released),
              "implementation": "synthetic_lateral_pose_relocation_zero_velocities_not_force_disturbance"}
    if not released:
        return {**record, "reason": "release_precondition_not_satisfied"}
    before = vector(observation["extra"]["obj_pose"], 7, "obj_pose")
    after = before.copy()
    after[1] += magnitude
    if pose_factory is None:
        from mani_skill.utils.structs.pose import Pose
        pose_factory = Pose.create_from_pq
    base = env.unwrapped
    base.cube.set_pose(pose_factory(p=after[:3], q=after[3:], device=base.device))
    base.cube.linear_velocity = np.zeros(3, dtype=np.float32)
    base.cube.angular_velocity = np.zeros(3, dtype=np.float32)
    return {**record, "before_pose_world": before.tolist(), "after_pose_world": after.tolist(), "velocities_zeroed": True}


def summarize_episode(config, reference, verifier, truth, verdict, recovery, steps, stopped, path, nominal_complete, injection, seconds):
    detected = verifier.first_failure if verifier else None
    first = reference.first_failure
    latency = detected["step"] - first["step"] if detected and first and detected["failure"] == first["failure"] and detected["step"] >= first["step"] else None
    excluded = not reference.eligibility["eligible"]
    snapshot = recovery.snapshot() if recovery else {"state": "disabled", "attempts": 0, "action_steps": 0, "observed_tcp_path_m": 0.}
    return {"episode": 0, "seed": config.seed, "steps": steps, "stopped": stopped, "excluded": excluded,
            "exclusion_reason": reference.eligibility["exclusion_reason"], "seconds": seconds,
            "task_success_at_end": truth.get("task_success", False), "first_task_success_step": reference.first_success_step,
            "release_success_at_end": truth.get("release_success", False),
            "support_stability_success_at_end": truth.get("support_stability_success", False),
            "retraction_success_at_end": truth.get("retracted", False),
            "final_horizontal_error_m": truth.get("horizontal_error_m", reference.eligibility["initial_horizontal_error_m"]),
            "final_reference": truth, "final_verification": verdict,
            "first_reference_failure": first, "first_detected_failure": detected, "first_failure_latency_steps": latency,
            "nominal_schedule_complete": nominal_complete,
            "controller_complete": nominal_complete if recovery is None or snapshot["state"] == "nominal" else snapshot["state"] == "attempt_complete",
            "total_observed_tcp_path_m": path, "disturbance_attempted": injection is not None,
            "disturbance_applied": bool(injection and injection["applied"]), "recovery": snapshot,
            "recovery_task_success": bool(snapshot["attempts"] and truth.get("task_success", False))}


def evaluation(config, episode, metrics, complete):
    return {"complete": complete, "eligible_episodes": int(not episode["excluded"]), "excluded_episodes": int(episode["excluded"]),
            "task_success_rate_at_end": float(episode["task_success_at_end"]) if complete and not episode["excluded"] else None,
            "verification_metrics": metrics.result(complete) if metrics else None,
            "system": config.system, "input_source": "privileged_simulator_state", "scope": "m6_support_placement"}


def run(config, publish=None, stop=None, env_factory=build_env, reset_fn=reset_native, observe_fn=observe_native,
        shift_fn=shift_native, native_sources_fn=upstream_sources):
    config.validate()
    stop = stop or threading.Event()
    directory = config.output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 6, "purpose": config.purpose, "config": json_value(asdict(config)),
                "software": software_manifest(), "task_contract": task_manifest(), "system": config.system,
                "verification": config.verification, "recovery": config.system == "v2",
                "physics_backend": "cpu", "control_mode": config.control_mode, "observation_mode": "state_dict"}
    result = {"state": "starting", "run_directory": str(directory), "purpose": config.purpose, "protocol": "m6",
              "system": config.system, "disturbance": config.disturbance, "episodes": []}
    env = None
    with (directory / "events.jsonl").open("w", encoding="utf-8", buffering=1) as log:
        def event(kind, **fields):
            log.write(json.dumps({"event": kind, "time_utc": datetime.now(timezone.utc).isoformat(), **json_value(fields)}, allow_nan=False) + "\n")
        def update(**fields):
            result.update(json_value(fields))
            if publish:
                publish(result.copy(), None)
        def capture():
            if config.render:
                jpeg = encode_frame(env.render())
                (directory / "latest.jpg").write_bytes(jpeg)
                if publish:
                    publish(result.copy(), jpeg)
        try:
            update(state="initializing")
            env = env_factory(config)
            observation, info, geometry_record = reset_fn(env, config.seed)
            observation, info = json_value(observation), json_value(info)
            env.action_space.seed(config.seed)
            base = json_value(env.unwrapped.agent.robot.pose.raw_pose)
            policy = FixedPlacement(observation, base)
            reference = PlacementReference(observation)
            verifier = PlacementVerifier(observation) if config.verification else None
            recovery = PlacementRecovery(policy, base, config.max_steps) if config.system == "v2" else None
            metrics = VerificationMetrics() if verifier else None
            manifest.update(policy_details=policy.manifest(), support_geometry=geometry_record, robot_base_pose=base,
                            upstream_sources_sha256=native_sources_fn(), action_space_shape=list(env.action_space.shape),
                            verifier=verifier.manifest() if verifier else None, recovery_controller=recovery.manifest() if recovery else None)
            (directory / "manifest.json").write_text(json.dumps(json_value(manifest), indent=2, allow_nan=False) + "\n")
            event("run_started", manifest=manifest)
            event("reset", episode=0, seed=config.seed, observation=observation, info=info, eligibility=reference.eligibility)
            verdict = {"status": "waiting" if verifier else "disabled", "failure": None}
            truth = {}
            update(state="running", step=0, phase="approach", task_success=False, verification=verdict, reference=truth,
                   recovery=recovery.snapshot() if recovery else {"state": "disabled"}, eligibility=reference.eligibility)
            capture()
            steps = 0
            path = 0.
            previous_tcp = geometry(observation)["tcp"]
            nominal_complete = False
            injection = None
            start = time.monotonic()
            if reference.eligibility["eligible"]:
                for step in range(1, config.max_steps + 1):
                    if stop.is_set():
                        break
                    tick = time.monotonic()
                    action, decision = recovery.action(observation, step, verdict) if recovery else policy.action(observation, step - 1)
                    action = fixed_action_for_space(action, env.action_space)
                    saved_action = json_value(action)
                    if step == INJECTION_STEP and config.disturbance != "none":
                        injection = shift_fn(env, config.disturbance_magnitude, observation, info, decision)
                        event("disturbance_attempted", episode=0, step=step, disturbance=injection)
                    observation, reward, term, trunc, info = env.step(action)
                    observation, info = observe_fn(env, observation, info)
                    observation, info = json_value(observation), json_value(info)
                    steps = step
                    final = step == config.max_steps or bool(scalar(trunc))
                    truth = reference.observe(observation, info, step, decision, final)
                    if verifier:
                        verdict = verifier.observe(observation, step, decision, final)
                        metrics.observe(truth, verdict)
                    if recovery:
                        recovery.observe(observation)
                    tcp = geometry(observation)["tcp"]
                    path += float(np.linalg.norm(tcp - previous_tcp))
                    previous_tcp = tcp
                    nominal_complete |= decision["phase"] == "settle" and decision["schedule_complete"]
                    event("step", episode=0, step=step, action=saved_action, observation=observation, info=info,
                          reward=reward, terminated=term, truncated=trunc, controller_decision=decision,
                          reference=truth, verification=verdict, recovery=recovery.snapshot() if recovery else {"state": "disabled"},
                          total_observed_tcp_path_m=path)
                    update(step=step, phase=decision["phase"], task_success=truth["task_success"], reference=truth, verification=verdict,
                           recovery=recovery.snapshot() if recovery else {"state": "disabled"}, disturbance_applied=bool(injection and injection["applied"]))
                    capture()
                    if final:
                        break
                    if publish:
                        stop.wait(max(0., 1 / config.fps - (time.monotonic() - tick)))
            summary = summarize_episode(config, reference, verifier, truth, verdict, recovery, steps, stop.is_set(), path,
                                        nominal_complete, injection, time.monotonic() - start)
            result["episodes"].append(summary)
            event("episode_excluded" if summary["excluded"] else "episode_finished", **summary)
            complete = not stop.is_set() and (summary["excluded"] or steps == config.max_steps)
            update(state="finished" if complete else "stopped", evaluation=evaluation(config, summary, metrics, complete))
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
                update(state="error", error=f"cleanup failed: {type(error).__name__}: {error}")
                event("cleanup_failed", error=result["error"])
                raise
            finally:
                (directory / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
