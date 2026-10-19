"""Preregistered M6R effect-aligned placement matrix, retained evidence and resumable execution."""

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
import tempfile
from uuid import uuid4

from .acceptance import archive_evidence, run_in_process, write_json as raw_write_json
from .m5_attribution import files, VOLATILE_ENVIRONMENT
from .runtime import json_value, software_manifest
from .verification import VerificationMetrics
from .m6r_runtime import M6RConfig
from .m6_policy import FixedPlacement, PlacementRecoverySettings, PHASES, NOMINAL_DURATIONS, NOMINAL_STEPS, INJECTION_STEP, MAX_STEPS
from .m6_task import task_manifest
from .m6r_audit import check_trial, compare
from .m6_sweep import preflight as m6_preflight
from .m6r_policy import LOWER_CONTRACT


SEEDS = tuple(range(120, 140))
SYSTEMS = ("baseline", "v1", "v2-old", "v2r")
NATIVE_PACKAGES = {"mani_skill": "3.0.1", "sapien": "3.0.3", "numpy": "1.26.4"}
MAGNITUDES = (.01, .04, .08, .12, .20)
SCOPE = "m6r_seed120_139_effect_aligned_placement"
NEW_SOURCES = ("m6r_policy.py", "m6r_runtime.py", "m6r_audit.py", "m6r_sweep.py", "m6r.py", "m6r_index.html")
PROTOCOL_PATH = Path(__file__).resolve().parents[3] / "docs/research/experiments/evidence/AETHER_CL_M6R_Placement_Protocol.json"


def write_json(path, value):
    raw_write_json(path, json_value(value))


def points():
    return [{"point_id": "normal", "condition": "none", "magnitude_m": None, "config_magnitude_m": .08}] + [
        {"point_id": f"release-shift-{round(m * 1000):03d}mm", "condition": "post_release_shift",
         "magnitude_m": m, "config_magnitude_m": m} for m in MAGNITUDES]


def protocol():
    return {"name": SCOPE, "date": "2026-10-06", "02_decision_commit": "33918f5f2da97c355a0c2d7cda60b448f77bb2a6",
            "authority": "DEC-0005 and AETHER_CL_M6_02_Research_Review_v0.1",
            "seeds": list(SEEDS), "systems": list(SYSTEMS), "conditions": points(), "requested_episodes": 480,
            "cells": 24, "episodes_per_cell": 20, "max_steps": MAX_STEPS, "env_id": "PickCube-v1",
            "physics_backend": "cpu", "render": False, "fps": 5., "render_device": "cuda:0",
            "nominal_phases": list(PHASES), "nominal_durations": list(NOMINAL_DURATIONS), "nominal_steps": NOMINAL_STEPS,
            "task_contract": task_manifest(), "release_tcp_clearance_m": .002,
            "recovery_settings": json_value(asdict(PlacementRecoverySettings())),
            "injection_step": INJECTION_STEP, "injection_timing": "after_nominal_release_before_final_stability_after_action_computation_before_physics",
            "injection_precondition": "previous_observation_released_open_supported_geometry_and_current_nominal_retract_phase",
            "invalid_release_precondition": "retain_episode_and_record_not_applied_no_exclusion_or_replacement",
            "execution": "fresh_python_interpreter_and_simulator_per_point_seed_system", "child_episodes": 1,
            "first_24_slots": "normal, 10mm, 80mm; seeds120,121; Baseline,V1,V2-old,V2R; these remain in the full matrix",
            "commissioning_gate": "first24_valid_replay_pairing_source_identity_at_least_one_eligible_healthy_baseline_placement_and_release_shift_applied_on_eligible_baseline_v1_sentinels_no_v2r_success_requirement",
            "remaining_order": "point normal then ascending magnitude; seed ascending; Baseline,V1,V2-old,V2R; omit already selected first24",
            "seed_selection": "fresh_preselected_120_139_no_native_outcomes_used_no_adaptive_replacement",
            "analysis_unit": "20_common_seed_scenes_reused_across_conditions_not_480_independent_scenes",
            "comparison_counts": {"pairs": 120, "recovery_pairs": 120, "repair_pairs": 120, "control_pairs": 100},
            "action_replay_tolerance": 3e-7, "physical_pair_tolerance": "exact_no_relaxation",
            "new_sources_sha256": {n: hashlib.sha256((Path(__file__).parent / n).read_bytes()).hexdigest() for n in NEW_SOURCES},
            "old_sources": "unchanged_M0_M6_preflight_chain",
            "frozen_m6_protocol_sha256": hashlib.sha256(Path(__file__).resolve().parents[3].joinpath("docs/research/experiments/evidence/AETHER_CL_M6_Placement_Protocol.json").read_bytes()).hexdigest(),
            "lower_transition_change": LOWER_CONTRACT,
            "engineering_only_seeds": [100, 101], "engineering_only_conditions": ["normal", "release-shift-080mm"],
            "fresh_entry_gate": "validated_known16_report_raw_hashes_replay_comparisons_same_frozen_revision_no_native_success_gate",
            "seed_provenance": "repository_preregistered_M2_20_39_M3_40_59_M4_60_79_M5_80_99_M6_100_119_no_recorded_native_120_139_before_freeze",
            "repair_pair_contract": "exact_all_physical_verifier_and_recovery_states_until_first_post_lower_gate_state_divergence_including_its_same_action_observation_reference_verdict_step_full_equality_if_no_divergence", "environment_normalization": list(VOLATILE_ENVIRONMENT),
            "required_native_packages": NATIVE_PACKAGES, "required_native_python": "3.10",
            "native_source_identity": "five_installed_upstream_source_hashes_recorded_per_child_equal_across_entire_matrix",
            "performance_gate": "none_task_failures_abort_false_alarm_missed_injection_are_retained_outcomes",
            "unnecessary_recovery": "attempt_in_eligible_matched_pair_whose_baseline_succeeds",
            "regression": "baseline_success_and_recovery_system_final_failure_in_eligible_matched_pair",
            "paired_cost": "v2r_minus_v2old_and_each_recovery_minus_v1_total_path_and_retry_actions_include_zero_and_failed_attempts",
            "resume": "only_unstarted_slots_sources_protocol_software_environment_raw_hashes_and_replay_checked",
            "return_boundary": "M6R_native_execution_and_independent_audit_then_return_to02_before_further_scope",
            "limitations": "privileged_state_one_cube_synthetic_postrelease_relocation_no_insertion_force_disturbance_camera_verifier_or_memory"}


def preflight():
    m6_preflight()
    value = protocol()
    if json.loads(PROTOCOL_PATH.read_text()) != value:
        raise ValueError("M6R sources/protocol differ from committed preregistration")
    for p in points():
        M6RConfig(disturbance=p["condition"], disturbance_magnitude=p["config_magnitude_m"]).validate()
    return value


def config_for(item):
    return M6RConfig(**{**item["config"], "output": Path(item["config"]["output"])})


def plan(output):
    natural = []
    for p in points():
        for seed in SEEDS:
            for system in SYSTEMS:
                c = M6RConfig(system=system, verification=system != "baseline", seed=seed, disturbance=p["condition"],
                             disturbance_magnitude=p["config_magnitude_m"], render=False, fps=5.,
                             output=output / p["point_id"] / f"seed-{seed}" / system)
                natural.append({**p, "seed": seed, "system": system, "requested_seed_index": seed - SEEDS[0], "config": json_value(asdict(c))})
    first_ids = ("normal", "release-shift-010mm", "release-shift-080mm")
    pilot = [t for p in first_ids for seed in SEEDS[:2] for t in natural if t["point_id"] == p and t["seed"] == seed]
    return pilot + [t for t in natural if not (t["point_id"] in first_ids and t["seed"] in SEEDS[:2])]


def commission_plan(output):
    selected = []
    for p in (points()[0], points()[3]):
        for seed in (100, 101):
            for system in SYSTEMS:
                c = M6RConfig(system=system, verification=system != "baseline", seed=seed,
                             disturbance=p["condition"], disturbance_magnitude=p["config_magnitude_m"],
                             render=False, fps=5., output=output / p["point_id"] / f"seed-{seed}" / system)
                selected.append({**p, "seed": seed, "system": system, "requested_seed_index": seed - 100,
                                 "config": json_value(asdict(c))})
    return selected


def commission_protocol(settings):
    return {**settings, "name": "m6r_engineering_known_seeds100_101_not_confirmatory", "confirmatory": False,
            "seeds": [100, 101], "conditions": [points()[0], points()[3]], "requested_episodes": 16,
            "cells": 8, "episodes_per_cell": 2, "comparison_counts": {"pairs": 4, "recovery_pairs": 4, "repair_pairs": 4, "control_pairs": 2},
            "seed_selection": "previously_observed_M6_engineering_only_no_fresh_seed_results",
            "first_24_slots": None, "remaining_order": "normal_then80mm_seed100_then101_four_systems"}


def verify_seed_history(root):
    """Check prior recorded resets before a fresh native study; never inspect new seeds."""
    observed = set()
    files_checked = 0
    for path in sorted(Path(root).rglob("events.jsonl")):
        files_checked += 1
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                event = json.loads(line)
                if event["event"] in ("reset", "controller_reset") and "seed" in event:
                    observed.add(event["seed"])
    overlap = sorted(observed.intersection(SEEDS))
    if overlap:
        raise ValueError("Fresh selected seeds already have recorded resets: " + str(overlap))
    return {"root": str(Path(root).resolve()), "event_files_checked": files_checked,
            "recorded_reset_seeds": sorted(observed), "selected_overlap": overlap,
            "scope": "available_native_runs_history_not_unreported_or_deleted_runs"}


def summarize_commission(report, output):
    lookup = {(t["point_id"], t["seed"], t["system"]): t for t in report["episode_trials"]}
    native = {json.dumps(t.get("native_sources_sha256"), sort_keys=True) for t in report["episode_trials"] if t["passed"]}
    report["native_source_identity_consistent"] = len(native) == 1 and "null" not in native
    report.update(pairs=[], recovery_pairs=[], repair_pairs=[], control_pairs=[], cells=[], paired_outcomes=[])
    for point in (points()[0], points()[3]):
        for seed in (100, 101):
            for left, right, group, kind in (("baseline", "v1", "pairs", "passive"), ("v1", "v2-old", "recovery_pairs", "recovery"), ("v2-old", "v2r", "repair_pairs", "repair")):
                a, b = lookup.get((point["point_id"], seed, left)), lookup.get((point["point_id"], seed, right))
                if a and b and a.get("run_directory") and b.get("run_directory"):
                    pair = {**point, "seed": seed, "systems": [left, right], "passed": False}
                    try: pair.update(compare(Path(a["run_directory"]), Path(b["run_directory"]), kind))
                    except Exception as error: pair["error"] = f"{type(error).__name__}: {error}"
                    report[group].append(pair)
            if point["condition"] != "none":
                a, b = lookup.get(("normal", seed, "baseline")), lookup.get((point["point_id"], seed, "baseline"))
                if a and b and a.get("run_directory") and b.get("run_directory"):
                    pair = {**point, "seed": seed, "passed": False}
                    try: pair.update(compare(Path(a["run_directory"]), Path(b["run_directory"]), "control"))
                    except Exception as error: pair["error"] = f"{type(error).__name__}: {error}"
                    report["control_pairs"].append(pair)
    # Development evidence has no confirmatory success curve or scientific effects.
    columns = ("point_id", "seed", "system", "passed", "task_success_at_end", "lower_transition_step",
               "lower_phase_timeout", "recovery_release_executed", "recovery_retraction_executed")
    with (output / "commission.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for trial in report["episode_trials"]:
            episode = trial.get("episodes", [{}])[0]
            writer.writerow({**trial, **episode})


def check_commission(report):
    trials = report["episode_trials"]
    checks = {"development_only": report["protocol"].get("confirmatory") is False,
              "known_16_slots": len(trials) == 16 and all(t["seed"] in (100, 101) for t in trials),
              "valid_trials": len(trials) == 16 and all(t["passed"] for t in trials),
              "native_source_identity": report.get("native_source_identity_consistent") is True}
    for group, count in (("pairs", 4), ("recovery_pairs", 4), ("repair_pairs", 4), ("control_pairs", 2)):
        checks[group] = len(report[group]) == count and all(p["passed"] for p in report[group])
    healthy = [t["episodes"][0] for t in trials if t["point_id"] == "normal" and t["system"] == "baseline" and len(t.get("episodes", [])) == 1 and not t["episodes"][0]["excluded"]]
    checks["native_healthy_placement_viable"] = any(e["task_success_at_end"] for e in healthy)
    shifted = [t["episodes"][0] for t in trials if t["condition"] != "none" and t["system"] in ("baseline", "v1") and len(t.get("episodes", [])) == 1 and not t["episodes"][0]["excluded"]]
    checks["native_release_injections"] = bool(shifted) and all(e["disturbance_applied"] for e in shifted)
    checks["lower_semantic_substitution_exercised"] = any(p.get("first_lower_state_divergence_step") is not None for p in report["repair_pairs"])
    return {"passed": all(checks.values()), "checks": checks, "failed_checks": [k for k, v in checks.items() if not v],
            "interpretation": "known_seed_engineering_only_no_v2r_success_requirement_no_confirmatory_results"}


def validate_commission(path, software):
    path = Path(path).resolve()
    report = json.loads(path.read_text())
    if report["protocol"] != commission_protocol(preflight()) or report["software"] != software:
        raise ValueError("Commissioning protocol/software differ from this frozen revision")
    if not check_commission(report)["passed"]:
        raise ValueError("Known-seed commissioning evidence is incomplete or invalid")
    selected = commission_plan(Path(report["run_directory"]))
    for trial, expected in zip(report["episode_trials"], selected):
        if (any(trial.get(k) != v for k, v in expected.items())
                or files(Path(trial["config"]["output"]), Path(report["run_directory"])) != trial["evidence_files"]):
            raise ValueError("Commissioning plan/raw hashes differ")
        checked = json_value(checked_trial(trial, software))
        if any(trial.get(k) != v for k, v in checked.items()):
            raise ValueError("Commissioning raw replay differs")
    copied = json.loads(json.dumps(report))
    with tempfile.TemporaryDirectory() as temporary:
        summarize_commission(copied, Path(temporary))
    if any(copied[k] != report[k] for k in ("pairs", "recovery_pairs", "repair_pairs", "control_pairs", "native_source_identity_consistent")):
        raise ValueError("Commissioning comparisons differ")
    return {"report": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "validated": True, "scope": "development_only"}


def checked_trial(trial, software):
    config = config_for(trial)
    directory = Path(trial["run_directory"])
    if config.output not in directory.parents:
        raise ValueError("Child evidence lies outside the selected trial directory")
    return check_trial(directory, config, software)


def launch_child(config, environment):
    return run_in_process(config, environment, module="aether_cl.m6r")


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
            "release_reached_attempts": sum(e["recovery_release_reached"] for e in attempted),
            "release_executed_attempts": sum(e["recovery_release_executed"] for e in attempted),
            "retraction_reached_attempts": sum(e["recovery_retraction_reached"] for e in attempted),
            "retraction_executed_attempts": sum(e["recovery_retraction_executed"] for e in attempted),
            "lower_phase_timeouts": sum(e["lower_phase_timeout"] for e in attempted),
            "lower_transition_steps": [{"seed": e["seed"], "step": e["lower_transition_step"]} for e in attempted],
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
    rows, excluded = [], []
    for seed in SEEDS:
        trials = [lookup.get((point["point_id"], seed, s)) for s in SYSTEMS]
        if any(not t or not t["passed"] or len(t.get("episodes", [])) != 1 for t in trials):
            comparable = False; continue
        episodes = [t["episodes"][0] for t in trials]
        if len({e["seed"] for e in episodes}) != 1 or len({e["excluded"] for e in episodes}) != 1:
            comparable = False; continue
        if episodes[0]["excluded"]:
            excluded.append(seed); continue
        rows.append(episodes)
    def mean(values):
        return ordered_sum(values) / len(values) if comparable and values else None
    def effect(left, right):
        pairs = [(e[left], e[right]) for e in rows]
        counts = Counter(f'{int(a["task_success_at_end"])}->{int(b["task_success_at_end"])}' for a, b in pairs)
        return {"both_failed": counts["0->0"], "right_only_success": counts["0->1"], "left_only_success": counts["1->0"], "both_succeeded": counts["1->1"],
                "success_rate_difference": (counts["0->1"] - counts["1->0"]) / len(pairs) if comparable and pairs else None,
                "mean_extra_retry_actions": mean([b["recovery"]["action_steps"] - a["recovery"]["action_steps"] for a, b in pairs]),
                "mean_extra_total_path_m": mean([b["total_observed_tcp_path_m"] - a["total_observed_tcp_path_m"] for a, b in pairs]),
                "mean_horizontal_error_difference_m": mean([b["final_horizontal_error_m"] - a["final_horizontal_error_m"] for a, b in pairs])}
    base_success = sum(e[0]["task_success_at_end"] for e in rows)
    controls = {}
    for index in (2, 3):
        unnecessary = sum(e[0]["task_success_at_end"] and bool(e[index]["recovery"]["attempts"]) for e in rows)
        regressions = sum(e[0]["task_success_at_end"] and not e[index]["task_success_at_end"] for e in rows)
        controls[SYSTEMS[index]] = {"baseline_success_pairs": base_success, "unnecessary_recovery_attempts": unnecessary, "regressions": regressions,
                                  "unnecessary_recovery_rate": unnecessary / base_success if comparable and base_success else None,
                                  "regression_rate": regressions / base_success if comparable and base_success else None}
    return {**point, "complete_valid_pairing": comparable, "eligible_pairs": len(rows), "excluded_seeds": excluded,
            "v2r_vs_v2old": effect(2, 3), "v2old_vs_v1": effect(1, 2), "v2r_vs_v1": effect(1, 3), "healthy_controls": controls}


def summarize(report, output):
    lookup = {(t["point_id"], t["seed"], t["system"]): t for t in report["episode_trials"]}
    native_sources = {json.dumps(t.get("native_sources_sha256"), sort_keys=True) for t in report["episode_trials"] if t["passed"]}
    report["native_source_identity_consistent"] = len(native_sources) == 1 and "null" not in native_sources
    report.update(pairs=[], recovery_pairs=[], repair_pairs=[], control_pairs=[], cells=[], paired_outcomes=[])
    for point in points():
        for seed in SEEDS:
            comparisons = [("baseline", "v1", "pairs", "passive"), ("v1", "v2-old", "recovery_pairs", "recovery"), ("v2-old", "v2r", "repair_pairs", "repair")]
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
        groups = ("pairs", "recovery_pairs", "repair_pairs") + (("control_pairs",) if point["condition"] != "none" else ())
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
               "recovery_success_rate", "release_reached_attempts", "release_executed_attempts", "retraction_reached_attempts", "retraction_executed_attempts", "lower_phase_timeouts", "mean_attempt_actions", "mean_attempt_path_m", "mean_total_path_m", "mean_final_horizontal_error_m")
    with (output / "curve.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader(); writer.writerows(report["cells"])


def check_pilot(report):
    trials = report["episode_trials"]
    checks = {"paused_first24": report["state"] == "paused" and len(trials) == 24,
              "valid_trial_replays": len(trials) == 24 and all(t["passed"] for t in trials),
              "native_source_identity": report.get("native_source_identity_consistent") is True}
    for group, count in (("pairs", 6), ("recovery_pairs", 6), ("repair_pairs", 6), ("control_pairs", 4)):
        checks[group] = len(report[group]) == count and all(p["passed"] for p in report[group])
    healthy = [t["episodes"][0] for t in trials if t["point_id"] == "normal" and t["system"] == "baseline" and len(t.get("episodes", [])) == 1 and not t["episodes"][0]["excluded"]]
    checks["viable_released_supported_healthy_placement"] = any(e["task_success_at_end"] for e in healthy)
    released = [t["episodes"][0] for t in trials if t["condition"] == "post_release_shift" and t["system"] in ("baseline", "v1") and len(t.get("episodes", [])) == 1 and not t["episodes"][0]["excluded"]]
    checks["placement_specific_injections"] = bool(released) and all(e["disturbance_applied"] for e in released)
    return {"passed": all(checks.values()), "checks": checks, "failed_checks": [k for k, v in checks.items() if not v],
            "interpretation": "commissioning_only_no_v2r_success_gate_no_exclusions_or_replacement_of_retained_outcomes"}


def run_sweep(output, archive, resume=False, stop_after=None, run_fn=None, commission_known=False, commission_report=None):
    settings = preflight()
    if commission_known:
        settings = commission_protocol(settings)
    output, archive = Path(output).resolve(), Path(archive).resolve()
    if stop_after is not None and (not isinstance(stop_after, int) or stop_after < 1):
        raise ValueError("stop_after must be a positive trial count")
    if archive.exists() or output == archive or output in archive.parents:
        raise ValueError("Archive must be new and outside the study directory")
    software = software_manifest()
    if run_fn is None and (not software.get("git_commit") or software.get("git_dirty") is not False):
        raise ValueError("Native M6R requires a clean committed repository")
    if run_fn is None and (not str(software.get("python", "")).startswith("3.10.") or
                          any((software.get("packages") or {}).get(k) != v for k, v in NATIVE_PACKAGES.items())):
        raise ValueError("Native M6R requires the frozen Python 3.10 / ManiSkill 3.0.1 / SAPIEN 3.0.3 / NumPy 1.26.4 environment")
    commissioning = None
    if run_fn is None and not resume and not commission_known:
        if commission_report is None:
            raise ValueError("Fresh native M6R requires --commission-report from validated known16 development evidence")
        commissioning = validate_commission(commission_report, software)
    environment = {k: v for k, v in os.environ.items() if k not in VOLATILE_ENVIRONMENT}
    environment_digest = hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()
    history = verify_seed_history(Path(__file__).resolve().parents[1] / "runs") if not resume and not commission_known and run_fn is None else None
    output.mkdir(parents=True, exist_ok=resume)
    with (output / "runner.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another M6R runner owns this study directory") from None
        selected = commission_plan(output) if commission_known else plan(output)
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
            report["scope"] = settings["name"]
            report["fresh_seed_history"] = history
            report["known_seed_commissioning"] = commissioning
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
            print(f"M6R trial {len(report['episode_trials'])}/{len(selected)}: {item['point_id']} / seed {item['seed']} / {item['system']}", flush=True)
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
        (summarize_commission if commission_known else summarize)(report, output)
        finished = len(report["episode_trials"]) == len(selected)
        good = finished and all(t["passed"] for t in report["episode_trials"]) and all(c["passed"] for c in report["cells"])
        good &= all(len(report[g]) == count and all(p["passed"] for p in report[g]) for g, count in settings["comparison_counts"].items())
        good &= report["native_source_identity_consistent"]
        if commission_known:
            report["commissioning"] = check_commission(report)
            good &= report["commissioning"]["passed"]
        report["state"] = "interrupted" if interrupted else "paused" if not finished else "passed" if good else "failed"
        saved = archive if finished else archive.with_name(archive.name.removesuffix(".tar.gz") + "-partial-" + uuid4().hex[:8] + ".tar.gz")
        report["saved_archive"] = str(saved)
        write_json(output / "suite.json", report)
        # The shared helper expects a first snapshot. Remove only the generated
        # old index; immutable previous archives and every raw trial stay intact.
        (output / "archive_index.json").unlink(missing_ok=True)
        digest = archive_evidence(output, saved, None, root="m6r-commission" if commission_known else "m6r-placement", scope=settings["name"])
        write_json(Path(str(saved) + ".receipt.json"), {"state": report["state"], "archive": str(saved), "archive_sha256": digest})
        print(f"M6R {report['state']}: {saved}\nSHA-256: {digest}", flush=True)
        return {**report, "archive_sha256": digest}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path, required=True)
    cli.add_argument("--resume", action="store_true")
    cli.add_argument("--commission-known", action="store_true", help="Run only 16 development slots on already-observed seeds 100/101")
    cli.add_argument("--commission-report", type=Path, help="Known16 suite.json required before starting a fresh native study")
    cli.add_argument("--check-commission", action="store_true", help="Inspect the returned known-seed commissioning report")
    cli.add_argument("--check-pilot", action="store_true", help="Inspect the retained first24 commissioning evidence without launching any trial")
    cli.add_argument("--stop-after", type=int, help="Gracefully pause after N new trials; continue unstarted slots with --resume")
    args = cli.parse_args()
    if args.check_pilot or args.check_commission:
        if args.resume or args.stop_after is not None:
            cli.error("--check-pilot cannot launch or resume trials")
        if args.check_pilot and args.check_commission:
            cli.error("Choose one read-only check")
        preflight()
        report = json.loads((args.output / "suite.json").read_text())
        result = check_commission(report) if args.check_commission else check_pilot(report)
        print(json.dumps(result, indent=2))
        print(("M6R_KNOWN16_VALID" if args.check_commission else "M6R_FIRST24_VALID") if result["passed"] else "M6R_STOP_UPLOAD_RETAINED_ARCHIVE", flush=True)
        raise SystemExit(0 if result["passed"] else 2)
    report = run_sweep(args.output, args.archive, args.resume, args.stop_after, commission_known=args.commission_known,
                       commission_report=args.commission_report)
    raise SystemExit(0 if report["state"] in ("passed", "paused") else 2)


if __name__ == "__main__":
    main()
