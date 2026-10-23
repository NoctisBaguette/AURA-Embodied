import json
import tempfile
import unittest
from pathlib import Path

from support import CHECKPOINT_SHA
from ledger import EvaluationLedger


class LedgerTests(unittest.TestCase):
    def test_started_and_terminal_records_are_exclusive_and_immutable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            ledger = EvaluationLedger(root, {"stage": "baseline", "seed_start": 100000})
            ledger.initialize(resume=False)
            start = {"episode_id": "episode-a", "shard_id": "cell-a", "scene_seed": 100000}
            ledger.begin(start)
            started_path = root / "records" / "episode-a.started.json"
            self.assertTrue(started_path.is_file())
            ledger.finish("episode-a", {"terminal_status": "REJECTED_SETUP", "category": "EXPERT_UNSOLVED"})
            terminal_path = root / "records" / "episode-a.terminal.json"
            before = terminal_path.read_bytes()
            with self.assertRaises(FileExistsError):
                ledger.finish("episode-a", {"terminal_status": "COMPLETE_POLICY"})
            self.assertEqual(before, terminal_path.read_bytes())

    def test_resume_rejects_changed_run_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            original = {
                "stage": "baseline", "seed_start": 100000,
                "backend_command": ["python", "adapter.py"],
                "cell_timeout_seconds": 7200,
                "stage_timeout_seconds": 259200,
            }
            EvaluationLedger(root, original).initialize(resume=False)
            changes = (
                {**original, "stage": "candidate"},
                {**original, "backend_command": ["python", "other_adapter.py"]},
                {**original, "cell_timeout_seconds": 3600},
                {**original, "stage_timeout_seconds": 86400},
            )
            for config in changes:
                with self.subTest(config=config):
                    changed = EvaluationLedger(root, config)
                    with self.assertRaisesRegex(ValueError, "configuration"):
                        changed.initialize(resume=True)

    def test_unresolved_start_is_reported_and_never_given_a_second_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            ledger = EvaluationLedger(root, {"stage": "baseline"})
            ledger.initialize(resume=False)
            ledger.begin({"episode_id": "episode-a", "shard_id": "cell-a", "scene_seed": 100000})
            self.assertEqual(["episode-a"], [item["episode_id"] for item in ledger.unresolved_started()])
            with self.assertRaises(FileExistsError):
                ledger.begin({"episode_id": "episode-a", "shard_id": "cell-a", "scene_seed": 100000})

    def test_run_lock_excludes_a_second_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            first = EvaluationLedger(root, {"stage": "baseline"})
            first.initialize(resume=False)
            second = EvaluationLedger(root, {"stage": "baseline"})
            with first.lock():
                with self.assertRaises(FileExistsError):
                    with second.lock():
                        pass

    def test_terminal_episode_identity_must_match_its_started_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            ledger = EvaluationLedger(root, {"stage": "baseline", "checkpoint_manifest_sha256": CHECKPOINT_SHA})
            ledger.initialize(resume=False)
            identity = {
                "episode_id": "episode-a", "shard_id": "shard-a", "task": "lift_pot",
                "setting": "clean", "stage": "baseline", "scene_seed": 100000,
                "checkpoint_manifest_sha256": CHECKPOINT_SHA,
            }
            ledger.begin(identity)
            wrong = {**identity, "scene_seed": 100001}
            with self.assertRaisesRegex(ValueError, "STARTED identity"):
                ledger.finish("episode-a", {"terminal_status": "COMPLETE_POLICY", "episode": wrong})

    def test_terminal_and_nested_episode_cannot_relabel_fixture_as_real_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            ledger = EvaluationLedger(root, {"stage": "baseline"})
            ledger.initialize(resume=False)
            identity = {
                "evidence_kind": "fixture", "episode_id": "episode-a", "shard_id": "shard-a",
                "task": "lift_pot", "setting": "clean", "stage": "baseline", "scene_seed": 100000,
                "checkpoint_manifest_sha256": CHECKPOINT_SHA,
            }
            ledger.begin(identity)
            episode = {**identity, "evidence_kind": "real_policy"}
            with self.assertRaisesRegex(ValueError, "evidence_kind"):
                ledger.finish("episode-a", {
                    "terminal_status": "COMPLETE_POLICY", "evidence_kind": "real_policy", "episode": episode,
                })
            with self.assertRaisesRegex(ValueError, "episode evidence_kind"):
                ledger.finish("episode-a", {
                    "terminal_status": "COMPLETE_POLICY", "evidence_kind": "fixture", "episode": episode,
                })

    def test_started_identity_must_match_configured_evidence_kind_stage_and_manifest_on_write(self):
        config = {
            "evidence_kind": "fixture",
            "plan": {"stage": "baseline", "checkpoint_manifest_sha256": CHECKPOINT_SHA},
        }
        invalid = {
            "evidence_kind": "real_policy",
            "stage": "candidate",
            "checkpoint_manifest_sha256": "b" * 64,
        }
        for field, value in invalid.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                ledger = EvaluationLedger(Path(temporary) / "run", config)
                ledger.initialize(resume=False)
                identity = {
                    "evidence_kind": "fixture", "stage": "baseline",
                    "checkpoint_manifest_sha256": CHECKPOINT_SHA,
                    "episode_id": "episode-a", "shard_id": "shard-a",
                    "task": "lift_pot", "setting": "clean", "scene_seed": 100000,
                }
                identity[field] = value
                with self.assertRaisesRegex(ValueError, field):
                    ledger.begin(identity)

    def test_started_reader_rejects_configured_evidence_kind_stage_and_manifest_mismatch(self):
        config = {
            "evidence_kind": "fixture",
            "plan": {"stage": "baseline", "checkpoint_manifest_sha256": CHECKPOINT_SHA},
        }
        invalid = {
            "evidence_kind": "real_policy",
            "stage": "candidate",
            "checkpoint_manifest_sha256": "b" * 64,
        }
        for field, value in invalid.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                ledger = EvaluationLedger(Path(temporary) / "run", config)
                ledger.initialize(resume=False)
                identity = {
                    "evidence_kind": "fixture", "stage": "baseline",
                    "checkpoint_manifest_sha256": CHECKPOINT_SHA,
                    "episode_id": "episode-a", "shard_id": "shard-a",
                    "task": "lift_pot", "setting": "clean", "scene_seed": 100000,
                }
                path = ledger.begin(identity)
                record = json.loads(path.read_text(encoding="utf-8"))
                record[field] = value
                record["record_sha256"] = ledger._record_sha256(record)
                path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, field):
                    ledger.started_records()

    def test_resume_reader_rejects_tampered_started_filename_or_config_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            ledger = EvaluationLedger(root, {"stage": "baseline"})
            ledger.initialize(resume=False)
            ledger.begin({"episode_id": "episode-a", "shard_id": "cell-a", "scene_seed": 100000})
            started_path = root / "records" / "episode-a.started.json"
            value = json.loads(started_path.read_text(encoding="utf-8"))
            value["episode_id"] = "episode-b"
            started_path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "filename|configuration SHA|integrity SHA"):
                ledger.started_records()


if __name__ == "__main__":
    unittest.main()
