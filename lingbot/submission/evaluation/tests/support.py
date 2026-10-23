import json
import sys
from pathlib import Path

EVALUATION = Path(__file__).resolve().parents[1]
ROOT = EVALUATION.parents[1]
sys.path.insert(0, str(EVALUATION))

TEMPLATE_PATH = ROOT / "official" / "results-template.json"
CHECKPOINT_SHA = "a" * 64


def template():
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def episode(task="lift_pot", setting="clean", seed=100000, *,
            episode_id="episode-a", stage="baseline", success=True,
            manifest_sha=CHECKPOINT_SHA):
    from aggregate_results import request_id_for
    return {
        "evidence_kind": "real_policy",
        "status": "COMPLETE",
        "stage": stage,
        "checkpoint_manifest_sha256": manifest_sha,
        "task": task,
        "setting": setting,
        "scene_seed": seed,
        "episode_id": episode_id,
        "shard_id": f"{stage}-{setting}-{task}",
        "task_success": success,
        "task_predicate": success,
        "actions_started": 50 if not success else 25,
        "step_limit": 50,
        "official_step_limit": 50,
        "chunks": 1,
        "wall_seconds": 12.5,
        "log_path": f"logs/{episode_id}.log",
        "video_path": f"videos/{episode_id}.mp4",
        "requests": [{
            "request_id": request_id_for(episode_id, 1),
            "chunk_index": 1,
            "noise_seed": seed,
        }],
    }
