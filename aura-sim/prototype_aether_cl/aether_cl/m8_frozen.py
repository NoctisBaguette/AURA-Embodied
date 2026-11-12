"""Frozen M8 contract, native evidence checks and parent-authorized fresh child."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tarfile
import traceback

from .acceptance import load_trial
from .runtime import build_env, json_value
from .m6_runtime import reset_native, observe_native
from .m6_task import task_manifest
from .m6_policy import INJECTION_STEP, MAX_STEPS, PlacementRecoverySettings
from .m6r_policy import LOWER_CONTRACT
from .m6r_runtime import M6RConfig, run as accepted_run
from .m6r_audit import check_trial
from .m5_attribution import VOLATILE_ENVIRONMENT
from .m8_force import ROOT, RECEIPT, ForceTrace, WINDOW_SUBSTEPS, receipt, sha256
from .m8_force_commission import audit_physics as known_physics, write_json
from .m8_matched import (SYSTEMS, LEGACY_SYSTEM, POINT_IDS, candidate_points, legacy_config,
    preflight as matched_preflight, DecisionTraceEnvironment, audit_gate, compare,
    plan as commission_plan, paired_outcomes as commission_pairs, DOSE_REVIEW)
from .m8_force_refine import RESPONSE_REVIEW

SEEDS = tuple(range(160, 180))
SCOPE = "m8_seed160_179_physics_propagated_placement"
AUTHORITY = "4d477da2a583717b773b3a1c746996a3c2127e40"
REVIEW = RECEIPT.with_name("AETHER_CL_M8_Matched_Commission_Review_v1.json")
REVIEW_SHA256 = "4b9d0e9f83d050e1b5c22d69f7f48e5801636cb132e25c0afc38c05ed3b73577"
COMMISSION_COMMIT = "a910a8cab8b0f0f67daeb0178f44457383aab814"
COMMISSION_ARCHIVE_SHA256 = "f8a05548c08e08a8b93f60dca2a29a14f919abf7e34e379fbe12ac256e2c165c"
PROTOCOL_PATH = RECEIPT.with_name("AETHER_CL_M8_Placement_Protocol.json")
HISTORY_SOURCE = ROOT / "tools/m8_physics_inspection.py"
SOURCES = (*receipt()["accepted_placement_sources_sha256"], "m6r_audit.py", "m8_force.py",
           "m8_force_commission.py", "m8_force_refine.py", "m8_matched.py", "m8_frozen.py", "m8_sweep.py")
SESSION_FIELDS = (*VOLATILE_ENVIRONMENT, "XDG_SESSION_ID")
PILOT_POINTS = ("normal", "force-easy-v1", "force-probe-2")


def reviewed_commission():
    if sha256(REVIEW) != REVIEW_SHA256:
        raise ValueError("Require the independently audited matched commissioning receipt")
    review = json.loads(REVIEW.read_text())
    if (not review["all_audit_checks_passed"] or review["fresh_study_started"]
            or review["measurement_commit"] != COMMISSION_COMMIT
            or review["archive_sha256"] != COMMISSION_ARCHIVE_SHA256
            or review["totals"]["native_trial_count"] != 36):
        raise ValueError("Invalid commissioning review provenance")
    return review


def protocol():
    reviewed_commission()
    return {"name": SCOPE, "date": "2026-10-08", "authority_commit": AUTHORITY,
        "status": "frozen_before_fresh_native_M8", "seeds": list(SEEDS), "systems": list(SYSTEMS),
        "points": candidate_points(), "requested_episodes": 360, "cells": 18, "episodes_per_cell": 20,
        "analysis_unit": "20_common_seed_scenes_reused_across_conditions_and_systems_not360_independent_scenes",
        "seed_selection": "preselected160_179_only_if_retained_history_unused_no_adaptive_replacement",
        "task": "PickCube-v1_accepted_released_support_placement", "task_contract": task_manifest(),
        "physics_backend": "cpu", "robot": "panda", "observation_mode": "state_dict",
        "control_mode": "pd_ee_pose", "render": False, "max_steps": MAX_STEPS,
        "nominal_controller": "unchanged_FixedPlacement", "legacy_system_mapping": LEGACY_SYSTEM,
        "recovery_controller": "unchanged_accepted_EffectAlignedRecovery",
        "recovery_settings": json_value(asdict(PlacementRecoverySettings())), "lower_contract": LOWER_CONTRACT,
        "recovery_attempts_maximum": 1, "force_api": "PhysxRigidBodyComponent.add_force_torque",
        "mode": "force", "world_axis": "+Y", "torque_world_nm": [0., 0., 0.],
        "injection_action": INJECTION_STEP, "window_substeps": WINDOW_SUBSTEPS,
        "actual_timestep_s": receipt()["actual_timestep_s"], "nominal_duration_s": .05,
        "force_gate": "active_nominal_retract_released_geometry_designated_support_not_grasped_contact_z_at_least0.01N",
        "missed_precondition_or_initial_failure": "retain_nonapplication_and_outcome_no_retime_or_replacement",
        "disturbance_implementation": "unchanged_engine_force_adapter_no_cube_pose_or_velocity_overwrite",
        "force_input_and_actual_effect": "report_separately_input_monotonic_effect_need_not_be",
        "point_label_provenance": "retained_development_identifiers_frozen_vectors_not_displacement_targets",
        "pilot": {"episodes": 18, "points": list(PILOT_POINTS), "seeds": list(SEEDS[:2]),
            "retained_in_final": True, "gate": "complete_replays_identities_pairs_and_fixed_force_provenance_no_task_success_gate",
            "review_boundary": "pause_first18_for_independent_review_before342_unstarted_slots"},
        "order": "pilot_point_seed_system_then_remaining_point_seed_system_skip_only_completed_pilot_slots",
        "comparison_counts": {"passive": 120, "recovery": 120, "pre_force_control": 100},
        "pilot_comparison_counts": {"passive": 6, "recovery": 6, "pre_force_control": 4},
        "action_replay_tolerance": 3e-7, "physical_pair_tolerance": "exact_no_relaxation",
        "execution": "fresh_interpreter_and_native_environment_per_slot_all800_actions_unless_frozen_initial_goal_exclusion",
        "model_training": False, "performance_gate": "none_task_failures_retained",
        "resume": "only_unstarted_slots_from_valid_paused_checkpoint_full_hash_replay_and_immutable_pilot_checks",
        "environment_normalization": list(SESSION_FIELDS), "child_timeout_s": 600,
        "constructor_initialization_reset_seeds": receipt()["constructor_initialization_reset_seeds"],
        "commissioning_commit": COMMISSION_COMMIT, "commissioning_archive_sha256": COMMISSION_ARCHIVE_SHA256,
        "commissioning_review_sha256": REVIEW_SHA256,
        "sources_sha256": {n: sha256(Path(__file__).with_name(n)) for n in SOURCES},
        "history_guard_source_sha256": sha256(HISTORY_SOURCE),
        "receipt_sources_sha256": {p.name: sha256(p) for p in (RECEIPT, RESPONSE_REVIEW, DOSE_REVIEW, REVIEW)},
        "return_boundary": "after_frozen_native_M8_and_independent_audit_return_to02_before_further_scope",
        "limitations": "privileged_state_one_cube_one_arm_engine_force_single_recovery_no_sensor_verifier_or_learning"}


def environment():
    return {k: v for k, v in os.environ.items() if k not in SESSION_FIELDS}


def environment_digest(values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def preflight(expected_head):
    settings = protocol()
    if json.loads(PROTOCOL_PATH.read_text()) != settings:
        raise ValueError("M8 source/protocol differs from frozen preregistration")
    identity = matched_preflight(expected_head)
    commissioned = reviewed_commission()["native_identity"]
    # Only the published wrapper revision changes. The native arithmetic,
    # libraries, driver, installed sources and accepted controllers stay fixed.
    if ({k:v for k,v in identity["software"].items() if k != "git_commit"}
            != {k:v for k,v in commissioned["software"].items() if k != "git_commit"}
            or any(identity[k] != commissioned[k] for k in
                ("receipt_sha256", "installed_sources_sha256", "accepted_placement_sources_sha256",
                 "sapien_binaries", "development_sources_sha256", "response_review_sha256", "dose_review_sha256"))):
        raise ValueError("Native environment or commissioned source bytes changed")
    identity.update(development_stage="frozen_fresh_M8", study_sources_sha256=settings["sources_sha256"],
                    commissioning_review_sha256=REVIEW_SHA256,
                    startup_environment_sha256=environment_digest(environment()))
    return settings, identity


class HistoryView:
    """Read-only filtered view; only a fully validated own checkpoint is omitted."""
    def __init__(self, root, excluded=None):
        self.root, self.excluded = root, excluded
    def __fspath__(self):
        return str(self.root)
    def __str__(self):
        return str(self.root)
    def is_dir(self):
        return self.root.is_dir()
    def rglob(self, pattern):
        return (p for p in self.root.rglob(pattern)
                if self.excluded is None or not p.resolve().is_relative_to(self.excluded))


def seed_history(output, resume=False):
    spec = importlib.util.spec_from_file_location("m8_pinned_history_inspector", HISTORY_SOURCE)
    inspector = importlib.util.module_from_spec(spec); spec.loader.exec_module(inspector)
    root = Path(__file__).resolve().parents[1] / "runs"
    scanned = inspector.inspect_history(HistoryView(root, output.resolve() if resume else None), print)
    overlap = sorted(set(scanned["recorded_reset_seeds"]) & set(SEEDS))
    if overlap:
        raise ValueError("Frozen fresh seeds already reset outside the validated study: " + str(overlap))
    return {**scanned, "selected_seeds": list(SEEDS), "selected_overlap": overlap,
            "own_validated_study_excluded": resume, "selection_frozen": True}


def file_index(root):
    rows = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("Evidence symlinks are not supported")
        if p.is_file() and p.name not in ("file_index.json", ".lock", "runner.lock"):
            rows[str(p.relative_to(root))] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    return rows


def verify_index(root):
    recorded = json.loads((root / "file_index.json").read_text())
    if recorded != file_index(root):
        raise ValueError("Retained raw file set, size or hash differs")
    return recorded


def audit_physics(output, carrier, point):
    # All physical checks remain the commissioned auditor. Replace only its
    # development-seed membership predicate with the frozen fresh-seed scope.
    audit = known_physics(output, carrier, point)
    starts = [json.loads(l) for l in (output / "physics.jsonl").read_text().splitlines()
              if json.loads(l)["event"] == "force_trace_started"]
    checks = dict(audit["checks"]); checks.pop("one_known_reset")
    checks["one_selected_fresh_reset"] = (type(carrier["seed"]) is int and carrier["seed"] in SEEDS
        and len(starts) == 1 and starts[0]["seed"] == carrier["seed"])
    return {**audit, "checks": checks, "passed": all(checks.values()),
            "failed_checks": [k for k,v in checks.items() if not v]}


def checked_trial(output, item, identity):
    carrier = json.loads((output / "m8_result.json").read_text())
    manifest = json.loads((output / "m8_manifest.json").read_text())
    expected = legacy_config(output, item["seed"], item["system"])
    registration = {"protocol_sha256": sha256(PROTOCOL_PATH), "authority_commit": AUTHORITY}
    if (carrier["state"] != "finished_valid_frozen_evidence" or not carrier["confirmatory"]
            or carrier["scope"] != SCOPE
            or manifest["scope"] != SCOPE or not manifest["confirmatory"]
            or manifest["preregistration"] != registration
            or manifest["point"] != next(p for p in candidate_points() if p["point_id"] == item["point_id"])
            or carrier["native_config"] != json_value(asdict(expected))
            or manifest["legacy_config"] != json_value(asdict(expected))
            or manifest["legacy_system_mapping"] != LEGACY_SYSTEM or manifest["output"] != str(output.resolve())
            or any(carrier[k] != item[k] or manifest[k] != item[k] for k in ("seed", "system", "point_id"))
            or any(manifest[k] != v for k,v in identity.items())):
        raise ValueError("Fresh child scope/configuration/identity differs from selected frozen slot")
    native = (output / carrier["run_relative"]).resolve()
    if not native.is_relative_to(output.resolve() / "native"):
        raise ValueError("Native evidence lies outside selected child")
    replay = check_trial(native, expected, identity["software"])
    physical, gate = audit_physics(output, carrier, manifest["point"]), audit_gate(output, carrier)
    _, result, _ = load_trial(native)
    if (not all(a["passed"] for a in (replay, physical, gate)) or result["episodes"] != [carrier["episode"]]
            or result["evaluation"]["verification_metrics"] != carrier["verification_metrics"]
            or physical["effects"] != carrier["physical_effects"]
            or carrier["physical_force_applied"] != bool(physical["force_calls"])):
        raise ValueError("Invalid accepted, physics or instrumentation replay")
    for name, audit in (("accepted_runner_replay.json", replay), ("physics_audit.json", physical),
                        ("controller_gate_audit.json", gate)):
        if json.loads((output / name).read_text()) != json_value(audit):
            raise ValueError("Recorded audit differs from independent reconstruction: " + name)
    return carrier


def validate_commission(report_path, archive_path):
    review = reviewed_commission(); root = report_path.resolve().parent
    if sha256(archive_path) != COMMISSION_ARCHIVE_SHA256:
        raise ValueError("Commissioning archive differs from independently reviewed evidence")
    indexed = verify_index(root); report = json.loads(report_path.read_text())
    with tarfile.open(archive_path) as tar:
        if json.load(tar.extractfile("m8-force-commission/file_index.json")) != indexed:
            raise ValueError("Commissioning live index differs from immutable archive")
        if tar.extractfile("m8-force-commission/suite.json").read() != report_path.read_bytes():
            raise ValueError("Commissioning report differs from reviewed immutable archive")
    if (report["state"] != "valid_development_evidence" or report["fresh_study_started"]
            or report["plan"] != commission_plan() or len(report["trials"]) != 36
            or report["identity"] != review["native_identity"]):
        raise ValueError("Commissioning plan/scope/identity differs")
    for snapshot in review["source_snapshots"]:
        if sha256(root / "sources" / snapshot["name"]) != snapshot["sha256"]:
            raise ValueError("Commissioned source snapshot differs")
    for item, trial in zip(commission_plan(), report["trials"]):
        if any(trial[k] != v for k,v in item.items()) or trial["returncode"] != 0:
            raise ValueError("Commissioning slot or completion differs")
        case = root / trial["directory"]; carrier = json.loads((case / "m8_result.json").read_text())
        manifest = json.loads((case / "m8_manifest.json").read_text())
        config = M6RConfig(**{**carrier["native_config"], "output": Path(carrier["native_config"]["output"])})
        audits = (check_trial(case / carrier["run_relative"], config, report["identity"]["software"]),
                  known_physics(case, carrier, manifest["point"]), audit_gate(case, carrier))
        if (carrier != trial["result"] or carrier["state"] != "finished_valid_development_evidence"
                or not all(a["passed"] for a in audits)):
            raise ValueError("Commissioning original trial no longer replays")
    pairs = comparisons(report["trials"], root)
    if pairs != report["comparisons"] or pairs != review["comparisons"]:
        raise ValueError("Commissioning matched comparisons differ")
    if commission_pairs(report["trials"]) != report["paired_outcomes"]:
        raise ValueError("Commissioning paired outcomes differ")
    return {"archive_sha256": COMMISSION_ARCHIVE_SHA256, "producer_commit": COMMISSION_COMMIT,
            "indexed_files": len(indexed), "replayed_trials": 36, "comparisons": len(pairs),
            "review_sha256": REVIEW_SHA256, "report_sha256": sha256(report_path)}


def comparisons(trials, root):
    locate = {(t["seed"],t["point_id"],t["system"]): root / t["directory"] for t in trials
              if t["result"]["state"] in ("finished_valid_development_evidence", "finished_valid_frozen_evidence")}
    rows = []
    seeds = sorted({t["seed"] for t in trials})
    for seed in seeds:
        for point in candidate_points():
            p = point["point_id"]
            for kind,a,b in (("passive","baseline","v1"),("recovery","v1","v2")):
                if (seed,p,a) in locate and (seed,p,b) in locate:
                    rows.append({"kind":kind,"seed":seed,"point_id":p,**compare(locate[seed,p,a],locate[seed,p,b],kind)})
            if p != "normal" and (seed,"normal","baseline") in locate and (seed,p,"baseline") in locate:
                rows.append({"kind":"pre_force_control","seed":seed,"point_id":p,
                    **compare(locate[seed,"normal","baseline"],locate[seed,p,"baseline"],"pre_force_control")})
    return rows


def run_fresh(output, expected_head, seed, system, point_id, suite_path):
    output = output.resolve()
    if type(seed) is not int or seed not in SEEDS or system not in SYSTEMS or point_id not in POINT_IDS:
        raise ValueError("Fresh child only accepts the frozen matrix")
    settings, identity = preflight(expected_head)
    report = json.loads(suite_path.read_text()); last = report["trials"][-1] if report["trials"] else {}
    selected = {"seed":seed,"system":system,"point_id":point_id,"output":str(output)}
    if (report["state"] != "running" or report["runner_pid"] != os.getppid()
            or report["protocol"] != settings or report["identity"] != identity
            or last["result"]["state"] != "started_pending_child_result"
            or any(last.get(k) != v for k,v in selected.items())):
        raise ValueError("Fresh reset must be the selected slot of its live guarded sweep parent")
    if (output / "m8_manifest.json").exists() or (output / "native").exists():
        raise FileExistsError("Retain earlier fresh child; no reruns")
    output.mkdir(parents=True, exist_ok=True)
    config = legacy_config(output, seed, system)
    point = next(p for p in settings["points"] if p["point_id"] == point_id)
    manifest = {"scope":SCOPE,"confirmatory":True,**selected,"point":point,
        "preregistration":{"protocol_sha256":sha256(PROTOCOL_PATH),"authority_commit":AUTHORITY},
        "legacy_config":json_value(asdict(config)),"legacy_system_mapping":LEGACY_SYSTEM,
        "legacy_disturbance_field_meaning":"M6R_synthetic_relocation_disabled_external_M8_force_separate",
        "native_runner":"unchanged_accepted_m6r_runtime.run_dependency_injection",
        "motor_command_authority":"accepted_runner_only_instrumentation_replay_must_match",**identity}
    write_json(output / "m8_manifest.json", manifest)
    carrier = {"scope":SCOPE,"confirmatory":True,"state":"starting","seed":seed,"system":system,
               "point_id":point_id,"physical_force_applied":False}
    try:
        with (output / "physics.jsonl").open("x",buffering=1) as physical_log, \
                (output / "controller_gate.jsonl").open("x",buffering=1) as gate_log:
            def record(value):physical_log.write(json.dumps(json_value(value),allow_nan=False)+"\n")
            def gate(value):gate_log.write(json.dumps(json_value(value),allow_nan=False)+"\n")
            def create(c):return DecisionTraceEnvironment(build_env(c))
            def reset(env,s):
                observation,info,support = reset_native(env,s)
                env.initialize(observation,info,json_value(env.unwrapped.agent.robot.pose.raw_pose),system,gate)
                env.trace = ForceTrace(env,point,record)
                record({"event":"force_trace_started","seed":s,"point":point,
                    "actual_gravity_world_m_s2":json_value(env.unwrapped.sim_config.scene_config.gravity),
                    "actual_timestep_s":float(env.unwrapped.scene.px.timestep)})
                return observation,info,support
            def observe(env,observation,info):
                observation,info = observe_native(env,observation,info)
                env.accept_observation(observation,info)
                return observation,info
            result = accepted_run(config,env_factory=create,reset_fn=reset,observe_fn=observe)
        carrier.update(run_relative=str(Path(result["run_directory"]).relative_to(output)),
            native_config=json_value(asdict(config)),episode=result["episodes"][0],
            verification_metrics=result["evaluation"]["verification_metrics"])
        replay = check_trial(output / carrier["run_relative"],config,identity["software"])
        physical, gate_checked = audit_physics(output,carrier,point),audit_gate(output,carrier)
        for name,audit in (("accepted_runner_replay.json",replay),("physics_audit.json",physical),
                           ("controller_gate_audit.json",gate_checked)):
            write_json(output / name,audit)
        if not all(a["passed"] for a in (replay,physical,gate_checked)):
            raise ValueError("Invalid fresh accepted/physics/controller-gate replay")
        carrier.update(physical_force_applied=physical["force_calls"] > 0,physical_effects=physical["effects"],
                       state="finished_valid_frozen_evidence")
    except BaseException as error:
        carrier.update(state="error_retained",error=f"{type(error).__name__}: {error}",traceback=traceback.format_exc())
        raise
    finally:
        write_json(output / "m8_result.json",carrier)
    return carrier


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output",type=Path,required=True);cli.add_argument("--expected-head",required=True)
    cli.add_argument("--seed",type=int,choices=SEEDS,required=True)
    cli.add_argument("--system",choices=SYSTEMS,required=True);cli.add_argument("--point",choices=POINT_IDS,required=True)
    cli.add_argument("--suite",type=Path,required=True)
    args=cli.parse_args()
    run_fresh(args.output,args.expected_head,args.seed,args.system,args.point,args.suite)
    print("M8_FROZEN_CHILD_VALID",args.seed,args.point,args.system,flush=True)


if __name__=="__main__":main()
