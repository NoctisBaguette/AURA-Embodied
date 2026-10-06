"""M7 known-seed development only: normal-six first, optional unfrozen magnitude commissioning."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile

from .runtime import json_value
from .m7_runtime import preflight_native, SYSTEMS, DEVELOPMENT_SEEDS, CANDIDATE_RATIOS, RECEIPT_PATH
from .m7_audit import replay, suite_pairs

INSPECTION_REPORT_PATH = Path("/home/jiangle/aura-work/m7-task-inspection.json")


def write_json(path, value):
    path.write_text(json.dumps(json_value(value), indent=2, allow_nan=False) + "\n")


def file_index(root):
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("No evidence symlinks")
        if path.is_file() and path.name != "archive_index.json":
            raw = path.read_bytes()
            records.append({"path": str(path.relative_to(root)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return records


def history_guard():
    script = Path(__file__).resolve().parents[3] / "tools/m7_task_inspection.py"
    spec = importlib.util.spec_from_file_location("m7_static_history_guard", script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    history = module.inspect_history(Path(__file__).resolve().parents[1] / "runs")
    if history["preferred_overlap"]:
        raise ValueError("Preferred fresh seeds acquired recorded resets during development; stop before selecting/fixing a fresh range")
    return history


def launch_child(output, seed, system, ratio, environment):
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-u", "-m", "aether_cl.m7_runtime", "--seed", str(seed), "--system", system,
               "--offset-clearance-ratio", str(ratio), "--output", str(output)]
    with (output / "process.stdout.log").open("x") as stdout, (output / "process.stderr.log").open("x") as stderr:
        process = subprocess.Popen(command, env=environment.copy(), stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            status = process.wait()
        except BaseException:
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
    if status:
        raise RuntimeError(f"Child exit{status}; retain evidence and inspect {output / 'process.stderr.log'}")
    results = list(output.glob("*/result.json"))
    if len(results) != 1:
        raise ValueError("Expected one child episode")
    return results[0].parent, json.loads(results[0].read_text())


def run_suite(output, archive, candidate_series=False):
    output, archive = Path(output).resolve(), Path(archive).resolve()
    if output.exists() or archive.exists() or output == archive or output in archive.parents:
        raise ValueError("Development output and outside archive must be new; no slot reruns/resume")
    native = preflight_native()
    inspection_bytes = INSPECTION_REPORT_PATH.read_bytes()
    receipt = json.loads(RECEIPT_PATH.read_text())
    if hashlib.sha256(inspection_bytes).hexdigest() != receipt["inspection_report_sha256"]:
        raise ValueError("Original installed inspection report differs; retain evidence")
    # Preserve the exact historical source/protocol guard chain.
    from .m6r_sweep import preflight as previous_preflight
    previous_preflight()
    history = history_guard()
    environment = dict(os.environ)
    digest = hashlib.sha256(json.dumps(environment, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    ratios = CANDIDATE_RATIOS if candidate_series else (0.,)
    selected = [{"ratio": ratio, "seed": seed, "system": system} for ratio in ratios for seed in DEVELOPMENT_SEEDS for system in SYSTEMS]
    report = {"scope": "m7_known_seed_development_not_confirmatory", "state": "running", "native": native,
              "child_environment_sha256": digest, "history_before": history, "selected": selected, "trials": [],
              "candidate_series": candidate_series, "fresh_native": False, "protocol_frozen": False,
              "archive": str(archive), "passed_means": "complete_replayed_matched_evidence_not_task_or_recovery_success"}
    # Preserve local source bytes/receipt in the evidence archive for portable audit.
    source_snapshot = output / "source_snapshot"
    source_snapshot.mkdir()
    for name in ("m7_task.py", "m7_policy.py", "m7_runtime.py", "m7_audit.py", "m7_development.py", "policies.py", "runtime.py", "verification.py"):
        (source_snapshot / name).write_bytes(Path(__file__).with_name(name).read_bytes())
    (source_snapshot / RECEIPT_PATH.name).write_bytes(RECEIPT_PATH.read_bytes())
    (source_snapshot / "m7-task-inspection.json").write_bytes(inspection_bytes)
    interrupted = False
    try:
        for slot, item in enumerate(selected, 1):
            trial = {**item, "state": "running"}; report["trials"].append(trial)
            write_json(output / "suite.json", report)
            print(f"START {slot}/{len(selected)} ratio={item['ratio']} seed={item['seed']} {item['system']}", flush=True)
            child_root = output / f"ratio-{item['ratio']:g}" / f"seed-{item['seed']}" / item["system"]
            try:
                directory, result = launch_child(child_root, item["seed"], item["system"], item["ratio"], environment)
                child_manifest = json.loads((directory / "manifest.json").read_text())
                expected_config = {"seed": item["seed"], "system": item["system"], "offset_clearance_ratio": item["ratio"], "output": str(child_root)}
                if child_manifest["config"] != expected_config or result["config"] != expected_config:
                    raise ValueError("Child configuration differs from selected slot")
                if any(child_manifest.get(k) != v for k, v in native.items()) or child_manifest["startup_environment_sha256"] != digest:
                    raise ValueError("Child source/software/startup environment differs from parent")
                trial.update(run_directory=str(directory.relative_to(output)), result=result, audit=replay(directory), state="passed")
            except BaseException as error:
                trial.update(state="error", error=f"{type(error).__name__}: {error}")
                raise
            print(f"END {slot}/{len(selected)} success={result['task_success_at_end']} depth_mm={result['final_reference']['depth_m']*1000:.3f} recovery={result['recovery']['state']}", flush=True)
        report["pairs"] = suite_pairs(report["trials"], output, include_controls=candidate_series)
        expected_pairs = len(ratios) * 2 * 2 + ((len(ratios) - 1) * 2 if candidate_series else 0)
        if len(report["pairs"]) != expected_pairs:
            raise ValueError("Matched development pairs incomplete")
        report["history_after"] = history_guard()
        report["state"] = "passed"
    except BaseException as error:
        interrupted = isinstance(error, KeyboardInterrupt)
        report.update(state="interrupted" if interrupted else "error", error=f"{type(error).__name__}: {error}")
    finally:
        write_json(output / "suite.json", report)
        write_json(output / "archive_index.json", {"files": file_index(output), "index_excludes_self": True})
        archive.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive archive creation retains partial/error evidence too.
        with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
            tar.add(output, arcname=output.name)
        print("Archive:", archive, flush=True)
        print("Archive SHA-256:", hashlib.sha256(archive.read_bytes()).hexdigest(), flush=True)
    if report["state"] != "passed":
        raise RuntimeError("Development did not pass evidence checks; archive/log retained. " + report.get("error", ""))
    print("M7_DEVELOPMENT_EVIDENCE_VALID", flush=True)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path, required=True)
    cli.add_argument("--candidate-series", action="store_true", help="Development only; normal + clearance ratios .5/1/2/4/8 on known100/101")
    args = cli.parse_args()
    run_suite(args.output, args.archive, args.candidate_series)


if __name__ == "__main__":
    main()
