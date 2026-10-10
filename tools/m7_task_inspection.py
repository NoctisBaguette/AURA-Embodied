"""Inspect installed insertion-task sources/assets and reset history without simulation."""

import argparse
import ast
import hashlib
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import subprocess
import sys

AUTHORITY = "145aadce249b23a49ecb899ff273e93f673dd03b"


def source_record(path, root):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(root)), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "source": raw.decode("utf-8")}


def task_definitions(path, root):
    value = path.read_text(encoding="utf-8")
    records = []
    for node in ast.walk(ast.parse(value)):
        if not isinstance(node, ast.ClassDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            name = getattr(decorator.func, "id", getattr(decorator.func, "attr", None))
            if name != "register_env" or not decorator.args:
                continue
            uid = decorator.args[0]
            if not isinstance(uid, ast.Constant) or not isinstance(uid.value, str):
                continue
            records.append({"env_id": uid.value, "class": node.name,
                            "source_path": str(path.relative_to(root)),
                            "registration_keywords": {k.arg or "expanded_kwargs": ast.unparse(k.value) for k in decorator.keywords},
                            "description": ast.get_docstring(node)})
    return records


def inspect_history(root):
    observed, event_files = set(), 0
    for path in sorted(root.rglob("events.jsonl")):
        event_files += 1
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                # Parse every possible reset event, without deserializing the
                # much larger step observations; never execute a reset.
                if '"reset"' not in line and '"controller_reset"' not in line:
                    continue
                event = json.loads(line)
                if event.get("event") not in ("reset", "controller_reset"):
                    continue
                if "seed" in event:
                    seed = event["seed"]
                    if not isinstance(seed, int) or isinstance(seed, bool):
                        raise ValueError(f"Non-integer recorded reset seed in {path}")
                    observed.add(seed)
    if event_files == 0 or not observed:
        raise ValueError("No recorded native resets found; cannot establish preferred seed provenance")
    preferred = list(range(140, 160))
    proposed_start = 140
    while set(range(proposed_start, proposed_start + 20)) & observed:
        proposed_start += 1
    return {"root": str(root), "event_files_checked": event_files,
            "recorded_reset_seeds": sorted(observed), "preferred_seeds": preferred,
            "preferred_overlap": sorted(set(preferred) & observed),
            "first_unused_contiguous_20_from140": list(range(proposed_start, proposed_start + 20)),
            "scope": "available_native_runs_history_not_unreported_or_deleted_runs",
            "fresh_entry_must_recheck": True}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--prototype", type=Path, default=Path("/home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl"))
    args = cli.parse_args()
    if sys.version_info[:2] != (3, 10) or version("mani_skill") != "3.0.1":
        raise ValueError("Use the existing native Python3.10 aether-cl / ManiSkill3.0.1 environment")
    if args.output.exists():
        raise FileExistsError("Retain the earlier inspection report; choose a new output filename")
    prototype = args.prototype.resolve()
    if not (prototype / "runs").is_dir():
        raise ValueError("Native runs history is missing; cannot verify preferred seed provenance")
    pkg = Path(distribution("mani_skill").locate_file("mani_skill")).resolve()
    task_root = pkg / "envs/tasks"
    if not task_root.is_dir():
        raise ValueError("Installed ManiSkill task sources not found")
    inventory, candidates = [], set()
    for path in sorted(task_root.rglob("*.py")):
        records = task_definitions(path, pkg)
        inventory.extend(records)
        if any(any(word in r["env_id"].lower() for word in ("insert", "peg", "charger", "assembling", "slot")) for r in records):
            candidates.add(path)
    support = [pkg / name for name in ("__init__.py", "utils/registration.py", "envs/sapien_env.py",
               "utils/structs/actor.py", "utils/structs/pose.py", "utils/structs/types.py",
               "utils/scene_builder/table/scene_builder.py", "agents/controllers/pd_ee_pose.py")]
    support += sorted((pkg / "agents/robots/panda").glob("*.py"))
    sources = [source_record(path, pkg) for path in sorted(candidates | {p for p in support if p.is_file()})]
    asset_roots = [pkg / "assets", Path("~/maniskill/data").expanduser(), Path("~/.maniskill/data").expanduser()]
    if os.environ.get("MS_ASSET_DIR"):
        asset_roots.append(Path(os.environ["MS_ASSET_DIR"]).expanduser())
    assets = []
    visited = set()
    for root in asset_roots:
        root = root.resolve()
        if root in visited or not root.is_dir():
            continue
        visited.add(root)
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix in (".urdf", ".srdf") and any(s in str(path).lower() for s in ("panda", "franka")):
                assets.append({"asset_root": str(root), **source_record(path, root)})
    def git(*arguments):
        result = subprocess.run(["git", "-C", str(prototype), *arguments], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    history = inspect_history(prototype / "runs")
    report = {"scope": "M7_static_installed_task_inspection_no_simulator_or_reset", "02_authority_commit": AUTHORITY,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "python": sys.version.split()[0], "conda_environment": os.environ.get("CONDA_DEFAULT_ENV"),
              "packages": {n: version(n) for n in ("mani_skill", "sapien", "numpy", "scipy", "torch", "gymnasium")},
              "native_repo_commit": git("rev-parse", "HEAD"), "native_repo_dirty": bool(git("status", "--porcelain")),
              "installed_package_root": str(pkg), "registered_task_definitions": inventory,
              "candidate_source_paths": [str(p.relative_to(pkg)) for p in sorted(candidates)],
              "sources": sources, "panda_urdf_srdf_assets": assets,
              "native_reset_history": history, "environments_created": 0, "resets_executed": 0,
              "selection_status": "inspect_exact_source_then_choose_task_no_magnitudes_or_scorer_frozen_yet"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False); stream.write("\n")
    print("M7_INSTALLED_TASK_INSPECTION_READY", flush=True)
    print("Candidates:", ", ".join(r["env_id"] for r in inventory if r["source_path"] in report["candidate_source_paths"]), flush=True)
    print("Fresh140_159_overlap:", history["preferred_overlap"], flush=True)
    print("First unused contiguous20:", history["first_unused_contiguous_20_from140"], flush=True)
    print("Report:", args.output.resolve(), flush=True)
    print("SHA-256:", hashlib.sha256(args.output.read_bytes()).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
