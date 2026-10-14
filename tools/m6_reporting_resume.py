"""Resume frozen M6 after its first parent-report NumPy boolean write failure.

Run an exported copy outside the repository, from prototype_aether_cl. The
scientific checkout remains at SCIENTIFIC_COMMIT. Only parent JSON encoding is
adapted; simulator children, source guards, replay and comparisons are unchanged.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile


SCIENTIFIC_COMMIT = "7059c713d3b36e3f032aab8d1f87662ed6fdab91"
REPAIR_ID = "m6_parent_numpy_boolean_serialization_v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def reporting_encoder(sweep):
    """Preserve values and NaN rejection; convert NumPy scalars to JSON types."""
    original = sweep.write_json
    def encoded(path, value):
        return original(path, sweep.json_value(value))
    sweep.write_json = encoded
    try:
        yield
    finally:
        sweep.write_json = original


def repair_initial(sweep, output, archive, backup, software):
    """Adopt exactly one finished child by replay, never execute it again."""
    output, archive, backup = map(lambda p: Path(p).resolve(), (output, archive, backup))
    if archive.exists() or backup.exists() or output == backup or output in backup.parents:
        raise ValueError("Final archive and external immutable backup must be new")
    with (output / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = json.loads((output / "suite.json").read_text())
        settings = sweep.preflight()
        environment = {k: v for k, v in os.environ.items() if k not in sweep.VOLATILE_ENVIRONMENT}
        environment_sha = hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()
        if (report["state"] != "running" or len(report["episode_trials"]) != 1
                or report.get("reporting_repair") is not None
                or report["protocol"] != settings
                or json.loads((output / "protocol.json").read_text()) != settings
                or report["software"] != software
                or report["child_environment_sha256"] != environment_sha
                or report["run_directory"] != str(output) or report["archive"] != str(archive)):
            raise ValueError("Not the guarded first-slot reporting failure; retain evidence")
        trial = report["episode_trials"][0]
        planned = sweep.plan(output)[0]
        if trial["state"] != "running" or trial["passed"] is not False or any(trial.get(k) != v for k, v in planned.items()):
            raise ValueError("First slot identity/state differs; retain evidence")
        child_root = Path(trial["config"]["output"])
        results = sorted(child_root.glob("*/result.json"))
        if len(results) != 1:
            raise ValueError("Exactly one retained child result is required")
        child = json.loads(results[0].read_text())
        directory = results[0].parent.resolve()
        if child["run_directory"] != str(directory) or child["state"] != "finished":
            raise ValueError("Child is not complete; do not relaunch or waive checks")
        candidate = {**trial, "run_directory": str(directory)}
        checked = sweep.checked_trial(candidate, software)
        if not checked["passed"]:
            raise ValueError("Retained child replay failed: " + ", ".join(checked["failed_checks"]))
        raw_files = sweep.files(child_root, output)
        retained = []
        with backup.open("xb") as raw, tarfile.open(fileobj=raw, mode="w:gz") as bundle:
            for path in sorted(output.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Symlink in retained evidence")
                if path.is_file():
                    relative = path.relative_to(output).as_posix()
                    retained.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest(path)})
                    bundle.add(path, arcname="m6-before-report-repair/" + relative, recursive=False)
        trial.update(checked)
        trial.update(state="passed", run_directory=str(directory), evidence_files=raw_files)
        report["state"] = "paused"
        report["reporting_repair"] = {
            "id": REPAIR_ID, "scientific_commit": SCIENTIFIC_COMMIT,
            "launcher_sha256": digest(__file__), "time_utc": datetime.now(timezone.utc).isoformat(),
            "cause": "numpy_bool_in_parent_audit_checks_not_JSON_serializable",
            "operation": "JSON_scalar_conversion_and_complete_first_child_replay_no_reexecution",
            "backup": str(backup), "backup_sha256": digest(backup), "backup_files": retained,
            "adopted_slot": {k: planned[k] for k in ("point_id", "seed", "system")},
            "retained_child_files": raw_files,
            "controller_protocol_evaluator_pairing_and_child_environment_changes": False}
        with reporting_encoder(sweep):
            sweep.write_json(output / "suite.json", report)
        if sweep.files(child_root, output) != raw_files:
            raise ValueError("Raw child bytes changed during repair")
        return sweep.json_value(report)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path, required=True)
    cli.add_argument("--repair-initial", action="store_true")
    cli.add_argument("--backup", type=Path)
    cli.add_argument("--stop-after", type=int)
    args = cli.parse_args()
    if args.repair_initial != (args.backup is not None):
        cli.error("--repair-initial requires --backup; continuation does not use --backup")
    if args.repair_initial and args.stop_after != 17:
        cli.error("Initial repair continues exactly the next 17 retained pilot slots")
    if not (Path.cwd() / "aether_cl/m6_sweep.py").is_file():
        cli.error("Run from the original prototype_aether_cl directory")
    sys.path.insert(0, str(Path.cwd()))
    from aether_cl import m6_sweep as sweep
    software = sweep.software_manifest()
    if software["git_commit"] != SCIENTIFIC_COMMIT or software["git_dirty"] is not False:
        raise ValueError("Require clean original scientific commit " + SCIENTIFIC_COMMIT)
    sweep.preflight()
    if args.repair_initial:
        repaired = repair_initial(sweep, args.output, args.archive, args.backup, software)
        print("M6_REPORT_REPAIRED_FIRST_CHILD_RETAINED", flush=True)
        print("Backup SHA-256: " + repaired["reporting_repair"]["backup_sha256"], flush=True)
    report = json.loads((args.output / "suite.json").read_text())
    repair = report.get("reporting_repair", {})
    if repair.get("id") != REPAIR_ID or repair.get("launcher_sha256") != digest(__file__):
        raise ValueError("Missing or different recorded reporting repair")
    if digest(repair["backup"]) != repair["backup_sha256"]:
        raise ValueError("Immutable repair backup changed")
    with reporting_encoder(sweep):
        report = sweep.run_sweep(args.output, args.archive, resume=True, stop_after=args.stop_after)
    raise SystemExit(0 if report["state"] in ("passed", "paused") else 2)


if __name__ == "__main__":
    main()
