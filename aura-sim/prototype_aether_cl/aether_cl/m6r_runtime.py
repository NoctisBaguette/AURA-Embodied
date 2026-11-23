"""M6R isolated runtime; shared M6 native adapters and all motion primitives."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from uuid import uuid4

import numpy as np

from .runtime import build_env, encode_frame, fixed_action_for_space, json_value, scalar, software_manifest
from .verification import VerificationMetrics
from .m6_task import PlacementReference, PlacementVerifier, geometry, task_manifest
from .m6_policy import FixedPlacement, PlacementRecovery, INJECTION_STEP, MAX_STEPS
from .m6_runtime import (M6Config, reset_native, observe_native, shift_native, upstream_sources,
                         UPSTREAM_SOURCE_MODULES, evaluation, summarize_episode as m6_summary)
from .m6r_policy import EffectAlignedRecovery


@dataclass(frozen=True)
class M6RConfig(M6Config):
    protocol: str = "m6r"
    system: str = "v2r"

    def validate(self):
        if self.protocol != "m6r" or self.system not in ("baseline", "v1", "v2-old", "v2r"):
            raise ValueError("M6R requires Baseline/V1/V2-old/V2R and the m6r protocol")
        M6Config.validate(replace(self, protocol="m6", system="v2" if self.system in ("v2-old", "v2r") else self.system))

    @property
    def purpose(self):
        return "m6r_effect_aligned_placement_" + self.system


def recovery_class(system):
    return EffectAlignedRecovery if system == "v2r" else PlacementRecovery


def progress_record(step, decision, recovery):
    snapshot = recovery.snapshot() if recovery else {}
    return {"step": step, "phase": decision["phase"], "after_phase": snapshot.get("phase"),
            "failure_detail": snapshot.get("failure_detail")}


def progress_summary(progress):
    def first(predicate):
        return next((p["step"] for p in progress if predicate(p)), None)
    lower = first(lambda p: p["phase"] == "recovery_lower" and p["after_phase"] == "release")
    return {"lower_transition_step": lower,
            "lower_phase_timeout": any(p["failure_detail"] == "retry_lower_not_completed" for p in progress),
            "recovery_release_reached": lower is not None,
            "recovery_release_first_action_step": first(lambda p: p["phase"] == "recovery_release"),
            "recovery_release_executed": any(p["phase"] == "recovery_release" for p in progress),
            "recovery_retraction_reached": any(p["after_phase"] == "retract" for p in progress),
            "recovery_retraction_first_action_step": first(lambda p: p["phase"] == "recovery_retract"),
            "recovery_retraction_executed": any(p["phase"] == "recovery_retract" for p in progress)}


def summarize_episode(config, reference, verifier, truth, verdict, recovery, steps, stopped, path,
                      nominal_complete, injection, seconds, progress):
    return {**m6_summary(config, reference, verifier, truth, verdict, recovery, steps, stopped, path,
                        nominal_complete, injection, seconds), **progress_summary(progress)}


def run(config, publish=None, stop=None, env_factory=build_env, reset_fn=reset_native, observe_fn=observe_native,
        shift_fn=shift_native, native_sources_fn=upstream_sources):
    config.validate()
    stop = stop or threading.Event()
    directory = config.output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 7, "purpose": config.purpose, "config": json_value(asdict(config)),
                "software": software_manifest(), "task_contract": task_manifest(), "system": config.system,
                "verification": config.verification, "recovery": config.system in ("v2-old", "v2r"),
                "physics_backend": "cpu", "control_mode": config.control_mode, "observation_mode": "state_dict"}
    result = {"state": "starting", "run_directory": str(directory), "purpose": config.purpose, "protocol": "m6r",
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
            recovery = recovery_class(config.system)(policy, base, config.max_steps) if config.system in ("v2-old", "v2r") else None
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
            progress = []
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
                    progress.append(progress_record(step, decision, recovery))
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
                                        nominal_complete, injection, time.monotonic() - start, progress)
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
