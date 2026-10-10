"""M9a known-seed camera commissioning; no sensor verifier or fresh evaluation."""

import argparse
from dataclasses import replace
import fcntl
import hashlib
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import traceback

import m9_sensor_inspection as inspection

ROOT, PROTOTYPE = inspection.ROOT, inspection.PROTOTYPE
REVIEW = ROOT / "docs/research/experiments/evidence/AURA_M9a_Sensor_Inspection_Review_v1.json"
REVIEW_SHA256 = "5a5750a14e209977072af06f02848043bf094605aef0e4267bf7cf5790298f7e"
INSPECTION_ARCHIVE_SHA256 = "c3afdec4f968f5c18466e6ec29554424ce82a816b300923e5c0469e72a1760d2"
MODES = ("unrendered", "render_idle", "capture_only", "record_no_view", "record_with_view")
SEED, ACTIONS, PORT = 100, 800, 18709
REPORTING_FAILURE_HEAD = "c05ee86c98ba7dd6a372d27c12dc3d51f1ea9b34"
REPORTING_FAILURE_ARCHIVE_SHA256 = "d4726e7a043622a92a3d6c8f516f231ba70c4c2c5cdf73007d11c64228d85565"
REPORTING_FAILURE_ERROR = "TypeError: Object of type bool_ is not JSON serializable"


def json_default(value):
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_json(path, data):
    # Audit calculations can return NumPy bool_/integer/float/array values.
    # Encode before creating the file, retaining false checks and rejecting NaN.
    encoded = json.dumps(data, indent=2, allow_nan=False, default=json_default) + "\n"
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(encoded)


def read_lines(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream]


def require_healthy_episode(episode):
    # Read the terminal episode schema produced by unchanged M6R, rather than
    # the per-observation reference field named task_success.
    if "task_success_at_end" not in episode:
        raise ValueError("Missing accepted episode field task_success_at_end; retain evidence")
    if episode["task_success_at_end"] is not True:
        raise ValueError("Known zero-force Baseline did not finish healthy; retain for review")


def archive_receipt(path):
    if inspection.sha256(path) != INSPECTION_ARCHIVE_SHA256:
        raise ValueError("Require the independently reviewed native source-inspection archive")
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(set(names)) != len(names) or sum(m.size for m in members) > 100_000_000:
            raise ValueError("Invalid inspection archive membership/size")
        for member in members:
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts or not p.parts or p.parts[0] != "m9-sensor-inspection" or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe inspection archive entry")
        index = json.load(archive.extractfile("m9-sensor-inspection/file_index.json"))
        files = {m.name.removeprefix("m9-sensor-inspection/"): m for m in members if m.isfile()}
        if set(files) != set(index) | {"file_index.json"}:
            raise ValueError("Inspection archive index mismatch")
        for name, record in index.items():
            raw = archive.extractfile(files[name]).read()
            if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                raise ValueError("Inspection archive hash mismatch: " + name)
        return json.load(archive.extractfile("m9-sensor-inspection/inspection.json"))


def preflight(args):
    if inspection.git("rev-parse", "HEAD") != args.expected_head or inspection.git("status", "--porcelain"):
        raise ValueError("Require the exact clean camera-commissioning revision")
    inspection.git("merge-base", "--is-ancestor", "fe3d5a75db919dafa2dd06bb08aa817ccd4a8ada", "HEAD")
    if inspection.sha256(REVIEW) != REVIEW_SHA256:
        raise ValueError("Reviewed sensor receipt changed")
    review = json.loads(REVIEW.read_text())
    record = archive_receipt(args.inspection_archive)
    if record["native_repo_commit"] != review["measurement_commit"] or record["status"] != "source_inspection_complete_await_native_camera_commissioning":
        raise ValueError("Invalid source-inspection identity")
    environment = {name: os.environ.get(name) for name in record["native_library_environment"]}
    if environment != record["native_library_environment"] or sys.version.split()[0] != record["python"]:
        raise ValueError("Require the inspected Python/conda/Vulkan/CUDA startup environment")
    inspection.check_frozen_sources()
    if sys.version_info[:2] != (3, 10) or {name: version(name) for name in review["packages"]} != review["packages"]:
        raise ValueError("Require unchanged Python3.10 aether-cl native packages")
    for name in ("Pillow", "imageio-ffmpeg", "opencv-python"):
        if version(name) != review["optional_packages"][name]:
            raise ValueError("Recording package changed: " + name)
    for name, digest in review["installed_source_sha256"].items():
        _, package, relative = name.split("/", 2)
        path = Path(distribution(package).locate_file(package)) / relative
        if inspection.sha256(path) != digest:
            raise ValueError("Inspected camera/asset/binding source changed: " + name)
    sapien = Path(distribution("sapien").locate_file("sapien"))
    for binary in review["sapien_native_binaries"]:
        if inspection.sha256(sapien / binary["path"]) != binary["sha256"]:
            raise ValueError("Inspected SAPIEN binary changed")
    history = review["history"]
    if SEED not in history["recorded_reset_seeds"]:
        raise ValueError("Development scene was not previously observed")
    witness = history["development_seed100_witness"]
    with (PROTOTYPE / "runs" / witness["path"]).open() as stream:
        native = next(json.loads(line) for line_number, line in enumerate(stream, 1) if line_number == witness["line"])
    if native.get("event") != "reset" or native.get("seed") != SEED:
        raise ValueError("Retained development-scene witness differs")
    import m8_physics_inspection as preserved
    package = Path(distribution("mani_skill").locate_file("mani_skill"))
    constructor_seeds = preserved.constructor_reset_seeds((package / "envs/sapien_env.py").read_text())
    shader_sources = {str(p.relative_to(package)): inspection.sha256(p)
                      for p in sorted((package / "render").rglob("*.py"))}
    if not shader_sources:
        raise ValueError("Installed renderer shader Python source is unavailable")
    import imageio_ffmpeg
    executable = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    result = subprocess.run([str(executable), "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=30)
    if result.returncode or "libx264" not in result.stdout:
        raise ValueError("Existing bundled ffmpeg lacks H264 encoder; no installation attempted")
    if shutil.disk_usage(PROTOTYPE / "runs").free < 12_000_000_000:
        raise ValueError("Require 12GB free for bounded commissioning and archive copies")
    return {"review_sha256": REVIEW_SHA256, "inspection_archive_sha256": INSPECTION_ARCHIVE_SHA256,
        "history_snapshot_sha256": history["reset_index_sha256"], "development_witness": witness,
        "constructor_reset_seeds": constructor_seeds, "fresh_seed_allocation": False,
        "renderer_python_source_sha256": shader_sources,
        "native_library_environment": environment, "python_executable": sys.executable,
        "bundled_ffmpeg": str(executable), "bundled_ffmpeg_sha256": inspection.sha256(executable)}


def require_paths(args):
    runs = (PROTOTYPE / "runs").resolve()
    output, archive = args.output.resolve(), args.archive.resolve()
    if not output.is_relative_to(runs) or output == runs:
        raise ValueError("Commissioning must be retained under the existing native runs history")
    if archive.is_relative_to(ROOT) or archive.is_relative_to(output) or archive == args.inspection_archive.resolve():
        raise ValueError("Use a new archive outside the checkout and inspection evidence")
    if output.exists() or archive.exists():
        raise FileExistsError("Retain previous commissioning; never replace a started slot")


def child(args):
    identity = preflight(args)
    if args.mode not in MODES or args.output.name != args.mode or not args.output.resolve().is_relative_to(PROTOTYPE / "runs"):
        raise ValueError("Unknown development mode or child output")
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(PROTOTYPE))
    from aether_cl.m6r_runtime import M6RConfig, run as accepted_run
    from aether_cl.runtime import build_env, json_value
    from aether_cl.m6_runtime import reset_native, observe_native
    from aether_cl.m6r_audit import check_trial
    from aether_cl.m8_force import ForceTrace
    from aether_cl.m8_matched import DecisionTraceEnvironment, candidate_points, audit_gate
    from aether_cl.m8_force_commission import audit_physics
    from aether_cl.m9_camera import CameraPair, Recorder, LiveView, display_frame, packet_hashes, distribution_summary
    import numpy as np

    config = M6RConfig(seed=SEED, system="baseline", verification=False, render=False,
                      disturbance="none", output=args.output / "native")
    point = next(p for p in candidate_points() if p["point_id"] == "normal")
    rendered = args.mode != "unrendered"
    captured = args.mode in MODES[2:]
    recording = args.mode in MODES[3:]
    camera = recorder = viewer = None
    frame_rows, robot_rows = [], []
    carrier = {"scope": "M9a_known_seed_camera_commissioning", "confirmatory": False,
        "mode": args.mode, "seed": SEED, "system": "baseline", "state": "starting",
        "fresh_evaluation_started": False, "sensor_verifier_started": False,
        "constructor_reset_seeds": identity["constructor_reset_seeds"]}
    write_json(args.output / "camera_manifest.json", {**carrier, **identity,
        "native_renderer_override": "cuda:0" if rendered else "none",
        "executor_config_render": False, "physics_backend": "cpu", "phase_and_controller_sources": "unchanged",
        "camera_capture_schedule": "reset_and_every_control_endpoint_20Hz_simulation",
        "real_time_pacing": "record_with_view_only_minimum50ms_no_claim_of_real_time_feasibility",
        "renderer_device_note": "cuda:0 requested under inherited CUDA_VISIBLE_DEVICES=1; actual backend recorded separately"})

    try:
        with (args.output / "physics.jsonl").open("x", buffering=1) as physics, \
             (args.output / "controller_gate.jsonl").open("x", buffering=1) as gates, \
             (args.output / "frames.jsonl").open("x", buffering=1) as frames, \
             (args.output / "robot_state.jsonl").open("x", buffering=1) as robots:
            def log(stream, value):
                stream.write(json.dumps(json_value(value), allow_nan=False) + "\n")

            def physical_state(env):
                base = env.unwrapped
                return {"object_and_contact_audit": env.trace.state(),
                        "qpos": json_value(base.agent.robot.get_qpos()), "qvel": json_value(base.agent.robot.get_qvel()),
                        "tcp": json_value(base.agent.tcp_pose.raw_pose)}

            def capture(env, step):
                if not captured:
                    return
                before = physical_state(env)
                begin = time.monotonic_ns()
                packet, times = camera.capture()
                if physical_state(env) != before:
                    raise ValueError("Camera capture changed physical state; retain failure")
                hashes = packet_hashes(packet)
                image = display_frame(packet, step, args.mode) if recording else None
                write_begin = time.monotonic_ns()
                if recorder:
                    recorder.put(packet, image, step)
                write_end = time.monotonic_ns()
                if viewer:
                    viewer.publish(image, "waiting_for_start" if step == 0 else "running", step)
                    # Controlled short-lived clients exercise connect/disconnect
                    # and cached frame reads, never a simulator read or action.
                    if step in (200, 400, 600):
                        from urllib.request import urlopen
                        with urlopen(f"http://127.0.0.1:{PORT}/frame.jpg", timeout=5) as response:
                            if response.status != 200 or not response.read().startswith(b"\xff\xd8"):
                                raise ValueError("Cached live frame self-check failed")
                end = time.monotonic_ns()
                if physical_state(env) != before:
                    raise ValueError("Recording/streaming changed physical state")
                row = {"frame_id": step, "action_endpoint": step, "simulation_time_s": step/20,
                    "capture_begin_monotonic_ns": begin, **times, "pipeline_ready_monotonic_ns": end,
                    "capture_ms": (times["pixels_ready_monotonic_ns"]-begin)/1e6,
                    "record_ms": (write_end-write_begin)/1e6, "pipeline_ms": (end-begin)/1e6,
                    "dtype": {key: str(value.dtype) for key, value in packet.items()}, "array_sha256": hashes,
                    "valid_depth_fraction": float(packet["primary_validity"].mean()),
                    "raw_file": f"frames/frame_{step:05d}.npz" if recording else None}
                frame_rows.append(row)
                log(frames, row)
                if viewer and step == 0:
                    print(f"M9_CAMERA_LIVE_READY http://127.0.0.1:{PORT} — click Start; initial camera frame retained", flush=True)
                    if not viewer.start.wait(timeout=3600):
                        raise TimeoutError("Live commissioning start was not requested within one hour")
                elif viewer:
                    time.sleep(max(0., .05-(time.monotonic_ns()-begin)/1e9))

            def create(c):
                native_config = replace(c, render=True, render_device="cuda:0") if rendered else c
                return DecisionTraceEnvironment(build_env(native_config))

            def reset(env, seed):
                nonlocal camera, recorder, viewer
                if seed != SEED:
                    raise ValueError("Fresh/native seed entry is not available in this commissioning")
                observation, info, support = reset_native(env, seed)
                env.initialize(observation, info, json_value(env.unwrapped.agent.robot.pose.raw_pose), "baseline", lambda x: log(gates, x))
                env.trace = ForceTrace(env, point, lambda x: log(physics, x))
                carrier["actual_backend"] = {"render_device": str(env.unwrapped.backend.render_device),
                    "simulation_device": str(env.unwrapped.device), "gpu_sim_enabled": bool(env.unwrapped.gpu_sim_enabled),
                    "sim_freq": env.unwrapped.sim_freq, "control_freq": env.unwrapped.control_freq}
                log(physics, {"event": "force_trace_started", "seed": seed, "point": point,
                    "actual_gravity_world_m_s2": json_value(env.unwrapped.sim_config.scene_config.gravity),
                    "actual_timestep_s": float(env.unwrapped.scene.px.timestep)})
                state = physical_state(env)
                if rendered:
                    camera = CameraPair(env.unwrapped)
                    if physical_state(env) != state:
                        raise ValueError("Camera construction changed physical state")
                    calibration = {**camera.calibration, "declared_task_target_world_m": json_value(observation["extra"]["goal_pos"])}
                    write_json(args.output / "calibration.json", calibration)
                if recording:
                    recorder = Recorder(args.output)
                if args.mode == "record_with_view":
                    viewer = LiveView(args.output)
                log(robots, {"step": 0, **state})
                capture(env, 0)
                return observation, info, support

            def observe(env, observation, info):
                observation, info = observe_native(env, observation, info)
                env.accept_observation(observation, info)
                robot = {"step": env.step_number, **physical_state(env)}
                robot_rows.append(robot)
                log(robots, robot)
                capture(env, env.step_number)
                if env.step_number % 100 == 0:
                    print(f"{args.mode}: action {env.step_number}/{ACTIONS}", flush=True)
                return observation, info

            result = accepted_run(config, env_factory=create, reset_fn=reset, observe_fn=observe)
        if recorder:
            recorder.close()
            recorder = None
        carrier.update(state=result["state"], run_relative=str(Path(result["run_directory"]).relative_to(args.output)),
                       episode=result["episodes"][0], native_config=json_value(config.__dict__))
        replay, physical, gate = check_trial(Path(result["run_directory"]), config), audit_physics(args.output, carrier, point), audit_gate(args.output, carrier)
        for name, audit in (("accepted_runner_replay", replay), ("physics_audit", physical), ("controller_gate_audit", gate)):
            write_json(args.output / (name + ".json"), audit)
        if not all(a["passed"] for a in (replay, physical, gate)) or physical["force_calls"] or len(robot_rows) != ACTIONS:
            raise ValueError("Frozen runner/physics/gate audit failed; retain every outcome")
        require_healthy_episode(carrier["episode"])
        if captured and [r["frame_id"] for r in frame_rows] != list(range(ACTIONS+1)):
            raise ValueError("Missing/duplicate camera frame; no frame replacement")
        if recording:
            from aether_cl.m9_camera import ARRAY_KEYS, validate_packet
            raw_total, stored_total = 0, 0
            for row in frame_rows:
                target = args.output / row["raw_file"]
                with np.load(target, allow_pickle=False) as saved:
                    packet = {key: saved[key] for key in saved.files}
                validate_packet(packet)
                if packet_hashes(packet) != row["array_sha256"]:
                    raise ValueError("Retained raw camera arrays differ from the live packet")
                if {key: str(packet[key].dtype) for key in ARRAY_KEYS} != row["dtype"]:
                    raise ValueError("Retained raw camera dtypes changed")
                raw_total += sum(value.nbytes for value in packet.values())
                stored_total += target.stat().st_size
            carrier["raw_recording"] = {"verified_frames": len(frame_rows), "raw_array_bytes": raw_total,
                                        "stored_npz_bytes": stored_total, "compression_ratio": raw_total/stored_total}
            import cv2
            video = cv2.VideoCapture(str(args.output / "camera.mp4"))
            count, shape = 0, None
            while True:
                ok, image = video.read()
                if not ok:
                    break
                count, shape = count+1, list(image.shape)
            fps = video.get(cv2.CAP_PROP_FPS)
            video.release()
            if count != ACTIONS+1 or shape != [528, 1280, 3] or abs(fps-20) > .01:
                raise ValueError("Recorded camera MP4 failed native decoding/count/geometry/fps check")
            carrier["video"] = {"decoded_frames": count, "shape": shape, "playback_fps": fps}
        carrier["timing"] = {key: distribution_summary([r[key] for r in frame_rows]) for key in ("capture_ms", "record_ms", "pipeline_ms")}
        if frame_rows:
            periods = np.diff([r["capture_begin_monotonic_ns"] for r in frame_rows])/1e6
            # The manually held initial frame is explicitly excluded only from
            # cadence statistics, never from outcomes/raw files/frame counts.
            carrier["timing"]["wall_capture_period_ms_excluding_initial_start_hold"] = distribution_summary(periods[1:] if viewer else periods)
        carrier.update(state="finished_valid_development_camera_evidence", camera_frames=len(frame_rows),
                       external_physics_samples=physical["external_physics_samples"], force_calls=physical["force_calls"])
        if viewer:
            viewer.complete("finished")
            (args.output / "latest.jpg").write_bytes(viewer.jpeg)
            carrier["http_requests"] = dict(viewer.requests)
    except BaseException as exc:
        carrier.update(state="error_retained", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        if viewer:
            viewer.complete("error")
        raise
    finally:
        try:
            if recorder:
                recorder.close()
        finally:
            if viewer:
                viewer.close()
            write_json(args.output / "camera_result.json", carrier)
    return carrier


def compare_modes(output):
    from aether_cl.acceptance import load_trial
    from aether_cl.m6r_audit import PHYSICAL_FIELDS
    cases = {}
    for mode in MODES:
        directory = output / mode
        carrier = json.loads((directory / "camera_result.json").read_text())
        _, _, events = load_trial(directory / carrier["run_relative"])
        cases[mode] = {"reset": [e for e in events if e["event"] == "reset"],
            "steps": [{k: e[k] for k in (*PHYSICAL_FIELDS, "verification", "recovery")} for e in events if e["event"] == "step"],
            "physics": [e for e in read_lines(directory / "physics.jsonl") if e["event"] == "physics_action"],
            "robot": read_lines(directory / "robot_state.jsonl")}
    results = {}
    for mode in MODES[1:]:
        left, right = cases[MODES[0]], cases[mode]
        checks = {"exact_reset_observation_info": [(r["observation"], r["info"]) for r in left["reset"]] == [(r["observation"], r["info"]) for r in right["reset"]],
            "800_actions": len(left["steps"]) == len(right["steps"]) == ACTIONS,
            "4000_physics_samples_per_case": len(left["physics"]) == len(right["physics"]) == ACTIONS
                and all(len(e["substeps"]) == 5 for case in (left, right) for e in case["physics"]),
            "exact_action_decision_observation_score_verdict_recovery_path": left["steps"] == right["steps"],
            "exact_all_100Hz_physics_samples_and_contacts": left["physics"] == right["physics"],
            "exact_robot_qpos_qvel_tcp_and_reset_state": left["robot"] == right["robot"]}
        results[mode] = {"passed": all(checks.values()), "checks": checks}
    return results


def recover_reporting_failure(args, report):
    """Re-audit exactly the retained first slot; never reset or replay motion."""
    source = args.recover_reporting_archive.resolve()
    if inspection.sha256(source) != REPORTING_FAILURE_ARCHIVE_SHA256:
        raise ValueError("Not the pinned first-slot bool_ reporting failure; retain evidence")
    with tarfile.open(source) as archive:
        members = archive.getmembers()
        if len({m.name for m in members}) != len(members) or sum(m.size for m in members) > 250_000_000:
            raise ValueError("Invalid reporting-failure archive membership/size")
        files = {}
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or not path.parts
                    or path.parts[0] != "m9-camera-commissioning"
                    or not (member.isfile() or member.isdir())):
                raise ValueError("Unsafe reporting-failure archive entry")
            if member.isfile():
                files[str(path.relative_to("m9-camera-commissioning"))] = member
        index = json.load(archive.extractfile(files["file_index.json"]))
        if set(files) != set(index) | {"file_index.json"}:
            raise ValueError("Reporting-failure archive index mismatch")
        for name, record in index.items():
            raw = archive.extractfile(files[name]).read()
            if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                raise ValueError("Reporting-failure archive hash mismatch: " + name)
        def read(name):
            return json.load(archive.extractfile(files[name]))
        previous = read("commissioning.json")
        trials = previous.get("trials", [])
        carrier = read("unrendered/camera_result.json")
        manifest = read("unrendered/camera_manifest.json")
        if (previous.get("native_head") != REPORTING_FAILURE_HEAD
                or previous.get("state") != "error_retained_no_replacement"
                or previous.get("fresh_matrix_started") is not False
                or previous.get("sensor_verifier_implemented") is not False
                or len(trials) != 1 or trials[0].get("mode") != "unrendered"
                or trials[0].get("returncode") != 1
                or carrier.get("state") != "error_retained"
                or carrier.get("error") != REPORTING_FAILURE_ERROR
                or any(name.startswith(mode + "/") for mode in MODES[1:] for name in files)):
            raise ValueError("Not the guarded completed-first-slot reporting failure")
        if previous.get("preflight") != report["preflight"] or any(
                manifest.get(key) != value for key, value in report["preflight"].items()):
            raise ValueError("Native environment/source/encoder identity differs from retained first slot")
        review = json.loads(REVIEW.read_text())
        for name, digest in review["frozen_sources_sha256"].items():
            if index.get("source_snapshot/" + name, {}).get("sha256") != digest:
                raise ValueError("Retained accepted source differs: " + name)
        shutil.copyfile(source, args.output / "preserved_reporting_failure_v1.tar.gz")
        for name, member in files.items():
            if name.startswith("unrendered/"):
                target = args.output / name
                if name == "unrendered/camera_result.json":
                    target = target.with_name("camera_result_before_reporting_repair.json")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as incoming, target.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
    report["reporting_recovery"] = {"state": "revalidating_retained_first_slot",
        "source_archive_sha256": REPORTING_FAILURE_ARCHIVE_SHA256,
        "original_native_head": REPORTING_FAILURE_HEAD, "native_motion_rerun": False}
    item = {"mode": "unrendered", "state": "revalidating_retained", "retained": True,
            "native_motion_rerun": False, "original_returncode": 1}
    report["trials"].append(item)
    sys.path.insert(0, str(PROTOTYPE))
    from aether_cl.m6r_runtime import M6RConfig
    from aether_cl.acceptance import load_trial
    from aether_cl.m6r_audit import check_trial
    from aether_cl.m8_matched import candidate_points, audit_gate
    from aether_cl.m8_force_commission import audit_physics
    directory = args.output / "unrendered"
    relative = Path(carrier["run_relative"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid retained native run path")
    native_manifest, native_result, events = load_trial(directory / relative)
    config = M6RConfig(**{**carrier["native_config"], "output": Path(carrier["native_config"]["output"])})
    config.validate()
    if (config.seed != SEED or config.system != "baseline" or config.verification or config.render
            or config.disturbance != "none" or config.max_steps != ACTIONS
            or native_manifest["software"]["git_commit"] != REPORTING_FAILURE_HEAD
            or native_manifest["software"]["git_dirty"] is not False
            or native_result.get("state") != "finished" or native_result.get("episodes") != [carrier["episode"]]
            or [e["step"] for e in events if e["event"] == "step"] != list(range(1, ACTIONS+1))
            or [r["step"] for r in read_lines(directory / "robot_state.jsonl")] != list(range(ACTIONS+1))
            or read_lines(directory / "frames.jsonl")):
        raise ValueError("Retained first slot is not the complete unrendered Baseline")
    point = next(p for p in candidate_points() if p["point_id"] == "normal")
    replay, physical, gate = check_trial(directory / relative, config), audit_physics(directory, carrier, point), audit_gate(directory, carrier)
    for name, audit in (("accepted_runner_replay", replay), ("physics_audit", physical), ("controller_gate_audit", gate)):
        write_json(directory / (name + "_revalidated.json"), audit)
    if (not all(a["passed"] for a in (replay, physical, gate)) or physical["force_calls"]
            or physical["external_physics_samples"] != ACTIONS * 5):
        raise ValueError("Retained first-slot re-audit failed; no rerun or replacement")
    require_healthy_episode(carrier["episode"])
    # The original error carrier and failed audit file are retained unchanged.
    repaired = {k: value for k, value in carrier.items() if k not in ("error", "traceback")}
    repaired.update(state="finished_valid_development_camera_evidence", camera_frames=0,
        external_physics_samples=physical["external_physics_samples"], force_calls=0,
        timing={key: {"count": 0} for key in ("capture_ms", "record_ms", "pipeline_ms")},
        reporting_repair={"original_error": carrier["error"], "native_motion_rerun": False,
                          "original_native_head": REPORTING_FAILURE_HEAD, "reporting_head": args.expected_head})
    write_json(directory / "camera_result.json", repaired)
    item.update(state="finished", result=repaired, reporting_revalidated=True)
    report["reporting_recovery"]["state"] = "retained_first_slot_revalidated"
    print("M9_UNRENDERED_REPORTING_REVALIDATED — 800 retained actions; no native rerun", flush=True)


def bundle(args, report):
    write_json(args.output / "commissioning.json", report)
    snapshot = args.output / "source_snapshot"
    missing = []
    try:
        review_sources = list(json.loads(REVIEW.read_text())["frozen_sources_sha256"])
    except (OSError, ValueError, KeyError):
        review_sources = []
        missing.append(str(REVIEW.relative_to(ROOT)))
    files = review_sources + [
        str(REVIEW.relative_to(ROOT)), "tools/m9_camera_commission.py", "tools/m9_sensor_inspection.py",
        "aura-sim/prototype_aether_cl/aether_cl/m9_camera.py",
        str(inspection.PROTOCOL.relative_to(ROOT))]
    for name in files:
        if not (ROOT / name).is_file():
            missing.append(name)
            continue
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    if args.inspection_archive.is_file():
        shutil.copyfile(args.inspection_archive, args.output / "input_source_inspection.tar.gz")
    if "preflight" in report:
        package = Path(distribution("mani_skill").locate_file("mani_skill"))
        for name, digest in report["preflight"]["renderer_python_source_sha256"].items():
            source = package / name
            if not source.is_file():
                missing.append("installed/mani_skill/"+name)
                continue
            target = snapshot / "installed/mani_skill" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    write_json(args.output / "source_snapshot_missing.json", sorted(set(missing)))
    write_json(args.output / "file_index.json", {str(p.relative_to(args.output)): {"bytes": p.stat().st_size,
        "sha256": inspection.sha256(p)} for p in sorted(args.output.rglob("*")) if p.is_file()})
    with args.archive.open("xb") as raw:
        with tarfile.open(fileobj=raw, mode="w:gz", compresslevel=1) as archive:
            archive.add(args.output, arcname="m9-camera-commissioning")
    print("Archive:", args.archive, flush=True)
    print("SHA-256:", inspection.sha256(args.archive), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--inspection-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--recover-reporting-archive", type=Path,
                        help="Only the pinned c05ee86 completed-first-slot bool_ reporting failure")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--replay-service-seconds", type=int, default=3600)
    args = parser.parse_args(argv)
    args.output, args.archive = args.output.resolve(), args.archive.resolve()
    if args.child:
        child(args)
        return
    require_paths(args)
    if not 0 <= args.replay_service_seconds <= 3600:
        raise ValueError("Replay service lifetime must be between zero and one hour")
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "M9a_development_camera_commissioning_only", "confirmatory": False,
        "state": "starting", "seed": SEED, "systems": ["baseline"], "fresh_matrix_started": False,
        "sensor_verifier_implemented": False, "trials": [], "native_head": args.expected_head}
    process = None
    failed = None
    try:
        report["preflight"] = preflight(args)
        with (args.archive.parent / "m9-camera-commissioning.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.recover_reporting_archive:
                recover_reporting_failure(args, report)
            for mode in (MODES[1:] if args.recover_reporting_archive else MODES):
                item = {"mode": mode, "state": "started", "retained": True}
                report["trials"].append(item)
                print("Starting", mode, "development seed100 / 800 actions / zero force", flush=True)
                command = [sys.executable, "-u", str(Path(__file__).resolve()), "--child", "--mode", mode,
                    "--expected-head", args.expected_head, "--inspection-archive", str(args.inspection_archive),
                    "--output", str(args.output / mode), "--archive", str(args.archive)]
                with (args.output / (mode + ".log")).open("x", buffering=1) as child_log:
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in process.stdout:
                        child_log.write(line)
                        print(line, end="", flush=True)
                    process.wait()
                item["returncode"] = process.returncode
                result_path = args.output / mode / "camera_result.json"
                if result_path.is_file():
                    item["result"] = json.loads(result_path.read_text())
                if process.returncode or item.get("result", {}).get("state") != "finished_valid_development_camera_evidence":
                    raise ValueError("Native camera child failed; no rerun or replacement: " + mode)
                manifest = json.loads((args.output / mode / "camera_manifest.json").read_text())
                if manifest["renderer_python_source_sha256"] != report["preflight"]["renderer_python_source_sha256"]:
                    raise ValueError("Renderer shader Python source changed between isolated children")
                item["state"] = "finished"
            sys.path.insert(0, str(PROTOTYPE))
            report["neutrality"] = compare_modes(args.output)
            if not all(r["passed"] for r in report["neutrality"].values()):
                raise ValueError("Exact render/capture/record/view neutrality failed; return retained evidence")
            if preflight(args) != report["preflight"]:
                raise ValueError("Inspected packages/source/shader/encoder identity changed during commissioning")
            if inspection.git("rev-parse", "HEAD") != args.expected_head or inspection.git("status", "--porcelain"):
                raise ValueError("Checkout changed during commissioning")
            report.update(state="camera_io_neutrality_complete_await_independent_review",
                interpretation="Camera_I/O_only_not_observability_estimator_accuracy_latency_acceptance_or_M9_success",
                view_port=PORT, retained_episodes=5, retained_actions=4000)
            print("M9_CAMERA_IO_NEUTRALITY_READY", flush=True)
    except BaseException as exc:
        failed = exc
        report.update(state="error_retained_no_replacement", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        print(report["error"], file=sys.stderr, flush=True)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        bundle(args, report)
    if failed:
        raise SystemExit(1)
    if args.replay_service_seconds:
        sys.path.insert(0, str(PROTOTYPE))
        from aether_cl.m9_camera import LiveView
        viewer = LiveView(args.output / "record_with_view")
        viewer.jpeg = (args.output / "record_with_view/latest.jpg").read_bytes()
        viewer.status = {"state": "finished", "frame_available": True, "step": ACTIONS,
                         "note": "Live episode complete; recorded camera MP4 available", "port": PORT}
        print(f"Evidence archived. Camera replay service: http://127.0.0.1:{PORT} for {args.replay_service_seconds}s", flush=True)
        try:
            # One-second waits allow prompt signal handling; no simulation runs.
            deadline = time.monotonic()+args.replay_service_seconds
            while time.monotonic() < deadline:
                time.sleep(1)
        finally:
            viewer.close()


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Interrupted; retain partial native camera evidence")
    signal.signal(signal.SIGTERM, interrupted)
    main()
