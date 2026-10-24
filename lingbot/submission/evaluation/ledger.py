"""Exclusive immutable JSON ledger for one serial evaluation run."""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile


def _json_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"ledger data is not finite JSON: {error}") from error
    return (rendered + "\n").encode("utf-8")


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"ledger record must be a JSON object: {path}")
    return value


def _exclusive_atomic_write(path: Path, value: object) -> None:
    """Write a complete temp file, then atomically link it without replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".pending-", delete=False) as stream:
            temporary_name = stream.name
            stream.write(_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_name, path)
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


class EvaluationLedger:
    def __init__(self, root: str | Path, run_config: dict):
        self.root = Path(root)
        self.run_config = json.loads(_json_bytes(run_config))
        self.run_config_sha256 = hashlib.sha256(_json_bytes(self.run_config)).hexdigest()
        self.records_dir = self.root / "records"
        self.metadata_dir = self.root / "metadata"

    def initialize(self, *, resume: bool) -> None:
        config_path = self.root / "run-config.json"
        if resume:
            if not config_path.is_file():
                raise ValueError("resume requires an existing run configuration")
            saved = _read_json(config_path)
            if saved != self.run_config:
                raise ValueError("run configuration differs from the immutable saved configuration")
            self.records_dir.mkdir(parents=True, exist_ok=True)
            self.metadata_dir.mkdir(parents=True, exist_ok=True)
            return
        self.root.mkdir(parents=True, exist_ok=True)
        if config_path.exists():
            raise FileExistsError("run configuration already exists; use --resume")
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        _exclusive_atomic_write(config_path, self.run_config)

    @contextlib.contextmanager
    def lock(self):
        lock_path = self.root / ".run.lock"
        payload = f"pid={os.getpid()}\ncreated_utc={dt.datetime.now(dt.timezone.utc).isoformat()}\n".encode()
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
            yield
        finally:
            os.close(descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _file_id(episode_id: str) -> str:
        if not isinstance(episode_id, str) or not episode_id or Path(episode_id).name != episode_id:
            raise ValueError("unsafe or empty episode_id")
        return episode_id

    def begin(self, identity: dict) -> Path:
        episode_id = self._file_id(identity.get("episode_id"))
        if "record_type" in identity or "started_at_utc" in identity or "run_config_sha256" in identity:
            raise ValueError("STARTED identity cannot override ledger-owned metadata")
        self._validate_configured_identity(identity, "STARTED")
        started_path = self.records_dir / f"{episode_id}.started.json"
        terminal_path = self.records_dir / f"{episode_id}.terminal.json"
        if terminal_path.exists():
            raise FileExistsError(f"episode already has a terminal record: {episode_id}")
        record = dict(identity)
        record.update({
            "record_type": "STARTED",
            "episode_id": episode_id,
            "run_config_sha256": self.run_config_sha256,
            "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        record["record_sha256"] = self._record_sha256(record)
        _exclusive_atomic_write(started_path, record)
        return started_path

    def finish(self, episode_id: str, terminal: dict) -> Path:
        episode_id = self._file_id(episode_id)
        started_path = self.records_dir / f"{episode_id}.started.json"
        if not started_path.is_file():
            raise ValueError(f"cannot finish an episode that was not started: {episode_id}")
        started = _read_json(started_path)
        self._validate_started(started_path, started)
        if started.get("episode_id") != episode_id:
            raise ValueError("STARTED identity differs from its filename")
        if "record_type" in terminal or "finished_at_utc" in terminal or "run_config_sha256" in terminal:
            raise ValueError("terminal payload cannot override ledger-owned metadata")
        if terminal.get("episode_id", episode_id) != episode_id:
            raise ValueError("terminal episode_id differs from STARTED identity")
        if "evidence_kind" in started and terminal.get("evidence_kind") != started["evidence_kind"]:
            raise ValueError("terminal evidence_kind differs from STARTED identity")
        identity_fields = ("episode_id", "shard_id", "task", "setting", "stage", "scene_seed", "checkpoint_manifest_sha256")
        for field in identity_fields:
            if field in terminal and field in started and terminal[field] != started[field]:
                raise ValueError(f"terminal {field} differs from STARTED identity")
        episode = terminal.get("episode")
        if episode is not None:
            if not isinstance(episode, dict):
                raise ValueError("terminal episode must be a JSON object")
            for field in identity_fields:
                if field in started and episode.get(field) != started[field]:
                    raise ValueError(f"terminal episode {field} differs from STARTED identity")
            if "evidence_kind" in started and episode.get("evidence_kind") != started["evidence_kind"]:
                raise ValueError("terminal episode evidence_kind differs from STARTED identity")
        terminal_path = self.records_dir / f"{episode_id}.terminal.json"
        wrapped = dict(terminal)
        wrapped.update({key: started[key] for key in identity_fields if key in started})
        if "evidence_kind" in started:
            wrapped["evidence_kind"] = started["evidence_kind"]
        wrapped.update({
            "record_type": "TERMINAL",
            "episode_id": episode_id,
            "run_config_sha256": self.run_config_sha256,
            "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        wrapped["record_sha256"] = self._record_sha256(wrapped)
        _exclusive_atomic_write(terminal_path, wrapped)
        return terminal_path

    @staticmethod
    def _record_sha256(record: dict) -> str:
        payload = dict(record)
        payload.pop("record_sha256", None)
        return hashlib.sha256(_json_bytes(payload)).hexdigest()

    def _validate_started(self, path: Path, record: dict) -> None:
        episode_id = path.name.removesuffix(".started.json")
        if record.get("record_type") != "STARTED" or record.get("episode_id") != episode_id:
            raise ValueError(f"STARTED record identity differs from filename: {path.name}")
        if record.get("run_config_sha256") != self.run_config_sha256:
            raise ValueError(f"STARTED record configuration SHA mismatch: {path.name}")
        if record.get("record_sha256") != self._record_sha256(record):
            raise ValueError(f"STARTED record integrity SHA mismatch: {path.name}")
        self._validate_configured_identity(record, f"STARTED record {path.name}")

    def _validate_configured_identity(self, record: dict, label: str) -> None:
        expected = {}
        if "evidence_kind" in self.run_config:
            expected["evidence_kind"] = self.run_config["evidence_kind"]
        plan = self.run_config.get("plan")
        if isinstance(plan, dict):
            for field in ("stage", "checkpoint_manifest_sha256"):
                if field in plan:
                    expected[field] = plan[field]
        for field, value in expected.items():
            if record.get(field) != value:
                raise ValueError(f"{label} {field} differs from immutable run configuration")

    def started_records(self) -> list[dict]:
        records = []
        for path in sorted(self.records_dir.glob("*.started.json")):
            record = _read_json(path)
            self._validate_started(path, record)
            records.append(record)
        return records

    def terminal_records(self) -> list[dict]:
        starts = {record["episode_id"]: record for record in self.started_records()}
        records = []
        identity_fields = ("episode_id", "shard_id", "task", "setting", "stage", "scene_seed", "checkpoint_manifest_sha256")
        for path in sorted(self.records_dir.glob("*.terminal.json")):
            record = _read_json(path)
            episode_id = path.name.removesuffix(".terminal.json")
            if record.get("record_type") != "TERMINAL" or record.get("episode_id") != episode_id:
                raise ValueError(f"TERMINAL record identity differs from filename: {path.name}")
            if record.get("run_config_sha256") != self.run_config_sha256:
                raise ValueError(f"TERMINAL record configuration SHA mismatch: {path.name}")
            if record.get("record_sha256") != self._record_sha256(record):
                raise ValueError(f"TERMINAL record integrity SHA mismatch: {path.name}")
            if episode_id not in starts:
                raise ValueError(f"TERMINAL record has no STARTED record: {path.name}")
            started = starts[episode_id]
            for field in identity_fields:
                if field in started and record.get(field) != started[field]:
                    raise ValueError(f"TERMINAL {field} differs from STARTED identity: {path.name}")
            if "evidence_kind" in started and record.get("evidence_kind") != started["evidence_kind"]:
                raise ValueError(f"TERMINAL evidence_kind differs from STARTED identity: {path.name}")
            episode = record.get("episode")
            if episode is not None:
                if not isinstance(episode, dict):
                    raise ValueError(f"TERMINAL episode is not an object: {path.name}")
                for field in identity_fields:
                    if field in started and episode.get(field) != started[field]:
                        raise ValueError(f"TERMINAL episode {field} differs from STARTED identity: {path.name}")
                if "evidence_kind" in started and episode.get("evidence_kind") != started["evidence_kind"]:
                    raise ValueError(f"TERMINAL episode evidence_kind differs from STARTED identity: {path.name}")
            records.append(record)
        return records

    def unresolved_started(self) -> list[dict]:
        terminal_ids = {item.get("episode_id") for item in self.terminal_records()}
        return [item for item in self.started_records() if item.get("episode_id") not in terminal_ids]

    def _scope_started_at(self, scope: str, scope_id: str) -> dt.datetime:
        safe_id = self._file_id(scope_id)
        path = self.metadata_dir / f"{scope}-{safe_id}.started.json"
        if path.exists():
            record = _read_json(path)
            if (record.get("record_type") != "SCOPE_STARTED"
                    or record.get("scope") != scope
                    or record.get("scope_id") != safe_id
                    or record.get("run_config_sha256") != self.run_config_sha256):
                raise ValueError(f"{scope} start metadata identity mismatch: {path.name}")
        else:
            record = {
                "record_type": "SCOPE_STARTED",
                "scope": scope,
                "scope_id": safe_id,
                "run_config_sha256": self.run_config_sha256,
                "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            _exclusive_atomic_write(path, record)
        value = dt.datetime.fromisoformat(record["started_at_utc"])
        if value.tzinfo is None:
            raise ValueError(f"{scope} start time must include a timezone")
        return value

    def stage_started_at(self) -> dt.datetime:
        return self._scope_started_at("stage", "stage")

    def cell_started_at(self, shard_id: str) -> dt.datetime:
        return self._scope_started_at("cell", shard_id)
