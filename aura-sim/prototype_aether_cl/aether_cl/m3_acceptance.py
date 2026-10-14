"""Nine isolated seed-0 development trials; failures remain measured outcomes."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .acceptance import (CONDITIONS, FROZEN_FILES_SHA256, STEP_FIELDS, archive_evidence,
                         check_trial, compare_pair, load_trial, run_in_process, write_json)
from .m3_runtime import M3Config
from .runtime import json_value, software_manifest


def check_v2(directory, passive_directory, config):
    manifest, result, events = load_trial(directory)
    passive_manifest, _, passive = load_trial(passive_directory)
    steps = [e for e in events if e["event"] == "step"]
    prior = [e for e in passive if e["event"] == "step"]
    episodes = result.get("episodes", [])
    ep = episodes[0] if len(episodes) == 1 else {}
    recovery = ep.get("recovery", {})
    condition = manifest["config"]["disturbance"]
    checks = {
        "config_matches": manifest.get("config") == json_value(asdict(config)),
        "shared_software_policy_task_verifier": all(manifest.get(k) == passive_manifest.get(k)
            for k in ("software", "policy_details", "task_contract", "verifier")),
        "complete_eligible_episode": (result.get("state") == "finished" and len(episodes) == 1
            and ep.get("seed") == 0 and ep.get("excluded") is False and not ep.get("stopped")
            and result.get("evaluation", {}).get("complete") is True),
        "full_shared_budget": ep.get("steps") == 360 and [e["step"] for e in steps] == list(range(1, 361)),
        "clean_revision": bool(manifest["software"].get("git_commit")) and manifest["software"].get("git_dirty") is False,
        "no_execution_errors": not any(e["event"] in ("run_failed", "cleanup_failed") for e in events),
        "bounded_attempt": recovery.get("attempts", 2) <= 1 and recovery.get("action_steps", 231) <= recovery.get("action_budget", 0) <= 230,
        "same_reset": [e["observation"] for e in events if e["event"] == "reset"]
            == [e["observation"] for e in passive if e["event"] == "reset"],
        "same_injection": [e["disturbance"] for e in events if e["event"] == "disturbance_applied"]
            == [e["disturbance"] for e in passive if e["event"] == "disturbance_applied"],
        "transport_gate": True,
    }
    if condition == "none":
        checks["normal_unchanged"] = recovery.get("attempts") == 0 and ep.get("task_success_at_end") is True
        prefix = 360
    else:
        detected = ep.get("first_detected_failure") or {}
        checks["verifier_triggered_once"] = (recovery.get("attempts") == 1 and detected.get("failure") == CONDITIONS[condition]
            and recovery.get("trigger_step") == detected.get("step")
            and recovery.get("first_action_step") == detected.get("step", -1) + 1
            and recovery.get("state") in ("attempt_complete", "aborted"))
        prefix = recovery.get("trigger_step") or 0
    checks["nominal_prefix_equal"] = (prefix > 0 and len(steps) >= prefix and len(prior) >= prefix
        and all(all(a[k] == b[k] for k in STEP_FIELDS) for a, b in zip(steps[:prefix], prior[:prefix])))
    for i, event in enumerate(steps):
        if event["controller_decision"]["phase"] == "recovery_transport" and (
                i == 0 or steps[i - 1]["controller_decision"]["phase"] != "recovery_transport"):
            previous = steps[i - 1]["recovery"] if i else {}
            checks["transport_gate"] &= (previous.get("candidate_persistence_steps", 0) >= 3
                                        and previous.get("attempt_max_cube_lift_m", 0) >= .05)
    return {"passed": all(checks.values()), "checks": checks,
            "failed_checks": [k for k, v in checks.items() if not v],
            "episode": ep, "evaluation": result.get("evaluation")}


def run_acceptance(output, archive=None, run_fn=None):
    frozen = {n: hashlib.sha256((Path(__file__).parent / n).read_bytes()).hexdigest() for n in FROZEN_FILES_SHA256}
    if frozen != FROZEN_FILES_SHA256:
        raise ValueError("Frozen M2 sources changed before M3 acceptance")
    output = Path(output).resolve()
    directory = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    archive = Path(archive).resolve() if archive else directory.with_suffix(".tar.gz")
    if archive.exists() or archive == directory or directory in archive.parents:
        raise ValueError("Archive must be a new path outside the suite directory")
    directory.mkdir(parents=True, exist_ok=False)
    report = {"state": "running", "scope": "seed0_m3_development_evidence_not_robustness_benchmark",
              "passed_means": "complete_matched_evidence_and_recovery_contracts_not_recovery_success",
              "software": software_manifest(), "frozen_m2_files_sha256": frozen,
              "trial_process_isolation": "fresh_python_interpreter_same_suite_start_environment" if run_fn is None else "injected_test_runner",
              "run_directory": str(directory), "archive": str(archive), "trials": [], "pairs": []}
    environment = os.environ.copy()
    interrupted = False
    paths = {}
    for condition in CONDITIONS:
        for system in ("baseline", "v1", "v2"):
            config = M3Config(system=system, verification=system != "baseline", disturbance=condition,
                              render=False, render_device="cuda:0", output=directory / f"{condition}-{system}")
            trial = {"condition": condition, "system": system, "state": "running", "passed": False,
                     "config": json_value(asdict(config))}
            report["trials"].append(trial)
            write_json(directory / "suite.json", report)
            print(f"M3 development: {condition} / {system}", flush=True)
            try:
                result = run_fn(config) if run_fn else run_in_process(config, environment, module="aether_cl.m3")
                path = Path(result["run_directory"])
                paths[(condition, system)] = path
                trial["run_directory"] = str(path)
                trial.update(check_v2(path, paths[(condition, "v1")], config) if system == "v2" else check_trial(path, config))
                trial["state"] = "passed" if trial["passed"] else "failed"
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
        for left, right in (("baseline", "v1"), ("v1", "v2")):
            if right == "v2" and condition != "none":
                continue
            if (condition, left) in paths and (condition, right) in paths:
                report["pairs"].append({"condition": condition, "systems": [left, right],
                                        **compare_pair(paths[(condition, left)], paths[(condition, right)])})
    good = (len(report["trials"]) == 9 and all(t["passed"] for t in report["trials"])
            and len(report["pairs"]) == 4 and all(p["passed"] for p in report["pairs"]))
    report["state"] = "interrupted" if interrupted else "passed" if good else "failed"
    write_json(directory / "suite.json", report)
    report["archive_sha256"] = archive_evidence(directory, archive, None, root="m3-acceptance", scope=report["scope"])
    write_json(directory / "receipt.json", report)
    return report


def main():
    cli = argparse.ArgumentParser(description="M3 nine-cell isolated native development check")
    cli.add_argument("--output", type=Path, default=Path("runs/m3-acceptance"))
    cli.add_argument("--archive", type=Path)
    args = cli.parse_args()
    report = run_acceptance(args.output, args.archive)
    print(json.dumps({"state": report["state"], "archive": report["archive"], "archive_sha256": report["archive_sha256"],
                      "trials": [{"condition": t["condition"], "system": t["system"], "state": t["state"],
                                  "error": t.get("error"), "failed_checks": t.get("failed_checks"),
                                  "task_success": t.get("episode", {}).get("task_success_at_end"),
                                  "recovery": t.get("episode", {}).get("recovery")} for t in report["trials"]]}, indent=2))
    raise SystemExit(0 if report["state"] == "passed" else 2)


if __name__ == "__main__":
    main()
