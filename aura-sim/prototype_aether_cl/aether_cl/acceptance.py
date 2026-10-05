"""M2 acceptance or frozen fresh-seed screening, with archived evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
from uuid import uuid4

from .runtime import RunConfig, json_value, software_manifest


CONDITIONS = {"none": None, "object_shift": "GRASP_FAILURE", "object_drop": "OBJECT_LOST"}
FROZEN_FILES_SHA256 = {
    "policies.py": "c4e16450ad64ad8683db69d7a166720e411e5e97c8c1def3471b1b04ced04f29",
    "verification.py": "472073de5db587de20c2185b324181f169a7bc0e52cd5706aef7506f928f83a7",
    "disturbances.py": "d745ca4368fdee0a2fcc9abba02a9db069a652b8cabcb7feb9f761a6cebbb95d",
    "runtime.py": "471a5d26a384c6997f0d5a6713d5595bc07dcfe64e0bc2a19b13c786d9449c07",
}
STEP_FIELDS = ("step", "action", "observation", "controller_decision", "reference",
               "info", "reward", "terminated", "truncated")


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_trial(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in
              (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    return manifest, result, events


def check_trial(directory, config):
    """Fail closed on missing evidence, exclusions, errors, or unexpected outcomes."""
    manifest, result, events = load_trial(directory)
    checks = {}
    checks["config_matches"] = manifest.get("config") == json_value(asdict(config))
    checks["clean_revision_recorded"] = (bool(manifest["software"].get("git_commit"))
                                           and manifest["software"].get("git_dirty") is False)
    checks["finished"] = result.get("state") == "finished"
    evaluation = result.get("evaluation", {})
    checks["complete_eligible_episode"] = (evaluation.get("complete") is True
                                           and evaluation.get("eligible_episodes") == 1
                                           and evaluation.get("excluded_episodes") == 0)
    episodes = result.get("episodes", [])
    episode = episodes[0] if len(episodes) == 1 else {}
    steps = [e for e in events if e["event"] == "step"]
    checks["full_budget"] = (episode.get("steps") == config.max_steps
                              and [e["step"] for e in steps] == list(range(1, config.max_steps + 1)))
    checks["no_execution_errors"] = not any(e["event"] in ("run_failed", "cleanup_failed") for e in events)
    injections = [e for e in events if e["event"] == "disturbance_applied"]
    expected_count = int(config.disturbance != "none")
    checks["injection_count"] = len(injections) == expected_count
    if injections:
        expected_step = 81 if config.disturbance == "object_shift" else 181
        checks["injection_matches_plan"] = (len(injections) == 1 and injections[0]["step"] == expected_step
                                              and all(injections[0]["disturbance"].get(k) == v
                                                      for k, v in manifest["disturbance"].items()))
        record = injections[0]["disturbance"]
        before, after = record["before_pose_world"], record["after_pose_world"]
        reset = next(e for e in events if e["event"] == "controller_reset")
        expected_z = reset["initial_cube_position_world_m"][2] if config.disturbance == "object_drop" else before[2]
        checks["logged_pose_intervention"] = (len(before) == len(after) == 7
                                               and math.isclose(after[1] - before[1], config.disturbance_magnitude,
                                                                rel_tol=0, abs_tol=1e-6)
                                               and after[0] == before[0] and after[3:] == before[3:]
                                               and math.isclose(after[2], expected_z, rel_tol=0, abs_tol=1e-6)
                                               and record.get("velocities_zeroed") is True)
        index = events.index(injections[0])
        following = events[index + 1] if index + 1 < len(events) else {}
        checks["injection_before_physics_result"] = (following.get("event") == "step"
                                                     and following.get("step") == expected_step)
    expected_failure = CONDITIONS[config.disturbance]
    checks["expected_task_outcome"] = episode.get("task_success_at_end") is (expected_failure is None)
    reference = episode.get("first_reference_failure")
    checks["expected_reference_failure"] = (reference is None if expected_failure is None
                                             else bool(reference) and reference.get("failure") == expected_failure)
    verification = episode.get("final_verification", {})
    if config.verification:
        detected = episode.get("first_detected_failure")
        checks["expected_verification"] = (verification.get("status") == "passed" and detected is None
                                             if expected_failure is None else
                                             verification.get("status") == "failed"
                                             and verification.get("failure") == expected_failure
                                             and bool(detected) and detected.get("failure") == expected_failure
                                             and episode.get("first_failure_latency_steps") == 2)
        metrics = evaluation.get("verification_metrics", {}) or {}
        checks["no_false_alerts_or_uncertainty"] = (metrics.get("complete") is True
                                                     and metrics.get("false_positive") == 0
                                                     and metrics.get("uncertain_steps") == 0)
    else:
        checks["verification_disabled"] = verification.get("status") == "disabled"
    return {"passed": all(checks.values()), "checks": checks,
            "failed_checks": [k for k, v in checks.items() if not v],
            "episode": episode, "evaluation": evaluation}


def trace(events):
    records = []
    for event in events:
        if event["event"] == "reset":
            records.append({"event": "reset", "seed": event["seed"],
                            "observation": event["observation"], "eligibility": event["eligibility"]})
        elif event["event"] == "disturbance_applied":
            records.append({k: event[k] for k in ("event", "step", "disturbance")})
        elif event["event"] == "step":
            records.append({"event": "step", **{k: event[k] for k in STEP_FIELDS}})
    return records


def check_screening(directory, config):
    """Check integrity and denominators; performance is measured, not gated."""
    manifest, result, events = load_trial(directory)
    episodes = result.get("episodes", [])
    eligible = [e for e in episodes if not e.get("excluded", False)]
    evaluation = result.get("evaluation", {})
    step_events = [e for e in events if e["event"] == "step"]
    checks = {
        "config_matches": manifest.get("config") == json_value(asdict(config)),
        "clean_revision_recorded": bool(manifest["software"].get("git_commit"))
        and manifest["software"].get("git_dirty") is False,
        "finished": result.get("state") == "finished" and evaluation.get("complete") is True,
        "exact_requested_seeds": [e.get("seed") for e in episodes] == list(range(config.seed, config.seed + config.episodes)),
        "episode_indices": [e.get("episode") for e in episodes] == list(range(config.episodes)),
        "has_eligible_episode": bool(eligible),
        "eligible_full_budget": all(e.get("steps") == config.max_steps and not e.get("stopped") for e in eligible),
        "exclusions_have_no_actions": all(e.get("steps") == 0 for e in episodes if e.get("excluded", False)),
        "no_execution_errors": not any(e["event"] in ("run_failed", "cleanup_failed") for e in events),
        "logged_step_count": len(step_events) == sum(e.get("steps", 0) for e in episodes),
        "logged_step_sequences": all([e["step"] for e in step_events if e["episode"] == episode["episode"]]
                                     == list(range(1, episode.get("steps", 0) + 1)) for episode in episodes),
        "eligible_denominator": evaluation.get("eligible_episodes") == len(eligible)
        and evaluation.get("excluded_episodes") == len(episodes) - len(eligible),
        "task_rate_matches_episodes": evaluation.get("task_success_rate_at_end")
        == (sum(e["task_success_at_end"] for e in eligible) / len(eligible) if eligible else None),
    }
    injections = [e for e in events if e["event"] == "disturbance_applied"]
    expected_step = {"none": None, "object_shift": 81, "object_drop": 181}[config.disturbance]
    expected_ids = [e["episode"] for e in eligible] if expected_step else []
    checks["injection_per_eligible_episode"] = [e["episode"] for e in injections] == expected_ids
    checks["injection_plan_matches"] = all(e["step"] == expected_step and
                                           all(e["disturbance"].get(k) == v for k, v in manifest["disturbance"].items())
                                           for e in injections)
    metrics = evaluation.get("verification_metrics")
    checks["verification_accounted"] = (metrics is not None and metrics.get("complete") is True
                                        and metrics.get("steps") == len(step_events)
                                        if config.verification else metrics is None)
    # False alarms, uncertain observations, and task failures remain measured
    # outcomes. Requiring seed-0 behavior here would bias fresh-seed results.
    return {"passed": all(checks.values()), "checks": checks,
            "failed_checks": [k for k, v in checks.items() if not v],
            "episodes": episodes, "evaluation": evaluation}


def compare_pair(baseline, v1):
    left_manifest, left_result, left_events = load_trial(baseline)
    right_manifest, right_result, right_events = load_trial(v1)
    left, right = trace(left_events), trace(right_events)
    first_difference = None
    for index in range(max(len(left), len(right))):
        if index >= min(len(left), len(right)):
            first_difference = {"record_index": index, "field": "record_count"}
            break
        for field in sorted(set(left[index]) | set(right[index])):
            if left[index].get(field) != right[index].get(field):
                first_difference = {"record_index": index, "step": left[index].get("step"), "field": field}
                break
        if first_difference:
            break
    checks = {"trace_equal": first_difference is None,
              "policy_equal": left_manifest.get("policy_details") == right_manifest.get("policy_details"),
              "task_contract_equal": left_manifest.get("task_contract") == right_manifest.get("task_contract"),
              "software_equal": left_manifest.get("software") == right_manifest.get("software"),
              "task_outcome_equal": left_result.get("evaluation", {}).get("task_success_rate_at_end")
              == right_result.get("evaluation", {}).get("task_success_rate_at_end")}
    def digest(records):
        return hashlib.sha256(json.dumps(records, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return {"passed": all(checks.values()), "checks": checks, "first_difference": first_difference,
            "baseline_records": len(left), "v1_records": len(right),
            "baseline_trace_sha256": digest(left), "v1_trace_sha256": digest(right),
            "reset_info_contact_flags_compared": False,
            "reset_observation_contact_flags_compared": True}


def archive_evidence(directory, archive, live_run, root="acceptance",
                     scope="development_acceptance_evidence_not_held_out_benchmark"):
    files = [(p, str(Path(root) / p.relative_to(directory)))
             for p in sorted(directory.rglob("*")) if p.is_file() and not p.is_symlink()]
    if live_run:
        files.extend((live_run / name, str(Path("prior-live-run") / name))
                     for name in ("manifest.json", "result.json", "events.jsonl", "latest.jpg")
                     if (live_run / name).is_file() and not (live_run / name).is_symlink())
    index = {"files": [{"path": name, "bytes": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                        for path, name in files],
             "prior_live_run": str(live_run) if live_run else None,
             "scope": scope}
    write_json(directory / "archive_index.json", index)
    files.append((directory / "archive_index.json", str(Path(root) / "archive_index.json")))
    archive.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement of earlier evidence.
    with archive.open("xb") as output:
        with tarfile.open(fileobj=output, mode="w:gz") as bundle:
            for path, name in files:
                bundle.add(path, arcname=name, recursive=False)
    return hashlib.sha256(archive.read_bytes()).hexdigest()


def run_in_process(config, environment):
    """Use exec, not fork reuse: native imports can modify process environment."""
    config.output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "aether_cl.experiment", "--system",
               "v1" if config.verification else "baseline", "--no-render",
               "--seed", str(config.seed), "--episodes", str(config.episodes),
               "--max-steps", str(config.max_steps), "--render-device", config.render_device,
               "--disturbance", config.disturbance, "--disturbance-magnitude",
               str(config.disturbance_magnitude), "--output", str(config.output)]
    with (config.output / "process.stdout.log").open("w", encoding="utf-8") as stdout, \
            (config.output / "process.stderr.log").open("w", encoding="utf-8") as stderr:
        # The target is Linux. A separate session lets Ctrl+C reach the suite,
        # which then signals and joins this child before evidence is archived.
        process = subprocess.Popen(command, env=environment.copy(), stdout=stdout,
                                   stderr=stderr, start_new_session=True)
        try:
            returncode = process.wait()
        except KeyboardInterrupt:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise
    if returncode:
        raise RuntimeError(f"Trial process exited {returncode}; see {config.output / 'process.stderr.log'}")
    results = sorted(config.output.glob("*/result.json"))
    if len(results) != 1:
        raise RuntimeError(f"Expected one trial result, found {len(results)} in {config.output}")
    return json.loads(results[0].read_text(encoding="utf-8"))


def run_acceptance(output, archive=None, live_run=None, run_fn=None, screening=False):
    output = Path(output).resolve()
    frozen = None
    if screening:
        frozen = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                  for name in FROZEN_FILES_SHA256}
        changed = [name for name in frozen if frozen[name] != FROZEN_FILES_SHA256[name]]
        if changed:
            raise ValueError("Frozen M2 source hashes differ: " + ", ".join(changed))
    live_run = Path(live_run).resolve() if live_run else None
    if live_run:
        for name in ("manifest.json", "result.json", "events.jsonl"):
            if not (live_run / name).is_file() or (live_run / name).is_symlink():
                raise ValueError(f"Prior live evidence is missing or invalid: {live_run / name}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = output / f"{stamp}-{uuid4().hex[:8]}"
    archive = Path(archive).resolve() if archive else directory.with_suffix(".tar.gz")
    if archive.exists():
        raise FileExistsError(f"Evidence archive already exists: {archive}")
    if archive == directory or directory in archive.parents:
        raise ValueError("Archive must be outside the acceptance directory")
    directory.mkdir(parents=True, exist_ok=False)
    seed, episodes = (20, 20) if screening else (0, 1)
    report = {"state": "running", "run_directory": str(directory), "archive": str(archive),
              "scope": "frozen_seed20_39_screening" if screening else "seed0_development_acceptance_not_held_out_benchmark",
              "seed": seed, "episodes_per_cell": episodes, "max_steps": 360, "disturbance_magnitude_m": 0.12,
              "software": software_manifest(), "trials": [], "pairs": [],
              "prior_live_run": str(live_run) if live_run else None,
              "trial_process_isolation": "fresh_python_interpreter_same_suite_start_environment"
              if run_fn is None else "injected_test_runner"}
    if screening:
        report["acceptance_revision"] = "3e07c58d68290d009d9a7c175ee22104a9b51379"
        report["frozen_files_sha256"] = frozen
        report["passed_means"] = "complete_valid_paired_evidence_not_successful_manipulation_or_perfect_detection"
    trial_environment = os.environ.copy()
    interrupted = False
    for condition in CONDITIONS:
        for system in ("baseline", "v1"):
            cell = directory / f"{condition}-{system}"
            config = RunConfig(controller="fixed_pick_cube", protocol="m2", verification=system == "v1",
                               disturbance=condition, max_steps=360, render=False, render_device="cuda:0",
                               output=cell, seed=seed, episodes=episodes, disturbance_magnitude=0.12)
            trial = {"condition": condition, "system": system, "config": json_value(asdict(config)),
                     "run_directory": None, "passed": False, "state": "running"}
            report["trials"].append(trial)
            write_json(directory / "suite.json", report)
            print(f"M2 {'screening' if screening else 'acceptance'}: {condition} / {system}; seeds {seed}-{seed + episodes - 1}", flush=True)
            try:
                result = run_fn(config) if run_fn else run_in_process(config, trial_environment)
                trial["run_directory"] = result["run_directory"]
                check = check_screening if screening else check_trial
                trial.update(check(Path(result["run_directory"]), config), state="checked")
            except (Exception, KeyboardInterrupt) as error:
                trial.update(state="error", error=f"{type(error).__name__}: {error}")
                # runtime writes its error result in finally; retain that directory.
                candidates = sorted(cell.glob("*/result.json"))
                if len(candidates) == 1:
                    trial["run_directory"] = str(candidates[0].parent)
                interrupted = isinstance(error, KeyboardInterrupt)
            write_json(directory / "suite.json", report)
            if interrupted:
                break
        if interrupted:
            break
    for condition in CONDITIONS:
        pair = {"condition": condition, "passed": False}
        trials = [t for t in report["trials"] if t["condition"] == condition]
        if len(trials) == 2 and all(t["state"] == "checked" for t in trials):
            try:
                pair.update(compare_pair(*(Path(t["run_directory"]) for t in trials)))
            except Exception as error:
                pair["error"] = f"{type(error).__name__}: {error}"
        else:
            pair["error"] = "Pair is missing a completed, readable trial"
        report["pairs"].append(pair)
    report["state"] = ("interrupted" if interrupted else "passed" if
                       len(report["trials"]) == 6 and all(t["passed"] for t in report["trials"])
                       and all(p["passed"] for p in report["pairs"]) else "failed")
    write_json(directory / "suite.json", report)
    report["archive_sha256"] = archive_evidence(directory, archive, live_run,
                                               root="screening" if screening else "acceptance", scope=report["scope"])
    # The archive contains the pre-hash suite; this file adds the archive receipt.
    write_json(directory / "receipt.json", report)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, default=Path("runs/m2-acceptance"))
    cli.add_argument("--archive", type=Path)
    cli.add_argument("--live-run", type=Path, help="Include a prior live run's raw evidence")
    cli.add_argument("--screening", action="store_true", help="Run frozen seeds 20-39; task/detection outcomes are measured, not gated")
    args = cli.parse_args()
    result = run_acceptance(args.output, args.archive, args.live_run, screening=args.screening)
    print(json.dumps({"state": result["state"], "run_directory": result["run_directory"],
                      "scope": result["scope"], "seed": result["seed"],
                      "episodes_per_cell": result["episodes_per_cell"],
                      "passed_means": result.get("passed_means", "seed0_expected_outcomes_and_pair_integrity"),
                      "archive": result["archive"], "archive_sha256": result["archive_sha256"],
                      "trials": [{k: t.get(k) for k in
                                  ("condition", "system", "passed", "failed_checks", "error", "evaluation")}
                                 for t in result["trials"]],
                      "pairs": result["pairs"]}, indent=2, allow_nan=False))
    raise SystemExit(0 if result["state"] == "passed" else 2)


if __name__ == "__main__":
    main()
