"""Strict, CPU-only aggregation into the official LingBot results schema."""

from __future__ import annotations

import argparse
import copy
import json
import math
from collections.abc import Mapping
from pathlib import Path
import re
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTITY_FIELDS = (
    "episode_id", "shard_id", "task", "setting", "stage", "scene_seed",
    "checkpoint_manifest_sha256",
)


def request_id_for(episode_id: str, chunk_index: int) -> str:
    """Return the globally unique identifier shared with the evaluation runner."""
    if not isinstance(episode_id, str) or not episode_id:
        raise ValueError("episode_id must be a non-empty string")
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, int) or chunk_index < 1:
        raise ValueError("chunk_index must be a positive integer")
    return f"req-{episode_id}-chunk-{chunk_index:04d}"


def _bool(value: Any, field: str) -> bool:
    if type(value) is bool:
        return value
    # Accept NumPy's scalar bool without importing NumPy during CPU-only use.
    value_type = type(value)
    if value_type.__module__ == "numpy" and value_type.__name__ in {"bool", "bool_"}:
        return bool(value)
    raise ValueError(f"{field} must be a boolean")


def _int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _finite_number(value: Any, field: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{field} must be a finite number >= {minimum}")
    return number


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _json_identity(record: Mapping[str, Any]) -> str:
    try:
        return json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"episode record is not finite JSON: {error}") from error


class _Aggregator:
    def __init__(self, official_template: Mapping[str, Any], expected_manifest_sha256: str,
                 team_id: str, target_episodes: int):
        if not isinstance(expected_manifest_sha256, str) or not SHA256_RE.fullmatch(expected_manifest_sha256):
            raise ValueError("manifest SHA must be 64 lowercase hexadecimal characters")
        if not isinstance(team_id, str) or not team_id.strip():
            raise ValueError("team_id must be a non-empty string")
        self.expected_hash = expected_manifest_sha256
        self.team_id = team_id
        self.target = _int(target_episodes, "target_episodes", minimum=1)
        self.template = self._check_template(official_template)
        self.tasks = tuple(self.template["results"]["clean"])
        self.counts = {setting: {task: [0, 0] for task in self.tasks}
                       for setting in ("clean", "randomized")}
        self.physical: dict[tuple[str, str, int], str] = {}
        self.request_ids: dict[str, tuple[str, str, int]] = {}
        self.started_records: dict[str, dict[str, Any]] = {}
        self.terminal_records: dict[str, dict[str, Any]] = {}
        self.duplicate_count = 0
        self.excluded = {"fixture": 0, "commissioning": 0, "other": 0}
        self.errors: list[dict[str, Any]] = []
        self.stage: str | None = None
        self.video_review_status_counts: dict[str, int] = {}

    @staticmethod
    def _check_template(template: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(template, Mapping):
            raise ValueError("official template must be an object")
        value = copy.deepcopy(dict(template))
        if set(value) != {"schema_version", "team_id", "results"} or value.get("schema_version") != 1:
            raise ValueError("official template top-level schema differs")
        results = value.get("results")
        if not isinstance(results, dict) or set(results) != {"clean", "randomized"}:
            raise ValueError("official template must contain exactly clean and randomized results")
        clean, randomized = results["clean"], results["randomized"]
        if not isinstance(clean, dict) or not isinstance(randomized, dict):
            raise ValueError("official template task cells must be objects")
        tasks = tuple(clean)
        if len(tasks) != 50 or len(set(tasks)) != 50 or set(tasks) != set(randomized):
            raise ValueError("official template must contain the same 50 task cells per setting")
        for setting in ("clean", "randomized"):
            for task, cell in results[setting].items():
                if not isinstance(task, str) or not task or not isinstance(cell, dict):
                    raise ValueError("official template contains an invalid task cell")
                if set(cell) != {"attempts", "successes"}:
                    raise ValueError("official template task cell must contain attempts and successes only")
                for field in ("attempts", "successes"):
                    _int(cell[field], f"template {field}")
        return value

    def _stage_hash(self, record: Mapping[str, Any], *, context: str) -> None:
        stage = record.get("stage")
        if stage is not None:
            if stage not in {"baseline", "candidate"}:
                raise ValueError(f"invalid stage in {context}")
            if self.stage is not None and stage != self.stage:
                raise ValueError("mixed stage records")
            self.stage = stage
        manifest = record.get("checkpoint_manifest_sha256")
        if manifest is not None and manifest != self.expected_hash:
            raise ValueError("manifest SHA mismatch")

    def _cell_identity(self, record: Mapping[str, Any], *, context: str) -> tuple[str, str, int]:
        for field in IDENTITY_FIELDS:
            if field not in record:
                raise ValueError(f"{context} missing {field}")
        task = _string(record["task"], "task")
        setting = _string(record["setting"], "setting")
        if task not in self.tasks:
            raise ValueError(f"unknown task: {task}")
        if setting not in {"clean", "randomized"}:
            raise ValueError("setting must be clean or randomized")
        self._stage_hash(record, context=context)
        if record["checkpoint_manifest_sha256"] != self.expected_hash:
            raise ValueError("manifest SHA mismatch")
        episode_id = _string(record["episode_id"], "episode_id")
        shard_id = _string(record["shard_id"], "shard_id")
        seed = _int(record["scene_seed"], "scene_seed")
        # Validate the remaining exact identity fields even though only the cell
        # and seed form the physical deduplication key.
        _string(record["stage"], "stage")
        _string(record["checkpoint_manifest_sha256"], "checkpoint_manifest_sha256")
        return task, setting, seed

    def _validate_episode(self, record: Mapping[str, Any], *, context: str = "episode") -> tuple[dict[str, Any], tuple[str, str, int]]:
        if not isinstance(record, Mapping):
            raise ValueError(f"{context} must be an object")
        evidence_kind = record.get("evidence_kind")
        if evidence_kind is None:
            raise ValueError("evidence_kind is required on completed episode records")
        if evidence_kind != "real_policy":
            raise ValueError("_excluded")
        status = record.get("status")
        if status != "COMPLETE":
            raise ValueError(f"invalid completed episode status: {status!r}")
        key = self._cell_identity(record, context=context)
        success = _bool(record.get("task_success"), "task_success")
        predicate = _bool(record.get("task_predicate"), "task_predicate")
        if predicate != success:
            raise ValueError("task predicate disagrees with task_success")
        step_limit = _int(record.get("step_limit"), "step_limit", minimum=1)
        official_limit = _int(record.get("official_step_limit"), "official_step_limit", minimum=1)
        if step_limit != official_limit:
            raise ValueError("step_limit differs from official step limit")
        actions = _int(record.get("actions_started"), "actions_started", minimum=1)
        if actions > step_limit:
            raise ValueError("actions_started exceeds the official step limit")
        chunks = _int(record.get("chunks"), "chunks", minimum=1)
        _finite_number(record.get("wall_seconds"), "wall_seconds", minimum=0.0)
        _string(record.get("log_path"), "log_path")
        video_path = record.get("video_path")
        video_review_status = record.get("video_review_status")
        if video_path is None:
            if video_review_status != "NOT_REVIEWED":
                raise ValueError("video_path may be null only with video_review_status NOT_REVIEWED")
        else:
            _string(video_path, "video_path")
        if video_review_status is not None:
            if video_review_status not in {"REVIEWED", "NOT_REVIEWED"}:
                raise ValueError("video_review_status must be REVIEWED or NOT_REVIEWED")
        request_list = record.get("requests")
        if not isinstance(request_list, list) or len(request_list) != chunks:
            raise ValueError("requests must contain exactly one identity per chunk")
        episode_id = record["episode_id"]
        for index, request in enumerate(request_list, start=1):
            if not isinstance(request, Mapping):
                raise ValueError("request identity must be an object")
            if _int(request.get("chunk_index"), "request chunk_index", minimum=1) != index:
                raise ValueError("request identity chunk indexes must be consecutive from one")
            _int(request.get("noise_seed"), "request noise_seed")
            expected_request_id = request_id_for(episode_id, index)
            if request.get("request_id") != expected_request_id:
                raise ValueError(f"request identity differs for episode {episode_id} chunk {index}")
        normalized = dict(record)
        normalized["task_success"] = success
        normalized["task_predicate"] = predicate
        return normalized, key

    def _accept_episode(self, episode: Mapping[str, Any], terminal: Mapping[str, Any] | None = None) -> None:
        if terminal is not None:
            if terminal.get("evidence_kind") != episode.get("evidence_kind"):
                raise ValueError("terminal evidence_kind differs from nested episode")
            for field in IDENTITY_FIELDS:
                if field not in terminal or terminal[field] != episode.get(field):
                    raise ValueError(f"terminal identity mismatch for {field}")
        try:
            normalized, physical_key = self._validate_episode(episode)
        except ValueError as error:
            if str(error) == "_excluded":
                kind = episode.get("evidence_kind")
                bucket = "fixture" if kind == "fixture" else "commissioning" if kind == "commissioning" else "other"
                self.excluded[bucket] += 1
                return
            raise
        identity = _json_identity(normalized)
        prior = self.physical.get(physical_key)
        if prior is not None:
            if prior != identity:
                raise ValueError(f"conflicting duplicate physical episode {physical_key}")
            self.duplicate_count += 1
            return
        self.physical[physical_key] = identity
        video_review_status = normalized.get("video_review_status")
        if video_review_status is not None:
            self.video_review_status_counts[video_review_status] = self.video_review_status_counts.get(video_review_status, 0) + 1
        requests = normalized["requests"]
        for request in requests:
            request_id = request["request_id"]
            prior_episode = self.request_ids.get(request_id)
            if prior_episode is not None and prior_episode != physical_key:
                raise ValueError(f"request identity reused across episodes: {request_id}")
            if prior_episode is not None:
                raise ValueError(f"request identity reused within episode: {request_id}")
            self.request_ids[request_id] = physical_key
        pair = self.counts[physical_key[1]][physical_key[0]]
        pair[0] += 1
        pair[1] += int(_bool(normalized["task_success"], "task_success"))

    def _event_identity(self, event: Mapping[str, Any], *, context: str) -> None:
        if event.get("evidence_kind") == "real_policy":
            if "stage" not in event or "checkpoint_manifest_sha256" not in event:
                raise ValueError(f"{context} real_policy identity requires stage and manifest SHA")
            if event["stage"] not in {"baseline", "candidate"}:
                raise ValueError(f"invalid stage in {context}")
            if event["checkpoint_manifest_sha256"] != self.expected_hash:
                raise ValueError("manifest SHA mismatch")
        if "stage" in event or "checkpoint_manifest_sha256" in event:
            self._stage_hash(event, context=context)
        if "task" in event and event["task"] not in self.tasks:
            raise ValueError(f"unknown task: {event['task']}")
        if "setting" in event and event["setting"] not in {"clean", "randomized"}:
            raise ValueError("setting must be clean or randomized")
        if "episode_id" in event:
            _string(event["episode_id"], "episode_id")
        if "shard_id" in event:
            _string(event["shard_id"], "shard_id")
        if "scene_seed" in event:
            _int(event["scene_seed"], "scene_seed")

    def _event(self, kind: str, value: Any, *, source: str | None = None) -> None:
        item: dict[str, Any] = {"kind": kind, "record": copy.deepcopy(value)}
        if source is not None:
            item["source"] = source
        self.errors.append(item)

    def _child_event(self, kind: str, value: Any, parent: Mapping[str, Any], *, source: str | None) -> None:
        if isinstance(value, Mapping):
            for field in IDENTITY_FIELDS:
                if field in parent and field in value and parent[field] != value[field]:
                    raise ValueError(f"report envelope identity mismatch for {field}")
            identity = dict(parent)
            identity.update(value)
            self._event_identity(identity, context="nested report event")
        self._event(kind, value, source=source)

    def _validate_nested_counts(self, results: Any) -> None:
        if not isinstance(results, Mapping) or set(results) != {"clean", "randomized"}:
            raise ValueError("report results must contain clean and randomized")
        for setting in ("clean", "randomized"):
            cells = results[setting]
            if not isinstance(cells, Mapping) or set(cells) != set(self.tasks):
                raise ValueError("report results contain unknown or missing task cells")
            for task in self.tasks:
                cell = cells[task]
                if not isinstance(cell, Mapping) or set(cell) != {"attempts", "successes"}:
                    raise ValueError("report result cell must contain attempts and successes")
                attempts = _int(cell["attempts"], "attempts")
                successes = _int(cell["successes"], "successes")
                if successes > attempts:
                    raise ValueError("successes cannot exceed attempts")

    def _episode_counts(self, episodes: list[Any]) -> dict[str, dict[str, list[int]]]:
        nested = _Aggregator(self.template, self.expected_hash, self.team_id, 1)
        for episode in episodes:
            nested.visit(episode)
        return nested.counts

    def _validate_report_counts(self, record: Mapping[str, Any], episodes: list[Any]) -> None:
        has_attempts = "attempts" in record
        has_successes = "successes" in record
        if has_attempts != has_successes:
            raise ValueError("report attempts and successes must be provided together")
        if not has_attempts and "results" not in record:
            return
        observed = self._episode_counts(episodes)
        if "results" in record:
            self._validate_nested_counts(record["results"])
            for setting in ("clean", "randomized"):
                for task in self.tasks:
                    cell = record["results"][setting][task]
                    if [cell["attempts"], cell["successes"]] != observed[setting][task]:
                        raise ValueError(f"report results disagree with completed episodes for {setting}/{task}")
        if has_attempts:
            attempts = _int(record["attempts"], "attempts")
            successes = _int(record["successes"], "successes")
            if successes > attempts:
                raise ValueError("successes cannot exceed attempts")
            if record.get("task") is not None or record.get("setting") is not None:
                task = _string(record.get("task"), "task")
                setting = _string(record.get("setting"), "setting")
                if task not in self.tasks:
                    raise ValueError(f"unknown task: {task}")
                if setting not in {"clean", "randomized"}:
                    raise ValueError("setting must be clean or randomized")
                expected = observed[setting][task]
            else:
                expected = [sum(counts[0] for cells in observed.values() for counts in cells.values()),
                            sum(counts[1] for cells in observed.values() for counts in cells.values())]
            if [attempts, successes] != expected:
                raise ValueError("report attempts/successes disagree with completed episodes")

    def visit(self, value: Any, *, source: str | None = None) -> None:
        if isinstance(value, (list, tuple)):
            for item in value:
                self.visit(item, source=source)
            return
        if not isinstance(value, Mapping):
            raise ValueError("each records source must contain JSON objects")
        record = value
        # Retained commissioning reports are explicit negative evidence.
        if record.get("stage") == "commission" or record.get("native_commissioned") is True or record.get("checkpoint") == "NO_MODEL_TRANSPORT_COMMISSION":
            self.excluded["commissioning"] += 1
            return

        record_type = record.get("record_type")
        if record_type == "STARTED":
            if record.get("evidence_kind") not in {"real_policy", "fixture"}:
                raise ValueError("STARTED evidence_kind must be real_policy or fixture")
            self._cell_identity(record, context="started record")
            self._check_run_identity(record, started=True)
            episode_id = record["episode_id"]
            previous = self.started_records.get(episode_id)
            if previous is not None and _json_identity(previous) != _json_identity(record):
                raise ValueError(f"conflicting STARTED records for episode {episode_id}")
            self.started_records[episode_id] = dict(record)
            return
        if record_type == "TERMINAL":
            evidence_kind = record.get("evidence_kind")
            if evidence_kind not in {"real_policy", "fixture"}:
                raise ValueError("TERMINAL evidence_kind must be real_policy or fixture")
            self._cell_identity(record, context="terminal record")
            self._check_run_identity(record, started=False)
            episode_id = record["episode_id"]
            started = self.started_records.get(episode_id)
            if started is not None and started.get("evidence_kind") != evidence_kind:
                raise ValueError("TERMINAL evidence_kind differs from STARTED record")
            previous = self.terminal_records.get(episode_id)
            current_identity = self._terminal_fingerprint(record)
            if previous is not None and self._terminal_fingerprint(previous) != current_identity:
                raise ValueError(f"conflicting terminal records for episode {episode_id}")
            self.terminal_records[episode_id] = dict(record)
            terminal_status = record.get("terminal_status")
            if terminal_status == "COMPLETE_POLICY":
                episode = record.get("episode")
                if not isinstance(episode, Mapping):
                    raise ValueError("COMPLETE_POLICY terminal record requires a nested episode")
                self._accept_episode(episode, record)
            elif terminal_status in {"REJECTED_SETUP", "INFRA_ERROR"}:
                if evidence_kind == "fixture":
                    self.excluded["fixture"] += 1
                else:
                    self._event("rejection" if terminal_status == "REJECTED_SETUP" else "failure", record, source=source)
            else:
                raise ValueError(f"invalid terminal status: {terminal_status!r}")
            return

        if record.get("evidence_kind") == "fixture":
            self.excluded["fixture"] += 1
            return

        if "episodes" in record:
            self._event_identity(record, context="report envelope")
            if "status" in record and record["status"] not in {"COMPLETE", "PARTIAL", "ERROR", "FAILED", "RUNNING"}:
                raise ValueError(f"invalid report status: {record['status']!r}")
            for field in ("errors", "rejections"):
                if field in record and not isinstance(record[field], list):
                    raise ValueError(f"report {field} must be a list")
            episodes = record["episodes"]
            if not isinstance(episodes, list):
                raise ValueError("report episodes must be a list")
            self._validate_report_counts(record, episodes)
            for episode in episodes:
                if isinstance(episode, Mapping):
                    # Envelopes may establish shared stage/hash identity.
                    for field in IDENTITY_FIELDS:
                        if field in record and field in episode and record[field] != episode[field]:
                            raise ValueError(f"report envelope identity mismatch for {field}")
                self.visit(episode, source=source)
            for item in record.get("rejections", []):
                self._child_event("rejection", item, record, source=source)
            for item in record.get("errors", []):
                self._child_event("failure", item, record, source=source)
            if record.get("status") in {"ERROR", "FAILED"} and not record.get("errors"):
                self._child_event("failure", record, record, source=source)
            elif record.get("status") == "PARTIAL":
                self._event("partial_report", record, source=source)
            return

        evidence_kind = record.get("evidence_kind")
        if evidence_kind is not None or "status" in record:
            if evidence_kind is None:
                raise ValueError("evidence_kind is required on completed episode records")
            if evidence_kind == "real_policy":
                if record.get("status") == "COMPLETE":
                    self._accept_episode(record)
                elif record.get("status") in {"ERROR", "FAILED", "PARTIAL", "RUNNING"} and (
                    "error" in record or "traceback" in record or "failure" in record
                    or not all(field in record for field in IDENTITY_FIELDS)
                ):
                    self._event_identity(record, context="failure record")
                    self._event(record["status"].lower(), record, source=source)
                else:
                    raise ValueError(f"invalid episode status: {record.get('status')!r}")
                return
            if evidence_kind == "commissioning":
                self.excluded["commissioning"] += 1
                return
            self.excluded["other"] += 1
            return
        if record.get("status") in {"ERROR", "FAILED", "PARTIAL", "RUNNING"} and "error" in record:
            self._event_identity(record, context="failure record")
            self._event(record["status"].lower(), record, source=source)
            return
        if "error" in record or "traceback" in record or record.get("terminal_status") in {"REJECTED_SETUP", "INFRA_ERROR"}:
            self._event_identity(record, context="failure record")
            self._event("failure", record, source=source)

    @staticmethod
    def _check_run_identity(record: Mapping[str, Any], *, started: bool) -> None:
        run_hash = record.get("run_config_sha256")
        if not isinstance(run_hash, str) or not SHA256_RE.fullmatch(run_hash):
            raise ValueError("record run_config_sha256 must be 64 lowercase hexadecimal characters")
        timestamp_field = "started_at_utc" if started else "finished_at_utc"
        _string(record.get(timestamp_field), timestamp_field)
        if started:
            prefix = f"req-{record['episode_id']}"
            if record.get("request_id_prefix") != prefix:
                raise ValueError("started request identity prefix differs")

    def _terminal_fingerprint(self, record: Mapping[str, Any]) -> str:
        normalized = dict(record)
        episode = record.get("episode")
        if isinstance(episode, Mapping) and episode.get("evidence_kind") == "real_policy":
            episode, _ = self._validate_episode(episode, context="terminal episode")
            normalized["episode"] = episode
        return _json_identity(normalized)

    def _resolve_starts(self) -> None:
        for episode_id, started in self.started_records.items():
            terminal = self.terminal_records.get(episode_id)
            if terminal is None:
                self._event("interrupted_started", started)
                continue
            for field in (*IDENTITY_FIELDS, "run_config_sha256", "evidence_kind"):
                if started.get(field) != terminal.get(field):
                    raise ValueError(f"terminal identity differs from STARTED record for {field}")

    def finish(self) -> tuple[dict[str, Any], dict[str, Any]]:
        official = copy.deepcopy(self.template)
        official["team_id"] = self.team_id
        coverage_cells = []
        remaining = []
        covered = 0
        remaining_total = 0
        total = 0
        for setting in ("clean", "randomized"):
            for task in self.tasks:
                attempts, successes = self.counts[setting][task]
                official["results"][setting][task] = {"attempts": int(attempts), "successes": int(successes)}
                left = max(0, self.target - attempts)
                total += attempts
                remaining_total += left
                covered += int(left == 0)
                cell = {"task": task, "setting": setting, "attempts": attempts,
                        "successes": successes, "target_episodes": self.target,
                        "remaining_episodes": left, "complete": left == 0}
                coverage_cells.append(cell)
                if left:
                    remaining.append({"task": task, "setting": setting, "attempts": attempts,
                                      "target_episodes": self.target, "remaining_episodes": left})
        status = "COMPLETE" if covered == 100 and not self.errors else "PARTIAL"
        report = {
            "schema_version": 1,
            "status": status,
            "team_id": self.team_id,
            "stage": self.stage,
            "checkpoint_manifest_sha256": self.expected_hash,
            "target_episodes_per_cell": self.target,
            "real_policy_episodes": total,
            "duplicate_records_deduplicated": self.duplicate_count,
            "excluded": self.excluded,
            "video_review_status_counts": dict(sorted(self.video_review_status_counts.items())),
            "coverage": {
                "cell_count": 100,
                "covered_cells": covered,
                "real_policy_episodes": total,
                "remaining_episodes": remaining_total,
                "cells": coverage_cells,
            },
            "remaining": remaining,
            "errors": self.errors,
        }
        return official, report


def aggregate_records(sources, official_template, expected_manifest_sha256, team_id,
                      target_episodes=100):
    """Aggregate completed real-policy episodes; return official counts and audit report.

    ``sources`` accepts episode records, terminal journal records, and report
    envelopes. Only validated ``evidence_kind=real_policy`` completed episodes
    affect the official result. Rejections, failures and interrupted starts are
    retained in the coverage report.
    """
    aggregator = _Aggregator(official_template, expected_manifest_sha256, team_id, target_episodes)
    if isinstance(sources, Mapping):
        sources = [sources]
    try:
        iterator = iter(sources)
    except TypeError as error:
        raise ValueError("sources must be an iterable of record objects") from error
    for source in iterator:
        aggregator.visit(source)
    aggregator._resolve_starts()
    return aggregator.finish()


def _read_source(path: Path) -> list[Any]:
    if path.is_dir():
        values = []
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in {".json", ".jsonl"}:
                values.extend(_read_source(child))
        return values
    if not path.is_file():
        raise ValueError(f"records path does not exist: {path}")
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        values = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            if line.strip():
                try:
                    values.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(f"invalid JSONL at {path}:{line_number}: {error}") from error
        return values
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error
    return value if isinstance(value, list) else [value]


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True, type=Path, help="JSON/JSONL file or terminal journal directory")
    parser.add_argument("--checkpoint-manifest-sha256", required=True)
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--output", required=True, type=Path, help="official-schema JSON output path")
    parser.add_argument("--template", type=Path, default=root / "official" / "results-template.json")
    args = parser.parse_args(argv)
    try:
        records = _read_source(args.records)
        template = json.loads(args.template.read_text(encoding="utf-8"))
        official, report = aggregate_records(
            records, template, args.checkpoint_manifest_sha256, args.team_id
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(official, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        sidecar = Path(str(args.output) + ".coverage.json")
        sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
