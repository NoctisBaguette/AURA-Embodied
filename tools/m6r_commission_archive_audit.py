"""Read-only independent replay of returned native M6R known16 evidence."""

import argparse
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aura-sim/prototype_aether_cl"))
from aether_cl.acceptance import load_trial
from aether_cl.m5_attribution import files
from aether_cl.m6r_audit import check_trial, compare, PHYSICAL_FIELDS
from aether_cl import m6r_sweep as sweep
from aether_cl.runtime import json_value


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, required=True)
    cli.add_argument("--archive", type=Path, required=True)
    cli.add_argument("--log", type=Path, required=True)
    cli.add_argument("--m6-root", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    root = args.root.resolve()
    report = json.loads((root / "suite.json").read_text())
    original = Path(report["run_directory"])
    translate = lambda p: root / Path(p).relative_to(original)
    digest = hashlib.sha256(args.archive.read_bytes()).hexdigest()
    assert digest == "779b8cc01ab2f0c47ff4d7a407750c20a17fd46f98bf93fc3726bf38eb912bb1"
    assert "SHA-256: " + digest in args.log.read_text()
    index = json.loads((root / "archive_index.json").read_text())
    indexed = set()
    for entry in index["files"]:
        path = root.parent / entry["path"]
        assert path.resolve().is_relative_to(root)
        assert entry["path"] not in indexed
        indexed.add(entry["path"])
        raw = path.read_bytes()
        assert len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"]
    assert indexed == {str(p.relative_to(root.parent)) for p in root.rglob("*") if p.is_file() and p != root / "archive_index.json"}
    protocol = sweep.commission_protocol(sweep.preflight())
    assert report["protocol"] == protocol == json.loads((root / "protocol.json").read_text())
    assert report["scope"] == protocol["name"] and report["state"] == "passed"
    assert report["software"]["git_commit"] == "9ac5439e003f2ed65ecf2ea02f59a6186c7b6714"
    assert report["software"]["git_dirty"] is False
    assert report["software"]["python"].startswith("3.10.")
    assert all(report["software"]["packages"][k] == v for k, v in sweep.NATIVE_PACKAGES.items())
    assert report["trial_process_isolation"] == protocol["execution"]
    assert report["fresh_seed_history"] is None and report["known_seed_commissioning"] is None
    expected = sweep.commission_plan(original)
    assert len(report["episode_trials"]) == len(expected) == 16
    rows = []
    steps_replayed = 0
    for trial, planned in zip(report["episode_trials"], expected):
        assert all(trial.get(k) == v for k, v in planned.items())
        assert files(translate(trial["config"]["output"]), root) == trial["evidence_files"]
        directory = translate(trial["run_directory"])
        checked = json_value(check_trial(directory, sweep.config_for(trial), report["software"]))
        assert checked["passed"] and all(trial.get(k) == v for k, v in checked.items())
        manifest, result, events = load_trial(directory)
        steps = [e for e in events if e["event"] == "step"]
        steps_replayed += len(steps)
        assert len(steps) == 800 and not checked["episodes"][0]["excluded"]
        assert checked["max_action_replay_error"] == 0.
        episode = checked["episodes"][0]
        rows.append({"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"],
                     "steps": len(steps), "passed": checked["passed"],
                     "max_action_replay_error": checked["max_action_replay_error"],
                     **{k: episode[k] for k in ("task_success_at_end", "release_success_at_end",
                         "support_stability_success_at_end", "retraction_success_at_end", "final_horizontal_error_m",
                         "lower_transition_step", "lower_phase_timeout", "recovery_release_reached",
                         "recovery_release_first_action_step", "recovery_release_executed",
                         "recovery_retraction_reached", "recovery_retraction_first_action_step",
                         "recovery_retraction_executed", "recovery_task_success", "first_task_success_step",
                         "total_observed_tcp_path_m", "recovery", "final_reference")}})
        print(f"Replay {len(rows)}/16: {trial['point_id']} seed {trial['seed']} {trial['system']} PASS", flush=True)
    # Recompute each comparison from raw files while preserving report paths.
    previous_compare = sweep.compare
    sweep.compare = lambda a, b, kind: compare(translate(a), translate(b), kind)
    copied = json.loads(json.dumps(report))
    try:
        with tempfile.TemporaryDirectory() as temporary:
            sweep.summarize_commission(copied, Path(temporary))
            assert (Path(temporary) / "commission.csv").read_bytes() == (root / "commission.csv").read_bytes()
    finally:
        sweep.compare = previous_compare
    groups = ("pairs", "recovery_pairs", "repair_pairs", "control_pairs")
    diagnostic_roundoff = []
    for group in groups:
        assert len(copied[group]) == len(report[group])
        for calculated, recorded in zip(copied[group], report[group]):
            a, b = json.loads(json.dumps(calculated)), json.loads(json.dumps(recorded))
            if a != b:
                # Local SciPy/NumPy differ from the native stack. Only this
                # derived angle diagnostic may differ by sub-picoradian rounding;
                # raw trajectories, replay and gate decisions remain exact.
                assert group == "repair_pairs"
                x = a["lower_predicates_at_divergence"].pop("rotation_error_rad")
                y = b["lower_predicates_at_divergence"].pop("rotation_error_rad")
                assert math.isfinite(x) and math.isfinite(y) and abs(x - y) <= 1e-12
                diagnostic_roundoff.append({"point_id": a["point_id"], "seed": a["seed"],
                                            "field": "rotation_error_rad", "recorded": y,
                                            "local_recomputed": x, "absolute_difference": abs(x - y)})
            assert a == b
    assert copied["native_source_identity_consistent"] == report["native_source_identity_consistent"]
    gate = sweep.check_commission(copied)
    assert gate["passed"] and gate == report["commissioning"]
    assert sum(len(copied[k]) for k in groups) == 14
    # Verify retained Baseline/V1/V2-old native trajectories against accepted M6.
    m6 = json.loads((args.m6_root / "suite.json").read_text())
    old_lookup = {(t["point_id"], t["seed"], t["system"]): t for t in m6["episode_trials"]}
    old_rows = []
    for trial in report["episode_trials"]:
        if trial["system"] == "v2r":
            continue
        old_system = "v2" if trial["system"] == "v2-old" else trial["system"]
        old_trial = old_lookup[(trial["point_id"], trial["seed"], old_system)]
        old_directory = args.m6_root / Path(old_trial["run_directory"]).relative_to(m6["run_directory"])
        om, _, oe = load_trial(old_directory)
        nm, _, ne = load_trial(translate(trial["run_directory"]))
        assert om["upstream_sources_sha256"] == nm["upstream_sources_sha256"]
        for key in ("policy_details", "task_contract", "support_geometry", "robot_base_pose", "action_space_shape", "verifier", "recovery_controller"):
            assert om[key] == nm[key], key
        old_reset = next(e for e in oe if e["event"] == "reset")
        new_reset = next(e for e in ne if e["event"] == "reset")
        assert all(old_reset[k] == new_reset[k] for k in ("seed", "observation", "info", "eligibility"))
        a = [e for e in oe if e["event"] == "step"]
        b = [e for e in ne if e["event"] == "step"]
        assert len(a) == len(b) == 800
        assert all(all(x[k] == y[k] for k in (*PHYSICAL_FIELDS, "verification", "recovery")) for x, y in zip(a, b))
        assert [e["disturbance"] for e in oe if e["event"] == "disturbance_attempted"] == [e["disturbance"] for e in ne if e["event"] == "disturbance_attempted"]
        old_rows.append({"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"], "exact_steps": 800, "passed": True})
    assert len(old_rows) == 12
    summaries = []
    for point in ("normal", "release-shift-080mm"):
        for system in sweep.SYSTEMS:
            selected = [r for r in rows if r["point_id"] == point and r["system"] == system]
            summaries.append({"point_id": point, "system": system, "successes": sum(r["task_success_at_end"] for r in selected), "episodes": len(selected)})
    audit = {"scope": "native_known16_development_only_independent_raw_replay", "confirmatory": False,
             "all_passed": True, "archive_sha256": digest, "archive_bytes": args.archive.stat().st_size,
             "log_sha256": hashlib.sha256(args.log.read_bytes()).hexdigest(),
             "suite_sha256": hashlib.sha256((root / "suite.json").read_bytes()).hexdigest(),
             "indexed_files_verified": len(indexed), "frozen_native_commit": report["software"]["git_commit"],
             "protocol_and_source_preflight": True, "full_actions_replayed": steps_replayed,
             "max_action_replay_error": max(r["max_action_replay_error"] for r in rows),
             "local_replay_environment": {"python": sys.version.split()[0], "numpy": version("numpy"), "scipy": version("scipy")},
             "derived_angle_roundoff_only": diagnostic_roundoff,
             "physical_and_controller_comparisons_exact": True,
             "comparison_counts": {k: len(copied[k]) for k in groups}, "commissioning_gate": gate,
             "repair_pairs": copied["repair_pairs"], "frozen_m6_trajectories": old_rows,
             "summaries": summaries, "trials": rows,
             "fresh_seeds_observed": [], "next_step": "frozen_480_slot_fresh_native_matrix_120_139_no_tuning"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(json_value(audit), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: v for k, v in audit.items() if k not in ("trials", "repair_pairs", "frozen_m6_trajectories")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
