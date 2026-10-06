"""Development-only isolated PegInsertionSide runs; native geometry never reset/modified."""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

import numpy as np

from .runtime import fixed_action_for_space, json_value, software_manifest
from .policies import vector
from .verification import single_bool
from .m7_task import InsertionReference, InsertionVerifier, geometry, task_manifest
from .m7_policy import FixedInsertion, InsertionRecovery, INJECTION_STEP, MAX_STEPS, DURATIONS

RECEIPT_PATH = Path(__file__).resolve().parents[3] / "docs/research/experiments/evidence/AETHER_CL_M7_Installed_Inspection.json"
SYSTEMS = ("baseline", "v1", "v2")
DEVELOPMENT_SEEDS = (100, 101)
CANDIDATE_RATIOS = (0., .5, 1., 2., 4., 8.)


def preflight_native():
    receipt = json.loads(RECEIPT_PATH.read_text())
    if sys.version_info[:2] != (3, 10) or any(version(k) != v for k, v in receipt["packages"].items()):
        raise ValueError("Use the inspected native Python3.10 / aether-cl environment without dependency changes")
    pkg = Path(distribution("mani_skill").locate_file("mani_skill"))
    sources = {k: hashlib.sha256((pkg / k).read_bytes()).hexdigest() for k in receipt["source_sha256"]}
    assets = {k: hashlib.sha256((pkg / "assets" / k).read_bytes()).hexdigest() for k in receipt["asset_sha256"]}
    if sources != receipt["source_sha256"] or assets != receipt["asset_sha256"]:
        raise ValueError("Installed task/controller/asset bytes differ from the inspected sources")
    software = software_manifest()
    if not software.get("git_commit") or software.get("git_dirty"):
        raise ValueError("Native development requires a clean pinned Git checkout")
    environment_digest = hashlib.sha256(json.dumps(dict(os.environ), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"software": software, "installed_sources_sha256": sources, "installed_assets_sha256": assets,
            "startup_environment_sha256": environment_digest,
            "inspection_receipt_sha256": hashlib.sha256(RECEIPT_PATH.read_bytes()).hexdigest()}


@dataclass(frozen=True)
class M7DevelopmentConfig:
    seed: int = 100
    system: str = "baseline"
    offset_clearance_ratio: float = 0.
    output: Path = Path("runs/m7-development-child")

    def validate(self):
        if self.seed not in DEVELOPMENT_SEEDS or self.system not in SYSTEMS or self.offset_clearance_ratio not in CANDIDATE_RATIOS:
            raise ValueError("M7 development accepts only seeds100/101 and candidate ratios; fresh native entry is not implemented")


def build_env():
    import gymnasium as gym
    import mani_skill.envs
    return gym.make("PegInsertionSide-v1", num_envs=1, robot_uids="panda_wristcam", obs_mode="state_dict",
                    control_mode="pd_ee_pose", reward_mode="none", sim_backend="cpu",
                    render_backend="none", render_mode=None, max_episode_steps=MAX_STEPS)


def observe_native(env, observation, info):
    b = env.unwrapped
    if bool(getattr(b, "gpu_sim_enabled", False)):
        raise ValueError("CPU physics required")
    e = {**observation["extra"], "peg_linear_velocity": b.peg.linear_velocity,
         "peg_angular_velocity": b.peg.angular_velocity, "box_pose": b.box.pose.raw_pose}
    return json_value({**observation, "extra": e}), json_value({**info,
        "contact_grasped": single_bool(b.agent.is_grasping(b.peg), "contact_grasped"),
        "left_finger_peg_force_world_n": b.scene.get_pairwise_contact_forces(b.agent.finger1_link, b.peg),
        "right_finger_peg_force_world_n": b.scene.get_pairwise_contact_forces(b.agent.finger2_link, b.peg),
        "left_finger_open_direction_world": b.agent.finger1_link.pose.to_transformation_matrix()[..., :3, 1],
        "right_finger_open_direction_world": -b.agent.finger2_link.pose.to_transformation_matrix()[..., :3, 1],
        "peg_box_contact_force_world_n": b.scene.get_pairwise_contact_forces(b.peg, b.box),
        "peg_table_contact_force_world_n": b.scene.get_pairwise_contact_forces(b.peg, b.table_scene.table)})


def perturb_waypoints(policy, observation, reference_state, info, ratio, recovering):
    g = geometry(observation)
    force = vector(info["peg_box_contact_force_world_n"], 3, "peg_box_contact")
    precondition = (not recovering and policy.calibrated and reference_state.get("valid_acquisition", False)
        and g["maximum_vertex_axial_m"] <= -g["half"][0] - .04
        and g["alignment_margin_m"] >= -.0002 and g["orientation_error_rad"] <= .05
        and np.linalg.norm(force) <= .05)
    magnitude = ratio * (g["radius"] - g["half"][1])
    offset = policy.rh[:, 1] * magnitude if policy.calibrated else np.zeros(3)
    applied = bool(precondition and ratio != 0)
    if applied:
        policy.bias_insertion_waypoints(offset)
    return {"implementation": "synthetic_cached_nominal_waypoint_lateral_bias_not_force_or_actor_teleport",
            "step": INJECTION_STEP, "clearance_ratio": ratio, "requested_magnitude_m": float(magnitude),
            "axis": "hole_local_positive_y", "world_offset_m": offset.tolist(),
            "precondition": bool(precondition), "applied": applied,
            "missed_precondition_retained": not precondition,
            "physical_precondition_state": {"maximum_vertex_axial_m": g["maximum_vertex_axial_m"],
                "channel_front_x_m": -float(g["half"][0]), "alignment_margin_m": g["alignment_margin_m"],
                "orientation_error_rad": g["orientation_error_rad"], "peg_box_contact_force_world_n": force.tolist()},
            "actual_offset_must_be_measured_before_insertion": True}


def run(config, env_factory=build_env, observe_fn=observe_native, preflight_fn=preflight_native):
    config.validate()
    preflight = preflight_fn()
    directory = config.output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    result = {"state": "starting", "run_directory": str(directory), "config": json_value(asdict(config)),
              "development_only": True, "fresh_native": False}
    env = None
    with (directory / "events.jsonl").open("x", buffering=1, encoding="utf-8") as log:
        def event(kind, **fields):
            log.write(json.dumps(json_value({"event": kind, "time_utc": datetime.now(timezone.utc).isoformat(), **fields}), allow_nan=False) + "\n")
        try:
            env = env_factory()
            observation, info = env.reset(seed=config.seed)
            observation, info = observe_fn(env, observation, info)
            env.action_space.seed(config.seed)
            base = json_value(env.unwrapped.agent.robot.pose.raw_pose)
            nominal = FixedInsertion(observation, base)
            reference = InsertionReference(observation)
            verifier = InsertionVerifier(observation) if config.system != "baseline" else None
            recovery = InsertionRecovery(nominal) if config.system == "v2" else None
            manifest = {**preflight, "development_only": True, "task": "PegInsertionSide-v1", "robot": "panda_wristcam",
                "physics_backend": "cpu", "control_mode": "pd_ee_pose", "observation_mode": "state_dict",
                "config": json_value(asdict(config)), "max_steps": MAX_STEPS, "robot_base_pose": base,
                "task_contract": task_manifest(), "nominal": nominal.manifest(),
                "recovery": recovery.manifest() if recovery else None,
                "action_space_shape": list(env.action_space.shape),
                "episode_geometry": {"peg_half_size": observation["extra"]["peg_half_size"],
                    "hole_radius": observation["extra"]["box_hole_radius"], "hole_pose": observation["extra"]["box_hole_pose"]}}
            (directory / "manifest.json").write_text(json.dumps(json_value(manifest), indent=2, allow_nan=False) + "\n")
            event("run_started", manifest=manifest)
            event("reset", seed=config.seed, observation=observation, info=info)
            verdict, truth, injection = {"status": "waiting" if verifier else "disabled", "failure": None}, {}, None
            path = 0.; previous_tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")[:3]
            nominal_complete = False
            first_contact_step = first_positive_depth_step = None
            pre_insert_state = None
            for step in range(1, MAX_STEPS + 1):
                if step == INJECTION_STEP:
                    injection = perturb_waypoints(nominal, observation, truth, info, config.offset_clearance_ratio,
                                                  bool(recovery and recovery.state != "nominal"))
                    event("disturbance_considered", disturbance=injection)
                if step == sum(DURATIONS[:7]) + 1:
                    pre_insert_state = {"step": step - 1, "reference": truth, "recovery_state": recovery.snapshot() if recovery else None,
                                        "peg_box_contact_force_world_n": info["peg_box_contact_force_world_n"]}
                action, decision = recovery.action(observation, step, verdict) if recovery else nominal.action(observation, step - 1)
                action = fixed_action_for_space(action, env.action_space)
                observation, reward, term, trunc, info = env.step(action)
                observation, info = observe_fn(env, observation, info)
                truth = reference.observe(observation, info, step, decision, final=step == MAX_STEPS)
                if verifier:
                    verdict = verifier.observe(observation, step, decision, final=step == MAX_STEPS)
                if recovery:
                    recovery.observe(observation)
                tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp_pose")[:3]
                path += float(np.linalg.norm(tcp - previous_tcp)); previous_tcp = tcp
                nominal_complete |= not decision["phase"].startswith("recovery_") and decision["schedule_complete"]
                if first_contact_step is None and np.linalg.norm(vector(info["peg_box_contact_force_world_n"], 3, "peg_box_contact")) > .05:
                    first_contact_step = step
                if first_positive_depth_step is None and truth["depth_m"] > 0:
                    first_positive_depth_step = step
                event("step", step=step, action=action, observation=observation, info=info, reward=reward,
                      terminated=term, truncated=trunc, controller_decision=decision, reference=truth,
                      verification=verdict, recovery=recovery.snapshot() if recovery else {"state": "disabled", "attempts": 0})
                if bool(np.asarray(json_value(trunc)).reshape(-1)[0]) and step != MAX_STEPS:
                    raise ValueError("Native TimeLimit truncated before the full development action budget")
            snapshot = recovery.snapshot() if recovery else {"state": "disabled", "attempts": 0, "action_steps": 0, "observed_tcp_path_m": 0., "completed_stages": []}
            result.update(state="finished", steps=MAX_STEPS, task_success_at_end=bool(truth["task_success"]),
                built_in_success_at_end=single_bool(info["success"], "success"), final_reference=truth,
                final_verification=verdict, first_reference_failure=reference.first_failure,
                first_detected_failure=verifier.first_failure if verifier else None,
                first_task_success_step=reference.first_success_step, recovery=snapshot,
                total_observed_tcp_path_m=path, controller_complete=nominal_complete if not snapshot["attempts"] else snapshot["state"] == "attempt_complete",
                injection=injection, pre_insert_state=pre_insert_state, first_peg_box_contact_step=first_contact_step,
                first_positive_depth_step=first_positive_depth_step)
            event("run_finished", result=result)
        except BaseException as error:
            result.update(state="error", error=f"{type(error).__name__}: {error}")
            event("run_failed", error=result["error"])
            raise
        finally:
            try:
                if env is not None:
                    env.close()
            except BaseException as error:
                result.update(state="error", error=f"cleanup: {type(error).__name__}: {error}")
                event("cleanup_failed", error=result["error"])
                raise
            finally:
                (directory / "result.json").write_text(json.dumps(json_value(result), indent=2, allow_nan=False) + "\n")
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--seed", type=int, choices=DEVELOPMENT_SEEDS, required=True)
    cli.add_argument("--system", choices=SYSTEMS, required=True)
    cli.add_argument("--offset-clearance-ratio", type=float, choices=CANDIDATE_RATIOS, default=0.)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    result = run(M7DevelopmentConfig(**vars(args)))
    print(json.dumps({k: result[k] for k in ("state", "run_directory", "task_success_at_end", "controller_complete")}), flush=True)


if __name__ == "__main__":
    main()
