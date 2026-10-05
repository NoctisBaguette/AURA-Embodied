"""Bounded simulator runs with distinct smoke and fixed-controller modes."""

from __future__ import annotations

import argparse
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import threading
import time
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from typing import Callable
from uuid import uuid4


@dataclass(frozen=True)
class RunConfig:
    env_id: str = "PickCube-v1"
    seed: int = 0
    episodes: int = 1
    max_steps: int = 50
    render: bool = True
    render_device: str = "cuda:1"
    fps: float = 5.0
    output: Path = Path("runs")
    controller: str = "random"

    @property
    def control_mode(self):
        return "pd_ee_pose" if self.controller == "fixed_pick_cube" else "pd_joint_delta_pos"

    @property
    def purpose(self):
        return "fixed_pick_cube_baseline_candidate" if self.controller == "fixed_pick_cube" else "random_action_environment_smoke"

    def validate(self):
        if self.episodes < 1 or self.max_steps < 1:
            raise ValueError("episodes and max_steps must be positive")
        if not 0 < self.fps <= 60:
            raise ValueError("fps must be greater than zero and at most 60")
        if self.seed < 0 or self.seed + self.episodes > 2**32:
            raise ValueError("episode seeds must fit in unsigned 32-bit integers")
        if self.controller not in ("random", "fixed_pick_cube"):
            raise ValueError("Unknown controller")
        if self.controller == "fixed_pick_cube":
            from .policies import PickCubeSettings
            if self.env_id != "PickCube-v1":
                raise ValueError("fixed_pick_cube supports only PickCube-v1 with the Panda robot")
            if self.max_steps < PickCubeSettings().scheduled_steps:
                raise ValueError("fixed_pick_cube needs at least 320 max_steps for its complete schedule")


def json_value(value):
    """Convert simulator tensors and arrays before they can be mutated by step()."""
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    if hasattr(value, "tolist"):
        return json_value(value.tolist())
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def scalar(value):
    value = json_value(value)
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, list):
        raise ValueError("Expected a scalar for a single environment")
    return value


def software_manifest():
    packages = {}
    for name in ("torch", "numpy", "mani_skill", "sapien", "gymnasium", "Pillow"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True,
            timeout=5,
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL,
            text=True, timeout=5,
        ).strip())
    except (OSError, subprocess.SubprocessError):
        commit, dirty = None, None
    try:
        gpu_inventory = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,driver_version",
             "--format=csv,noheader"], stderr=subprocess.DEVNULL,
            text=True, timeout=5,
        ).strip().splitlines()
    except (OSError, subprocess.SubprocessError):
        gpu_inventory = None
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": packages, "git_commit": commit, "git_dirty": dirty,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "native_library_environment": {key: os.environ.get(key)
                                       for key in ("LD_LIBRARY_PATH", "LD_PRELOAD")},
        "gpu_inventory": gpu_inventory,
    }


def build_env(config):
    import gymnasium as gym
    import mani_skill.envs  # Registers tasks with Gymnasium.

    return gym.make(
        config.env_id, num_envs=1, obs_mode="state_dict", robot_uids="panda",
        control_mode=config.control_mode, reward_mode="none",
        sim_backend="cpu",
        render_backend=config.render_device if config.render else "none",
        render_mode="rgb_array" if config.render else None,
        human_render_camera_configs={"width": 480, "height": 360,
                                     "shader_pack": "default"},
        max_episode_steps=config.max_steps,
    )


def encode_frame(frame):
    import numpy as np
    from PIL import Image

    if frame is None:
        raise RuntimeError("The renderer returned no frame")
    if hasattr(frame, "detach"):
        frame = frame.detach().cpu().numpy()
    frame = np.asarray(frame)
    if frame.ndim == 4 and frame.shape[0] == 1:
        frame = frame[0]
    if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise RuntimeError(f"Unexpected RGB frame: {frame.shape}, {frame.dtype}")
    if frame.size == 0 or int(frame.max()) == int(frame.min()):
        raise RuntimeError("The rendered frame is empty or constant")
    buffer = io.BytesIO()
    Image.fromarray(frame).save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def run(config: RunConfig, publish: Callable | None = None,
        stop: threading.Event | None = None, env_factory=build_env):
    config.validate()
    stop = stop if stop is not None else threading.Event()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = config.output / f"{stamp}-{uuid4().hex[:8]}"
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": 2, "purpose": config.purpose,
        "config": json_value(asdict(config)), "software": software_manifest(),
        "physics_backend": "cpu", "observation_mode": "state_dict",
        "control_mode": config.control_mode,
        "policy": "fixed_pick_cube" if config.controller == "fixed_pick_cube" else "seeded_random_actions",
        "verification": False, "recovery": False,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    env = None
    result = {"state": "starting", "run_directory": str(directory),
              "purpose": manifest["purpose"], "controller": config.controller,
              "episodes": []}
    with (directory / "events.jsonl").open("w", encoding="utf-8", buffering=1) as log:
        def event(kind, **fields):
            record = {"event": kind, "time_utc": datetime.now(timezone.utc).isoformat(),
                      **json_value(fields)}
            log.write(json.dumps(record, allow_nan=False) + "\n")

        def update(**fields):
            result.update(fields)
            if publish:
                publish(json_value(result), None)

        def capture():
            if config.render:
                jpeg = encode_frame(env.render())
                (directory / "latest.jpg").write_bytes(jpeg)
                if publish:
                    publish(json_value(result), jpeg)

        try:
            event("run_started", manifest=manifest)
            update(state="initializing")
            env = env_factory(config)
            backend = getattr(env.unwrapped, "backend", None)
            event("environment_created", render_device=str(
                getattr(backend, "render_device", "unknown")))
            for episode in range(config.episodes):
                if stop.is_set():
                    break
                seed = config.seed + episode
                observation, info = env.reset(seed=seed)
                env.action_space.seed(seed)
                policy = None
                diagnostics = {}
                decision = {"phase": "random", "schedule_complete": False}
                if config.controller == "fixed_pick_cube":
                    from .policies import FixedPickCube, task_diagnostics
                    policy = FixedPickCube(observation, env.unwrapped.agent.robot.pose.raw_pose)
                    if env.action_space.shape != (1, 7):
                        raise RuntimeError(f"Unexpected Panda pd_ee_pose action shape: {env.action_space.shape}")
                    diagnostics = task_diagnostics(observation, info)
                    manifest["policy_details"] = policy.manifest()
                    (directory / "manifest.json").write_text(
                        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8",
                    )
                    event("controller_reset", episode=episode, policy=policy.manifest(),
                          initial_cube_position_world_m=policy.cube.tolist(),
                          initial_goal_position_world_m=policy.goal.tolist())
                event("reset", episode=episode, seed=seed,
                      observation=observation, info=info)
                update(state="running", episode=episode, step=0,
                       phase="approach" if policy else "random",
                       success=bool(scalar(info.get("success", False))), **diagnostics)
                capture()
                success_ever = result["success"]
                terminated = truncated = False
                steps = 0
                start = time.monotonic()
                for step in range(1, config.max_steps + 1):
                    if stop.is_set():
                        break
                    tick = time.monotonic()
                    if policy:
                        action, decision = policy.action(observation, step - 1)
                    else:
                        action = env.action_space.sample()
                    if policy and not env.action_space.contains(action):
                        raise RuntimeError("Controller produced an invalid action")
                    logged_action = json_value(action)
                    observation, reward, term, trunc, info = env.step(action)
                    terminated, truncated = bool(scalar(term)), bool(scalar(trunc))
                    success = bool(scalar(info.get("success", False)))
                    success_ever = success_ever or success
                    steps = step
                    if policy:
                        diagnostics = task_diagnostics(observation, info)
                    event("step", episode=episode, step=step, action=logged_action,
                          observation=observation, reward=reward,
                          terminated=terminated, truncated=truncated, info=info,
                          controller_decision=decision, evaluator=diagnostics)
                    update(step=step, success=success, phase=decision["phase"], **diagnostics)
                    capture()
                    if terminated or truncated:
                        break
                    if publish:
                        stop.wait(max(0, 1 / config.fps - (time.monotonic() - tick)))
                summary = {
                    "episode": episode, "seed": seed, "steps": steps,
                    "success_at_end": result["success"], "success_ever": success_ever,
                    "terminated": terminated, "truncated": truncated,
                    "stopped": stop.is_set(), "seconds": time.monotonic() - start,
                }
                if policy:
                    summary.update(final_phase=decision["phase"],
                                   schedule_complete=decision["schedule_complete"],
                                   final_cube_goal_distance_m=diagnostics["cube_goal_distance_m"],
                                   final_is_grasped=bool(scalar(info.get("is_grasped", False))),
                                   final_is_obj_placed=bool(scalar(info.get("is_obj_placed", False))),
                                   final_is_robot_static=bool(scalar(info.get("is_robot_static", False))))
                result["episodes"].append(summary)
                event("episode_finished", **summary)
            update(state="stopped" if stop.is_set() else "finished")
            if config.controller == "fixed_pick_cube":
                complete = result["state"] == "finished" and len(result["episodes"]) == config.episodes
                evaluation = {
                    "requested_episodes": config.episodes,
                    "recorded_episodes": len(result["episodes"]),
                    "completed_episodes": sum(not e["stopped"] for e in result["episodes"]),
                    "complete": complete,
                    "success_rate_at_end": (sum(e["success_at_end"] for e in result["episodes"]) / config.episodes) if complete else None,
                    "success_rate_ever": (sum(e["success_ever"] for e in result["episodes"]) / config.episodes) if complete else None,
                    "verification": False, "recovery": False,
                    "input_source": "privileged_simulator_state",
                }
                update(evaluation=evaluation)
            event("run_finished", result=result)
        except BaseException as error:
            update(state="error", error=f"{type(error).__name__}: {error}")
            event("run_failed", error=result["error"])
            raise
        finally:
            try:
                if env is not None:
                    env.close()
            except BaseException as error:
                update(state="error", error=f"Environment cleanup failed: {type(error).__name__}: {error}")
                event("cleanup_failed", error=result["error"])
                raise
            finally:
                (directory / "result.json").write_text(
                    json.dumps(result, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8",
                )
    return result


def parser(description):
    args = argparse.ArgumentParser(description=description)
    args.add_argument("--env-id", default="PickCube-v1")
    args.add_argument("--seed", type=int, default=0)
    args.add_argument("--episodes", type=int, default=1)
    args.add_argument("--max-steps", type=int, default=50)
    args.add_argument("--render-device", default="cuda:1")
    args.add_argument("--no-render", action="store_true")
    args.add_argument("--fps", type=float, default=5)
    args.add_argument("--output", type=Path, default=Path("runs"))
    args.add_argument("--controller", choices=("random", "fixed_pick_cube"), default="random")
    return args


def config_from_args(args):
    return RunConfig(env_id=args.env_id, seed=args.seed, episodes=args.episodes,
                     max_steps=args.max_steps, render=not args.no_render,
                     render_device=args.render_device, fps=args.fps,
                     output=Path(args.output), controller=args.controller)
