"""M8 second known-seed force-dose batch; no fresh or matched-system entry."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from .runtime import build_env, json_value
from .m6_runtime import reset_native, observe_native
from .m6r_runtime import M6RConfig, run as accepted_run
from .m6r_audit import check_trial
from .m6_policy import INJECTION_STEP, FixedPlacement, MAX_STEPS
from .m8_force import (ForceEnvironment, ForceTrace, DEVELOPMENT_SEEDS, WINDOW_SUBSTEPS,
    candidate_points as original_candidate_points, preflight as installed_preflight,
    receipt, sha256, SOURCE_FILES as PHYSICAL_SOURCE_FILES, RECEIPT)
from .m8_force_commission import write_json, audit_physics, compare, archive

SOURCE_FILES = (*PHYSICAL_SOURCE_FILES, "m8_force_refine.py")
RESPONSE_REVIEW = RECEIPT.with_name("AETHER_CL_M8_Force_Response_Review_v1.json")
RESPONSE_REVIEW_SHA256 = "b5b63bce1e560f0949ff4ddff6346481ed29b19c0e44e3f5e33a122a180bd83e"
PROBE_MULTIPLIERS = tuple(1.25**k for k in range(1, 5))


def response_review():
    if sha256(RESPONSE_REVIEW) != RESPONSE_REVIEW_SHA256:
        raise ValueError("Require the independently audited v1 force-response receipt")
    review = json.loads(RESPONSE_REVIEW.read_text())
    if (not review["all_audit_checks_passed"] or review["fresh_study_started"]
            or review["force_family_frozen_for_fresh_study"]
            or review["measurement_commit"] != "b6b01b863c89190dc795155877d38816216e6df6"
            or review["archive_sha256"] != "309a191f5683f832f1e5a2e338886fcd8c73d9d3c83416ec87a5e58e432da815"):
        raise ValueError("Invalid v1 response-review provenance")
    return review


def candidate_points():
    review = response_review()
    original = original_candidate_points()
    largest = max(e["command_force_y_n"] for e in review["outcomes"] if e["kind"] == "main")
    if largest != original[-1]["command_force_y_n"]:
        raise ValueError("Recorded v1 largest dose differs from the retained development plan")
    result = []
    references = ((original[0], "normal"), (original[1], "force-easy-v1"),
                  (original[-1], "force-reference-v1-high"))
    for point, identifier in references:
        result.append({**point, "point_id": identifier, "estimated_drift_m": None,
            "reference_v1_point_id": point["point_id"],
            "input_kind": "v1_zero_easy_or_high_reference"})
    for k, multiplier in enumerate(PROBE_MULTIPLIERS, 1):
        force = float(np.float32(largest * multiplier))
        result.append({"point_id": f"force-probe-{k}", "estimated_drift_m": None,
            "command_force_y_n": force, "command_force_world_n": [0., force, 0.],
            "torque_world_nm": [0., 0., 0.], "planned_nominal_duration_s": .05,
            "planned_command_integral_y_ns": force * WINDOW_SUBSTEPS * receipt()["actual_timestep_s"],
            "prediction_is_not_actor_state_command": True,
            "input_kind": "development_geometric_force_probe_not_desired_displacement",
            "multiplier_of_v1_highest_force": multiplier})
    return result


def preflight(expected_head):
    response_review()
    identity = installed_preflight(expected_head)
    identity["development_sources_sha256"] = {n: sha256(Path(__file__).with_name(n)) for n in SOURCE_FILES}
    identity["response_review_sha256"] = RESPONSE_REVIEW_SHA256
    identity["development_stage"] = "force_dose_refinement_after_recorded_finger_contact"
    return identity


def plan():
    points = candidate_points()
    original = [{"kind": "original", "point_id": "normal", "seed": s} for s in DEVELOPMENT_SEEDS]
    main = [{"kind": "main", "point_id": p["point_id"], "seed": s} for p in points for s in DEVELOPMENT_SEEDS]
    repeats = [{"kind": "repeat", "point_id": p["point_id"], "seed": s}
               for p in (points[0], points[2], points[4], points[6]) for s in DEVELOPMENT_SEEDS]
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
    manifest = {"scope": "M8_known_seed_baseline_force_dose_refinement", "confirmatory": False,
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


def run_suite(output, destination, expected_head):
    output, destination = output.resolve(), destination.resolve()
    if output.exists() or destination.exists() or destination.is_relative_to(output):
        raise FileExistsError("Require new separate commissioning output/archive paths; no resume/reruns")
    output.mkdir(parents=True, exist_ok=False)
    with (output / ".lock").open("x") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = {"scope": "M8_known_seed_baseline_force_dose_refinement", "confirmatory": False,
            "state": "starting", "time_utc": datetime.now(timezone.utc).isoformat(),
            "seeds": list(DEVELOPMENT_SEEDS), "systems": ["baseline"], "points": [],
            "plan": [], "trials": [], "fresh_study_started": False,
            "force_family_frozen_for_fresh_study": False,
            "stage": "force_dose_refinement_after_v1_finger_contact_review",
            "response_review_sha256": RESPONSE_REVIEW_SHA256,
            "force_input_is_monotonic_actual_effect_need_not_be": True,
            "performance_success_gate": "none_failures_exclusions_nonapplication_retained",
            "next_boundary": "independent_response_review_before_matched_commission_or_fresh_freeze"}
        try:
            report["points"] = candidate_points()
            report["plan"] = plan()
            report["identity"] = preflight(expected_head)
            snapshots = output / "sources"
            snapshots.mkdir()
            for n in (*receipt()["accepted_placement_sources_sha256"], *SOURCE_FILES):
                (snapshots / n).write_bytes(Path(__file__).with_name(n).read_bytes())
            (snapshots / RECEIPT.name).write_bytes(RECEIPT.read_bytes())
            (snapshots / RESPONSE_REVIEW.name).write_bytes(RESPONSE_REVIEW.read_bytes())
            report["state"] = "running"
            write_json(output / "suite.json", report)
            for item in report["plan"]:
                case = output / f"slot-{item['slot']:02d}-{item['kind']}-{item['point_id']}-seed{item['seed']}"
                case.mkdir(exist_ok=False)
                print(f"START {item['slot']+1}/24 {item['kind']} {item['point_id']} seed{item['seed']}", flush=True)
                record = {**item, "directory": str(case.relative_to(output)), "returncode": None,
                          "result": {"state": "started_pending_child_result"}}
                report["trials"].append(record)
                write_json(output / "suite.json", report)
                command = [sys.executable, "-u", "-m", "aether_cl.m8_force_refine", "--child",
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
                print(f"END {item['slot']+1}/24 {child['state']}", flush=True)
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
                for point in (candidate_points()[0],candidate_points()[2],candidate_points()[4],candidate_points()[6]):
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
        print("M8_FORCE_REFINEMENT_VALID", flush=True)
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
        print("M8_REFINEMENT_CHILD_VALID", result["seed"], result["point_id"], flush=True)
    else:
        if args.archive is None or any(v is not None for v in (args.seed,args.kind,args.point)):
            cli.error("Suite requires --archive and uses its fixed24 known-seed plan")
        run_suite(args.output, args.archive, args.expected_head)


if __name__ == "__main__":
    main()
