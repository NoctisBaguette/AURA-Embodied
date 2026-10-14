"""M8 matched known-seed commissioning; fresh evaluation is not an entry point."""

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

from .acceptance import load_trial
from .runtime import build_env, fixed_action_for_space, json_value, scalar
from .m6_runtime import reset_native, observe_native
from .m6_task import PlacementVerifier
from .m6_policy import FixedPlacement, INJECTION_STEP, MAX_STEPS
from .m6r_policy import EffectAlignedRecovery
from .m6r_runtime import M6RConfig, run as accepted_run
from .m6r_audit import check_trial, PHYSICAL_FIELDS
from .m8_force import ForceTrace, DEVELOPMENT_SEEDS, WINDOW_SUBSTEPS, RECEIPT, receipt, sha256
from .m8_force_refine import (candidate_points as dose_points, preflight as dose_preflight,
                             SOURCE_FILES as DOSE_SOURCES, RESPONSE_REVIEW)
from .m8_force_commission import write_json, audit_physics, archive

SYSTEMS = ("baseline", "v1", "v2")
LEGACY_SYSTEM = {"baseline": "baseline", "v1": "v1", "v2": "v2r"}
SOURCE_FILES = (*DOSE_SOURCES, "m8_matched.py")
DOSE_REVIEW = RECEIPT.with_name("AETHER_CL_M8_Force_Response_Review_v2.json")
DOSE_REVIEW_SHA256 = "9f838344d3f4811f069b19c9ff1d091b1ad8eef23a3790a7edff5040eea23a58"
POINT_IDS = ("normal", "force-easy-v1", "force-probe-1", "force-probe-2", "force-probe-3", "force-probe-4")


def reviewed_doses():
    if sha256(DOSE_REVIEW) != DOSE_REVIEW_SHA256:
        raise ValueError("Require the independently audited v2 dose-review receipt")
    review = json.loads(DOSE_REVIEW.read_text())
    if (not review["all_audit_checks_passed"] or review["fresh_study_started"]
            or review["force_family_frozen_for_fresh_study"]
            or review["measurement_commit"] != "155283683148218bc5a45ecf2167585223650724"
            or review["archive_sha256"] != "7374077d443ffc3e93134af2fd3b4daca307c8664004df194c42fe2e905cded0"
            or review["next_development_plan"]["point_ids"] != list(POINT_IDS)):
        raise ValueError("Invalid v2 review provenance or matched development family")
    return review


def candidate_points():
    reviewed_doses()
    selected = {p["point_id"]: p for p in dose_points()}
    points = [selected[n] for n in POINT_IDS]
    if not all(a["command_force_y_n"] < b["command_force_y_n"] for a, b in zip(points, points[1:])):
        raise ValueError("Require monotonically increasing force inputs")
    return points


def preflight(expected_head):
    reviewed_doses()
    identity = dose_preflight(expected_head)
    identity["development_sources_sha256"] = {n: sha256(Path(__file__).with_name(n)) for n in SOURCE_FILES}
    identity["dose_review_sha256"] = DOSE_REVIEW_SHA256
    identity["development_stage"] = "matched_baseline_passive_verification_effect_aligned_recovery"
    return identity


def plan():
    return [{"slot": i, **item} for i, item in enumerate(
        {"seed": seed, "point_id": point["point_id"], "system": system}
        for seed in DEVELOPMENT_SEEDS for point in candidate_points() for system in SYSTEMS)]


def validate_child(seed, system, point_id):
    if isinstance(seed, bool) or seed not in DEVELOPMENT_SEEDS:
        raise ValueError("Matched commissioning only reuses recorded development seeds100/101")
    if system not in SYSTEMS or point_id not in POINT_IDS:
        raise ValueError("Unknown fixed matched development slot")
    candidate_points()


def legacy_config(output, seed, system):
    config = M6RConfig(seed=seed, system=LEGACY_SYSTEM[system], verification=system != "baseline",
                       render=False, disturbance="none", output=output / "native")
    config.validate()
    return config


class DecisionTraceEnvironment:
    """Replay the unchanged controller solely to gate instrumentation by phase.

    The accepted runner remains the sole motor-command authority. This replay
    has independent controller/verifier state and never writes simulator state
    or supplies an action. Every received action must equal its reconstructed
    action before native stepping. Full decisions, verdicts and recovery states
    must also equal the accepted runner's retained log afterward. This avoids
    treating a nominal schedule as the active phase during early recovery.
    """

    def __init__(self, env):
        self.env, self.trace, self.step_number = env, None, 0
        self.pending = False

    def __getattr__(self, name):
        return getattr(self.env, name)

    def initialize(self, observation, info, base_pose, system, gate_log):
        self.observation, self.info = json_value(observation), json_value(info)
        self.policy = FixedPlacement(self.observation, base_pose)
        self.verifier = PlacementVerifier(self.observation) if system != "baseline" else None
        self.recovery = EffectAlignedRecovery(self.policy, base_pose, MAX_STEPS) if system == "v2" else None
        self.verdict = {"status": "waiting" if self.verifier else "disabled", "failure": None}
        self.gate_log = gate_log

    def step(self, action):
        if self.pending:
            raise ValueError("Missing preceding controller-observation replay")
        self.step_number += 1
        expected, decision = (self.recovery.action(self.observation, self.step_number, self.verdict)
            if self.recovery else self.policy.action(self.observation, self.step_number - 1))
        expected = fixed_action_for_space(expected, self.env.action_space)
        if not np.array_equal(action, expected):
            self.gate_log({"event": "controller_action_mismatch_before_native_step", "step": self.step_number,
                           "received": json_value(action), "replayed": json_value(expected)})
            raise ValueError("Instrumentation controller replay disagrees with authoritative action")
        self.decision, self.received_action = decision, json_value(action)
        self.trace.begin(self.step_number, self.observation, self.info, decision["phase"])
        self.trace.intent["controller_decision_replay"] = json_value(decision)
        self.trace.intent["authoritative_action"] = self.received_action
        result = self.env.step(action)
        self.truncated = result[3]
        self.trace.end()
        self.pending = True
        return result

    def accept_observation(self, observation, info):
        if not self.pending:
            raise ValueError("Controller replay has no preceding native action")
        self.observation, self.info = json_value(observation), json_value(info)
        final = self.step_number == MAX_STEPS or bool(scalar(self.truncated))
        if self.verifier:
            self.verdict = self.verifier.observe(self.observation, self.step_number, self.decision, final)
        if self.recovery:
            self.recovery.observe(self.observation)
        self.gate_log({"event": "controller_gate", "step": self.step_number, "action": self.received_action,
                       "controller_decision": self.decision, "verification": self.verdict,
                       "recovery": self.recovery.snapshot() if self.recovery else {"state": "disabled"}})
        self.pending = False

    def close(self):
        try:
            if self.trace is not None:
                self.trace.close()
        finally:
            self.env.close()


def audit_gate(output, carrier):
    _, _, events = load_trial(output / carrier["run_relative"])
    steps = [e for e in events if e["event"] == "step"]
    gates = [json.loads(line) for line in (output / "controller_gate.jsonl").read_text().splitlines()]
    physical = [json.loads(line) for line in (output / "physics.jsonl").read_text().splitlines()]
    samples = [e for e in physical if e["event"] == "physics_action"]
    fields = ("step", "action", "controller_decision", "verification", "recovery")
    checks = {"exact_one_gate_per_native_action": [e["step"] for e in gates] == [e["step"] for e in steps],
        "only_valid_gate_events": all(e["event"] == "controller_gate" for e in gates),
        "exact_controller_verifier_recovery_replay": len(gates) == len(steps) and all(
            all(g[k] == e[k] for k in fields) for g, e in zip(gates, steps)),
        "exact_active_decision_for_force_gate": len(samples) == len(steps) and all(
            p["intent"]["controller_decision_replay"] == e["controller_decision"]
            and p["intent"]["authoritative_action"] == e["action"] for p, e in zip(samples, steps))}
    return {"passed": all(checks.values()), "checks": checks,
            "failed_checks": [k for k, v in checks.items() if not v], "matched_actions": len(steps)}


def run_child(output, expected_head, seed, system, point_id):
    validate_child(seed, system, point_id)
    output = output.resolve()
    if (output / "m8_manifest.json").exists() or (output / "native").exists():
        raise FileExistsError("Retain earlier development child; do not rerun a slot")
    output.mkdir(parents=True, exist_ok=True)
    identity = preflight(expected_head)
    point = next(p for p in candidate_points() if p["point_id"] == point_id)
    config = legacy_config(output, seed, system)
    manifest = {"scope": "M8_known_seed_matched_force_commissioning", "confirmatory": False,
        "seed": seed, "system": system, "point": point, "force_api": "PhysxRigidBodyComponent.add_force_torque",
        "mode": "force", "fixed_injection_action": INJECTION_STEP, "fixed_window_substeps": WINDOW_SUBSTEPS,
        "legacy_config": json_value(asdict(config)), "legacy_system_mapping": LEGACY_SYSTEM,
        "legacy_disturbance_field_meaning": "M6R_synthetic_injection_disabled_not_the_external_M8_force",
        "native_runner": "unchanged_m6r_runtime.run_dependency_injection",
        "motor_command_authority": "accepted_runner_only_exact_online_action_replay_required",
        "force_gate_phase": "active_controller_decision_verified_against_native_log_not_nominal_schedule",
        "force_input_independent_of_verifier_or_final_task_score": True,
        "recovery": "accepted_EffectAlignedRecovery_one_episode_400_actions" if system == "v2" else None,
        "task_controller_scorer_recovery_changes": "none", **identity}
    write_json(output / "m8_manifest.json", manifest)
    carrier = {"scope": manifest["scope"], "confirmatory": False, "state": "starting", "seed": seed,
        "system": system, "point_id": point_id, "fresh_study_started": False, "physical_force_applied": False}
    try:
        with (output / "physics.jsonl").open("x", buffering=1) as physical_log, \
                (output / "controller_gate.jsonl").open("x", buffering=1) as gate_log:
            def record(value):
                physical_log.write(json.dumps(json_value(value), allow_nan=False) + "\n")
            def gate(value):
                gate_log.write(json.dumps(json_value(value), allow_nan=False) + "\n")
            def create(c):
                return DecisionTraceEnvironment(build_env(c))
            def reset(env, s):
                observation, info, support = reset_native(env, s)
                env.initialize(observation, info, json_value(env.unwrapped.agent.robot.pose.raw_pose), system, gate)
                env.trace = ForceTrace(env, point, record)
                record({"event": "force_trace_started", "seed": s, "point": point,
                    "actual_gravity_world_m_s2": json_value(env.unwrapped.sim_config.scene_config.gravity),
                    "actual_timestep_s": float(env.unwrapped.scene.px.timestep)})
                return observation, info, support
            def observe(env, observation, info):
                observation, info = observe_native(env, observation, info)
                env.accept_observation(observation, info)
                return observation, info
            result = accepted_run(config, env_factory=create, reset_fn=reset, observe_fn=observe)
        native = Path(result["run_directory"])
        carrier.update(state=result["state"], run_relative=str(native.relative_to(output)),
                       native_config=json_value(asdict(config)), episode=result["episodes"][0],
                       verification_metrics=result["evaluation"]["verification_metrics"])
        replay = check_trial(native, config, identity["software"])
        write_json(output / "accepted_runner_replay.json", replay)
        physical = audit_physics(output, carrier, point)
        write_json(output / "physics_audit.json", physical)
        checked_gate = audit_gate(output, carrier)
        write_json(output / "controller_gate_audit.json", checked_gate)
        if not all(a["passed"] for a in (replay, physical, checked_gate)):
            raise ValueError("Invalid accepted/physics/controller-gate replay; retain all evidence")
        carrier.update(physical_force_applied=physical["force_calls"] > 0, physical_effects=physical["effects"],
                       physics_audit_passed=True, controller_gate_audit_passed=True,
                       state="finished_valid_development_evidence")
    except BaseException as error:
        carrier.update(state="error_retained", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        raise
    finally:
        write_json(output / "m8_result.json", carrier)
    return carrier


def load_case(case):
    carrier = json.loads((case / "m8_result.json").read_text())
    m8 = json.loads((case / "m8_manifest.json").read_text())
    manifest, result, events = load_trial(case / carrier["run_relative"])
    return m8, manifest, result, events


def compare(left, right, kind):
    if kind not in ("passive", "recovery", "pre_force_control"):
        raise ValueError("Unknown matched comparison")
    l8, lm, lr, le = load_case(left)
    r8, rm, rr, re = load_case(right)
    a = [e for e in le if e["event"] == "step"]
    b = [e for e in re if e["event"] == "step"]
    checks = {"shared_software_policy_task_support": all(lm[k] == rm[k] for k in
        ("software", "policy_details", "task_contract", "support_geometry", "robot_base_pose", "upstream_sources_sha256", "action_space_shape")),
        "exact_reset_including_contact": [{k: e[k] for k in ("seed", "observation", "info", "eligibility")} for e in le if e["event"] == "reset"] ==
            [{k: e[k] for k in ("seed", "observation", "info", "eligibility")} for e in re if e["event"] == "reset"],
        "same_config_except_system_output": {k:v for k,v in lm["config"].items() if k not in ("system", "verification", "output")} ==
            {k:v for k,v in rm["config"].items() if k not in ("system", "verification", "output")},
        "both_full_budget_or_same_initial_exclusion": len(a) == len(b) and len(a) in (0, MAX_STEPS)}
    first_action = rr["episodes"][0]["recovery"].get("first_action_step") if kind == "recovery" else None
    trigger = rr["episodes"][0]["recovery"].get("trigger_step") if kind == "recovery" else None
    # A rejected invocation also changes the accepted runner to terminal hold.
    # Its causal prefix ends at the trigger even if no retry action is granted.
    prefix = INJECTION_STEP - 1 if kind == "pre_force_control" else trigger if trigger is not None else MAX_STEPS
    if kind == "pre_force_control":
        checks["system_and_conditions"] = l8["system"] == r8["system"] == "baseline" and l8["point"]["point_id"] == "normal" and r8["point"]["command_force_y_n"] > 0
    else:
        checks["system_and_conditions"] = (l8["system"], r8["system"]) == {"passive": ("baseline", "v1"), "recovery": ("v1", "v2")}[kind] and l8["point"] == r8["point"]
    fields = (*PHYSICAL_FIELDS, "verification") if kind == "recovery" else PHYSICAL_FIELDS
    aa, bb = [e for e in a if e["step"] <= prefix], [e for e in b if e["step"] <= prefix]
    checks["exact_physical_prefix"] = len(aa) == len(bb) and all(all(x[k] == y[k] for k in fields) for x, y in zip(aa, bb))
    pa = [json.loads(l) for l in (left / "physics.jsonl").read_text().splitlines()]
    pb = [json.loads(l) for l in (right / "physics.jsonl").read_text().splitlines()]
    xa = [e for e in pa if e["event"] == "physics_action" and e["step"] <= prefix]
    xb = [e for e in pb if e["event"] == "physics_action" and e["step"] <= prefix]
    checks["exact_physics_prefix"] = len(xa) == len(xb) and all(x["step"] == y["step"] and x["substeps"] == y["substeps"]
        and x["intent"]["nominal_phase"] == y["intent"]["nominal_phase"]
        and x["intent"]["release_support_precondition"] == y["intent"]["release_support_precondition"] for x,y in zip(xa,xb))
    if kind == "recovery":
        episode = rr["episodes"][0]
        checks["bounded_accepted_recovery"] = episode["recovery"]["attempts"] in (0, 1) and episode["recovery"]["action_steps"] <= 400 and rm["recovery_controller"] == json_value(EffectAlignedRecovery(FixedPlacement(next(e["observation"] for e in re if e["event"] == "reset"), rm["robot_base_pose"]), rm["robot_base_pose"], MAX_STEPS).manifest())
        checks["first_action_follows_recorded_trigger"] = first_action is None or episode["recovery"]["trigger_step"] == first_action - 1
    return {"passed": all(checks.values()), "checks": checks, "matched_steps": len(aa),
            "invocation_trigger_step": trigger, "first_recovery_action_step": first_action,
            "prefix_through_step": prefix}


def paired_outcomes(trials):
    lookup = {(t["seed"], t["point_id"], t["system"]): t["result"] for t in trials}
    rows = []
    for seed in DEVELOPMENT_SEEDS:
        for point in candidate_points():
            p = point["point_id"]
            b, v1, v2 = (lookup[seed, p, s] for s in SYSTEMS)
            be, e1, e2 = (r["episode"] for r in (b, v1, v2))
            attempt = bool(e2["recovery"]["attempts"])
            rows.append({"seed": seed, "point_id": p, "command_force_y_n": point["command_force_y_n"],
                "success": {s: r["episode"]["task_success_at_end"] for s,r in zip(SYSTEMS,(b,v1,v2))},
                "excluded": {s:r["episode"]["excluded"] for s,r in zip(SYSTEMS,(b,v1,v2))},
                "force_calls": {s:r["physical_effects"]["force_calls"] for s,r in zip(SYSTEMS,(b,v1,v2))},
                "v2_attempts": e2["recovery"]["attempts"], "v2_recovery_actions": e2["recovery"]["action_steps"],
                "v2_successful_recovery_episode": e2["recovery_task_success"],
                "v2_rescue": not be["excluded"] and not be["task_success_at_end"] and e2["task_success_at_end"],
                "v2_unnecessary_attempt": not be["excluded"] and be["task_success_at_end"] and attempt,
                "v2_final_regression": not be["excluded"] and be["task_success_at_end"] and not e2["task_success_at_end"],
                "v2_added_tcp_path_m": e2["total_observed_tcp_path_m"] - e1["total_observed_tcp_path_m"],
                "v1_detection": e1["first_detected_failure"], "v2_detection": e2["first_detected_failure"],
                "v2_recovery": e2["recovery"], "v2_lower_transition_step": e2["lower_transition_step"],
                "v2_release_executed": e2["recovery_release_executed"], "v2_retraction_executed": e2["recovery_retraction_executed"]})
    return rows


def run_suite(output, destination, expected_head):
    output, destination = output.resolve(), destination.resolve()
    if output.exists() or destination.exists() or destination.is_relative_to(output):
        raise FileExistsError("Require new separate matched development paths; no resume/reruns")
    output.mkdir(parents=True, exist_ok=False)
    with (output / ".lock").open("x") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = {"scope": "M8_known_seed_matched_force_commissioning", "confirmatory": False,
            "state": "starting", "time_utc": datetime.now(timezone.utc).isoformat(), "seeds": list(DEVELOPMENT_SEEDS),
            "systems": list(SYSTEMS), "points": [], "plan": [], "trials": [], "fresh_study_started": False,
            "force_family_frozen_for_fresh_study": False, "dose_review_sha256": DOSE_REVIEW_SHA256,
            "performance_success_gate": "none_failures_exclusions_nonapplication_retained",
            "next_boundary": "independent_matched_review_before_fresh_preregistration"}
        try:
            report["points"], report["plan"] = candidate_points(), plan()
            report["identity"] = preflight(expected_head)
            snapshots = output / "sources"; snapshots.mkdir()
            for n in (*receipt()["accepted_placement_sources_sha256"], *SOURCE_FILES):
                (snapshots / n).write_bytes(Path(__file__).with_name(n).read_bytes())
            for p in (RECEIPT, RESPONSE_REVIEW, DOSE_REVIEW):
                (snapshots / p.name).write_bytes(p.read_bytes())
            report["state"] = "running"; write_json(output / "suite.json", report)
            for item in report["plan"]:
                case = output / f"slot-{item['slot']:02d}-{item['point_id']}-seed{item['seed']}-{item['system']}"
                case.mkdir(exist_ok=False)
                print(f"START {item['slot']+1}/36 {item['point_id']} seed{item['seed']} {item['system']}", flush=True)
                record = {**item, "directory": str(case.relative_to(output)), "returncode": None,
                          "result": {"state": "started_pending_child_result"}}
                report["trials"].append(record); write_json(output / "suite.json", report)
                command = [sys.executable, "-u", "-m", "aether_cl.m8_matched", "--child", "--expected-head", expected_head,
                    "--output", str(case), "--seed", str(item["seed"]), "--system", item["system"], "--point", item["point_id"]]
                try:
                    with (case / "stdout.log").open("x") as stream:
                        process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
                except subprocess.TimeoutExpired:
                    record.update(result={"state": "child_timeout_retained", "timeout_s": 600,
                        "partial_evidence_directory": record["directory"], "replacement": False})
                    raise
                child = json.loads((case / "m8_result.json").read_text()) if (case / "m8_result.json").exists() else {"state": "missing_child_result"}
                record.update(returncode=process.returncode, result=child); write_json(output / "suite.json", report)
                print(f"END {item['slot']+1}/36 {child['state']}", flush=True)
                if process.returncode or child["state"] != "finished_valid_development_evidence":
                    raise ValueError("Matched child failed; retain all started evidence, no fallback/replacement")
                preflight(expected_head)
            locate = {(t["seed"], t["point_id"], t["system"]): output / t["directory"] for t in report["trials"]}
            comparisons = []
            for seed in DEVELOPMENT_SEEDS:
                for point in candidate_points():
                    p = point["point_id"]
                    for kind, a, b in (("passive", "baseline", "v1"), ("recovery", "v1", "v2")):
                        comparisons.append({"kind": kind, "seed": seed, "point_id": p,
                            **compare(locate[seed,p,a], locate[seed,p,b], kind)})
                    if p != "normal":
                        comparisons.append({"kind": "pre_force_control", "seed": seed, "point_id": p,
                            **compare(locate[seed,"normal","baseline"], locate[seed,p,"baseline"], "pre_force_control")})
            report["comparisons"] = comparisons
            report["paired_outcomes"] = paired_outcomes(report["trials"])
            report["state"] = "valid_development_evidence" if all(c["passed"] for c in comparisons) else "invalid_comparison_evidence_retained"
            report["interpretation"] = "known_two_scene_development_only_no_fresh_evaluation_or_training"
        except BaseException as error:
            report.update(state="error_retained", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
            print(report["error"], flush=True)
        finally:
            write_json(output / "suite.json", report)
            archive(output, destination)
        if report["state"] != "valid_development_evidence":
            raise SystemExit(1)
        print("M8_MATCHED_COMMISSION_VALID", flush=True)
        print("No fresh seeds executed; return archive for independent matched-system review", flush=True)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path)
    cli.add_argument("--expected-head", required=True)
    cli.add_argument("--child", action="store_true")
    cli.add_argument("--seed", type=int)
    cli.add_argument("--system", choices=SYSTEMS)
    cli.add_argument("--point")
    args = cli.parse_args()
    if args.child:
        run_child(args.output, args.expected_head, args.seed, args.system, args.point)
        print("M8_MATCHED_CHILD_VALID", args.seed, args.point, args.system, flush=True)
    else:
        if args.archive is None or any(v is not None for v in (args.seed, args.system, args.point)):
            cli.error("Suite requires --archive and uses its fixed36 known-seed plan")
        run_suite(args.output, args.archive, args.expected_head)


if __name__ == "__main__":
    main()
