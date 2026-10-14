"""Preregistered M4 magnitude curve; fresh native process per selected trial."""

import argparse
from collections import Counter
from dataclasses import asdict
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .acceptance import archive_evidence, compare_pair, load_trial, run_in_process, trace, write_json
from .m3_isolated_screening import SOURCES, check_episode, preflight as m3_preflight
from .m3_runtime import M3Config
from .m3_screening import SYSTEMS, compare_recovery, frozen_protocol
from .runtime import json_value, software_manifest
from .verification import VerificationMetrics


SEEDS = tuple(range(60, 80))
MAGNITUDES = (.02, .04, .08, .12, .20)
SCOPE = "m4_seed60_79_frozen_magnitude_robustness"
FROZEN_SOURCES = {**SOURCES, "m3_isolated_screening.py":
                  "4ae4ff7ee1cf919898a786a79ba398c452984f72bf1e64429ed68a59fa966fbd"}
PROTOCOL_PATH = Path(__file__).resolve().parents[3] / "docs/research/experiments/evidence/AETHER_CL_M4_Robustness_Protocol.json"
VOLATILE_ENVIRONMENT = ("SSH_CLIENT", "SSH_CONNECTION", "SSH_TTY", "TERM", "SHLVL", "_", "PWD", "OLDPWD")


def points():
    # A zero horizontal shift in drop would still change height. Normal is a
    # separate no-injection control, not a fictional zero-magnitude drop.
    return [{"point_id": "normal", "condition": "none", "magnitude_m": None,
             "config_magnitude_m": .12}] + [
        {"point_id": f"{condition}-{round(magnitude * 1000):03d}mm", "condition": condition,
         "magnitude_m": magnitude, "config_magnitude_m": magnitude}
        for condition in ("object_shift", "object_drop") for magnitude in MAGNITUDES]


def protocol():
    value = frozen_protocol()
    value.pop("disturbance_magnitude_m")
    return {**value, "name": SCOPE, "seeds": list(SEEDS), "conditions": points(),
            "magnitudes_m": list(MAGNITUDES), "requested_episodes": 660,
            "acceptance_revision": "c4a9b30475e60794f893b415f6ee4f5b70a2540e",
            "acceptance_archive_sha256": "87d1ada67b827e6a6c8b5b074d0654fbf3b03176d62c7b01714bd05584cc1421",
            "execution": "fresh_python_interpreter_and_simulator_per_point_seed_system",
            "child_episodes": 1, "frozen_files_sha256": FROZEN_SOURCES,
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "order": "normal, ascending shift magnitudes, ascending drop magnitudes; seed; baseline/V1/V2",
            "analysis_unit": "matched seed episodes; same 20 seeds reused across magnitudes; no frame-level independence",
            "seed_selection": "new preselected contiguous seeds 60-79; no adaptive selection or replacement",
            "resume": "verify source/protocol/software/environment and raw hashes; continue unstarted slots only; retain errors",
            "cross_magnitude_control": "each baseline reset and pre-injection prefix must exactly match the same-seed normal baseline",
            "environment_normalization": list(VOLATILE_ENVIRONMENT),
            "limitations": "one held-cube task, privileged state, synthetic positive world-Y relocation; drop also resets height; finite 2-20 cm range"}


def preflight():
    m3_preflight()
    changed = [name for name, digest in FROZEN_SOURCES.items()
               if hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest() != digest]
    if changed:
        raise ValueError("Frozen M4 sources changed: " + ", ".join(changed))
    value = protocol()
    if json.loads(PROTOCOL_PATH.read_text(encoding="utf-8")) != value:
        raise ValueError("M4 protocol/runner differs from committed preregistration")
    for point in points():
        M3Config(disturbance=point["condition"], disturbance_magnitude=point["config_magnitude_m"]).validate()
    return value


def plan(output):
    return [{**point, "seed": seed, "requested_seed_index": seed - SEEDS[0], "system": system,
             "config": json_value(asdict(M3Config(
                 system=system, verification=system != "baseline", seed=seed, episodes=1,
                 disturbance=point["condition"], disturbance_magnitude=point["config_magnitude_m"],
                 render=False, fps=5.0, output=output / point["point_id"] / f"seed-{seed}" / system)))}
            for point in points() for seed in SEEDS for system in SYSTEMS]


def files(directory, root):
    result = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Evidence symlinks are not supported")
        if path.is_file():
            data = path.read_bytes()
            result.append({"path": str(path.relative_to(root)), "bytes": len(data),
                           "sha256": hashlib.sha256(data).hexdigest()})
    return result


def checked_trial(trial, software):
    config = M3Config(**{**trial["config"], "output": Path(trial["config"]["output"])})
    directory = Path(trial["run_directory"])
    if config.output not in directory.parents:
        raise ValueError("Child evidence is outside its selected trial directory")
    checked = check_episode(directory, config)
    checked["checks"]["suite_software_matches"] = load_trial(directory)[0]["software"] == software
    checked["passed"] = all(checked["checks"].values())
    checked["failed_checks"] = [k for k, v in checked["checks"].items() if not v]
    return checked


def summarize_cell(trials):
    complete = (len(trials) == len(SEEDS) and [t["seed"] for t in trials] == list(SEEDS)
                and all(t["passed"] for t in trials))
    episodes = [t["episodes"][0] for t in trials if len(t.get("episodes", [])) == 1]
    eligible = [e for e in episodes if not e["excluded"]]
    attempted = [e for e in eligible if e.get("recovery", {}).get("attempts")]
    count = sum(e["task_success_at_end"] for e in eligible)
    def mean(values):
        return sum(values) / len(values) if complete and values else None
    metrics = None
    if trials and trials[0]["system"] != "baseline":
        metrics = VerificationMetrics()
        attributes = {"steps": "steps", "uncertain_steps": "uncertain", "true_positive": "tp",
                      "false_positive": "fp", "false_negative": "fn", "true_negative": "tn",
                      "uncertain_on_negative": "uncertain_on_negative"}
        for trial in trials:
            value = trial.get("evaluation", {}).get("verification_metrics")
            if not value:
                continue
            for name, attribute in attributes.items():
                setattr(metrics, attribute, getattr(metrics, attribute) + value[name])
            for key, amount in value["confusion"].items():
                metrics.confusion[key] = metrics.confusion.get(key, 0) + amount
                truth, prediction = key.split("->")
                if truth == prediction and truth not in ("NONE", "UNCERTAIN"):
                    metrics.correct_diagnoses += amount
        metrics = metrics.result(complete)
    successes = sum(e["recovery_task_success"] for e in attempted)
    return {"complete": complete, "passed": complete and bool(eligible), "recorded_episodes": len(episodes),
            "eligible_episodes": len(eligible), "excluded_seeds": [e["seed"] for e in episodes if e["excluded"]],
            "task_successes": count, "task_success_rate_at_end": count / len(eligible) if complete and eligible else None,
            "attempted_episodes": len(attempted), "recovery_successes": successes,
            "recovery_success_rate": successes / len(attempted) if complete and attempted else None,
            "aborted_attempts": sum(e["recovery"]["state"] == "aborted" for e in attempted),
            "mean_attempt_action_steps": mean([e["recovery"]["action_steps"] for e in attempted]),
            "mean_attempt_observed_tcp_path_m": mean([e["recovery"]["observed_tcp_path_m"] for e in attempted]),
            "mean_final_cube_goal_distance_m": mean([e["final_cube_goal_distance_m"] for e in eligible]),
            "abort_or_decline_reasons": dict(Counter(e["recovery"]["failure_detail"] for e in eligible if e.get("recovery", {}).get("failure_detail"))),
            "first_detected_failure_counts": dict(Counter(e["first_detected_failure"]["failure"] for e in eligible if e["first_detected_failure"])),
            "first_failure_latency_steps": [e["first_failure_latency_steps"] for e in eligible if e["first_failure_latency_steps"] is not None],
            "verification_metrics": metrics}


def summarize_pairs(point, pairs, trials):
    complete = len(pairs) == len(SEEDS) and all(p["passed"] for p in pairs)
    counts, excluded = Counter(), []
    for seed in SEEDS:
        a, b = trials.get((point["point_id"], seed, "v1")), trials.get((point["point_id"], seed, "v2"))
        if not a or not b or not a["passed"] or not b["passed"]:
            complete = False
            continue
        left, right = a["episodes"][0], b["episodes"][0]
        if left["excluded"] != right["excluded"]:
            complete = False
        elif left["excluded"]:
            excluded.append(seed)
        else:
            counts[f'{int(left["task_success_at_end"])}->{int(right["task_success_at_end"])}'] += 1
    total = sum(counts.values())
    return {**point, "complete_valid_pairing": complete, "eligible_pairs": total, "excluded_seeds": excluded,
            "both_failed": counts["0->0"], "recovery_only_success": counts["0->1"],
            "passive_only_success": counts["1->0"], "both_succeeded": counts["1->1"],
            "success_rate_difference_v2_minus_v1": (counts["0->1"] - counts["1->0"]) / total if complete and total else None}


def compare_control(normal_directory, disturbed_directory, before_step):
    left, _, a = load_trial(normal_directory)
    right, _, b = load_trial(disturbed_directory)
    def prefix(events):
        return [e for e in trace(events) if e["event"] == "reset"
                or e.get("step", before_step + 1) <= before_step]
    checks = {"same_software_policy_task": all(left.get(k) == right.get(k)
              for k in ("software", "policy_details", "task_contract")),
              "same_reset_and_preinjection_trace": prefix(a) == prefix(b)}
    return {"passed": all(checks.values()), "checks": checks, "before_injection_step": before_step + 1}


def summarize(report, output):
    lookup = {(t["point_id"], t["seed"], t["system"]): t for t in report["episode_trials"]}
    report.update(pairs=[], recovery_pairs=[], control_pairs=[], cells=[], paired_outcomes=[])
    for point in points():
        for seed in SEEDS:
            control = lookup.get(("normal", seed, "baseline"))
            disturbed = lookup.get((point["point_id"], seed, "baseline"))
            if point["condition"] != "none" and control and disturbed and control.get("run_directory") and disturbed.get("run_directory"):
                pair = {**point, "seed": seed, "passed": False}
                try:
                    pair.update(compare_control(Path(control["run_directory"]), Path(disturbed["run_directory"]),
                                                80 if point["condition"] == "object_shift" else 180))
                except Exception as error:
                    pair["error"] = f"{type(error).__name__}: {error}"
                report["control_pairs"].append(pair)
            for left, right, group, checker in (("baseline", "v1", "pairs", compare_pair),
                                               ("v1", "v2", "recovery_pairs", compare_recovery)):
                a, b = lookup.get((point["point_id"], seed, left)), lookup.get((point["point_id"], seed, right))
                if a and b and a.get("run_directory") and b.get("run_directory"):
                    pair = {**point, "seed": seed, "systems": [left, right], "passed": False}
                    try:
                        pair.update(checker(Path(a["run_directory"]), Path(b["run_directory"])))
                    except Exception as error:
                        pair["error"] = f"{type(error).__name__}: {error}"
                    report[group].append(pair)
        comparable = all(len([p for p in report[g] if p["point_id"] == point["point_id"]]) == len(SEEDS)
                         and all(p["passed"] for p in report[g] if p["point_id"] == point["point_id"])
                         for g in ("pairs", "recovery_pairs"))
        if point["condition"] != "none":
            comparable &= (len([p for p in report["control_pairs"] if p["point_id"] == point["point_id"]]) == len(SEEDS)
                           and all(p["passed"] for p in report["control_pairs"] if p["point_id"] == point["point_id"]))
            normal_trials = [t for t in report["episode_trials"] if t["point_id"] == "normal" and t["system"] == "baseline"]
            comparable &= len(normal_trials) == len(SEEDS) and all(t["passed"] for t in normal_trials)
        point_trials = [t for t in report["episode_trials"] if t["point_id"] == point["point_id"]]
        comparable &= len(point_trials) == len(SEEDS) * len(SYSTEMS) and all(t["passed"] for t in point_trials)
        for system in SYSTEMS:
            selected = [t for t in report["episode_trials"] if t["point_id"] == point["point_id"] and t["system"] == system]
            cell = {**point, "system": system, **summarize_cell(selected)}
            cell["comparison_valid"] = comparable and cell["passed"]
            cell["validated_curve_success_rate"] = cell["task_success_rate_at_end"] if cell["comparison_valid"] else None
            report["cells"].append(cell)
        report["paired_outcomes"].append(summarize_pairs(point, [p for p in report["recovery_pairs"] if p["point_id"] == point["point_id"]], lookup))
    columns = ("point_id", "condition", "magnitude_m", "system", "complete", "comparison_valid", "eligible_episodes", "task_successes",
               "validated_curve_success_rate",
               "task_success_rate_at_end", "attempted_episodes", "recovery_success_rate", "mean_attempt_action_steps",
               "mean_attempt_observed_tcp_path_m", "mean_final_cube_goal_distance_m")
    with (output / "curve.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["cells"])


def run_sweep(output, archive, resume=False, stop_after=None, run_fn=None):
    settings = preflight()
    output, archive = Path(output).resolve(), Path(archive).resolve()
    if stop_after is not None and (not isinstance(stop_after, int) or stop_after < 1):
        raise ValueError("stop_after must be a positive trial count")
    if archive.exists() or output == archive or output in archive.parents:
        raise ValueError("Archive must be new and outside the study directory")
    software = software_manifest()
    if run_fn is None and (not software.get("git_commit") or software.get("git_dirty") is not False):
        raise ValueError("Native M4 requires a clean committed repository")
    environment = {k: v for k, v in os.environ.items() if k not in VOLATILE_ENVIRONMENT}
    environment_digest = hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=resume)
    with (output / "runner.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another M4 runner owns this study directory") from None
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
            print(f"M4 trial {len(report['episode_trials'])}/660: {item['point_id']} / seed {item['seed']} / {item['system']}", flush=True)
            config = M3Config(**{**item["config"], "output": Path(item["config"]["output"])})
            try:
                result = run_fn(config) if run_fn else run_in_process(config, environment, module="aether_cl.m3")
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
        good &= all(len(report[g]) == 220 and all(p["passed"] for p in report[g]) for g in ("pairs", "recovery_pairs"))
        good &= len(report["control_pairs"]) == 200 and all(p["passed"] for p in report["control_pairs"])
        report["state"] = "interrupted" if interrupted else "paused" if not finished else "passed" if good else "failed"
        saved = archive if finished else archive.with_name(archive.name.removesuffix(".tar.gz") + "-partial-" + uuid4().hex[:8] + ".tar.gz")
        report["saved_archive"] = str(saved)
        write_json(output / "suite.json", report)
        # The shared helper expects a first snapshot. Remove only the generated
        # old index; immutable previous archives and every raw trial stay intact.
        (output / "archive_index.json").unlink(missing_ok=True)
        digest = archive_evidence(output, saved, None, root="m4-robustness", scope=SCOPE)
        write_json(Path(str(saved) + ".receipt.json"), {"state": report["state"], "archive": str(saved), "archive_sha256": digest})
        print(f"M4 {report['state']}: {saved}\nSHA-256: {digest}", flush=True)
        return {**report, "archive_sha256": digest}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path, required=True)
    cli.add_argument("--resume", action="store_true")
    cli.add_argument("--stop-after", type=int, help="Gracefully pause after N new trials; continue unstarted slots with --resume")
    args = cli.parse_args()
    report = run_sweep(args.output, args.archive, args.resume, args.stop_after)
    raise SystemExit(0 if report["state"] in ("passed", "paused") else 2)


if __name__ == "__main__":
    main()
