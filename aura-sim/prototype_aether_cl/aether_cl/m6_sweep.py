"""Preregistered M6 placement matrix, retained evidence and resumable execution."""

import argparse
from collections import Counter
from dataclasses import asdict
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
from uuid import uuid4

from .acceptance import archive_evidence, run_in_process, write_json
from .m5_attribution import files, VOLATILE_ENVIRONMENT, preflight as m5_preflight
from .runtime import json_value, software_manifest
from .verification import VerificationMetrics
from .m6_runtime import M6Config
from .m6_policy import FixedPlacement, PlacementRecoverySettings, PHASES, NOMINAL_DURATIONS, NOMINAL_STEPS, INJECTION_STEP, MAX_STEPS
from .m6_task import task_manifest
from .m6_audit import check_trial, compare


SEEDS = tuple(range(100, 120))
SYSTEMS = ("baseline", "v1", "v2")
NATIVE_PACKAGES = {"mani_skill": "3.0.1", "sapien": "3.0.3", "numpy": "1.26.4"}
MAGNITUDES = (.01, .04, .08, .12, .20)
SCOPE = "m6_seed100_119_support_placement_release"
NEW_SOURCES = ("m6_task.py", "m6_policy.py", "m6_runtime.py", "m6_audit.py", "m6_sweep.py", "m6.py", "m6_index.html")
PROTOCOL_PATH = Path(__file__).resolve().parents[3] / "docs/research/experiments/evidence/AETHER_CL_M6_Placement_Protocol.json"


def points():
    return [{"point_id": "normal", "condition": "none", "magnitude_m": None, "config_magnitude_m": .08}] + [
        {"point_id": f"release-shift-{round(m * 1000):03d}mm", "condition": "post_release_shift",
         "magnitude_m": m, "config_magnitude_m": m} for m in MAGNITUDES]


def protocol():
    return {"name": SCOPE, "date": "2026-10-06", "02_decision_commit": "03b9b2dc77c33dc1aa47edd67dcb20238ad8b0bb",
            "authority": "DEC-0004 and AETHER_CL_M5_02_Research_Review_v0.1",
            "seeds": list(SEEDS), "systems": list(SYSTEMS), "conditions": points(), "requested_episodes": 360,
            "cells": 18, "episodes_per_cell": 20, "max_steps": MAX_STEPS, "env_id": "PickCube-v1",
            "physics_backend": "cpu", "render": False, "fps": 5., "render_device": "cuda:0",
            "nominal_phases": list(PHASES), "nominal_durations": list(NOMINAL_DURATIONS), "nominal_steps": NOMINAL_STEPS,
            "task_contract": task_manifest(), "release_tcp_clearance_m": .002,
            "recovery_settings": json_value(asdict(PlacementRecoverySettings())),
            "injection_step": INJECTION_STEP, "injection_timing": "after_nominal_release_before_final_stability_after_action_computation_before_physics",
            "injection_precondition": "previous_observation_released_open_supported_geometry_and_current_nominal_retract_phase",
            "invalid_release_precondition": "retain_episode_and_record_not_applied_no_exclusion_or_replacement",
            "execution": "fresh_python_interpreter_and_simulator_per_point_seed_system", "child_episodes": 1,
            "first_18_slots": "normal, 10mm, 80mm; seeds100,101; Baseline,V1,V2; these remain in the full matrix",
            "commissioning_gate": "first18_valid_replay_pairing_source_identity_at_least_one_eligible_healthy_baseline_placement_and_release_shift_applied_on_eligible_baseline_v1_sentinels_no_v2_success_requirement",
            "remaining_order": "point normal then ascending magnitude; seed ascending; Baseline,V1,V2; omit already selected first18",
            "seed_selection": "fresh_preselected_100_119_no_native_outcomes_used_no_adaptive_replacement",
            "analysis_unit": "20_common_seed_scenes_reused_across_conditions_not_360_independent_scenes",
            "comparison_counts": {"pairs": 120, "recovery_pairs": 120, "control_pairs": 100},
            "action_replay_tolerance": 3e-7, "physical_pair_tolerance": "exact_no_relaxation",
            "new_sources_sha256": {n: hashlib.sha256((Path(__file__).parent / n).read_bytes()).hexdigest() for n in NEW_SOURCES},
            "old_sources": "unchanged_M0_M5_preflight_chain", "environment_normalization": list(VOLATILE_ENVIRONMENT),
            "required_native_packages": NATIVE_PACKAGES, "required_native_python": "3.10",
            "native_source_identity": "five_installed_upstream_source_hashes_recorded_per_child_equal_across_entire_matrix",
            "performance_gate": "none_task_failures_abort_false_alarm_missed_injection_are_retained_outcomes",
            "unnecessary_recovery": "attempt_in_eligible_matched_pair_whose_baseline_succeeds",
            "regression": "baseline_success_and_v2_final_failure_in_eligible_matched_pair",
            "paired_cost": "v2_minus_v1_total_path_and_retry_actions_include_zero_and_failed_attempts",
            "resume": "only_unstarted_slots_sources_protocol_software_environment_raw_hashes_and_replay_checked",
            "return_boundary": "M6_native_execution_and_independent_audit_then_return_to02_before_further_scope",
            "limitations": "privileged_state_one_cube_synthetic_postrelease_relocation_no_insertion_force_disturbance_camera_verifier_or_memory"}


def preflight():
    m5_preflight()
    value = protocol()
    if json.loads(PROTOCOL_PATH.read_text()) != value:
        raise ValueError("M6 sources/protocol differ from committed preregistration")
    for p in points():
        M6Config(disturbance=p["condition"], disturbance_magnitude=p["config_magnitude_m"]).validate()
    return value


def config_for(item):
    return M6Config(**{**item["config"], "output": Path(item["config"]["output"])})


def plan(output):
    natural = []
    for p in points():
        for seed in SEEDS:
            for system in SYSTEMS:
                c = M6Config(system=system, verification=system != "baseline", seed=seed, disturbance=p["condition"],
                             disturbance_magnitude=p["config_magnitude_m"], render=False, fps=5.,
                             output=output / p["point_id"] / f"seed-{seed}" / system)
                natural.append({**p, "seed": seed, "system": system, "requested_seed_index": seed - SEEDS[0], "config": json_value(asdict(c))})
    first_ids = ("normal", "release-shift-010mm", "release-shift-080mm")
    pilot = [t for p in first_ids for seed in SEEDS[:2] for t in natural if t["point_id"] == p and t["seed"] == seed]
    return pilot + [t for t in natural if not (t["point_id"] in first_ids and t["seed"] in SEEDS[:2])]


def checked_trial(trial, software):
    config = config_for(trial)
    directory = Path(trial["run_directory"])
    if config.output not in directory.parents:
        raise ValueError("Child evidence lies outside the selected trial directory")
    return check_trial(directory, config, software)


def launch_child(config, environment):
    return run_in_process(config, environment, module="aether_cl.m6")


def aggregate_verification(trials, complete):
    if not trials or trials[0]["system"] == "baseline":
        return None
    metrics = VerificationMetrics()
    attributes = {"steps": "steps", "uncertain_steps": "uncertain", "true_positive": "tp", "false_positive": "fp",
                  "false_negative": "fn", "true_negative": "tn", "uncertain_on_negative": "uncertain_on_negative"}
    for trial in trials:
        value = (trial.get("evaluation") or {}).get("verification_metrics")
        if not value:
            continue
        for key, attribute in attributes.items():
            setattr(metrics, attribute, getattr(metrics, attribute) + value[key])
        for key, amount in value["confusion"].items():
            metrics.confusion[key] = metrics.confusion.get(key, 0) + amount
            truth, prediction = key.split("->")
            if truth == prediction and truth not in ("NONE", "UNCERTAIN"):
                metrics.correct_diagnoses += amount
    return metrics.result(complete)


def ordered_sum(values):
    # Explicit binary64 accumulation also reproduces Python 3.10 under 3.12 audits.
    total = 0.
    for value in values:
        total += value
    return total


def summarize_cell(trials):
    # Pilot ordering differs from the remaining order; compare seed identities, not insertion order.
    complete = len(trials) == len(SEEDS) and sorted(t["seed"] for t in trials) == list(SEEDS) and all(t["passed"] for t in trials)
    episodes = [t["episodes"][0] for t in sorted(trials, key=lambda t: t["seed"]) if len(t.get("episodes", [])) == 1]
    eligible = [e for e in episodes if not e["excluded"]]
    attempted = [e for e in eligible if e["recovery"]["attempts"]]
    def mean(values):
        return ordered_sum(values) / len(values) if complete and values else None
    def rate(key):
        return sum(bool(e[key]) for e in eligible) / len(eligible) if complete and eligible else None
    return {"complete": complete, "passed": complete and bool(eligible), "eligible_episodes": len(eligible),
            "excluded_seeds": [e["seed"] for e in episodes if e["excluded"]],
            "task_successes": sum(e["task_success_at_end"] for e in eligible), "task_success_rate_at_end": rate("task_success_at_end"),
            "release_success_rate": rate("release_success_at_end"), "support_stability_success_rate": rate("support_stability_success_at_end"),
            "retraction_success_rate": rate("retraction_success_at_end"), "controller_completion_rate": rate("controller_complete"),
            "disturbance_attempted_episodes": sum(e["disturbance_attempted"] for e in eligible),
            "disturbance_applied_episodes": sum(e["disturbance_applied"] for e in eligible),
            "missed_release_precondition_episodes": sum(e["disturbance_attempted"] and not e["disturbance_applied"] for e in eligible),
            "attempted_episodes": len(attempted), "recovery_successes": sum(e["recovery_task_success"] for e in attempted),
            "recovery_success_rate": sum(e["recovery_task_success"] for e in attempted) / len(attempted) if complete and attempted else None,
            "attempt_complete_episodes": sum(e["recovery"]["state"] == "attempt_complete" for e in attempted),
            "aborted_attempts": sum(e["recovery"]["state"] == "aborted" for e in attempted),
            "mean_attempt_actions": mean([e["recovery"]["action_steps"] for e in attempted]),
            "mean_attempt_path_m": mean([e["recovery"]["observed_tcp_path_m"] for e in attempted]),
            "mean_total_actions": mean([e["steps"] for e in eligible]),
            "mean_total_path_m": mean([e["total_observed_tcp_path_m"] for e in eligible]),
            "mean_final_horizontal_error_m": mean([e["final_horizontal_error_m"] for e in eligible]),
            "median_final_horizontal_error_m": statistics.median([e["final_horizontal_error_m"] for e in eligible]) if complete and eligible else None,
            "failure_counts": dict(Counter(e["first_detected_failure"]["failure"] for e in eligible if e["first_detected_failure"])),
            "abort_reasons": dict(Counter(e["recovery"]["failure_detail"] for e in attempted if e["recovery"]["failure_detail"])),
            "first_failure_latency_steps": [e["first_failure_latency_steps"] for e in eligible if e["first_failure_latency_steps"] is not None],
            "verification_metrics": aggregate_verification(trials, complete)}


def summarize_paired(point, lookup, comparable):
    rows, excluded, counts = [], [], Counter()
    for seed in SEEDS:
        trio = [lookup.get((point["point_id"], seed, s)) for s in SYSTEMS]
        if any(not t or not t["passed"] or len(t.get("episodes", [])) != 1 for t in trio):
            comparable = False; continue
        a, b, c = [t["episodes"][0] for t in trio]
        if len({e["seed"] for e in (a, b, c)}) != 1 or len({e["excluded"] for e in (a, b, c)}) != 1:
            comparable = False; continue
        if a["excluded"]:
            excluded.append(seed); continue
        rows.append((a, b, c)); counts[f'{int(b["task_success_at_end"])}->{int(c["task_success_at_end"])}'] += 1
    n = len(rows)
    base_success = sum(a["task_success_at_end"] for a, _, _ in rows)
    unnecessary = sum(a["task_success_at_end"] and bool(c["recovery"]["attempts"]) for a, _, c in rows)
    regressions = sum(a["task_success_at_end"] and not c["task_success_at_end"] for a, _, c in rows)
    def mean(values):
        return ordered_sum(values) / len(values) if comparable and values else None
    return {**point, "complete_valid_pairing": comparable, "eligible_pairs": n, "excluded_seeds": excluded,
            "both_failed": counts["0->0"], "v2_only_success": counts["0->1"], "v1_only_success": counts["1->0"], "both_succeeded": counts["1->1"],
            "success_rate_difference_v2_minus_v1": (counts["0->1"] - counts["1->0"]) / n if comparable and n else None,
            "baseline_success_pairs": base_success, "unnecessary_recovery_attempts": unnecessary, "regressions": regressions,
            "unnecessary_recovery_rate_on_baseline_success": unnecessary / base_success if comparable and base_success else None,
            "regression_rate_on_baseline_success": regressions / base_success if comparable and base_success else None,
            "mean_paired_extra_retry_actions": mean([c["recovery"]["action_steps"] for _, _, c in rows]),
            "mean_paired_extra_total_path_m": mean([c["total_observed_tcp_path_m"] - b["total_observed_tcp_path_m"] for _, b, c in rows]),
            "mean_paired_horizontal_error_difference_m": mean([c["final_horizontal_error_m"] - b["final_horizontal_error_m"] for _, b, c in rows])}


def summarize(report, output):
    lookup = {(t["point_id"], t["seed"], t["system"]): t for t in report["episode_trials"]}
    native_sources = {json.dumps(t.get("native_sources_sha256"), sort_keys=True) for t in report["episode_trials"] if t["passed"]}
    report["native_source_identity_consistent"] = len(native_sources) == 1 and "null" not in native_sources
    report.update(pairs=[], recovery_pairs=[], control_pairs=[], cells=[], paired_outcomes=[])
    for point in points():
        for seed in SEEDS:
            comparisons = [("baseline", "v1", "pairs", "passive"), ("v1", "v2", "recovery_pairs", "recovery")]
            for left, right, group, kind in comparisons:
                a, b = lookup.get((point["point_id"], seed, left)), lookup.get((point["point_id"], seed, right))
                if a and b and a.get("run_directory") and b.get("run_directory"):
                    pair = {**point, "seed": seed, "systems": [left, right], "passed": False}
                    try:
                        pair.update(compare(Path(a["run_directory"]), Path(b["run_directory"]), kind))
                    except Exception as error:
                        pair["error"] = f"{type(error).__name__}: {error}"
                    report[group].append(pair)
            a, b = lookup.get(("normal", seed, "baseline")), lookup.get((point["point_id"], seed, "baseline"))
            if point["condition"] != "none" and a and b and a.get("run_directory") and b.get("run_directory"):
                pair = {**point, "seed": seed, "passed": False}
                try:
                    pair.update(compare(Path(a["run_directory"]), Path(b["run_directory"]), "control"))
                except Exception as error:
                    pair["error"] = f"{type(error).__name__}: {error}"
                report["control_pairs"].append(pair)
        groups = ("pairs", "recovery_pairs") + (("control_pairs",) if point["condition"] != "none" else ())
        comparable = all(len([p for p in report[g] if p["point_id"] == point["point_id"]]) == len(SEEDS) and
                         all(p["passed"] for p in report[g] if p["point_id"] == point["point_id"]) for g in groups)
        point_trials = [t for t in report["episode_trials"] if t["point_id"] == point["point_id"]]
        comparable &= len(point_trials) == len(SEEDS) * len(SYSTEMS) and all(t["passed"] for t in point_trials)
        comparable &= report["native_source_identity_consistent"]
        if point["condition"] != "none":
            controls = [t for t in report["episode_trials"] if t["point_id"] == "normal" and t["system"] == "baseline"]
            comparable &= len(controls) == len(SEEDS) and all(t["passed"] for t in controls)
        for system in SYSTEMS:
            cell = {**point, "system": system, **summarize_cell([t for t in point_trials if t["system"] == system])}
            cell["comparison_valid"] = comparable and cell["passed"]
            cell["validated_curve_success_rate"] = cell["task_success_rate_at_end"] if cell["comparison_valid"] else None
            report["cells"].append(cell)
        report["paired_outcomes"].append(summarize_paired(point, lookup, comparable))
    columns = ("point_id", "condition", "magnitude_m", "system", "complete", "comparison_valid", "eligible_episodes", "task_successes",
               "validated_curve_success_rate", "release_success_rate", "support_stability_success_rate", "retraction_success_rate",
               "controller_completion_rate", "disturbance_applied_episodes", "missed_release_precondition_episodes", "attempted_episodes",
               "recovery_success_rate", "mean_attempt_actions", "mean_attempt_path_m", "mean_total_path_m", "mean_final_horizontal_error_m")
    with (output / "curve.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader(); writer.writerows(report["cells"])


def check_pilot(report):
    trials = report["episode_trials"]
    checks = {"paused_first18": report["state"] == "paused" and len(trials) == 18,
              "valid_trial_replays": len(trials) == 18 and all(t["passed"] for t in trials),
              "native_source_identity": report.get("native_source_identity_consistent") is True}
    for group, count in (("pairs", 6), ("recovery_pairs", 6), ("control_pairs", 4)):
        checks[group] = len(report[group]) == count and all(p["passed"] for p in report[group])
    healthy = [t["episodes"][0] for t in trials if t["point_id"] == "normal" and t["system"] == "baseline" and len(t.get("episodes", [])) == 1 and not t["episodes"][0]["excluded"]]
    checks["viable_released_supported_healthy_placement"] = any(e["task_success_at_end"] for e in healthy)
    released = [t["episodes"][0] for t in trials if t["condition"] == "post_release_shift" and t["system"] in ("baseline", "v1") and len(t.get("episodes", [])) == 1 and not t["episodes"][0]["excluded"]]
    checks["placement_specific_injections"] = bool(released) and all(e["disturbance_applied"] for e in released)
    return {"passed": all(checks.values()), "checks": checks, "failed_checks": [k for k, v in checks.items() if not v],
            "interpretation": "commissioning_only_no_v2_success_gate_no_exclusions_or_replacement_of_retained_outcomes"}


def run_sweep(output, archive, resume=False, stop_after=None, run_fn=None):
    settings = preflight()
    output, archive = Path(output).resolve(), Path(archive).resolve()
    if stop_after is not None and (not isinstance(stop_after, int) or stop_after < 1):
        raise ValueError("stop_after must be a positive trial count")
    if archive.exists() or output == archive or output in archive.parents:
        raise ValueError("Archive must be new and outside the study directory")
    software = software_manifest()
    if run_fn is None and (not software.get("git_commit") or software.get("git_dirty") is not False):
        raise ValueError("Native M6 requires a clean committed repository")
    if run_fn is None and (not str(software.get("python", "")).startswith("3.10.") or
                          any((software.get("packages") or {}).get(k) != v for k, v in NATIVE_PACKAGES.items())):
        raise ValueError("Native M6 requires the frozen Python 3.10 / ManiSkill 3.0.1 / SAPIEN 3.0.3 / NumPy 1.26.4 environment")
    environment = {k: v for k, v in os.environ.items() if k not in VOLATILE_ENVIRONMENT}
    environment_digest = hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=resume)
    with (output / "runner.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another M6 runner owns this study directory") from None
        selected = plan(output)
        if resume:
            report = json.loads((output / "suite.json").read_text(encoding="utf-8"))
            expected_mode = "injected_single_episode_runner" if run_fn else settings["execution"]
            if (report["protocol"] != settings or report["software"] != software
                    or report["child_environment_sha256"] != environment_digest
                    or report["archive"] != str(archive) or report["trial_process_isolation"] != expected_mode
                    or json.loads((output / "protocol.json").read_text()) != settings):
                raise ValueError("Resume source/protocol/software/environment/path differs")
            if len(report["episode_trials"]) >= len(selected):
                raise ValueError("No unstarted slots remain; existing trials are never rerun")
            for index, trial in enumerate(report["episode_trials"]):
                if any(trial.get(k) != v for k, v in selected[index].items()):
                    raise ValueError("Resume trial order/configuration differs")
                if files(Path(trial["config"]["output"]), output) != trial["evidence_files"]:
                    raise ValueError("Resume raw evidence hashes differ")
                if trial["state"] in ("passed", "failed"):
                    checked = checked_trial(trial, software)
                    if any(trial.get(k) != v for k, v in checked.items()):
                        raise ValueError("Resume recorded checks differ from raw replay")
                elif trial["state"] not in ("error", "interrupted") or trial["passed"]:
                    raise ValueError("Resume contains an unfinished or invalid trial")
        else:
            report = {"scope": SCOPE, "protocol": settings, "software": software,
                      "trial_process_isolation": "injected_single_episode_runner" if run_fn else settings["execution"],
                      "child_environment_sha256": environment_digest, "run_directory": str(output),
                      "archive": str(archive), "episode_trials": [],
                      "passed_means": "valid_complete_matched_evidence_not_successful_recovery"}
            write_json(output / "protocol.json", settings)
        report["state"] = "running"
        write_json(output / "suite.json", report)
        interrupted, launched = False, 0
        for item in selected[len(report["episode_trials"]):]:
            if stop_after is not None and launched >= stop_after:
                break
            preflight()
            trial = {**item, "state": "running", "passed": False}
            report["episode_trials"].append(trial)
            write_json(output / "suite.json", report)
            print(f"M6 trial {len(report['episode_trials'])}/360: {item['point_id']} / seed {item['seed']} / {item['system']}", flush=True)
            config = config_for(item)
            try:
                result = run_fn(config) if run_fn else launch_child(config, environment)
                trial["run_directory"] = result["run_directory"]
                trial.update(checked_trial(trial, software))
                trial["state"] = "passed" if trial["passed"] else "failed"
                ep = trial["episodes"][0]
                print(f"  evidence={trial['state']}, excluded={ep['excluded']}, task_success={ep['task_success_at_end']}", flush=True)
                if trial["failed_checks"]:
                    print("  failed checks: " + ", ".join(trial["failed_checks"]), flush=True)
            except KeyboardInterrupt:
                trial.update(state="interrupted", error="KeyboardInterrupt")
                interrupted = True
            except Exception as error:
                trial.update(state="error", error=f"{type(error).__name__}: {error}")
                print(f"  evidence=error: {trial['error']}", flush=True)
            trial["evidence_files"] = files(config.output, output)
            write_json(output / "suite.json", report)
            launched += 1
            if interrupted:
                break
        summarize(report, output)
        finished = len(report["episode_trials"]) == len(selected)
        good = finished and all(t["passed"] for t in report["episode_trials"]) and all(c["passed"] for c in report["cells"])
        good &= all(len(report[g]) == 120 and all(p["passed"] for p in report[g]) for g in ("pairs", "recovery_pairs"))
        good &= len(report["control_pairs"]) == 100 and all(p["passed"] for p in report["control_pairs"])
        good &= report["native_source_identity_consistent"]
        report["state"] = "interrupted" if interrupted else "paused" if not finished else "passed" if good else "failed"
        saved = archive if finished else archive.with_name(archive.name.removesuffix(".tar.gz") + "-partial-" + uuid4().hex[:8] + ".tar.gz")
        report["saved_archive"] = str(saved)
        write_json(output / "suite.json", report)
        # The shared helper expects a first snapshot. Remove only the generated
        # old index; immutable previous archives and every raw trial stay intact.
        (output / "archive_index.json").unlink(missing_ok=True)
        digest = archive_evidence(output, saved, None, root="m6-placement", scope=SCOPE)
        write_json(Path(str(saved) + ".receipt.json"), {"state": report["state"], "archive": str(saved), "archive_sha256": digest})
        print(f"M6 {report['state']}: {saved}\nSHA-256: {digest}", flush=True)
        return {**report, "archive_sha256": digest}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path, required=True)
    cli.add_argument("--resume", action="store_true")
    cli.add_argument("--check-pilot", action="store_true", help="Inspect the retained first18 commissioning evidence without launching any trial")
    cli.add_argument("--stop-after", type=int, help="Gracefully pause after N new trials; continue unstarted slots with --resume")
    args = cli.parse_args()
    if args.check_pilot:
        if args.resume or args.stop_after is not None:
            cli.error("--check-pilot cannot launch or resume trials")
        preflight()
        report = json.loads((args.output / "suite.json").read_text())
        result = check_pilot(report)
        print(json.dumps(result, indent=2))
        print("M6_FIRST18_VALID" if result["passed"] else "M6_PILOT_STOP_UPLOAD_RETAINED_ARCHIVE", flush=True)
        raise SystemExit(0 if result["passed"] else 2)
    report = run_sweep(args.output, args.archive, args.resume, args.stop_after)
    raise SystemExit(0 if report["state"] in ("passed", "paused") else 2)


if __name__ == "__main__":
    main()
