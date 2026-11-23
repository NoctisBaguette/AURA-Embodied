"""Frozen seed 40-59 recovery screening; performance is measured, never gated."""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from uuid import uuid4

import numpy as np

from .acceptance import (CONDITIONS, FROZEN_FILES_SHA256, STEP_FIELDS, archive_evidence,
                         check_screening, compare_pair, load_trial, run_in_process, write_json)
from .m3_runtime import M3Config
from .policies import PickCubeSettings, vector
from .recovery import RecoverySettings, SUPPORTED_FAILURES
from .runtime import json_value, software_manifest
from .verification import (StateVerifier, TaskReference, TaskSettings,
                           VerificationMetrics, VerificationSettings)


SEEDS = tuple(range(40, 60))
SYSTEMS = ("baseline", "v1", "v2")
SCOPE = "frozen_m3_seed40_59_matched_recovery_screening"
FROZEN_SOURCES = {**FROZEN_FILES_SHA256,
    "recovery.py": "cb553d923c171e2582e8d41b77b4571118f166057b3f6cd0f4dc674dc2b04103",
    "m3_runtime.py": "a88fccf0dd257a356f71fbecb14636ec04a360b438f8fbac6d762a25977edd24",
    "m3.py": "0ceee0b8743345af3fce58e20e23e6c17e0660ec1ec068810cda59065dd3fa68",
    "acceptance.py": "09c8d44568330ba90ba7237bd2b25bf636b118fc037df82c14475599cae7b960"}
PROTOCOL_PATH = Path(__file__).resolve().parents[3] / "docs/research/experiments/evidence/AETHER_CL_M3_Frozen_Screening_Protocol.json"


def frozen_protocol():
    return {"name": SCOPE, "date": "2026-10-05", "acceptance_revision": "2d1c063e13811d9ad935504eaa46546f9d7aa86a",
            "acceptance_archive_sha256": "22871e65df0d946abb53382a86e4299d17ebbc028ce2505ee55758d1fdd182aa",
            "seeds": list(SEEDS), "episodes_per_cell": 20, "systems": list(SYSTEMS),
            "conditions": list(CONDITIONS), "requested_episodes": 180,
            "max_steps": 360, "disturbance_magnitude_m": .12, "shift_step": 81, "drop_step": 181,
            "env_id": "PickCube-v1", "physics_backend": "cpu", "render": False, "fps": 5.0,
            "policy_settings": asdict(PickCubeSettings()), "task_settings": asdict(TaskSettings()),
            "verification_settings": asdict(VerificationSettings()), "recovery_settings": asdict(RecoverySettings()),
            "frozen_files_sha256": FROZEN_SOURCES,
            "exclusions": "original seed order; no replacement; eligible-only denominators",
            "performance_gate": "none; task failures, false alarms, uncertainty, aborts and zero attempts remain measured outcomes",
            "analysis_unit": "matched episodes across 20 unique seeds; dense frames are correlated",
            "pairing": "baseline/V1 full traces; V1/V2 identical reset and trace through first intervention, or entire trace without intervention",
            "limitations": "one task, privileged state, synthetic pose relocation, one magnitude; not camera perception, physical realism, or full robustness curve"}


def preflight():
    root = Path(__file__).parent
    hashes = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in FROZEN_SOURCES}
    changed = [n for n in hashes if hashes[n] != FROZEN_SOURCES[n]]
    if changed:
        raise ValueError("Frozen M3 sources changed: " + ", ".join(changed))
    protocol = frozen_protocol()
    if json.loads(PROTOCOL_PATH.read_text(encoding="utf-8")) != protocol:
        raise ValueError("Frozen M3 protocol/settings differ from committed preregistration")
    return protocol


def episode_events(events, index):
    return [e for e in events if e.get("episode") == index]


def check_cell(directory, config):
    checked = check_screening(directory, config)
    manifest, result, events = load_trial(directory)
    checks = checked["checks"]
    episodes = checked["episodes"]
    checks["exact_reset_seeds"] = [e["seed"] for e in events if e["event"] == "reset"] == list(range(config.seed, config.seed + config.episodes))
    checks["episode_summaries_match_logs"] = [
        {k: v for k, v in e.items() if k not in ("event", "time_utc")}
        for e in events if e["event"] in ("episode_finished", "episode_excluded")] == episodes
    checks["final_result_matches_log"] = [e["result"] for e in events if e["event"] == "run_finished"] == [result]
    checks["no_unassigned_steps"] = all(e.get("episode") in range(config.episodes) for e in events if e["event"] == "step")
    checks["injection_geometry_and_order"] = True
    checks["final_step_task_matches_summary"] = True
    checks["recovery_contracts"] = True
    checks["recovery_metrics_match_episodes"] = True
    checks["reference_and_verifier_replay"] = True
    checks["first_failure_and_latency_match"] = True
    metrics = VerificationMetrics() if config.verification else None
    for ep in episodes:
        local = episode_events(events, ep["episode"])
        reset = next(e for e in local if e["event"] == "reset")
        steps = [e for e in local if e["event"] == "step"]
        injections = [e for e in local if e["event"] == "disturbance_applied"]
        if ep["excluded"]:
            checks["recovery_contracts"] &= not steps and not injections
            continue
        if not steps:
            checks["final_step_task_matches_summary"] = False
            continue
        reference = TaskReference(reset["observation"])
        verifier = StateVerifier(reset["observation"]) if config.verification else None
        for e in steps:
            final = e["step"] == config.max_steps or e["truncated"]
            truth = reference.observe(e["observation"], e["info"], e["step"], final=final)
            checks["reference_and_verifier_replay"] &= truth == e["reference"]
            if verifier:
                verdict = verifier.observe(e["observation"], e["step"], final=final)
                checks["reference_and_verifier_replay"] &= verdict == e["verification"]
                metrics.observe(truth, verdict)
        detected = verifier.first_failure if verifier else None
        truth = reference.first_failure
        latency = (detected["step"] - truth["step"] if detected and truth
                   and detected["failure"] == truth["failure"] and detected["step"] >= truth["step"] else None)
        checks["first_failure_and_latency_match"] &= (ep["first_reference_failure"] == truth
            and ep["first_detected_failure"] == detected and ep["first_failure_latency_steps"] == latency)
        if verifier:
            checks["reference_and_verifier_replay"] &= ep["final_verification"] == verdict
        checks["final_step_task_matches_summary"] &= steps[-1]["reference"]["task_success"] == ep["task_success_at_end"]
        for injection in injections:
            record = injection["disturbance"]
            before, after = record["before_pose_world"], record["after_pose_world"]
            prior = steps[injection["step"] - 2]["observation"]["extra"]["obj_pose"]
            initial_z = vector(reset["observation"]["extra"]["obj_pose"], 7, "obj_pose")[2]
            position = local.index(injection)
            following = local[position + 1] if position + 1 < len(local) else {}
            checks["injection_geometry_and_order"] &= (
                np.array_equal(np.asarray(prior).reshape(-1), before)
                and len(before) == len(after) == 7 and after[0] == before[0]
                and after[3:] == before[3:] and record.get("velocities_zeroed") is True
                and math.isclose(after[1] - before[1], config.disturbance_magnitude, abs_tol=1e-6)
                and math.isclose(after[2], initial_z if config.disturbance == "object_drop" else before[2], abs_tol=1e-6)
                and following.get("event") == "step" and following.get("step") == injection["step"])
        if config.system != "v2":
            continue
        snapshot = ep["recovery"]
        valid = steps[-1]["recovery"] == snapshot
        valid &= snapshot["attempts"] in (0, 1) and snapshot["state"] in ("nominal", "attempt_complete", "aborted")
        changed = [e for e in steps if e["controller_decision"]["phase"].startswith("recovery_")]
        trigger = snapshot["trigger_step"]
        if trigger is None:
            valid &= snapshot["state"] == "nominal" and not changed and snapshot["attempts"] == snapshot["action_steps"] == 0
        else:
            valid &= 1 <= trigger < config.max_steps and bool(changed) and changed[0]["step"] == trigger + 1
            verdict = steps[trigger - 1]["verification"]
            valid &= verdict["status"] == "failed" and verdict["failure"] == snapshot["reason"]
            valid &= not any(e["verification"]["status"] == "failed" for e in steps[:trigger - 1])
            used = snapshot["action_steps"]
            if snapshot["attempts"]:
                valid &= snapshot["reason"] in SUPPORTED_FAILURES and snapshot["first_action_step"] == trigger + 1
                valid &= snapshot["action_budget"] == min(RecoverySettings().action_budget, config.max_steps - trigger)
                valid &= 0 < used <= snapshot["action_budget"]
                active = steps[trigger:trigger + used]
                valid &= [e["recovery"]["action_steps"] for e in active] == list(range(1, used + 1))
                valid &= all(e["recovery"]["attempts"] == 1 for e in steps[trigger:])
                path = 0.0
                previous = vector(steps[trigger - 1]["observation"]["extra"]["tcp_pose"], 7, "tcp_pose")[:3]
                for e in active:
                    # Goal-change/invalid-observation aborts can occur before cost is updated.
                    if e["recovery"].get("failure_detail") not in ("goal_changed_during_attempt", "invalid_recovery_observation"):
                        current = vector(e["observation"]["extra"]["tcp_pose"], 7, "tcp_pose")[:3]
                        path += float(np.linalg.norm(current - previous))
                        previous = current
                    valid &= math.isclose(path, e["recovery"]["observed_tcp_path_m"], abs_tol=1e-8)
                valid &= math.isclose(path, snapshot["observed_tcp_path_m"], abs_tol=1e-8)
            else:
                valid &= snapshot["state"] == "aborted" and used == 0
                valid &= (snapshot["failure_detail"] == "unsupported_failure" and snapshot["reason"] not in SUPPORTED_FAILURES
                          or snapshot["failure_detail"] == "insufficient_remaining_budget"
                          and snapshot["reason"] in SUPPORTED_FAILURES and config.max_steps - trigger < RecoverySettings().minimum_remaining_steps)
            terminal = trigger + used if snapshot["attempts"] else trigger
            for e in steps[terminal:]:
                valid &= e["action"] == steps[terminal - 1]["action"] and e["recovery"] == snapshot
        for i, e in enumerate(steps):
            if e["controller_decision"]["phase"] == "recovery_transport" and (not i or steps[i - 1]["controller_decision"]["phase"] != "recovery_transport"):
                before = steps[i - 1]["recovery"] if i else {}
                valid &= before.get("candidate_persistence_steps", 0) >= VerificationSettings().failure_persistence_steps
                valid &= before.get("attempt_max_cube_lift_m", 0) >= TaskSettings().minimum_lift_m
        valid &= ep["recovery_task_success"] == bool(snapshot["attempts"] and ep["task_success_at_end"])
        checks["recovery_contracts"] &= valid
    checks["verification_metrics_match_replay"] = result["evaluation"].get("verification_metrics") == (metrics.result(True) if metrics else None)
    if config.system == "v2":
        eligible = [e for e in episodes if not e["excluded"]]
        attempted = [e for e in eligible if e["recovery"]["attempts"]]
        successes = sum(e["recovery_task_success"] for e in attempted)
        expected = {"scope": "final_shared_task_success_after_one_attempt", "complete": True,
                    "attempted_episodes": len(attempted), "detected_failure_episodes": sum(e["first_detected_failure"] is not None for e in eligible),
                    "aborted_attempts": sum(e["recovery"]["state"] == "aborted" for e in attempted), "recovery_successes": successes,
                    "recovery_success_rate": successes / len(attempted) if attempted else None,
                    "mean_attempt_action_steps": sum(e["recovery"]["action_steps"] for e in attempted) / len(attempted) if attempted else None,
                    "mean_attempt_observed_tcp_path_m": sum(e["recovery"]["observed_tcp_path_m"] for e in attempted) / len(attempted) if attempted else None}
        checks["recovery_metrics_match_episodes"] = result["evaluation"].get("recovery_metrics") == expected
    return {**checked, "passed": all(checks.values()), "failed_checks": [k for k, v in checks.items() if not v]}


def compare_recovery(passive_directory, active_directory):
    left, _, passive = load_trial(passive_directory)
    right, _, active = load_trial(active_directory)
    checks = {"shared_software_policy_task_verifier": all(left.get(k) == right.get(k)
              for k in ("software", "policy_details", "task_contract", "verifier", "disturbance")),
              "same_resets": True, "causal_prefixes": True, "same_preintervention_injections": True}
    prefixes = []
    for i in range(left["config"]["episodes"]):
        le, re = episode_events(passive, i), episode_events(active, i)
        lr = [e for e in le if e["event"] == "reset"]
        rr = [e for e in re if e["event"] == "reset"]
        checks["same_resets"] &= (len(lr) == len(rr) == 1 and all(lr[0][k] == rr[0][k] for k in ("seed", "observation", "eligibility")))
        ls = [e for e in le if e["event"] == "step"]
        rs = [e for e in re if e["event"] == "step"]
        summary = next(e for e in re if e["event"] in ("episode_finished", "episode_excluded"))
        trigger = summary.get("recovery", {}).get("trigger_step")
        prefix = trigger if trigger is not None else len(rs)
        checks["causal_prefixes"] &= len(ls) == len(rs) and all(
            all(a[k] == b[k] for k in (*STEP_FIELDS, "verification")) for a, b in zip(ls[:prefix], rs[:prefix]))
        li = [e["disturbance"] for e in le if e["event"] == "disturbance_applied" and e["step"] <= prefix]
        ri = [e["disturbance"] for e in re if e["event"] == "disturbance_applied" and e["step"] <= prefix]
        checks["same_preintervention_injections"] &= li == ri
        prefixes.append({"episode": i, "seed": lr[0]["seed"], "matched_steps": prefix,
                         "trigger_step": trigger, "entire_trace_without_intervention": trigger is None})
    return {"passed": all(checks.values()), "checks": checks, "episode_prefixes": prefixes}


def paired_outcomes(passive, active):
    counts = Counter()
    excluded = []
    for left, right in zip(passive["episodes"], active["episodes"]):
        if left["seed"] != right["seed"] or left["excluded"] != right["excluded"]:
            raise ValueError("Cannot summarize mismatched seeds or eligibility")
        if left["excluded"]:
            excluded.append(left["seed"])
        else:
            counts[f'{int(left["task_success_at_end"])}->{int(right["task_success_at_end"])}'] += 1
    total = sum(counts.values())
    return {"eligible_pairs": total, "excluded_seeds": excluded,
            "both_failed": counts["0->0"], "recovery_only_success": counts["0->1"],
            "passive_only_success": counts["1->0"], "both_succeeded": counts["1->1"],
            "success_rate_difference_v2_minus_v1": (counts["0->1"] - counts["1->0"]) / total if total else None}


def run_screening(output, archive=None, run_fn=None):
    protocol = preflight()
    output = Path(output).resolve()
    directory = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    archive = Path(archive).resolve() if archive else directory.with_suffix(".tar.gz")
    if archive.exists() or archive == directory or directory in archive.parents:
        raise ValueError("Archive must be a new path outside the suite directory")
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "protocol.json", protocol)
    report = {"state": "running", "scope": SCOPE,
              "passed_means": "complete_valid_matched_evidence_not_successful_recovery_or_perfect_detection",
              "protocol": protocol, "run_directory": str(directory), "archive": str(archive),
              "software": software_manifest(), "trial_process_isolation": "fresh_python_interpreter_same_suite_start_environment" if run_fn is None else "injected_test_runner",
              "trials": [], "pairs": [], "recovery_pairs": [], "paired_outcomes": []}
    environment = os.environ.copy()
    paths, trials = {}, {}
    interrupted = False
    for condition in CONDITIONS:
        for system in SYSTEMS:
            config = M3Config(system=system, verification=system != "baseline", seed=SEEDS[0], episodes=len(SEEDS),
                              disturbance=condition, disturbance_magnitude=protocol["disturbance_magnitude_m"],
                              max_steps=protocol["max_steps"], fps=protocol["fps"],
                              render=False, render_device="cuda:0", output=directory / f"{condition}-{system}")
            trial = {"condition": condition, "system": system, "state": "running", "passed": False, "config": json_value(asdict(config))}
            report["trials"].append(trial)
            trials[(condition, system)] = trial
            write_json(directory / "suite.json", report)
            print(f"M3 frozen screening: {condition} / {system}; seeds 40-59", flush=True)
            try:
                result = run_fn(config) if run_fn else run_in_process(config, environment, module="aether_cl.m3")
                path = Path(result["run_directory"])
                paths[(condition, system)] = path
                trial["run_directory"] = str(path)
                trial.update(check_cell(path, config))
                trial["state"] = "passed" if trial["passed"] else "failed"
                evaluation = trial["evaluation"]
                print(f"Cell {trial['state']}: eligible={evaluation['eligible_episodes']}, "
                      f"excluded={evaluation['excluded_episodes']}, "
                      f"task_success_rate={evaluation['task_success_rate_at_end']}", flush=True)
            except KeyboardInterrupt:
                interrupted = True
                trial.update(state="interrupted", error="KeyboardInterrupt")
                break
            except Exception as error:
                trial.update(state="error", error=f"{type(error).__name__}: {error}")
            write_json(directory / "suite.json", report)
        if interrupted:
            break
    for condition in CONDITIONS:
        for left, right, group, checker in (("baseline", "v1", "pairs", compare_pair), ("v1", "v2", "recovery_pairs", compare_recovery)):
            if (condition, left) in paths and (condition, right) in paths:
                pair = {"condition": condition, "systems": [left, right], "passed": False}
                try:
                    pair.update(checker(paths[(condition, left)], paths[(condition, right)]))
                    if right == "v2" and pair["passed"] and all(trials[(condition, s)]["passed"] for s in (left, right)):
                        report["paired_outcomes"].append({"condition": condition, **paired_outcomes(trials[(condition, left)], trials[(condition, right)])})
                except Exception as error:
                    pair["error"] = f"{type(error).__name__}: {error}"
                report[group].append(pair)
    valid = len(report["trials"]) == 9 and all(t["passed"] for t in report["trials"])
    valid &= all(len(report[g]) == 3 and all(p["passed"] for p in report[g]) for g in ("pairs", "recovery_pairs"))
    report["state"] = "interrupted" if interrupted else "passed" if valid else "failed"
    write_json(directory / "suite.json", report)
    print(f"Saving {report['state']} evidence archive: {archive}", flush=True)
    report["archive_sha256"] = archive_evidence(directory, archive, None, root="m3-screening", scope=SCOPE)
    write_json(directory / "receipt.json", report)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, default=Path("runs/m3-screening"))
    cli.add_argument("--archive", type=Path)
    args = cli.parse_args()
    report = run_screening(args.output, args.archive)
    print(json.dumps({"state": report["state"], "archive": report["archive"], "archive_sha256": report["archive_sha256"],
                      "scope": SCOPE, "passed_means": report["passed_means"],
                      "trials": [{k: t.get(k) for k in ("condition", "system", "state", "failed_checks", "error", "evaluation")} for t in report["trials"]],
                      "paired_outcomes": report["paired_outcomes"]}, indent=2, allow_nan=False))
    raise SystemExit(0 if report["state"] == "passed" else 2)


if __name__ == "__main__":
    main()
