"""Test-only subprocess fixture; never loads a model or starts simulation."""

import json
from pathlib import Path
import subprocess
import sys
import time


mode, counter_file = sys.argv[1:]
job = json.load(sys.stdin)
counter = Path(counter_file)
previous = int(counter.read_text(encoding="utf-8")) if counter.exists() else 0
counter.write_text(str(previous + 1), encoding="utf-8")

if mode in {"large_crash", "large_invalid_json"}:
    marker = "CRASH" if mode == "large_crash" else "JSON"
    sys.stdout.write(f"{marker}_OUT_BEGIN_" + "x" * 6000 + f"_{marker}_OUT_END\n")
    sys.stderr.write(f"{marker}_ERR_BEGIN_" + "y" * 6000 + f"_{marker}_ERR_END\n")
    sys.stdout.flush()
    sys.stderr.flush()
    raise SystemExit(9 if mode == "large_crash" else 0)

identity = {
    key: job[key]
    for key in (
        "evidence_kind", "stage", "checkpoint_manifest_sha256", "task", "setting",
        "scene_seed", "episode_id", "shard_id",
    )
}

if mode == "typed_then_success" and job["scene_seed"] == job["seed_start"]:
    response = {
        **identity,
        "status": "REJECTED_SETUP",
        "rejection_category": "EXPERT_UNSOLVED",
        "rejection_evidence": {"plan_success": False, "init_scene": True},
    }
elif mode in {"typed_then_success", "success", "large_success", "pending_video", "wrong_evidence_kind", "bool_chunk_index"}:
    response = {
        **identity,
        "status": "COMPLETE",
        "task_success": True,
        "task_predicate": True,
        "actions_started": 25,
        "step_limit": 50,
        "official_step_limit": 50,
        "chunks": 1,
        "wall_seconds": 0.25,
        "log_path": f"logs/{job['episode_id']}.log",
        "video_path": None,
        "video_review_status": "NOT_REVIEWED",
        "requests": [{
            "request_id": job["request_id_prefix"] + "-chunk-0001",
            "chunk_index": 1,
            "noise_seed": job["noise_seed_base"],
        }],
    }
    if mode == "large_success":
        response["stream_payload"] = "OUT_BEGIN_" + "x" * 6000 + "_OUT_END"
        sys.stderr.write("ERR_BEGIN_" + "y" * 6000 + "_ERR_END\n")
    if mode == "pending_video":
        response["video_path"] = "videos/fixture.mp4"
        response["video_review_status"] = "PENDING"
    if mode == "wrong_evidence_kind":
        response["evidence_kind"] = "real_policy" if job["evidence_kind"] == "fixture" else "fixture"
    if mode == "bool_chunk_index":
        response["requests"][0]["chunk_index"] = True
elif mode == "always_reject":
    response = {
        **identity,
        "status": "REJECTED_SETUP",
        "rejection_category": "EXPERT_UNSOLVED",
        "rejection_evidence": {"plan_success": False, "init_scene": True},
    }
elif mode == "fatal":
    response = {**identity, "status": "ERROR", "error_kind": "PLANNER_ERROR", "error": "fixture planner failure"}
elif mode == "mismatched_identity":
    response = {**identity, "status": "ERROR", "task": "wrong_task", "error_kind": "PROTOCOL_ERROR"}
elif mode == "sleep":
    print("TIMEOUT_OUT_BEGIN_" + "x" * 6000 + "_TIMEOUT_OUT_END", flush=True)
    print("TIMEOUT_ERR_BEGIN_" + "y" * 6000 + "_TIMEOUT_ERR_END", file=sys.stderr, flush=True)
    time.sleep(5)
    response = {**identity, "status": "ERROR", "error_kind": "FIXTURE_TIMEOUT"}
elif mode == "spawn_child":
    marker = Path(str(counter) + ".child-marker")
    child_code = "import pathlib,sys,time; time.sleep(1.8); pathlib.Path(sys.argv[1]).write_text('alive')"
    child = subprocess.Popen([sys.executable, "-c", child_code, str(marker)])
    Path(str(counter) + ".childpid").write_text(str(child.pid), encoding="utf-8")
    time.sleep(10)
    response = {**identity, "status": "ERROR", "error_kind": "FIXTURE_TIMEOUT"}
else:
    raise SystemExit("unknown test fixture mode")

print(json.dumps(response, allow_nan=False))
