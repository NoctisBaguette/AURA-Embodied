"""Replicate frozen M3 seeds 40-59 with a fresh native process per episode."""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .acceptance import CONDITIONS, archive_evidence, compare_pair, run_in_process, write_json
from .m3_runtime import M3Config
from .m3_screening import (FROZEN_SOURCES, SEEDS, SYSTEMS, check_cell, compare_recovery,
                           frozen_protocol, preflight as original_preflight)
from .runtime import json_value, software_manifest


SCOPE = "m3_seed40_59_isolated_episode_replication"
SOURCES = {**FROZEN_SOURCES, "m3_screening.py": "1a7a01e4f23e012d675f3dbf7a111b25d44b6440961ece158007edf835597d7d"}
PROTOCOL_PATH = Path(__file__).resolve().parents[3] / "docs/research/experiments/evidence/AETHER_CL_M3_Isolated_Screening_Protocol.json"


def protocol():
    return {**frozen_protocol(), "name": SCOPE,
            "execution": "fresh_python_interpreter_and_simulator_per_condition_system_seed",
            "child_episodes": 1, "episodes_per_cell": 20,
            "frozen_files_sha256": SOURCES,
            "seeds_already_observed": True,
            "interpretation": "correction replication of original preselected seeds; no new held-out sample or policy tuning",
            "failed_archive_sha256": "c8c73ef11f91c9ea55d519701660c89456b55cbd5fc1e283fbd5fa2a1257fb74",
            "correction": "remove simulator reuse across seeded episodes; retain strict full-reset/prefix checks",
            "exclusion_integrity": "single excluded episode is valid zero-action evidence; each complete cell must contain eligible episodes"}


def preflight():
    original_preflight()
    root = Path(__file__).parent
    changed = [n for n, digest in SOURCES.items() if hashlib.sha256((root / n).read_bytes()).hexdigest() != digest]
    if changed:
        raise ValueError("Frozen isolated-screening sources changed: " + ", ".join(changed))
    value = protocol()
    if json.loads(PROTOCOL_PATH.read_text(encoding="utf-8")) != value:
        raise ValueError("Isolated-screening protocol differs from committed amendment")
    return value


def check_episode(directory, config):
    checked = check_cell(directory, config)
    checks = checked["checks"]
    # Eligibility is a denominator, not an obligation for every selected reset.
    # Enforce eligible evidence at the complete cell rather than discarding or
    # resampling the preselected excluded seed's standalone zero-action trial.
    del checks["has_eligible_episode"]
    checks["single_requested_seed"] = config.episodes == 1 and len(checked["episodes"]) == 1 and checked["episodes"][0]["seed"] == config.seed
    return {**checked, "passed": all(checks.values()), "failed_checks": [k for k, v in checks.items() if not v]}


def cell_summary(trials):
    complete = len(trials) == len(SEEDS) and [t["seed"] for t in trials] == list(SEEDS) and all(t["passed"] for t in trials)
    episodes = [t["episodes"][0] for t in trials if len(t.get("episodes", [])) == 1]
    eligible = [e for e in episodes if not e["excluded"]]
    attempted = [e for e in eligible if e.get("recovery", {}).get("attempts")]
    recovery_successes = sum(e["recovery_task_success"] for e in attempted)
    return {"complete": complete, "passed": complete and bool(eligible),
            "recorded_episodes": len(episodes), "eligible_episodes": len(eligible),
            "excluded_seeds": [e["seed"] for e in episodes if e["excluded"]],
            "task_successes": sum(e["task_success_at_end"] for e in eligible),
            "task_success_rate_at_end": sum(e["task_success_at_end"] for e in eligible) / len(eligible) if complete and eligible else None,
            "attempted_episodes": len(attempted), "recovery_successes": recovery_successes,
            "recovery_success_rate": recovery_successes / len(attempted) if complete and attempted else None,
            "mean_attempt_action_steps": sum(e["recovery"]["action_steps"] for e in attempted) / len(attempted) if complete and attempted else None,
            "mean_attempt_observed_tcp_path_m": sum(e["recovery"]["observed_tcp_path_m"] for e in attempted) / len(attempted) if complete and attempted else None,
            "abort_or_decline_reasons": dict(Counter(e["recovery"]["failure_detail"] for e in eligible if e.get("recovery", {}).get("failure_detail"))),
            "first_detected_failure_counts": dict(Counter(e["first_detected_failure"]["failure"] for e in eligible if e["first_detected_failure"])),
            "first_failure_latency_steps": [e["first_failure_latency_steps"] for e in eligible if e["first_failure_latency_steps"] is not None]}


def paired_summary(pairs, trials, condition):
    complete = len(pairs) == len(SEEDS) and all(p["passed"] for p in pairs)
    counts = Counter()
    excluded = []
    for seed in SEEDS:
        left, right = trials.get((condition, "v1", seed)), trials.get((condition, "v2", seed))
        if not left or not right or not left["passed"] or not right["passed"]:
            complete = False
            continue
        a, b = left["episodes"][0], right["episodes"][0]
        if a["excluded"] != b["excluded"]:
            complete = False
        elif a["excluded"]:
            excluded.append(seed)
        else:
            counts[f'{int(a["task_success_at_end"])}->{int(b["task_success_at_end"])}'] += 1
    total = sum(counts.values())
    return {"condition": condition, "complete_valid_pairing": complete,
            "eligible_pairs": total, "excluded_seeds": excluded,
            "both_failed": counts["0->0"], "recovery_only_success": counts["0->1"],
            "passive_only_success": counts["1->0"], "both_succeeded": counts["1->1"],
            "success_rate_difference_v2_minus_v1": (counts["0->1"] - counts["1->0"]) / total if complete and total else None}


def run_screening(output, archive=None, run_fn=None):
    settings = preflight()
    output = Path(output).resolve()
    directory = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    archive = Path(archive).resolve() if archive else directory.with_suffix(".tar.gz")
    if archive.exists() or archive == directory or directory in archive.parents:
        raise ValueError("Archive must be a new path outside the suite directory")
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "protocol.json", settings)
    report = {"state": "running", "scope": SCOPE, "protocol": settings,
              "passed_means": "complete_valid_matched_evidence_not_successful_recovery",
              "run_directory": str(directory), "archive": str(archive), "software": software_manifest(),
              "trial_process_isolation": settings["execution"] if run_fn is None else "injected_single_episode_runner",
              "episode_trials": [], "pairs": [], "recovery_pairs": [], "cells": [], "paired_outcomes": []}
    environment = os.environ.copy()
    trials, paths = {}, {}
    interrupted = False
    for condition in CONDITIONS:
        for seed in SEEDS:
            for system in SYSTEMS:
                config = M3Config(system=system, verification=system != "baseline", seed=seed, episodes=1,
                                  disturbance=condition, disturbance_magnitude=settings["disturbance_magnitude_m"],
                                  max_steps=settings["max_steps"], fps=settings["fps"], render=False,
                                  render_device="cuda:0", output=directory / f"{condition}-{system}" / f"seed-{seed}")
                trial = {"condition": condition, "system": system, "seed": seed, "requested_seed_index": seed - SEEDS[0],
                         "state": "running", "passed": False, "config": json_value(asdict(config))}
                report["episode_trials"].append(trial)
                key = (condition, system, seed)
                trials[key] = trial
                write_json(directory / "suite.json", report)
                print(f"Isolated trial {len(report['episode_trials'])}/180: {condition} / seed {seed} / {system}", flush=True)
                try:
                    result = run_fn(config) if run_fn else run_in_process(config, environment, module="aether_cl.m3")
                    path = Path(result["run_directory"])
                    paths[key] = path
                    trial["run_directory"] = str(path)
                    trial.update(check_episode(path, config))
                    trial["state"] = "passed" if trial["passed"] else "failed"
                    ep = trial["episodes"][0]
                    print(f"  evidence={trial['state']}, excluded={ep['excluded']}, task_success={ep['task_success_at_end']}", flush=True)
                except KeyboardInterrupt:
                    interrupted = True
                    trial.update(state="interrupted", error="KeyboardInterrupt")
                    break
                except Exception as error:
                    trial.update(state="error", error=f"{type(error).__name__}: {error}")
                write_json(directory / "suite.json", report)
            for left, right, group, checker in (("baseline", "v1", "pairs", compare_pair), ("v1", "v2", "recovery_pairs", compare_recovery)):
                if (condition, left, seed) in paths and (condition, right, seed) in paths:
                    pair = {"condition": condition, "seed": seed, "systems": [left, right], "passed": False}
                    try:
                        pair.update(checker(paths[(condition, left, seed)], paths[(condition, right, seed)]))
                    except Exception as error:
                        pair["error"] = f"{type(error).__name__}: {error}"
                    report[group].append(pair)
            if interrupted:
                break
        if interrupted:
            break
    for condition in CONDITIONS:
        for system in SYSTEMS:
            cell_trials = [t for t in report["episode_trials"] if t["condition"] == condition and t["system"] == system]
            report["cells"].append({"condition": condition, "system": system, **cell_summary(cell_trials)})
        pairs = [p for p in report["recovery_pairs"] if p["condition"] == condition]
        report["paired_outcomes"].append(paired_summary(pairs, trials, condition))
    good = len(report["episode_trials"]) == 180 and all(t["passed"] for t in report["episode_trials"])
    good &= all(c["passed"] for c in report["cells"])
    good &= all(len(report[g]) == 60 and all(p["passed"] for p in report[g]) for g in ("pairs", "recovery_pairs"))
    report["state"] = "interrupted" if interrupted else "passed" if good else "failed"
    write_json(directory / "suite.json", report)
    print(f"Saving {report['state']} evidence: {archive}", flush=True)
    report["archive_sha256"] = archive_evidence(directory, archive, None, root="m3-isolated-screening", scope=SCOPE)
    write_json(directory / "receipt.json", report)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, default=Path("runs/m3-isolated-screening"))
    cli.add_argument("--archive", type=Path)
    args = cli.parse_args()
    report = run_screening(args.output, args.archive)
    print(json.dumps({k: report[k] for k in ("state", "scope", "archive", "archive_sha256", "cells", "paired_outcomes")}, indent=2, allow_nan=False))
    raise SystemExit(0 if report["state"] == "passed" else 2)


if __name__ == "__main__":
    main()
