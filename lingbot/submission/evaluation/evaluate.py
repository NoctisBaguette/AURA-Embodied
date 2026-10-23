"""CPU-only schedule and fail-closed serial backend runner.

The runner speaks a JSON subprocess protocol.  It never imports the simulator,
policy framework, Torch, or NumPy; a deployment-specific native adapter must be
provided as the subprocess command.
"""

from __future__ import annotations

import hashlib
import importlib.util
import argparse
import json
import math
import os
import re
import signal
import subprocess
import uuid
import datetime as dt
import time
from pathlib import Path
from typing import Any, Sequence

from ledger import EvaluationLedger


SETTINGS = ("clean", "randomized")
SEEN_BY_SETTING = {"clean": "seen", "randomized": "unseen"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _sha256(value: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError("manifest SHA must be 64 lowercase hexadecimal characters")
    return value


def load_tasks(path: str | Path) -> list[str]:
    """Read the official results template and return its validated task order."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("results"), dict):
        raise ValueError("tasks file must use the official results-template schema")
    results = value["results"]
    if set(results) != set(SETTINGS):
        raise ValueError("official task settings must be exactly clean and randomized")
    clean, randomized = results["clean"], results["randomized"]
    if not isinstance(clean, dict) or not isinstance(randomized, dict):
        raise ValueError("official results for each setting must be an object")
    tasks = list(clean)
    if len(tasks) != 50 or len(set(tasks)) != 50 or set(tasks) != set(randomized):
        raise ValueError("official task grid must contain the same 50 unique tasks per setting")
    if any(not isinstance(task, str) or not task for task in tasks):
        raise ValueError("task names must be non-empty strings")
    return tasks


def build_plan(*, tasks: list[str], setting: str, episodes: int,
               max_candidates: int, seed_start: int,
               manifest_sha256: str, stage: str,
               output_dir: str | Path,
               selected_tasks: list[str] | None = None) -> dict:
    """Build deterministic candidate, episode and per-chunk request namespaces."""
    episodes = _positive_int(episodes, "episodes")
    max_candidates = _positive_int(max_candidates, "candidate budget")
    if max_candidates < episodes:
        raise ValueError("candidate budget must be >= target episodes")
    if isinstance(seed_start, bool) or not isinstance(seed_start, int) or seed_start < 0:
        raise ValueError("seed_start must be a non-negative integer")
    if seed_start + max_candidates > 2**31:
        raise ValueError("seed range exceeds the policy request noise-seed limit")
    manifest_sha256 = _sha256(manifest_sha256)
    if stage not in {"baseline", "candidate"}:
        raise ValueError("stage must be baseline or candidate")
    if setting not in {"clean", "randomized", "all"}:
        raise ValueError("setting must be clean, randomized, or all")
    if len(tasks) != 50 or len(set(tasks)) != 50 or any(not isinstance(t, str) or not t for t in tasks):
        raise ValueError("tasks must be the 50 unique official task names")
    if selected_tasks is None:
        selected_tasks = list(tasks)
    if (not selected_tasks or len(set(selected_tasks)) != len(selected_tasks)
            or any(task not in tasks for task in selected_tasks)):
        raise ValueError("selected task must be a unique official task name")
    selected = set(selected_tasks)
    tasks = [task for task in tasks if task in selected]

    settings = SETTINGS if setting == "all" else (setting,)
    identity = {
        "stage": stage,
        "checkpoint_manifest_sha256": manifest_sha256,
        "tasks": list(tasks),
        "settings": list(settings),
        "target_episodes": episodes,
        "candidate_budget": max_candidates,
        "seed_start": seed_start,
        "seed_step": 1,
        "seed_policy": "sequential_per_cell_same_panel_across_checkpoints",
        "noise_seed_policy": "fixed_777_plus_chunk_index_minus_one",
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    run_id = hashlib.sha256(encoded).hexdigest()[:24]
    output_root = Path(output_dir).resolve()
    cells = []
    for current_setting in settings:
        for task in tasks:
            cell_identity = f"{run_id}|{current_setting}|{task}"
            shard_id = f"{stage}-{current_setting}-{task}"
            candidates = []
            for offset in range(max_candidates):
                seed = seed_start + offset
                episode_hex = uuid.uuid5(uuid.NAMESPACE_URL, f"{cell_identity}|{seed}").hex
                episode_id = f"ep-{episode_hex}"
                candidates.append({
                    "scene_seed": seed,
                    "episode_id": episode_id,
                    "request_id_prefix": f"req-{episode_id}",
                    "first_request_id": f"req-{episode_id}-chunk-0001",
                    "request_id_template": f"req-{episode_id}-chunk-{{chunk_index:04d}}",
                    "output_dir": str(output_root / "episodes" / episode_id),
                })
            cell_hex = uuid.uuid5(uuid.NAMESPACE_URL, cell_identity).hex
            cells.append({
                "shard_id": f"sh-{cell_hex}",
                "display_shard": shard_id,
                "task": task,
                "setting": current_setting,
                "instruction_type": SEEN_BY_SETTING[current_setting],
                "target_episodes": episodes,
                "candidate_budget": max_candidates,
                "seed_plan": {
                    "start": seed_start,
                    "step": 1,
                    "stop_exclusive": seed_start + max_candidates,
                    "same_panel_across_checkpoints": True,
                },
                "candidates": candidates,
            })
    return {
        "schema_version": 1,
        "run_id": run_id,
        **identity,
        "candidate_budget_per_cell": max_candidates,
        "worker_count": 1,
        "policy_contract": {
            "precision": "FP32",
            "actions_per_chunk": 50,
            "denoising_steps": 10,
            "action_limit": "official_full_task_limit",
        },
        "cells": cells,
    }


IDENTITY_FIELDS = (
    "episode_id", "shard_id", "task", "setting", "stage", "scene_seed",
    "checkpoint_manifest_sha256",
)


def _finite_positive(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return result


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class _BackendResponse(dict):
    def __init__(self, value: dict, log_paths: dict[str, str]):
        super().__init__(value)
        self.backend_log_paths = dict(log_paths)


class SubprocessBackend:
    """Run one backend call using JSON stdin/stdout and a hard process timeout."""

    def __init__(self, command: Sequence[str]):
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("backend command must be a non-empty argument vector")
        self.command = tuple(command)

    def evaluate(self, job: dict, timeout_seconds: float) -> dict:
        output_dir = Path(job["output_dir"]).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = output_dir / "backend.stdout.log"
        stderr_path = output_dir / "backend.stderr.log"
        log_paths = {
            "backend_stdout_path": str(stdout_path),
            "backend_stderr_path": str(stderr_path),
        }
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            kwargs["start_new_session"] = True
        payload = json.dumps(job, ensure_ascii=False, allow_nan=False)
        try:
            with stdout_path.open("xb") as stdout_stream, stderr_path.open("xb") as stderr_stream:
                process = subprocess.Popen(
                    self.command,
                    stdin=subprocess.PIPE,
                    stdout=stdout_stream,
                    stderr=stderr_stream,
                    text=True,
                    encoding="utf-8",
                    **kwargs,
                )
                try:
                    process.communicate(payload, timeout=timeout_seconds)
                except subprocess.TimeoutExpired as timeout_error:
                    self._kill_process_tree(process)
                    try:
                        process.communicate(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        # A backend that escapes its process group violates the contract;
                        # close its input pipe so it cannot hold the runner past deadline.
                        if process.stdin is not None:
                            process.stdin.close()
                        if process.poll() is None:
                            process.kill()
                        process.wait(timeout=1.0)
                    self._sync_logs(stdout_stream, stderr_stream)
                    error = TimeoutError(f"backend process tree timeout after {timeout_seconds:.3f}s")
                    error.kind = "BACKEND_TIMEOUT"
                    self._attach_logs(error, log_paths)
                    raise error from timeout_error
                self._sync_logs(stdout_stream, stderr_stream)
                if process.returncode != 0:
                    error = RuntimeError(
                        f"backend exited with status {process.returncode}: {self._tail(stderr_path).strip()}"
                    )
                    error.kind = "BACKEND_EXIT"
                    self._attach_logs(error, log_paths)
                    raise error
                try:
                    with stdout_path.open("r", encoding="utf-8") as stream:
                        value = json.load(stream)
                except (json.JSONDecodeError, UnicodeDecodeError) as error:
                    protocol_error = ValueError(f"backend stdout is not one JSON object: {error}")
                    protocol_error.kind = "PROTOCOL_ERROR"
                    self._attach_logs(protocol_error, log_paths)
                    raise protocol_error from error
                if not isinstance(value, dict):
                    error = ValueError("backend response must be a JSON object")
                    error.kind = "PROTOCOL_ERROR"
                    self._attach_logs(error, log_paths)
                    raise error
                return _BackendResponse(value, log_paths)
        except OSError as error:
            self._attach_logs(error, log_paths)
            raise

    @staticmethod
    def _sync_logs(*streams) -> None:
        for stream in streams:
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _tail(path: Path, limit: int = 4000) -> str:
        try:
            with path.open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                size = stream.tell()
                stream.seek(max(0, size - limit))
                return stream.read().decode("utf-8", errors="replace")
        except OSError:
            return ""

    @classmethod
    def _attach_logs(cls, error: BaseException, log_paths: dict[str, str]) -> None:
        error.backend_log_paths = dict(log_paths)
        error.stdout_tail = cls._tail(Path(log_paths["backend_stdout_path"]))
        error.stderr_tail = cls._tail(Path(log_paths["backend_stderr_path"]))

    @staticmethod
    def _kill_process_tree(process: subprocess.Popen) -> None:
        """Kill only the subprocess and descendants created for this episode."""
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2.0,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
            if process.poll() is None:
                process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                process.kill()


class SerialEvaluator:
    """Execute a deterministic plan serially and preserve every outcome."""

    def __init__(
        self,
        *,
        plan: dict,
        output_dir: str | Path,
        policy_package: str,
        backend_command: Sequence[str],
        episode_timeout_seconds: float,
        cell_timeout_seconds: float,
        stage_timeout_seconds: float,
        test_only_fixture: bool = False,
    ):
        self.plan = json.loads(json.dumps(plan, allow_nan=False))
        self.output_dir = Path(output_dir).resolve()
        self.policy_package = str(policy_package)
        self.backend_command = tuple(backend_command)
        self.episode_timeout_seconds = _finite_positive(episode_timeout_seconds, "episode timeout")
        self.cell_timeout_seconds = _finite_positive(cell_timeout_seconds, "cell timeout")
        self.stage_timeout_seconds = _finite_positive(stage_timeout_seconds, "stage timeout")
        self.test_only_fixture = bool(test_only_fixture)
        if self.test_only_fixture is False and self.policy_package == "TEST_FIXTURE_ONLY":
            raise ValueError("TEST_FIXTURE_ONLY is reserved for fixture tests")
        if self.plan.get("worker_count") != 1:
            raise ValueError("only one serial worker is supported")
        if not self.test_only_fixture:
            self._verify_policy_manifest()
        self.backend = SubprocessBackend(self.backend_command)
        self.evidence_kind = "fixture" if self.test_only_fixture else "real_policy"
        self.run_config = {
            "schema_version": 1,
            "plan": self.plan,
            "policy_package": self.policy_package,
            "backend_command": list(self.backend_command),
            "episode_timeout_seconds": self.episode_timeout_seconds,
            "cell_timeout_seconds": self.cell_timeout_seconds,
            "stage_timeout_seconds": self.stage_timeout_seconds,
            "worker_count": 1,
            "evidence_kind": self.evidence_kind,
        }
        self.ledger = EvaluationLedger(self.output_dir, self.run_config)

    def _verify_policy_manifest(self) -> None:
        actual = _manifest_sha(self.policy_package)
        expected = self.plan.get("checkpoint_manifest_sha256")
        if actual != expected:
            raise ValueError("policy package manifest SHA differs from the immutable plan")

    def _identity(self, cell: dict, candidate: dict) -> dict:
        return {
            "evidence_kind": self.evidence_kind,
            "stage": self.plan["stage"],
            "checkpoint_manifest_sha256": self.plan["checkpoint_manifest_sha256"],
            "task": cell["task"],
            "setting": cell["setting"],
            "scene_seed": candidate["scene_seed"],
            "episode_id": candidate["episode_id"],
            "shard_id": cell["shard_id"],
            "request_id_prefix": candidate["request_id_prefix"],
            "seed_start": self.plan["seed_start"],
        }

    @staticmethod
    def _elapsed(started: dt.datetime) -> float:
        elapsed = (dt.datetime.now(dt.timezone.utc) - started).total_seconds()
        if elapsed < 0:
            raise ValueError("system clock moved before persisted run start")
        return elapsed

    @staticmethod
    def _check_response_identity(response: dict, identity: dict) -> None:
        if response.get("evidence_kind") != identity["evidence_kind"]:
            raise ValueError("backend response evidence_kind mismatch")
        for field in IDENTITY_FIELDS:
            if response.get(field) != identity[field]:
                raise ValueError(f"backend response identity mismatch for {field}")

    @staticmethod
    def _valid_rejection(response: dict) -> tuple[str, dict]:
        # A setup rejection cannot erase an episode after learned-policy execution.
        for field in ("actions_started", "chunks"):
            value = response.get(field, 0)
            if type(value) is not int or value != 0:
                raise ValueError("setup rejection contains policy actions/chunks")
        if response.get("requests", []) != []:
            raise ValueError("setup rejection contains policy requests")
        if "task_success" in response or "task_predicate" in response:
            raise ValueError("setup rejection contains a policy outcome")
        category = response.get("rejection_category")
        evidence = response.get("rejection_evidence")
        if not isinstance(evidence, dict):
            raise ValueError("typed setup rejection lacks structured evidence")
        if category == "EXPERT_UNSOLVED":
            plan_success = evidence.get("plan_success")
            init_scene = evidence.get("init_scene")
            if type(plan_success) is not bool or type(init_scene) is not bool:
                raise ValueError("EXPERT_UNSOLVED requires boolean plan_success and init_scene evidence")
            if plan_success and init_scene:
                raise ValueError("EXPERT_UNSOLVED requires a failed plan or failed scene initialization")
            return category, evidence
        if category == "UNSTABLE_SETUP":
            if (evidence.get("exception_type") != "UnStableError"
                    or evidence.get("exception_module") != "envs.utils.create_actor"):
                raise ValueError("UNSTABLE_SETUP requires exact UnStableError type")
            frames = evidence.get("traceback_frames")
            if not isinstance(frames, list) or not any(
                isinstance(frame, dict)
                and frame.get("name") == "_init_task_env_"
                and isinstance(frame.get("filename"), str)
                and frame["filename"].replace("\\", "/").endswith("/envs/_base_task.py")
                for frame in frames
            ):
                raise ValueError("UNSTABLE_SETUP traceback must originate in _init_task_env_ at envs/_base_task.py")
            return category, evidence
        raise ValueError(f"untyped or disallowed setup rejection: {category!r}")

    @staticmethod
    def _validate_episode(response: dict, identity: dict) -> dict:
        SerialEvaluator._check_response_identity(response, identity)
        if response.get("status") != "COMPLETE":
            raise ValueError("backend response is not a completed policy episode")
        success = response.get("task_success")
        predicate = response.get("task_predicate")
        if type(success) is not bool or type(predicate) is not bool:
            raise ValueError("task_success and task_predicate must be booleans")
        if success != predicate:
            raise ValueError("evaluator success differs from task.eval_success")
        step_limit = response.get("step_limit")
        official_step_limit = response.get("official_step_limit")
        actions_started = response.get("actions_started")
        chunks = response.get("chunks")
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (step_limit, official_step_limit, actions_started, chunks)):
            raise ValueError("step limits, action count and chunk count must be integers")
        if step_limit <= 0 or official_step_limit <= 0 or step_limit != official_step_limit:
            raise ValueError("reported step_limit must equal the official full task limit")
        expected_chunks = math.ceil(actions_started / 50) if isinstance(actions_started, int) and actions_started > 0 else 0
        if not 0 < actions_started <= step_limit or chunks <= 0 or chunks != expected_chunks:
            raise ValueError("action count or chunk count is outside the full-task bounds")
        wall_seconds = response.get("wall_seconds")
        if isinstance(wall_seconds, bool) or not isinstance(wall_seconds, (int, float)) or not math.isfinite(wall_seconds) or wall_seconds < 0:
            raise ValueError("wall_seconds must be finite and non-negative")
        for field in ("log_path",):
            if not isinstance(response.get(field), str) or not response[field].strip():
                raise ValueError(f"{field} must be a non-empty retained artifact path")
        video_path = response.get("video_path")
        video_review_status = response.get("video_review_status")
        if video_review_status is not None and (
            not isinstance(video_review_status, str)
            or video_review_status not in {"REVIEWED", "NOT_REVIEWED"}
        ):
            raise ValueError("video_review_status must be REVIEWED or NOT_REVIEWED")
        if video_path is None:
            if video_review_status != "NOT_REVIEWED":
                raise ValueError("missing video requires video_review_status=NOT_REVIEWED")
        elif not isinstance(video_path, str) or not video_path.strip():
            raise ValueError("video_path must be a non-empty path or null")
        requests = response.get("requests")
        if not isinstance(requests, list) or len(requests) != chunks:
            raise ValueError("requests must contain exactly one request identity per chunk")
        for index, request in enumerate(requests, start=1):
            expected_noise_seed = 777 + index - 1
            expected_request_id = f"req-{identity['episode_id']}-chunk-{index:04d}"
            if not isinstance(request, dict):
                raise ValueError(f"request identity mismatch for chunk {index}")
            chunk_index = request.get("chunk_index")
            noise_seed = request.get("noise_seed")
            if (isinstance(chunk_index, bool) or not isinstance(chunk_index, int)
                    or chunk_index != index
                    or isinstance(noise_seed, bool) or not isinstance(noise_seed, int)
                    or noise_seed != expected_noise_seed
                    or request.get("request_id") != expected_request_id):
                raise ValueError(f"request identity mismatch for chunk {index}")
        normalized = dict(response)
        return normalized

    @staticmethod
    def _execution_evidence(response: dict | None, elapsed_seconds: float,
                            candidate_output_dir: str, *, setup_rejection: bool = False,
                            error: BaseException | None = None,
                            backend_log_paths: dict | None = None) -> dict:
        response = response or {}
        def safe_int(field: str, default: int | None) -> int | None:
            value = response.get(field, default)
            return value if isinstance(value, int) and not isinstance(value, bool) else default

        def safe_path(field: str) -> str | None:
            value = response.get(field)
            return value if isinstance(value, str) and value.strip() else None

        response_wall = response.get("wall_seconds")
        wall_seconds = response_wall if (
            isinstance(response_wall, (int, float)) and not isinstance(response_wall, bool)
            and math.isfinite(response_wall) and response_wall >= 0
        ) else max(0.0, float(elapsed_seconds))
        video_path = safe_path("video_path")
        video_status = response.get("video_review_status")
        if not isinstance(video_status, str) or not video_status.strip():
            video_status = "NOT_REVIEWED" if video_path is None else "PENDING"
        evidence = {
            "wall_seconds": wall_seconds,
            "runner_wall_seconds": max(0.0, float(elapsed_seconds)),
            "actions_started": safe_int("actions_started", 0 if setup_rejection else None),
            "step_limit": safe_int("step_limit", None),
            "official_step_limit": safe_int("official_step_limit", None),
            "chunks": safe_int("chunks", 0 if setup_rejection else None),
            "log_path": safe_path("log_path"),
            "video_path": video_path,
            "video_review_status": video_status,
            "output_dir": candidate_output_dir,
        }
        if isinstance(backend_log_paths, dict):
            for field in ("backend_stdout_path", "backend_stderr_path"):
                path = backend_log_paths.get(field)
                if isinstance(path, str) and path.strip():
                    evidence[field] = path
        if error is not None:
            for output_name, error_name in (("stdout_tail", "stdout_tail"), ("stderr_tail", "stderr_tail")):
                value = getattr(error, error_name, None)
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")
                if isinstance(value, str) and value:
                    evidence[output_name] = value[-4000:]
        return evidence

    def _terminal_failure(self, identity: dict, error: BaseException, *,
                          response: dict | None, elapsed_seconds: float,
                          candidate_output_dir: str,
                          backend_log_paths: dict | None = None) -> dict:
        if isinstance(error, TimeoutError):
            default_kind = "BACKEND_TIMEOUT"
        elif isinstance(error, ValueError):
            default_kind = "PROTOCOL_ERROR"
        else:
            default_kind = "BACKEND_ERROR"
        execution_evidence = self._execution_evidence(
            response, elapsed_seconds, candidate_output_dir, error=error,
            backend_log_paths=backend_log_paths or getattr(error, "backend_log_paths", None),
        )
        return {
            **identity,
            "terminal_status": "INFRA_ERROR",
            "error": {"kind": getattr(error, "kind", default_kind), "message": str(error)},
            **execution_evidence,
            "execution_evidence": execution_evidence,
        }

    def _snapshot(self, status_hint: str = "RUNNING") -> dict:
        terminals = self.ledger.terminal_records()
        started = self.ledger.started_records()
        episodes = [record["episode"] for record in terminals
                    if record.get("terminal_status") == "COMPLETE_POLICY" and isinstance(record.get("episode"), dict)]
        rejections = []
        for record in terminals:
            if record.get("terminal_status") == "REJECTED_SETUP":
                item = {key: record.get(key) for key in IDENTITY_FIELDS}
                rejection = record.get("rejection", {})
                item.update({"category": rejection.get("category"), "evidence": rejection.get("evidence"),
                             "execution_evidence": record.get("execution_evidence"),
                             **(record.get("execution_evidence") or {}), "count": 1})
                rejections.append(item)
        errors = []
        for record in terminals:
            if record.get("terminal_status") == "INFRA_ERROR":
                item = {key: record.get(key) for key in IDENTITY_FIELDS}
                error = record.get("error", {})
                item.update({"kind": error.get("kind", "BACKEND_ERROR"), "message": error.get("message", ""), "count": 1,
                             "terminal_status": record.get("terminal_status"),
                             "execution_evidence": record.get("execution_evidence"),
                             **(record.get("execution_evidence") or {})})
                errors.append(item)
        terminal_ids = {record["episode_id"] for record in terminals}
        unresolved = [record for record in started if record["episode_id"] not in terminal_ids]
        errors.extend({**{key: item.get(key) for key in IDENTITY_FIELDS},
                       "terminal_status": "INTERRUPTED_STARTED", "kind": "INTERRUPTED_STARTED",
                       "message": "STARTED record has no terminal record; automatic replay is blocked", "count": 1}
                      for item in unresolved)
        cell_counts = []
        covered = 0
        remaining = 0
        for cell in self.plan["cells"]:
            task_terms = [t for t in terminals if t.get("shard_id") == cell["shard_id"]]
            completed = sum(t.get("terminal_status") == "COMPLETE_POLICY" for t in task_terms)
            left = max(0, cell["target_episodes"] - completed)
            remaining += left
            covered += int(left == 0)
            cell_counts.append({
                "task": cell["task"], "setting": cell["setting"],
                "completed_episodes": completed,
                "target_episodes": cell["target_episodes"],
                "remaining_episodes": left,
                "candidate_seeds_used": len({t.get("scene_seed") for t in task_terms}),
                "shard_id": cell["shard_id"],
            })
        error_cells = {item.get("shard_id") for item in errors}
        terminal_seeds_by_cell: dict[str, set[int]] = {}
        for record in terminals:
            terminal_seeds_by_cell.setdefault(record.get("shard_id"), set()).add(record.get("scene_seed"))
        started_seeds_by_cell: dict[str, set[int]] = {}
        for record in started:
            started_seeds_by_cell.setdefault(record.get("shard_id"), set()).add(record.get("scene_seed"))
        for cell, coverage in zip(self.plan["cells"], cell_counts):
            if coverage["remaining_episodes"] == 0 or cell["shard_id"] in error_cells:
                continue
            metadata_path = self.ledger.metadata_dir / f"cell-{cell['shard_id']}.started.json"
            if metadata_path.is_file():
                cell_elapsed = self._elapsed(self.ledger.cell_started_at(cell["shard_id"]))
                if cell_elapsed >= self.cell_timeout_seconds:
                    errors.append({
                        "stage": self.plan["stage"], "checkpoint_manifest_sha256": self.plan["checkpoint_manifest_sha256"],
                        "task": cell["task"], "setting": cell["setting"], "shard_id": cell["shard_id"],
                        "kind": "CELL_TIMEOUT", "message": "persisted cell deadline expired before target coverage", "count": 1,
                    })
                    continue
            used = terminal_seeds_by_cell.get(cell["shard_id"], set()) | started_seeds_by_cell.get(cell["shard_id"], set())
            if len(used) >= cell["candidate_budget"]:
                errors.append({
                    "stage": self.plan["stage"], "checkpoint_manifest_sha256": self.plan["checkpoint_manifest_sha256"],
                    "task": cell["task"], "setting": cell["setting"], "shard_id": cell["shard_id"],
                    "kind": "CANDIDATE_BUDGET_EXHAUSTED", "message": "candidate seed budget exhausted before target coverage", "count": 1,
                })
        if self.ledger.stage_started_at() and self._elapsed(self.ledger.stage_started_at()) >= self.stage_timeout_seconds:
            if not any(item.get("kind") == "STAGE_TIMEOUT" for item in errors):
                errors.append({
                    "stage": self.plan["stage"], "checkpoint_manifest_sha256": self.plan["checkpoint_manifest_sha256"],
                    "kind": "STAGE_TIMEOUT", "message": "persisted stage deadline expired before full target coverage", "count": 1,
                })
        full_grid = len(self.plan["cells"]) == 100
        complete = covered == len(self.plan["cells"]) and not errors
        status = "COMPLETE" if complete and full_grid else "PARTIAL"
        if status_hint in {"FAILED", "PARTIAL"} and not complete:
            status = "FAILED" if status_hint == "FAILED" and not episodes else "PARTIAL"
        report = {
            "schema_version": 1,
            "evidence_kind": self.evidence_kind,
            "status": status,
            "stage": self.plan["stage"],
            "checkpoint_manifest_sha256": self.plan["checkpoint_manifest_sha256"],
            "run_id": self.plan["run_id"],
            "run_config_sha256": self.ledger.run_config_sha256,
            "target_episodes_per_cell": self.plan["target_episodes"],
            "candidate_budget_per_cell": self.plan["candidate_budget_per_cell"],
            "real_policy_episodes": len(episodes) if self.evidence_kind == "real_policy" else 0,
            "completed_episodes": len(episodes),
            "completed_cells": covered,
            "cell_count": len(self.plan["cells"]),
            "remaining_episodes": remaining,
            "coverage": cell_counts,
            "episodes": episodes,
            "rejections": rejections,
            "errors": errors,
        }
        return report

    def _save_snapshot(self, status_hint: str = "RUNNING") -> dict:
        report = self._snapshot(status_hint)
        _json_write(self.output_dir / "evaluation-report.json", report)
        return report

    def run(self, *, resume: bool) -> dict:
        if not self.test_only_fixture:
            self._verify_policy_manifest()
            verified = _portable_contract().verify_package(self.policy_package)
            if verified["manifest_sha256"] != self.plan["checkpoint_manifest_sha256"]:
                raise ValueError("verified package differs from immutable plan")
        self.ledger.initialize(resume=resume)
        plan_path = self.output_dir / "run-plan.json"
        if resume:
            if not plan_path.is_file() or json.loads(plan_path.read_text(encoding="utf-8")) != self.plan:
                raise ValueError("saved run plan is missing or differs from the immutable plan")
        else:
            _json_write(plan_path, self.plan)
        with self.ledger.lock():
            terminals = self.ledger.terminal_records()
            started = self.ledger.started_records()
            terminal_ids = {item["episode_id"] for item in terminals}
            unresolved_ids = {item["episode_id"] for item in started if item["episode_id"] not in terminal_ids}
            stage_start = self.ledger.stage_started_at()
            stage_expired = self._elapsed(stage_start) >= self.stage_timeout_seconds
            fatal_cells = {item.get("shard_id") for item in terminals if item.get("terminal_status") == "INFRA_ERROR"}
            fatal_cells.update(item.get("shard_id") for item in started if item.get("episode_id") in unresolved_ids)
            for cell in self.plan["cells"]:
                if stage_expired:
                    break
                if cell["shard_id"] in fatal_cells:
                    continue
                prior = [item for item in terminals if item.get("shard_id") == cell["shard_id"]]
                completed = sum(item.get("terminal_status") == "COMPLETE_POLICY" for item in prior)
                used = {item.get("scene_seed") for item in prior}
                for item in started:
                    if item.get("shard_id") == cell["shard_id"]:
                        used.add(item.get("scene_seed"))
                if completed >= cell["target_episodes"]:
                    continue
                cell_start = self.ledger.cell_started_at(cell["shard_id"])
                cell_expired = self._elapsed(cell_start) >= self.cell_timeout_seconds
                if cell_expired:
                    continue
                for candidate in cell["candidates"]:
                    if completed >= cell["target_episodes"]:
                        break
                    if candidate["scene_seed"] in used:
                        continue
                    if self._elapsed(stage_start) >= self.stage_timeout_seconds:
                        stage_expired = True
                        break
                    cell_left = self.cell_timeout_seconds - self._elapsed(cell_start)
                    stage_left = self.stage_timeout_seconds - self._elapsed(stage_start)
                    timeout = min(self.episode_timeout_seconds, cell_left, stage_left)
                    if timeout <= 0:
                        break
                    identity = self._identity(cell, candidate)
                    started_identity = {**identity, "policy_package": self.policy_package}
                    self.ledger.begin(started_identity)
                    used.add(candidate["scene_seed"])
                    attempt_started = time.monotonic()
                    response = None
                    job = {
                        **identity,
                        "seed_start": self.plan["seed_start"],
                        "instruction_type": cell["instruction_type"],
                        "precision": self.plan["policy_contract"]["precision"],
                        "actions_per_chunk": self.plan["policy_contract"]["actions_per_chunk"],
                        "denoising_steps": self.plan["policy_contract"]["denoising_steps"],
                        "action_limit": "official_full_task_limit",
                        "noise_seed_base": 777,
                        "output_dir": candidate["output_dir"],
                        "policy_package": self.policy_package,
                        "request_id_prefix": candidate["request_id_prefix"],
                        "request_id_template": candidate["request_id_template"],
                    }
                    backend_log_paths = {}
                    try:
                        response = self.backend.evaluate(job, timeout)
                        backend_log_paths = getattr(response, "backend_log_paths", {})
                        self._check_response_identity(response, identity)
                        if response.get("status") == "REJECTED_SETUP":
                            category, evidence = self._valid_rejection(response)
                            execution_evidence = self._execution_evidence(
                                response, time.monotonic() - attempt_started, candidate["output_dir"],
                                setup_rejection=True,
                                backend_log_paths=backend_log_paths,
                            )
                            terminal = {
                                **identity,
                                "terminal_status": "REJECTED_SETUP",
                                "rejection": {"category": category, "evidence": evidence},
                                **execution_evidence,
                                "execution_evidence": execution_evidence,
                            }
                        elif response.get("status") == "COMPLETE":
                            episode = self._validate_episode(response, identity)
                            execution_evidence = self._execution_evidence(
                                response, time.monotonic() - attempt_started, candidate["output_dir"],
                                backend_log_paths=backend_log_paths,
                            )
                            terminal = {
                                **identity, "terminal_status": "COMPLETE_POLICY", "episode": episode,
                                **execution_evidence, "execution_evidence": execution_evidence,
                            }
                        else:
                            error = RuntimeError(f"backend returned terminal status {response.get('status')!r}: {response.get('error', '')}")
                            error.kind = response.get("error_kind", "BACKEND_ERROR")
                            raise error
                    except (OSError, RuntimeError, TimeoutError, ValueError) as error:
                        backend_log_paths = backend_log_paths or getattr(error, "backend_log_paths", {})
                        terminal = self._terminal_failure(
                            identity, error, response=response,
                            elapsed_seconds=time.monotonic() - attempt_started,
                            candidate_output_dir=candidate["output_dir"],
                            backend_log_paths=backend_log_paths,
                        )
                    self.ledger.finish(candidate["episode_id"], terminal)
                    terminals.append(terminal)
                    if terminal["terminal_status"] == "COMPLETE_POLICY":
                        completed += 1
                    elif terminal["terminal_status"] == "INFRA_ERROR":
                        fatal_cells.add(cell["shard_id"])
                    self._save_snapshot("FAILED" if terminal["terminal_status"] == "INFRA_ERROR" else "RUNNING")
                    if terminal["terminal_status"] == "INFRA_ERROR":
                        break
                    if self._elapsed(stage_start) >= self.stage_timeout_seconds:
                        stage_expired = True
                        break
            report = self._save_snapshot("PARTIAL" if stage_expired else "RUNNING")
            return report


def _portable_contract():
    """Read the sibling A implementation; importing it performs CPU work only."""
    path = Path(__file__).resolve().parents[1] / "portable/src/portable_manifest.py"
    if not path.is_file():
        raise ValueError("A portable implementation missing: portable/src/portable_manifest.py")
    spec = importlib.util.spec_from_file_location("lingbot_evaluation_portable_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest_sha(policy_package: str | Path) -> str:
    root = Path(policy_package)
    manifest_path = root / "package-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError(f"policy package has no regular package-manifest.json: {manifest_path}")
    if (root / "manifest.json").exists():
        raise ValueError("ambiguous manifest.json alias; preserve A's canonical package unchanged")
    contract = _portable_contract()
    parsed = contract.read_json(manifest_path)
    if (not isinstance(parsed, dict) or parsed.get("format") != contract.FORMAT
            or not isinstance(parsed.get("files"), dict) or not parsed["files"]):
        raise ValueError("invalid/empty A portable package manifest")
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-package", type=Path)
    parser.add_argument("--policy-manifest-sha256")
    parser.add_argument("--fixture-only", action="store_true", help="write a labeled CPU plan without a model package")
    parser.add_argument("--backend-executable")
    parser.add_argument("--backend-arg", action="append", default=[])
    parser.add_argument("--tasks-file", type=Path, default=root / "official" / "results-template.json")
    parser.add_argument("--setting", choices=("clean", "randomized", "all"), default="all")
    parser.add_argument("--task", action="append", help="select one or more official task names; repeatable")
    parser.add_argument("--stage", choices=("baseline", "candidate"), default="baseline")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--max-candidates", type=int, default=1000)
    parser.add_argument("--seed-start", type=int, default=100000)
    parser.add_argument("--episode-timeout-seconds", type=float, default=3600)
    parser.add_argument("--cell-timeout-seconds", type=float, default=86400)
    parser.add_argument("--stage-timeout-seconds", type=float, default=604800)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.fixture_only:
            if not args.dry_run:
                raise ValueError("--fixture-only is restricted to --dry-run on the CLI")
            if args.policy_package:
                raise ValueError("--fixture-only and --policy-package cannot be combined")
            manifest_sha = _sha256(args.policy_manifest_sha256) if args.policy_manifest_sha256 else hashlib.sha256(b"FIXTURE_ONLY").hexdigest()
        else:
            if args.policy_package is None:
                raise ValueError("--policy-package PATH is required outside fixture-only dry-run mode")
            manifest_sha = _manifest_sha(args.policy_package)
            if args.policy_manifest_sha256 and _sha256(args.policy_manifest_sha256) != manifest_sha:
                raise ValueError("provided manifest SHA differs from policy package manifest.json")
        tasks = load_tasks(args.tasks_file)
        selected_tasks = args.task or tasks
        plan = build_plan(
            tasks=tasks,
            setting=args.setting,
            episodes=args.episodes,
            max_candidates=args.max_candidates,
            seed_start=args.seed_start,
            manifest_sha256=manifest_sha,
            stage=args.stage,
            output_dir=args.output,
            selected_tasks=selected_tasks,
        )
        if args.dry_run:
            _json_write(args.output / "run-plan.json", plan)
            _json_write(args.output / "evaluation-report.json", {
                "schema_version": 1,
                "evidence_kind": "fixture" if args.fixture_only else "real_policy",
                "status": "NOT_RUN",
                "stage": args.stage,
                "checkpoint_manifest_sha256": manifest_sha,
                "run_id": plan["run_id"],
                "real_policy_episodes": 0,
                "completed_episodes": 0,
                "episodes": [], "rejections": [], "errors": [],
                "note": "Dry run writes schedule only; no backend or model was launched.",
            })
            return 0
        if not args.backend_executable:
            raise ValueError("--backend-executable is required for execution; native bridge is not bundled")
        command = [args.backend_executable, *args.backend_arg]
        runner = SerialEvaluator(
            plan=plan,
            output_dir=args.output,
            policy_package=str(args.policy_package.resolve()),
            backend_command=command,
            episode_timeout_seconds=args.episode_timeout_seconds,
            cell_timeout_seconds=args.cell_timeout_seconds,
            stage_timeout_seconds=args.stage_timeout_seconds,
        )
        report = runner.run(resume=args.resume)
        if report.get("errors"):
            return 1
    except (OSError, ValueError, FileExistsError, RuntimeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
