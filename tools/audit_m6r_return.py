"""Read-only replay, direct endpoint reconstruction and pilot audit of native M6R.

Safely extract the final/pilot archives before use. No simulator is launched.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
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
from aether_cl import m6r_sweep as sweep
from aether_cl.m6r_audit import check_trial, compare, lower_predicates
from aether_cl.runtime import json_value
from audit_m6_return import independent_endpoint, verify_index

COMMIT = "9ac5439e003f2ed65ecf2ea02f59a6186c7b6714"
ARCHIVES = {
    "final": ("aether-cl-m6r-placement-seeds120-139.tar.gz", "d3427dbdd9759ee018ad82182273462c6481869f54234e9d1523f4934857a391"),
    "pilot": ("aether-cl-m6r-placement-seeds120-139-pilot.tar.gz", "dc388e5bb6b96f4de838bab4494384de86cd38265327b6fb78e0ba80e149cbc0"),
    "known": ("aether-cl-m6r-known-commission.tar.gz", "779b8cc01ab2f0c47ff4d7a407750c20a17fd46f98bf93fc3726bf38eb912bb1"),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trial_job(job):
    directory, trial, software = job
    checked = json_value(check_trial(Path(directory), sweep.config_for(trial), software))
    assert checked["passed"], (directory, checked["failed_checks"])
    assert all(trial.get(k) == v for k, v in checked.items())
    manifest, result, events = load_trial(Path(directory))
    endpoint = independent_endpoint(events)
    episode = result["episodes"][0]
    assert episode["task_success_at_end"] == bool(endpoint["final"] and endpoint["final"]["task_success"])
    assert episode["first_task_success_step"] == endpoint["first_success_step"]
    steps = [e for e in events if e["event"] == "step"]
    phases = Counter(e["controller_decision"]["phase"] for e in steps)
    recovery = episode["recovery"]
    detail = {"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"],
              "replay": checked, "independent_endpoint": endpoint, "executed_phase_counts": dict(phases),
              "injections": [e["disturbance"] for e in events if e["event"] == "disturbance_attempted"]}
    if recovery["attempts"]:
        assert recovery["attempts"] == 1 and recovery["action_steps"] <= 400
        assert recovery["trigger_step"] == 342 and recovery["first_action_step"] == 343
        trigger_observation = steps[recovery["trigger_step"] - 1]["observation"]
        terminal = next(e for e in steps if e["recovery"]["state"] in ("aborted", "attempt_complete"))
        detail["terminal"] = {"step": terminal["step"], "state": terminal["recovery"]["state"],
                              "phase": terminal["controller_decision"]["phase"],
                              "phase_step": terminal["controller_decision"]["phase_step"],
                              "all_later_actions_repeat_terminal": all(e["action"] == terminal["action"] for e in steps if e["step"] > terminal["step"]),
                              "contact_grasped": terminal["reference"]["is_grasped"],
                              "supported": terminal["reference"]["supported"],
                              "cube_table_contact_force_z_n": terminal["reference"]["cube_table_contact_force_world_n"][2]}
        assert detail["terminal"]["all_later_actions_repeat_terminal"]
        if terminal["controller_decision"]["phase"] == "recovery_lower":
            detail["terminal"]["lower_predicates"] = lower_predicates(terminal, manifest, trigger_observation)
        assert episode["recovery_release_executed"] == bool(phases["recovery_release"])
        assert episode["recovery_retraction_executed"] == bool(phases["recovery_retract"])
    if trial["point_id"] == "release-shift-040mm" and trial["system"] == "baseline" and steps:
        detail["passive_4cm_drift"] = {str(n): {"cube_world": steps[n-1]["observation"]["extra"]["obj_pose"],
                                              "xy_error_m": steps[n-1]["reference"]["horizontal_error_m"]}
                                     for n in (295, 296, 340, 800)}
    return json_value(detail)


def assert_pair_report(calculated, recorded, group, diagnostic_roundoff):
    assert len(calculated) == len(recorded)
    for a0, b0 in zip(calculated, recorded):
        a, b = json.loads(json.dumps(a0)), json.loads(json.dumps(b0))
        assert a["passed"] and all(a["checks"].values())
        if a != b:
            assert group == "repair_pairs"
            x = a["lower_predicates_at_divergence"].pop("rotation_error_rad")
            y = b["lower_predicates_at_divergence"].pop("rotation_error_rad")
            assert math.isfinite(x) and math.isfinite(y) and abs(x-y) <= 1e-12, (a["seed"], x, y)
            diagnostic_roundoff.append({"point_id": a["point_id"], "seed": a["seed"], "field": "rotation_error_rad",
                                        "recorded": y, "local_recomputed": x, "absolute_difference": abs(x-y)})
        assert a == b


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--evidence-root", type=Path, required=True)
    cli.add_argument("--upload-root", type=Path, required=True)
    cli.add_argument("--known-root", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--workers", type=int, default=4)
    args = cli.parse_args()
    settings = sweep.preflight()
    roots = {tag: args.evidence_root / tag / "m6r-placement" for tag in ("final", "pilot")}
    reports = {tag: json.loads((root / "suite.json").read_text()) for tag, root in roots.items()}
    final, pilot = reports["final"], reports["pilot"]
    known = json.loads((args.known_root / "suite.json").read_text())
    archives = {}
    for tag, (name, expected) in ARCHIVES.items():
        path = args.upload_root / name
        assert digest(path) == expected
        archives[tag] = {"name": name, "sha256": expected, "bytes": path.stat().st_size}
    log = args.upload_root / "m6r-placement-seeds120-139.log"
    text = log.read_text()
    assert "SHA-256: " + archives["final"]["sha256"] in text
    assert "SHA-256: " + archives["pilot"]["sha256"] in text
    assert "M6R_FIRST24_VALID" in text
    assert "M6R trial 480/480:" in text
    assert final["state"] == "passed" and pilot["state"] == "paused"
    assert final["protocol"] == pilot["protocol"] == settings
    assert final["software"] == pilot["software"] == known["software"]
    assert final["software"]["git_commit"] == COMMIT and final["software"]["git_dirty"] is False
    assert final["software"]["python"].startswith("3.10.")
    assert all(final["software"]["packages"][k] == v for k, v in sweep.NATIVE_PACKAGES.items())
    assert final["child_environment_sha256"] == pilot["child_environment_sha256"]
    assert final["scope"] == pilot["scope"] == settings["name"]
    assert final["trial_process_isolation"] == pilot["trial_process_isolation"] == settings["execution"]
    assert final["fresh_seed_history"] == pilot["fresh_seed_history"]
    history = final["fresh_seed_history"]
    assert history["selected_overlap"] == []
    assert not set(history["recorded_reset_seeds"]) & set(sweep.SEEDS)
    assert history["event_files_checked"] == 2235
    assert final["known_seed_commissioning"] == pilot["known_seed_commissioning"]
    assert final["known_seed_commissioning"]["validated"] is True
    assert final["known_seed_commissioning"]["scope"] == "development_only"
    assert final["known_seed_commissioning"]["sha256"] == digest(args.known_root / "suite.json")
    assert sweep.check_commission(known)["passed"]
    assert known["protocol"] == sweep.commission_protocol(settings)
    known_native = {json.dumps(t["native_sources_sha256"], sort_keys=True) for t in known["episode_trials"]}
    fresh_native = {json.dumps(t["native_sources_sha256"], sort_keys=True) for t in final["episode_trials"]}
    assert len(known_native) == 1 and fresh_native == known_native
    indexes = {tag: verify_index(root) for tag, root in roots.items()}
    assert len(final["episode_trials"]) == 480 and len(pilot["episode_trials"]) == 24
    assert pilot["episode_trials"] == final["episode_trials"][:24]
    original = Path(final["run_directory"])
    assert original == Path(pilot["run_directory"])
    selected = sweep.plan(original)
    jobs = []
    for trial, expected in zip(final["episode_trials"], selected):
        assert all(trial.get(k) == v for k, v in expected.items())
        directory = roots["final"] / Path(trial["config"]["output"]).relative_to(original)
        assert files(directory, roots["final"]) == trial["evidence_files"]
        run = roots["final"] / Path(trial["run_directory"]).relative_to(original)
        jobs.append((str(run), trial, final["software"]))
    retained = 0
    for trial in pilot["episode_trials"]:
        for entry in trial["evidence_files"]:
            a, b = roots["pilot"] / entry["path"], roots["final"] / entry["path"]
            assert a.read_bytes() == b.read_bytes()
            retained += 1
    print(f"Archive indexes, frozen identities, plan and {retained} retained pilot child files PASS", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(trial_job, jobs, chunksize=1):
            rows.append(row)
            if len(rows) % 24 == 0:
                print(f"Raw replay + independent endpoint {len(rows)}/480 PASS", flush=True)
    print("Reconstructing all 460 pair comparisons and both aggregate reports", flush=True)
    groups = ("pairs", "recovery_pairs", "repair_pairs", "control_pairs")
    roundoff = []
    copied_final = None
    for tag, report in reports.items():
        root = roots[tag]
        copied = json.loads(json.dumps(report))
        old_compare = sweep.compare
        sweep.compare = lambda a, b, kind: compare(root / a.relative_to(original), root / b.relative_to(original), kind)
        try:
            with tempfile.TemporaryDirectory() as temporary:
                sweep.summarize(copied, Path(temporary))
                assert (Path(temporary) / "curve.csv").read_bytes() == (root / "curve.csv").read_bytes()
        finally:
            sweep.compare = old_compare
        for group in groups:
            assert_pair_report(copied[group], report[group], group, roundoff)
        for key in ("cells", "paired_outcomes", "native_source_identity_consistent"):
            assert json_value(copied[key]) == report[key], key
        if tag == "pilot":
            assert sweep.check_pilot(copied)["passed"]
        else:
            copied_final = copied
    assert {g: len(copied_final[g]) for g in groups} == settings["comparison_counts"]
    # Explicitly check action divergence starts exactly one step after each
    # independently justified lower-state difference, never earlier.
    lookup = {(t["point_id"], t["seed"], t["system"]): t for t in final["episode_trials"]}
    actual_divergences = []
    for pair in copied_final["repair_pairs"]:
        point, seed = pair["point_id"], pair["seed"]
        traces = []
        for system in ("v2-old", "v2r"):
            trial = lookup[(point, seed, system)]
            directory = roots["final"] / Path(trial["run_directory"]).relative_to(original)
            traces.append([e for e in load_trial(directory)[2] if e["event"] == "step"])
        a, b = traces
        first = next((x["step"] for x, y in zip(a,b) if x["action"] != y["action"]), None)
        assert first == pair["first_possible_action_divergence_step"]
        if first is not None:
            actual_divergences.append({"point_id": point, "seed": seed, "lower_state_step": first-1, "first_actual_action_difference_step": first})
    episodes = [r["replay"]["episodes"][0] for r in rows]
    counts = {"trial_records": len(rows), "eligible_trials": sum(not e["excluded"] for e in episodes),
              "excluded_trials": sum(e["excluded"] for e in episodes),
              "actions_replayed": sum(e["steps"] for e in episodes),
              "comparison_records": sum(len(copied_final[g]) for g in groups),
              "max_action_replay_error": max(r["replay"]["max_action_replay_error"] for r in rows),
              "actual_repair_action_divergences": len(actual_divergences)}
    assert counts["eligible_trials"] == 456 and counts["excluded_trials"] == 24
    assert counts["actions_replayed"] == 364800 and counts["actual_repair_action_divergences"] == 70
    assert counts["max_action_replay_error"] == 0.
    assert {e["seed"] for e in episodes if e["excluded"]} == {132}
    assert all(e["steps"] == (0 if e["excluded"] else 800) for e in episodes)
    audit = {"scope": "M6R_fresh_120_139_independent_raw_replay_and_direct_contact_endpoint_audit",
             "all_passed": True, "confirmatory": True, "measurement_commit": COMMIT,
             "archives": archives, "log_sha256": digest(log), "indexes": indexes,
             "pilot_raw_files_retained_exactly": retained, "pilot_check": sweep.check_pilot(pilot),
             "fresh_seed_history": history, "known_seed_commissioning": final["known_seed_commissioning"],
             "native_software": final["software"], "frozen_source_protocol_preflight": True,
             "native_source_identity_consistent": copied_final["native_source_identity_consistent"],
             "counts": counts, "comparison_counts": {g: len(copied_final[g]) for g in groups},
             "local_replay_environment": {"python": sys.version.split()[0], "numpy": version("numpy"), "scipy": version("scipy")},
             "derived_rotation_diagnostic_roundoff_only": roundoff,
             "raw_physical_controller_verifier_and_gate_fields_exact": True,
             "diagnostic_rotation_difference_bound_rad": 1e-12,
             "cells": final["cells"], "paired_outcomes": final["paired_outcomes"],
             "repair_pairs": copied_final["repair_pairs"], "actual_action_divergences": actual_divergences,
             "trials": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(json_value(audit), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(counts, indent=2), flush=True)
    print("M6R_NATIVE_RETURN_AUDIT_PASS", flush=True)


if __name__ == "__main__":
    main()
