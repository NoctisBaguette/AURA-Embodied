"""M9a source-only sensor inspection: no simulator construction or reset."""

import argparse
import ast
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distribution, PackageNotFoundError, version
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import traceback


ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "aura-sim/prototype_aether_cl"
ACCEPTED_HEAD = "e7664349af37001c043ff7891e4c1cdd214df1c2"
ARCHITECTURE_HEAD = "285943968977361f118473cceded55c72a5a5423"
EVIDENCE = ROOT / "docs/research/experiments/evidence"
PROTOCOL = EVIDENCE / "AETHER_CL_M8_Placement_Protocol.json"
PROTOCOL_SHA256 = "3e67b43747b4d52b73b39c64d2b1f159a855f91cde012b8a5ceffbaf6c40a031"
RECEIPT = EVIDENCE / "AETHER_CL_M8_Installed_Physics_Inspection.json"
REQUIRED_CAMERA_SOURCES = ("sensors/camera.py", "sensors/base_sensor.py",
                           "utils/structs/render_camera.py", "envs/sapien_env.py")
CAMERA_SOURCES = (*REQUIRED_CAMERA_SOURCES, "envs/scene.py", "utils/common.py",
    "utils/sapien_utils.py", "utils/structs/pose.py", "utils/structs/articulation.py",
    "utils/structs/link.py", "agents/base_agent.py", "agents/robots/panda/panda.py",
    "agents/controllers/pd_ee_pose.py", "envs/tasks/tabletop/pick_cube.py",
    "utils/scene_builder/table/scene_builder.py", "utils/visualization/misc.py")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
        text=True, capture_output=True, timeout=30).stdout.strip()


def check_frozen_sources(root=ROOT):
    evidence = root / "docs/research/experiments/evidence"
    if sha256(evidence / PROTOCOL.name) != PROTOCOL_SHA256:
        raise ValueError("Frozen M8 protocol changed; cannot trust replacement hashes")
    protocol = json.loads((evidence / PROTOCOL.name).read_text())
    paths = {"aura-sim/prototype_aether_cl/aether_cl/" + name: digest
             for name, digest in protocol["sources_sha256"].items()}
    paths["tools/m8_physics_inspection.py"] = protocol["history_guard_source_sha256"]
    paths.update({"docs/research/experiments/evidence/" + name: digest
                  for name, digest in protocol["receipt_sources_sha256"].items()})
    for name, expected in paths.items():
        if sha256(root / name) != expected:
            raise ValueError("Frozen M8 source/evidence changed: " + name)
    return paths


def candidate_banks(history):
    observed = set(history["recorded_reset_seeds"])
    banks = {}
    for name, seeds in (("calibration", range(180, 200)), ("evaluation", range(200, 240))):
        requested = list(seeds)
        overlap = sorted(observed.intersection(requested))
        banks[name] = {"proposed_seeds": requested, "retained_history_overlap": overlap,
            "unused_in_retained_history": not overlap, "allocation_frozen": False,
            "collision_response": "return_to_Core_no_automatic_replacement"}
    return banks


def storage_budget(width=640, height=480, fps=20, actions=800, episodes=1440):
    pixels = width * height
    rgb_depth_bytes = pixels * (3 + 2 + 3)
    mask_bytes = pixels
    per_set = rgb_depth_bytes + mask_bytes
    return {"status": "design_arithmetic_not_measured_sensor_output_or_throughput",
        "width": width, "height": height, "capture_hz": fps,
        "primary_rgb8_bytes": pixels * 3, "primary_depth16_bytes": pixels * 2,
        "primary_validity_uint8_bytes": mask_bytes, "complementary_rgb8_bytes": pixels * 3,
        "bytes_per_observation_set": per_set, "bytes_per_second": per_set * fps,
        "bytes_per_episode_800_observations": per_set * actions,
        "matrix_bytes_excluding_masks": rgb_depth_bytes * actions * episodes,
        "matrix_bytes_including_masks": per_set * actions * episodes,
        "matrix_requested_episodes_proposed_only": episodes,
        "excludes": ["reset_frames", "calibration_and_development", "metadata", "MP4",
                     "archive_copies", "filesystem_overhead"],
        "compression_ratio": None, "measured_throughput_bytes_s": None}


def copy_source(path, base, output):
    relative = path.relative_to(base)
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = path.read_bytes()
    with target.open("xb") as stream:
        stream.write(raw)
    return {"path": str(relative), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def source_outline(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            result.append({"class": node.name, "doc": ast.get_docstring(node),
                "methods": [{"name": method.name, "arguments": ast.unparse(method.args),
                             "doc": ast.get_docstring(method)}
                            for method in node.body if isinstance(method, ast.FunctionDef)]})
        elif isinstance(node, ast.FunctionDef):
            result.append({"function": node.name, "arguments": ast.unparse(node.args),
                           "doc": ast.get_docstring(node)})
    return result


def inspect_installed(output, report):
    receipt = json.loads(RECEIPT.read_text())
    report["packages"] = {name: version(name) for name in receipt["packages"]}
    report["python"] = sys.version.split()[0]
    if sys.version_info[:2] != (3, 10) or report["packages"] != receipt["packages"]:
        raise ValueError("Use the unchanged Python3.10 aether-cl native environment")
    package = Path(distribution("mani_skill").locate_file("mani_skill")).resolve()
    sapien = Path(distribution("sapien").locate_file("sapien")).resolve()
    expected = {**receipt["inherited_installed_sources_sha256"],
                **receipt["installed_source_sha256"]}
    for name, digest in expected.items():
        if sha256(package / name) != digest:
            raise ValueError("Previously inspected installed ManiSkill source changed: " + name)
    for name, digest in receipt["inherited_asset_sha256"].items():
        if sha256(package / "assets" / name) != digest:
            raise ValueError("Previously inspected Panda asset changed: " + name)
    for binary in receipt["sapien_native_binaries"]:
        if sha256(sapien / binary["path"]) != binary["sha256"]:
            raise ValueError("Previously inspected SAPIEN native binary changed: " + binary["path"])
    report["inherited_installed_sources_sha256"] = expected
    report["inherited_asset_sha256"] = receipt["inherited_asset_sha256"]
    report["inherited_sapien_binaries"] = receipt["sapien_native_binaries"]
    required_missing = [name for name in REQUIRED_CAMERA_SOURCES if not (package / name).is_file()]
    report["required_camera_sources_missing"] = required_missing
    paths = set(CAMERA_SOURCES)
    paths.update(str(p.relative_to(package)) for p in (package / "sensors").rglob("*.py"))
    report["camera_sources"] = [copy_source(package / name, package, output / "installed/mani_skill")
                                 for name in sorted(paths) if (package / name).is_file()]
    report["optional_camera_sources_missing"] = [name for name in CAMERA_SOURCES
        if name not in REQUIRED_CAMERA_SOURCES and not (package / name).is_file()]
    for name in receipt["inherited_asset_sha256"]:
        if name.endswith((".urdf", ".srdf")):
            copy_source(package / "assets" / name, package, output / "installed/mani_skill")
    report["sapien_binding_sources"] = [copy_source(p, sapien, output / "installed/sapien")
                                        for p in sorted(sapien.rglob("*.pyi"))]
    if required_missing:
        raise ValueError("Camera source layout needs engineering review: " + ", ".join(required_missing))
    report["camera_source_outline"] = {name: source_outline(package / name)
                                       for name in REQUIRED_CAMERA_SOURCES}
    report["optional_packages"] = {}
    for name in ("Pillow", "opencv-python", "imageio", "imageio-ffmpeg", "av", "h5py", "zstandard"):
        try:
            report["optional_packages"][name] = version(name)
        except PackageNotFoundError:
            report["optional_packages"][name] = None


def tool_probe(command):
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "command": command}
    try:
        result = subprocess.run([executable, *command[1:]], capture_output=True,
                                text=True, timeout=20)
        return {"available": True, "command": command, "returncode": result.returncode,
                "stdout": result.stdout[:20000], "stderr": result.stderr[:4000]}
    except subprocess.TimeoutExpired:
        return {"available": True, "command": command, "timed_out": True}


def write_bundle(output, archive, report):
    if archive.exists() or any((output / n).exists() for n in ("inspection.json", "file_index.json")):
        raise FileExistsError("Retain existing inspection evidence and archive")
    write_json(output / "inspection.json", report)
    copy_source(Path(__file__), Path(__file__).parent, output / "executed")
    index = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": sha256(p)}
             for p in sorted(output.rglob("*")) if p.is_file()}
    write_json(output / "file_index.json", index)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("xb") as raw:
        with tarfile.open(fileobj=raw, mode="w:gz") as tar:
            tar.add(output, arcname="m9-sensor-inspection")
    print("Report:", output / "inspection.json", flush=True)
    print("Archive:", archive, flush=True)
    print("SHA-256:", sha256(archive), flush=True)


def check_paths(output, archive, root=ROOT):
    if output.is_relative_to(root) or archive.is_relative_to(root):
        raise ValueError("Inspection output/archive must be outside the guarded checkout")
    if archive.is_relative_to(output):
        raise ValueError("Archive cannot be inside its evidence directory")
    if output.exists() or archive.exists():
        raise FileExistsError("Retain previous evidence; use new output/archive paths")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args(argv)
    output, archive = args.output.resolve(), args.archive.resolve()
    check_paths(output, archive)
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "scope": "M9a_source_only_sensor_interface_inspection",
        "status": "starting", "time_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_experiment_head": ACCEPTED_HEAD, "architecture_head": ARCHITECTURE_HEAD,
        "confirmatory": False, "environments_created": 0, "reset_calls": 0,
        "controller_actions_executed": 0, "force_commands_executed": 0,
        "actual_camera_captured": False, "live_service_started": False,
        "fresh_matrix_authorized": False, "fresh_matrix_started": False,
        "native_library_environment": {name: os.environ.get(name) for name in
            ("CONDA_DEFAULT_ENV", "LD_LIBRARY_PATH", "LD_PRELOAD", "CUDA_VISIBLE_DEVICES")}}
    error = None
    try:
        report["native_repo_commit"] = git("rev-parse", "HEAD")
        if report["native_repo_commit"] != args.expected_head or git("status", "--porcelain"):
            raise ValueError("Require the requested clean Git inspection revision")
        git("merge-base", "--is-ancestor", ACCEPTED_HEAD, "HEAD")
        report["frozen_sources_sha256"] = check_frozen_sources()
        copy_source(PROTOCOL, ROOT, output / "accepted")
        copy_source(RECEIPT, ROOT, output / "accepted")
        history_path = ROOT / "tools/m8_physics_inspection.py"
        copy_source(history_path, ROOT, output / "accepted")
        # Loading this preserved helper only defines functions. No native library
        # or environment is imported by its module-level code.
        spec = importlib.util.spec_from_file_location("m9_preserved_history_reader", history_path)
        history_reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(history_reader)
        print("Scanning retained reset history; no simulator construction or reset", flush=True)
        history = history_reader.inspect_history(PROTOTYPE / "runs", lambda s: print(s, flush=True))
        # The inherited reader also reports M8 candidate ranges. They are not
        # M9 allocations and must not be used to auto-select replacements.
        for name in ("preferred_seeds", "preferred_overlap", "first_unused_contiguous20_from160"):
            history.pop(name)
        report["retained_history"] = history
        report["proposed_seed_banks"] = candidate_banks(history)
        print("Reading installed sensor/depth/FK source bytes without importing the simulator", flush=True)
        inspect_installed(output, report)
        report["tooling"] = {"gpu_inventory": tool_probe(["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free", "--format=csv,noheader"]),
            "ffmpeg": tool_probe(["ffmpeg", "-hide_banner", "-encoders"]),
            "ffprobe": tool_probe(["ffprobe", "-version"])}
        disk = shutil.disk_usage(output)
        report["disk"] = {"path": str(output), "total_bytes": disk.total,
                          "used_bytes": disk.used, "free_bytes": disk.free}
        report["proposed_raw_storage_budget"] = storage_budget()
        if git("rev-parse", "HEAD") != args.expected_head or git("status", "--porcelain"):
            raise ValueError("Checkout changed during inspection")
        report["status"] = "source_inspection_complete_await_native_camera_commissioning"
        print("M9_SENSOR_SOURCE_INSPECTION_READY", flush=True)
        for name, bank in report["proposed_seed_banks"].items():
            print(name, "overlap:", bank["retained_history_overlap"], flush=True)
        print("Actual camera/live/rollout: not started; inspect this evidence before the camera adapter", flush=True)
    except BaseException as exc:
        error = exc
        report.update(status="error_retained_no_native_execution",
                      error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        print(report["error"], file=sys.stderr, flush=True)
    finally:
        write_bundle(output, archive, report)
    if error is not None:
        raise SystemExit(1)


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Inspection interrupted; retain partial evidence")
    signal.signal(signal.SIGTERM, interrupted)
    main()
