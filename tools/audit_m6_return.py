"""Read-only replay and independent endpoint audit of returned M6 evidence.

Usage: python tools/audit_m6_return.py --evidence-root EXTRACTED_PARENT --output NEW_JSON
Archives must first be safely extracted with directory names matching their names.
This does not import or execute the native simulator, change traces, or rerun trials.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aura-sim/prototype_aether_cl"))
from aether_cl import m6_sweep as sweep
from aether_cl.acceptance import load_trial
from aether_cl.m6_audit import check_trial, compare
from aether_cl.runtime import json_value


SCIENCE_COMMIT = "7059c713d3b36e3f032aab8d1f87662ed6fdab91"
EXPECTED_ARCHIVES = {
    "aether-cl-m6-placement-seeds100-119": "21b1739df6a8f66ecb2af5bb6dc865b3b96d7ffbb44ebbec030237ace2b3843e",
    "aether-cl-m6-placement-seeds100-119-pilot": "abc010ff900bab2f507f866046125ad86726e146f63c5e156274448990d0a1a5",
    "aether-cl-m6-before-report-repair": "cd22ce263eb507be262064c3da6bfeff7a86fba2d68d95c6d163da9909de09c3"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_index(root):
    index = json.loads((root / "archive_index.json").read_text())
    names = set()
    for e in index["files"]:
        p = Path(e["path"])
        assert p.parts[0] == root.name and not p.is_absolute() and ".." not in p.parts
        relative = Path(*p.parts[1:]).as_posix()
        assert relative not in names
        names.add(relative)
        actual = root / relative
        assert actual.is_file() and actual.stat().st_size == e["bytes"] and digest(actual) == e["sha256"], relative
    assert names | {"archive_index.json"} == {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    return {"indexed_files": len(names), "all_hashes_sizes_members_passed": True}


def independent_endpoint(events):
    """Recompute the frozen success conjunction directly, without task/evaluator helpers."""
    reset = next(e for e in events if e["event"] == "reset")
    initial = np.asarray(reset["observation"]["extra"]["obj_pose"], dtype=float).reshape(7)[:3]
    goal = np.asarray(reset["observation"]["extra"]["goal_pos"], dtype=float).reshape(3)
    eligible = np.linalg.norm(initial[:2] - goal[:2]) > .025
    previous = np.asarray(reset["observation"]["extra"]["obj_pose"], dtype=float).reshape(7)
    contact_grasp = release_command = False
    lift = 0.; stable = support_stable = 0
    count = 0; final = None; first_success = None
    for e in events:
        if e["event"] != "step": continue
        count += 1
        x = e["observation"]["extra"]
        pose = np.asarray(x["obj_pose"], dtype=float).reshape(7)
        tcp = np.asarray(x["tcp_pose"], dtype=float).reshape(7)[:3]
        current_goal = np.asarray(x["goal_pos"], dtype=float).reshape(3)
        q = pose[[4, 5, 6, 3]]; pq = previous[[4, 5, 6, 3]]
        rot = Rotation.from_quat(q)
        extent = .02 * np.abs(rot.as_matrix()).sum(axis=1)
        aperture = np.asarray(e["observation"]["agent"]["qpos"], dtype=float).reshape(9)[-2:].sum()
        gap = np.linalg.norm(tcp - pose[:3])
        grasped = bool(np.asarray(e["info"]["is_grasped"]).reshape(1)[0])
        contact_grasp |= grasped
        release_command |= e["controller_decision"]["phase"].removeprefix("recovery_") == "release" and e["controller_decision"]["gripper"] == "open"
        lift = max(lift, float(pose[2] - initial[2]))
        candidate = gap <= .04 and .01 <= aperture <= .06
        released = contact_grasp and release_command and not grasped and aperture >= .06 and not candidate
        support = (abs(pose[2] - extent[2]) <= .004 and np.all(np.abs(pose[:2]) + extent[:2] <= .40)
                   and abs(np.asarray(e["info"]["cube_table_contact_force_world_n"]).reshape(3)[2]) >= .01)
        retracted = gap >= .08 and tcp[2] - pose[2] >= .08
        still = (np.linalg.norm(np.asarray(x["obj_linear_velocity"]).reshape(3)) <= .01
                 and np.linalg.norm(np.asarray(x["obj_angular_velocity"]).reshape(3)) <= .2
                 and np.linalg.norm(pose[:3] - previous[:3]) <= .001
                 and (rot * Rotation.from_quat(pq).inv()).magnitude() <= .02)
        supported_ready = released and support and retracted and still
        support_stable = support_stable + 1 if supported_ready else 0
        ready = eligible and supported_ready and lift >= .05 and np.linalg.norm(pose[:2] - current_goal[:2]) <= .025 and np.linalg.norm(current_goal - goal) <= 1e-6
        stable = stable + 1 if ready else 0
        success = stable >= 5
        if success and first_success is None: first_success = e["step"]
        final = {"task_success": bool(success), "release_success": bool(released), "supported": bool(support),
                 "retracted": bool(retracted), "stable_frame": bool(still), "support_stability_success": bool(support_stable >= 5),
                 "stable_steps": stable, "support_stable_steps": support_stable}
        for k, value in final.items(): assert value == e["reference"][k], (e["step"], k)
        previous = pose
    assert count == (800 if eligible else 0)
    return {"passed": True, "eligible": bool(eligible), "actions": count, "first_success_step": first_success, "final": final}


def trial_job(job):
    directory, trial, software = job
    checked = json_value(check_trial(Path(directory), sweep.config_for(trial), software))
    assert checked["passed"], checked["failed_checks"]
    assert all(trial[k] == v for k, v in checked.items())
    manifest, result, events = load_trial(Path(directory))
    endpoint = independent_endpoint(events)
    assert result["episodes"][0]["task_success_at_end"] == bool(endpoint["final"] and endpoint["final"]["task_success"])
    assert result["episodes"][0]["first_task_success_step"] == endpoint["first_success_step"]
    steps = [e for e in events if e["event"] == "step"]
    detail = {"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"], "replay": checked,
              "independent_endpoint": endpoint, "injections": [e["disturbance"] for e in events if e["event"] == "disturbance_attempted"]}
    if trial["system"] == "v2" and result["episodes"][0]["recovery"]["attempts"]:
        abort = next(e for e in steps if e["recovery"]["state"] == "aborted")
        decision = abort["controller_decision"]
        target = np.array(decision["expected_tcp_position_world_m"])
        tcp_pose = np.asarray(abort["observation"]["extra"]["tcp_pose"]).reshape(7)
        # The common Panda grasp rotation is separately recoverable from the unchanged primitive.
        from aether_cl.m6_policy import FixedPlacement
        policy = FixedPlacement(next(e for e in events if e["event"] == "reset")["observation"], manifest["robot_base_pose"])
        actual_r = Rotation.from_quat(tcp_pose[[4, 5, 6, 3]]).as_matrix()
        angle = Rotation.from_matrix(actual_r @ policy.primitive.grasp_rotation.T).magnitude()
        detail["abort"] = {"step": abort["step"], "reason": abort["recovery"]["failure_detail"], "phase": decision["phase"],
                           "phase_step": decision["phase_step"], "attempt_actions": abort["recovery"]["action_steps"],
                           "tcp_world_m": tcp_pose[:3].tolist(), "target_world_m": target.tolist(),
                           "tcp_target_distance_m": float(np.linalg.norm(tcp_pose[:3] - target)),
                           "lower_vertical_error_m": float(abs(tcp_pose[2] - target[2])),
                           "rotation_error_rad": float(angle), "contact_grasped": abort["reference"]["is_grasped"],
                           "contact_supported": abort["reference"]["supported"],
                           "horizontal_error_m": abort["reference"]["horizontal_error_m"],
                           "vertical_table_contact_force_n": abort["reference"]["cube_table_contact_force_world_n"][2],
                           "attempt_lift_m": abort["recovery"]["attempt_max_cube_lift_m"],
                           "release_phase_executed_during_attempt": any(e["controller_decision"]["phase"] == "recovery_release" for e in steps),
                           "all_terminal_actions_repeat_abort": all(e["action"] == abort["action"] for e in steps if e["step"] > abort["step"]),
                           "final_grasped": steps[-1]["reference"]["is_grasped"]}
    if trial["point_id"] == "release-shift-040mm" and trial["system"] == "baseline" and steps:
        relevant = {e["step"]: e for e in steps}
        detail["passive_4cm_drift"] = {"positions_world_m": {str(n): relevant[n]["observation"]["extra"]["obj_pose"][0][:3] for n in (295, 296, 300, 330, 340, 800)},
                                     "horizontal_error_m": {str(n): relevant[n]["reference"]["horizontal_error_m"] for n in (295, 296, 300, 330, 340, 800)}}
    return detail


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--evidence-root", type=Path, required=True)
    cli.add_argument("--upload-root", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--workers", type=int, default=4)
    args = cli.parse_args()
    roots = {name: args.evidence_root / name / ("m6-before-report-repair" if name.endswith("repair") else "m6-placement") for name in EXPECTED_ARCHIVES}
    archives = {}
    for name, expected in EXPECTED_ARCHIVES.items():
        p = args.upload_root / (name + ".tar.gz")
        actual = digest(p); assert actual == expected
        archives[name] = {"bytes": p.stat().st_size, "sha256": actual}
    final_root = roots["aether-cl-m6-placement-seeds100-119"]
    pilot_root = roots["aether-cl-m6-placement-seeds100-119-pilot"]
    before_root = roots["aether-cl-m6-before-report-repair"]
    final, pilot, before = [json.loads((p / "suite.json").read_text()) for p in (final_root, pilot_root, before_root)]
    settings = sweep.preflight()
    indexes = {"final": verify_index(final_root), "pilot": verify_index(pilot_root)}
    assert final["protocol"] == pilot["protocol"] == before["protocol"] == settings
    assert final["software"] == pilot["software"] == before["software"]
    assert final["software"]["git_commit"] == SCIENCE_COMMIT and final["software"]["git_dirty"] is False
    assert final["child_environment_sha256"] == pilot["child_environment_sha256"] == before["child_environment_sha256"]
    assert final["reporting_repair"] == pilot["reporting_repair"]
    repair = final["reporting_repair"]
    assert repair["launcher_sha256"] == digest(ROOT / "tools/m6_reporting_resume.py")
    assert repair["backup_sha256"] == archives["aether-cl-m6-before-report-repair"]["sha256"]
    original_names = set()
    for e in repair["backup_files"]:
        p = before_root / e["path"]
        assert p.stat().st_size == e["bytes"] and digest(p) == e["sha256"]
        original_names.add(e["path"])
        if e["path"] != "suite.json":
            for root in (pilot_root, final_root): assert (root / e["path"]).read_bytes() == p.read_bytes()
    assert original_names == {p.relative_to(before_root).as_posix() for p in before_root.rglob("*") if p.is_file()}
    assert before["state"] == "running" and len(before["episode_trials"]) == 1 and before["episode_trials"][0]["state"] == "running"
    assert len(pilot["episode_trials"]) == 18 and pilot["episode_trials"] == final["episode_trials"][:18]
    for p in pilot_root.rglob("*"):
        if p.is_file() and p.name not in ("suite.json", "archive_index.json", "curve.csv"):
            assert (final_root / p.relative_to(pilot_root)).read_bytes() == p.read_bytes()
    assert sweep.check_pilot(pilot)["passed"]
    selected = sweep.plan(Path(final["run_directory"]))
    assert len(final["episode_trials"]) == 360
    for expected, trial in zip(selected, final["episode_trials"]): assert all(trial.get(k) == v for k, v in expected.items())
    assert len({t["run_directory"] for t in final["episode_trials"]}) == 360
    def local(directory, root=final_root): return root / Path(directory).relative_to(final["run_directory"])
    for trial in final["episode_trials"]:
        assert sweep.files(local(trial["config"]["output"]), final_root) == trial["evidence_files"]
    jobs = [(str(local(t["run_directory"])), t, final["software"]) for t in final["episode_trials"]]
    audit = {"archives": archives, "indexes": indexes, "protocol_passed": True, "software": final["software"],
             "repair_preservation_passed": True, "pilot_first18_preservation_and_commissioning_passed": True,
             "trial_plan_unique_first18_then_unstarted_passed": True,
             "all_trial_file_lists_hashes_sizes_passed": True,
             "startup_environment_hash_equal_before_pilot_final": final["child_environment_sha256"],
             "audit_runtime": {"python": sys.version.split()[0], "numpy": np.__version__}, "trials": []}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, result in enumerate(pool.map(trial_job, jobs), 1):
            audit["trials"].append(result)
            if i % 30 == 0: print("M6 replay", i, "/ 360", flush=True)
    for title, root, report in (("pilot", pilot_root, pilot), ("final", final_root, final)):
        copied = copy.deepcopy(report)
        with tempfile.TemporaryDirectory() as temp:
            real_compare = sweep.compare
            sweep.compare = lambda a, b, kind: real_compare(local(a, root), local(b, root), kind)
            try: sweep.summarize(copied, Path(temp))
            finally: sweep.compare = real_compare
            for field in ("pairs", "recovery_pairs", "control_pairs", "cells", "paired_outcomes", "native_source_identity_consistent"):
                assert json_value(copied[field]) == report[field], (title, field)
            assert (Path(temp) / "curve.csv").read_bytes() == (root / "curve.csv").read_bytes(), title
        audit[title + "_aggregate_JSON_CSV_exact"] = True
        audit[title + "_comparisons"] = {k: {"count": len(report[k]), "all_passed": all(e["passed"] for e in report[k])} for k in ("pairs", "recovery_pairs", "control_pairs")}
        assert all(all(e["passed"] for e in report[k]) for k in ("pairs", "recovery_pairs", "control_pairs"))
        print("M6", title, "all comparisons and aggregates reproduced", flush=True)
    audit["action_count"] = sum(t["independent_endpoint"]["actions"] for t in audit["trials"])
    audit["eligible_trials"] = sum(t["independent_endpoint"]["eligible"] for t in audit["trials"])
    audit["excluded_trials"] = 360 - audit["eligible_trials"]
    audit["maximum_action_replay_error"] = max(t["replay"]["max_action_replay_error"] for t in audit["trials"])
    audit["all_passed"] = True
    audit["cells"] = final["cells"]
    audit["paired_outcomes"] = final["paired_outcomes"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream: json.dump(json_value(audit), stream, indent=2, allow_nan=False); stream.write("\n")
    print("M6 independent audit passed:", args.output, flush=True)


if __name__ == "__main__": main()
