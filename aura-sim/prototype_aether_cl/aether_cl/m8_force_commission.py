"""Known-seed Baseline physical-response commissioning; fresh M8 is unavailable."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import traceback

import numpy as np

from .runtime import build_env, json_value
from .m6_runtime import reset_native, observe_native
from .m6r_runtime import M6RConfig, run as accepted_run
from .m6r_audit import check_trial, PHYSICAL_FIELDS
from .m6_policy import INJECTION_STEP, FixedPlacement, MAX_STEPS
from .acceptance import load_trial
from .m8_force import (ForceEnvironment, ForceTrace, DEVELOPMENT_SEEDS, WINDOW_SUBSTEPS,
    candidate_points, preflight, release_precondition, receipt, sha256, SOURCE_FILES, RECEIPT)


def write_json(path, value):
    path.write_text(json.dumps(json_value(value), indent=2, allow_nan=False) + "\n")


def plan():
    points = candidate_points()
    original = [{"kind": "original", "point_id": "normal", "seed": s} for s in DEVELOPMENT_SEEDS]
    main = [{"kind": "main", "point_id": p["point_id"], "seed": s} for p in points for s in DEVELOPMENT_SEEDS]
    repeats = [{"kind": "repeat", "point_id": p["point_id"], "seed": s}
               for p in (points[0], points[3], points[5]) for s in DEVELOPMENT_SEEDS]
    return [{"slot": i, **item} for i, item in enumerate(original + main + repeats)]


def validate_child(seed, kind, point_id):
    if seed not in DEVELOPMENT_SEEDS or isinstance(seed, bool):
        raise ValueError("Physical commissioning accepts only already-used seeds100/101")
    if kind not in ("original", "main", "repeat") or point_id not in {p["point_id"] for p in candidate_points()}:
        raise ValueError("Unknown fixed development slot")
    if kind == "original" and point_id != "normal":
        raise ValueError("Unmodified M6R control has no disturbance")


def run_child(output, expected_head, seed, kind, point_id):
    validate_child(seed, kind, point_id)
    output = output.resolve()
    if (output / "m8_manifest.json").exists() or (output / "native").exists():
        raise FileExistsError("Retain earlier development child; do not rerun a slot")
    output.mkdir(parents=True, exist_ok=True)
    identity = preflight(expected_head)
    point = next(p for p in candidate_points() if p["point_id"] == point_id)
    config = M6RConfig(seed=seed, system="baseline", verification=False, render=False,
        disturbance="none", output=output / "native")
    config.validate()
    manifest = {"scope": "M8_known_seed_baseline_force_response", "confirmatory": False,
        "kind": kind, "seed": seed, "system": "baseline", "point": point,
        "force_api": "PhysxRigidBodyComponent.add_force_torque", "mode": "force",
        "fixed_injection_action": INJECTION_STEP, "fixed_window_substeps": WINDOW_SUBSTEPS,
        "legacy_config": json_value(asdict(config)),
        "legacy_disturbance_field_meaning": "M6R_synthetic_injection_disabled_not_the_external_M8_force",
        "native_runner": "unchanged_m6r_runtime.run_baseline_dependency_injection",
        "force_input_independent_of_verifier_or_final_task_score": True,
        "clock": "one100Hz_engine_step_per_pre_post_hook_five_per20Hz_action",
        "task_controller_scorer_recovery_changes": "none_baseline_only_commissioning", **identity}
    write_json(output / "m8_manifest.json", manifest)
    carrier = {"scope": manifest["scope"], "confirmatory": False, "state": "starting", "kind": kind,
        "seed": seed, "point_id": point_id, "controller_system": "baseline",
        "fresh_study_started": False, "physical_force_applied": False}
    try:
        if kind == "original":
            result = accepted_run(config)
        else:
            with (output / "physics.jsonl").open("x", buffering=1) as log:
                def record(value):
                    log.write(json.dumps(json_value(value), allow_nan=False) + "\n")
                def create(c):
                    return ForceEnvironment(build_env(c))
                def reset(env, s):
                    observation, info, support = reset_native(env, s)
                    env.observation, env.info = json_value(observation), json_value(info)
                    env.policy = FixedPlacement(env.observation, json_value(env.unwrapped.agent.robot.pose.raw_pose))
                    env.trace = ForceTrace(env, point, record)
                    record({"event": "force_trace_started", "seed": s, "point": point,
                        "actual_gravity_world_m_s2": json_value(env.unwrapped.sim_config.scene_config.gravity),
                        "actual_timestep_s": float(env.unwrapped.scene.px.timestep)})
                    return observation, info, support
                def observe(env, observation, info):
                    observation, info = observe_native(env, observation, info)
                    env.observation, env.info = json_value(observation), json_value(info)
                    return observation, info
                result = accepted_run(config, env_factory=create, reset_fn=reset, observe_fn=observe)
        native = Path(result["run_directory"])
        carrier.update(state=result["state"], run_relative=str(native.relative_to(output)),
            native_config=json_value(asdict(config)), baseline_episode=result["episodes"][0])
        audit = check_trial(native, config, identity["software"])
        write_json(output / "accepted_runner_replay.json", audit)
        if not audit["passed"]:
            raise ValueError("Accepted action/scorer replay failed: " + ", ".join(audit["failed_checks"]))
        if kind != "original":
            physical = audit_physics(output, carrier, point)
            write_json(output / "physics_audit.json", physical)
            carrier.update(physical_force_applied=physical["force_calls"] > 0,
                           physical_effects=physical["effects"], physics_audit_passed=physical["passed"])
            if not physical["passed"]:
                raise ValueError("Physical force evidence failed: " + ", ".join(physical["failed_checks"]))
        carrier["state"] = "finished_valid_development_evidence"
    except BaseException as error:
        carrier.update(state="error_retained", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        raise
    finally:
        write_json(output / "m8_result.json", carrier)
    return carrier


STATE_FIELDS = ("cube_pose_world", "cube_linear_velocity_m_s", "cube_angular_velocity_rad_s")


def observation_state(obs):
    e = obs["extra"]
    return {"cube_pose_world": e["obj_pose"], "cube_linear_velocity_m_s": e["obj_linear_velocity"],
            "cube_angular_velocity_rad_s": e["obj_angular_velocity"]}


def audit_physics(output, carrier, point):
    expected_timestep = receipt()["actual_timestep_s"]
    manifest, result, events = load_trial(output / carrier["run_relative"])
    physics = [json.loads(line) for line in (output / "physics.jsonl").read_text().splitlines()]
    starts = [e for e in physics if e["event"] == "force_trace_started"]
    actions = [e for e in physics if e["event"] == "physics_action"]
    steps = [e for e in events if e["event"] == "step"]
    reset = next(e for e in events if e["event"] == "reset")
    previous_obs, previous_info = reset["observation"], reset["info"]
    checks = {"one_known_reset": len(starts) == 1 and starts[0]["seed"] == carrier["seed"] in DEVELOPMENT_SEEDS,
        "same_recorded_candidate": len(starts) == 1 and starts[0]["point"] == point,
        "no_legacy_synthetic_injection": manifest["config"]["disturbance"] == "none"
            and not any(e["event"] == "disturbance_attempted" for e in events),
        "one_physics_record_per_control_action": [e["step"] for e in actions] == [e["step"] for e in steps],
        "only_physics_events": all(e["event"] in ("force_trace_started", "physics_action") for e in physics),
        "complete_five_substeps": True, "fixed_window_and_precondition": True,
        "force_call_no_immediate_pose_velocity_change": True, "continuous_sample_state": True,
        "control_endpoint_matches_physics": True, "force_vector_mode_and_timestep": True}
    count, integral, all_post, pulse_before, pulse_after = 0, 0., [], None, None
    for physical, step in zip(actions, steps):
        substeps = physical["substeps"]
        checks["complete_five_substeps"] &= [s["substep"] for s in substeps] == list(range(1, 6))
        if not substeps:
            continue
        phase = step["controller_decision"]["phase"]
        precondition = release_precondition(previous_obs, previous_info, phase) if step["step"] == INJECTION_STEP else False
        apply = bool(step["step"] == INJECTION_STEP and precondition and point["command_force_y_n"] != 0)
        checks["fixed_window_and_precondition"] &= (physical["intent"]["step"] == step["step"]
            and physical["intent"]["nominal_phase"] == phase
            and physical["intent"]["release_support_precondition"] == precondition
            and physical["intent"]["injection_boundary"] == (step["step"] == INJECTION_STEP))
        prior = observation_state(previous_obs)
        for sample in substeps:
            checks["continuous_sample_state"] &= all(sample["before"][n] == prior[n] for n in STATE_FIELDS)
            checks["force_call_no_immediate_pose_velocity_change"] &= all(
                sample["before"][n] == sample["immediately_after_force_call"][n] for n in STATE_FIELDS)
            expected_force = point["command_force_world_n"] if apply else [0., 0., 0.]
            checks["force_vector_mode_and_timestep"] &= (sample["force_world_n"] == expected_force
                and sample["torque_world_nm"] == [0., 0., 0.] and sample["force_call_executed"] == apply
                and sample["dt_s"] == expected_timestep
                and physical["intent"]["mode"] == "force"
                and physical["intent"]["force_api"] == "PhysxRigidBodyComponent.add_force_torque"
                and physical["intent"]["requested_force_world_n"] == point["command_force_world_n"])
            count += int(sample["force_call_executed"])
            integral += sample["force_world_n"][1] * sample["dt_s"]
            prior = sample["after_physics"]
            if step["step"] >= INJECTION_STEP:
                all_post.append(prior)
            if step["step"] == INJECTION_STEP and sample["substep"] == 1:
                pulse_before = sample["before"]
            if step["step"] == INJECTION_STEP and sample["substep"] == 5:
                pulse_after = prior
        endpoint = observation_state(step["observation"])
        checks["control_endpoint_matches_physics"] &= all(prior[n] == endpoint[n] for n in STATE_FIELDS)
        checks["control_endpoint_matches_physics"] &= prior["cube_table_contact_force_world_n"] == step["info"]["cube_table_contact_force_world_n"]
        previous_obs, previous_info = step["observation"], step["info"]
    expected_calls = 5 if any(e["step"] == INJECTION_STEP and e["intent"]["release_support_precondition"] for e in actions) and point["command_force_y_n"] else 0
    checks["exact_force_call_count"] = count == expected_calls
    def pose(state):
        return np.asarray(state["cube_pose_world"]).reshape(7)[:3]
    effects = {"force_calls": count, "command_integral_y_ns": integral,
        "actual_application_duration_s": count * expected_timestep,
        "release_support_precondition": next((e["intent"]["release_support_precondition"] for e in actions if e["step"] == INJECTION_STEP), None),
        "before_pulse": pulse_before, "after_pulse": pulse_after,
        "peak_horizontal_displacement_from_pulse_start_m": max((float(np.linalg.norm((pose(s)-pose(pulse_before))[:2])) for s in all_post), default=None),
        "peak_linear_speed_after_pulse_m_s": max((float(np.linalg.norm(s["cube_linear_velocity_m_s"])) for s in all_post), default=None),
        "final_displacement_from_pulse_start_world_m": (pose(all_post[-1])-pose(pulse_before)).tolist() if all_post else None,
        "sampled_support_loss_after_pulse": any(np.asarray(s["cube_table_contact_force_world_n"]).reshape(3)[2] < .01 for s in all_post)}
    return {"passed": all(checks.values()), "checks": checks,
        "failed_checks": [k for k, v in checks.items() if not v], "force_calls": count,
        "external_physics_samples": sum(len(e["substeps"]) for e in actions), "effects": effects}


def compare(left, right, physics=False, prefix=MAX_STEPS):
    lm, _, le = load_trial(left / json.loads((left / "m8_result.json").read_text())["run_relative"])
    rm, _, re = load_trial(right / json.loads((right / "m8_result.json").read_text())["run_relative"])
    a = [e for e in le if e["event"] == "step" and e["step"] <= prefix]
    b = [e for e in re if e["event"] == "step" and e["step"] <= prefix]
    fields = (*PHYSICAL_FIELDS, "verification", "recovery")
    reset_fields = ("seed", "observation", "info", "eligibility")
    checks = {"same_software_task_policy_support": all(lm[k] == rm[k] for k in
        ("software", "task_contract", "policy_details", "support_geometry", "robot_base_pose", "upstream_sources_sha256")),
        "exact_reset": [{k:e[k] for k in reset_fields} for e in le if e["event"] == "reset"] ==
                       [{k:e[k] for k in reset_fields} for e in re if e["event"] == "reset"],
        "exact_physical_trace": len(a) == len(b) and all(all(x[k] == y[k] for k in fields) for x,y in zip(a,b))}
    if physics:
        checks["exact_physics_sidecar"] = (left / "physics.jsonl").read_bytes() == (right / "physics.jsonl").read_bytes()
    return {"passed": all(checks.values()), "checks": checks, "matched_steps": len(a)}


def archive(output, destination):
    index = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in sorted(output.rglob("*")) if p.is_file() and p.name not in (".lock", "file_index.json")}
    write_json(output / "file_index.json", index)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        with tarfile.open(fileobj=stream, mode="w:gz") as tar:
            tar.add(output, arcname="m8-force-commission", filter=lambda info: None if info.name.endswith("/.lock") else info)
    print("Archive:", destination, "SHA-256:", sha256(destination), flush=True)


def run_suite(output, destination, expected_head):
    output, destination = output.resolve(), destination.resolve()
    if output.exists() or destination.exists() or destination.is_relative_to(output):
        raise FileExistsError("Require new separate commissioning output/archive paths; no resume/reruns")
    output.mkdir(parents=True, exist_ok=False)
    with (output / ".lock").open("x") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = {"scope": "M8_known_seed_baseline_force_response", "confirmatory": False,
            "state": "starting", "time_utc": datetime.now(timezone.utc).isoformat(),
            "seeds": list(DEVELOPMENT_SEEDS), "systems": ["baseline"], "points": candidate_points(),
            "plan": plan(), "trials": [], "fresh_study_started": False,
            "force_family_frozen_for_fresh_study": False,
            "performance_success_gate": "none_failures_exclusions_nonapplication_retained",
            "next_boundary": "independent_response_review_before_matched_commission_or_fresh_freeze"}
        try:
            report["identity"] = preflight(expected_head)
            snapshots = output / "sources"
            snapshots.mkdir()
            for n in (*receipt()["accepted_placement_sources_sha256"], *SOURCE_FILES):
                (snapshots / n).write_bytes(Path(__file__).with_name(n).read_bytes())
            (snapshots / RECEIPT.name).write_bytes(RECEIPT.read_bytes())
            report["state"] = "running"
            write_json(output / "suite.json", report)
            for item in report["plan"]:
                case = output / f"slot-{item['slot']:02d}-{item['kind']}-{item['point_id']}-seed{item['seed']}"
                case.mkdir(exist_ok=False)
                print(f"START {item['slot']+1}/20 {item['kind']} {item['point_id']} seed{item['seed']}", flush=True)
                record = {**item, "directory": str(case.relative_to(output)), "returncode": None,
                          "result": {"state": "started_pending_child_result"}}
                report["trials"].append(record)
                write_json(output / "suite.json", report)
                command = [sys.executable, "-u", "-m", "aether_cl.m8_force_commission", "--child",
                    "--expected-head", expected_head, "--output", str(case), "--seed", str(item["seed"]),
                    "--kind", item["kind"], "--point", item["point_id"]]
                try:
                    with (case / "stdout.log").open("x") as stream:
                        process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
                except subprocess.TimeoutExpired:
                    record.update(result={"state": "child_timeout_retained", "timeout_s": 600,
                        "partial_evidence_directory": record["directory"], "replacement": False})
                    raise
                child = json.loads((case / "m8_result.json").read_text()) if (case / "m8_result.json").exists() else {"state":"missing_child_result"}
                record.update(returncode=process.returncode, result=child)
                write_json(output / "suite.json", report)
                print(f"END {item['slot']+1}/20 {child['state']}", flush=True)
                if process.returncode or child["state"] != "finished_valid_development_evidence":
                    raise ValueError("Development child failed; retain all started evidence, no fallback or replacement")
                preflight(expected_head)
            locate = {(t["kind"], t["point_id"], t["seed"]): output/t["directory"] for t in report["trials"]}
            comparisons = []
            for seed in DEVELOPMENT_SEEDS:
                comparisons.append({"kind":"unchanged_zero_control", "seed":seed,
                    **compare(locate["original","normal",seed], locate["main","normal",seed])})
                for point in candidate_points()[1:]:
                    comparisons.append({"kind":"pre_force_prefix", "seed":seed, "point":point["point_id"],
                        **compare(locate["main","normal",seed], locate["main",point["point_id"],seed], prefix=INJECTION_STEP-1)})
                for point in (candidate_points()[0],candidate_points()[3],candidate_points()[5]):
                    comparisons.append({"kind":"repeat_reproducibility", "seed":seed,"point":point["point_id"],
                        **compare(locate["main",point["point_id"],seed], locate["repeat",point["point_id"],seed], physics=True)})
            report["comparisons"] = comparisons
            report["state"] = "valid_development_evidence" if all(c["passed"] for c in comparisons) else "invalid_comparison_evidence_retained"
            report["interpretation"] = "development_only_no_fresh_force_family_selected_no_training"
        except BaseException as error:
            report.update(state="error_retained", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
            print(report["error"], flush=True)
        finally:
            write_json(output / "suite.json", report)
            archive(output, destination)
        if report["state"] != "valid_development_evidence":
            raise SystemExit(1)
        print("M8_FORCE_COMMISSION_VALID", flush=True)
        print("No fresh seeds executed; return the archive for independent response review", flush=True)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path)
    cli.add_argument("--expected-head", required=True)
    cli.add_argument("--child", action="store_true")
    cli.add_argument("--seed", type=int)
    cli.add_argument("--kind", choices=("original", "main", "repeat"))
    cli.add_argument("--point")
    args = cli.parse_args()
    if args.child:
        result = run_child(args.output, args.expected_head, args.seed, args.kind, args.point)
        print("M8_DEVELOPMENT_CHILD_VALID", result["seed"], result["point_id"], flush=True)
    else:
        if args.archive is None or any(v is not None for v in (args.seed,args.kind,args.point)):
            cli.error("Suite requires --archive and uses its fixed20 known-seed plan")
        run_suite(args.output, args.archive, args.expected_head)


if __name__ == "__main__":
    main()
