import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import CHECKPOINT_SHA, ROOT, episode, template
from aggregate_results import aggregate_records, request_id_for


class AggregationTests(unittest.TestCase):
    def aggregate(self, sources, **kwargs):
        options = dict(
            sources=sources,
            official_template=template(),
            expected_manifest_sha256=CHECKPOINT_SHA,
            team_id="fixture-team",
            target_episodes=100,
        )
        options.update(kwargs)
        return aggregate_records(**options)

    def test_true_and_false_policy_outcomes_count_as_official_attempts(self):
        true = episode(seed=100000, episode_id="episode-a", success=True)
        false = episode(seed=100001, episode_id="episode-b", success=False)
        official, report = self.aggregate([true, false])
        self.assertEqual({"attempts": 2, "successes": 1}, official["results"]["clean"]["lift_pot"])
        self.assertEqual(2, report["real_policy_episodes"])

    def test_numpy_boolean_success_is_accepted_when_numpy_is_available(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy is not installed")
        record = episode(success=np.bool_(True))
        official, _ = self.aggregate([record])
        self.assertEqual(1, official["results"]["clean"]["lift_pot"]["successes"])
        terminal = {
            "record_type": "TERMINAL", "evidence_kind": "real_policy",
            "terminal_status": "COMPLETE_POLICY",
            "run_config_sha256": "b" * 64, "finished_at_utc": "2026-10-22T00:00:00Z",
            **{field: record[field] for field in (
                "episode_id", "shard_id", "task", "setting", "stage", "scene_seed",
                "checkpoint_manifest_sha256",
            )},
            "episode": record,
        }
        _, terminal_report = self.aggregate([terminal, terminal])
        self.assertEqual(1, terminal_report["duplicate_records_deduplicated"])

    def test_identical_physical_episode_is_deduplicated_but_conflict_is_rejected(self):
        record = episode()
        official, report = self.aggregate([record, json.loads(json.dumps(record))])
        self.assertEqual(1, official["results"]["clean"]["lift_pot"]["attempts"])
        self.assertEqual(1, report["duplicate_records_deduplicated"])
        conflicting = dict(record, task_success=False, task_predicate=False, actions_started=50)
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            self.aggregate([record, conflicting])

    def test_request_identity_cannot_be_reused_by_another_episode(self):
        first = episode(seed=100000, episode_id="episode-a")
        second = episode(seed=100001, episode_id="episode-b")
        second["requests"][0]["request_id"] = first["requests"][0]["request_id"]
        with self.assertRaisesRegex(ValueError, "request identity"):
            self.aggregate([first, second])

    def test_request_ids_use_the_runner_namespace_exactly(self):
        self.assertEqual("req-ep-abc-chunk-0007", request_id_for("ep-abc", 7))

    def test_coverage_reports_all_one_hundred_cells_and_remaining_targets(self):
        _, report = self.aggregate([episode()], target_episodes=2)
        self.assertEqual(100, report["coverage"]["cell_count"])
        self.assertEqual(0, report["coverage"]["covered_cells"])
        self.assertEqual(199, report["coverage"]["remaining_episodes"])
        self.assertEqual(100, len(report["remaining"]))

    def test_terminal_journal_counts_only_complete_policy_episode(self):
        completed = episode()
        terminal = {
            "record_type": "TERMINAL",
            "evidence_kind": "real_policy",
            "terminal_status": "COMPLETE_POLICY",
            "run_config_sha256": "b" * 64,
            "finished_at_utc": "2026-10-22T00:00:00Z",
            "episode_id": completed["episode_id"],
            "shard_id": completed["shard_id"],
            "task": completed["task"],
            "setting": completed["setting"],
            "stage": completed["stage"],
            "scene_seed": completed["scene_seed"],
            "checkpoint_manifest_sha256": completed["checkpoint_manifest_sha256"],
            "episode": completed,
        }
        rejected = dict(terminal, terminal_status="REJECTED_SETUP", episode=None,
                        episode_id="ep-rejected", scene_seed=100001,
                        rejection={"category": "UNSTABLE_SETUP"})
        official, report = self.aggregate([terminal, rejected])
        self.assertEqual(1, official["results"]["clean"]["lift_pot"]["attempts"])
        self.assertEqual(1, report["real_policy_episodes"])
        self.assertEqual(1, len(report["errors"]))

    def test_terminal_identity_must_match_nested_completed_episode(self):
        completed = episode()
        terminal = {
            "record_type": "TERMINAL", "evidence_kind": "real_policy",
            "terminal_status": "COMPLETE_POLICY",
            "run_config_sha256": "b" * 64, "finished_at_utc": "2026-10-22T00:00:00Z",
            "episode_id": completed["episode_id"], "shard_id": completed["shard_id"],
            "task": completed["task"], "setting": completed["setting"],
            "stage": completed["stage"], "scene_seed": completed["scene_seed"],
            "checkpoint_manifest_sha256": completed["checkpoint_manifest_sha256"],
            "episode": dict(completed, scene_seed=completed["scene_seed"] + 1),
        }
        with self.assertRaisesRegex(ValueError, "terminal identity"):
            self.aggregate([terminal])

    def test_complete_and_failure_terminals_for_one_episode_are_conflicting(self):
        completed = episode()
        terminal = {
            "record_type": "TERMINAL", "evidence_kind": "real_policy",
            "terminal_status": "COMPLETE_POLICY",
            "run_config_sha256": "b" * 64, "finished_at_utc": "2026-10-22T00:00:00Z",
            "episode_id": completed["episode_id"], "shard_id": completed["shard_id"],
            "task": completed["task"], "setting": completed["setting"],
            "stage": completed["stage"], "scene_seed": completed["scene_seed"],
            "checkpoint_manifest_sha256": completed["checkpoint_manifest_sha256"],
            "episode": completed,
        }
        failure = dict(terminal, terminal_status="INFRA_ERROR", episode=None,
                       error={"message": "contradictory terminal"})
        with self.assertRaisesRegex(ValueError, "conflicting terminal"):
            self.aggregate([terminal, failure])

    def test_matching_started_and_terminal_records_are_not_reported_as_interrupted(self):
        completed = episode(episode_id="ep-paired")
        started = {
            "record_type": "STARTED", "evidence_kind": "real_policy",
            "run_config_sha256": "b" * 64,
            "started_at_utc": "2026-10-22T00:00:00Z", "request_id_prefix": "req-ep-paired",
            "episode_id": completed["episode_id"], "shard_id": completed["shard_id"],
            "task": completed["task"], "setting": completed["setting"],
            "stage": completed["stage"], "scene_seed": completed["scene_seed"],
            "checkpoint_manifest_sha256": completed["checkpoint_manifest_sha256"],
        }
        terminal = {
            "record_type": "TERMINAL", "evidence_kind": "real_policy",
            "terminal_status": "COMPLETE_POLICY",
            "run_config_sha256": "b" * 64, "finished_at_utc": "2026-10-22T00:01:00Z",
            **{field: completed[field] for field in (
                "episode_id", "shard_id", "task", "setting", "stage", "scene_seed",
                "checkpoint_manifest_sha256",
            )},
            "episode": completed,
        }
        _, report = self.aggregate([started, terminal])
        self.assertEqual([], report["errors"])

    def test_fixture_started_terminal_pair_is_excluded_and_cannot_be_upgraded(self):
        completed = episode(episode_id="ep-fixture-paired")
        completed["evidence_kind"] = "fixture"
        completed["video_path"] = None
        completed["video_review_status"] = "NOT_REVIEWED"
        started = {
            "record_type": "STARTED", "evidence_kind": "fixture",
            "run_config_sha256": "b" * 64,
            "started_at_utc": "2026-10-22T00:00:00Z",
            "request_id_prefix": "req-ep-fixture-paired",
            **{field: completed[field] for field in (
                "episode_id", "shard_id", "task", "setting", "stage", "scene_seed",
                "checkpoint_manifest_sha256",
            )},
        }
        terminal = {
            "record_type": "TERMINAL", "evidence_kind": "fixture",
            "terminal_status": "COMPLETE_POLICY",
            "run_config_sha256": "b" * 64,
            "finished_at_utc": "2026-10-22T00:01:00Z",
            **{field: completed[field] for field in (
                "episode_id", "shard_id", "task", "setting", "stage", "scene_seed",
                "checkpoint_manifest_sha256",
            )},
            "episode": completed,
        }
        for records in ([started, terminal], [terminal, started]):
            with self.subTest(order="started-first" if records[0] is started else "terminal-first"):
                official, report = self.aggregate(records)
                self.assertEqual(0, official["results"]["clean"]["lift_pot"]["attempts"])
                self.assertEqual(0, report["real_policy_episodes"])
                self.assertEqual(1, report["excluded"]["fixture"])
                self.assertEqual(0, report["excluded"]["commissioning"])
                self.assertEqual([], report["errors"])

        upgraded_terminal = dict(terminal, evidence_kind="real_policy",
                                 episode=dict(completed, evidence_kind="real_policy"))
        for records in ([started, upgraded_terminal], [upgraded_terminal, started]):
            with self.subTest(order="started-first" if records[0] is started else "terminal-first"):
                with self.assertRaisesRegex(ValueError, "evidence_kind"):
                    self.aggregate(records)

    def test_parent_cell_identity_cannot_conflict_with_completed_child(self):
        record = episode()
        conflicts = {
            "task": "hanging_mug", "setting": "randomized", "scene_seed": 100001,
            "episode_id": "ep-parent", "shard_id": "another-shard",
        }
        for field, value in conflicts.items():
            with self.subTest(field=field):
                envelope = {"status": "ERROR", "stage": "baseline",
                            "checkpoint_manifest_sha256": CHECKPOINT_SHA,
                            "episodes": [record], "errors": [], field: value}
                with self.assertRaisesRegex(ValueError, f"envelope identity mismatch for {field}"):
                    self.aggregate([envelope])

    def test_nested_real_policy_errors_must_match_parent_identity(self):
        envelope = {
            "evidence_kind": "real_policy", "status": "PARTIAL",
            "stage": "baseline", "checkpoint_manifest_sha256": CHECKPOINT_SHA,
            "episodes": [], "errors": [{"stage": "candidate",
                                           "checkpoint_manifest_sha256": CHECKPOINT_SHA,
                                           "evidence_kind": "real_policy", "message": "mixed"}],
        }
        with self.assertRaisesRegex(ValueError, "envelope identity mismatch for stage"):
            self.aggregate([envelope])
        envelope["errors"][0]["stage"] = "baseline"
        envelope["errors"][0]["checkpoint_manifest_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "envelope identity mismatch for checkpoint_manifest_sha256"):
            self.aggregate([envelope])
        envelope["errors"] = []
        envelope["rejections"] = [{"evidence_kind": "real_policy", "stage": "candidate",
                                    "checkpoint_manifest_sha256": CHECKPOINT_SHA,
                                    "episode_id": "ep-rejected", "task": "lift_pot",
                                    "setting": "clean", "scene_seed": 100000,
                                    "shard_id": "baseline-clean-lift_pot"}]
        with self.assertRaisesRegex(ValueError, "envelope identity mismatch for stage"):
            self.aggregate([envelope])

    def test_report_status_and_nested_official_counts_are_validated(self):
        with self.assertRaisesRegex(ValueError, "report status"):
            self.aggregate([{"status": "TYPO", "stage": "baseline",
                             "checkpoint_manifest_sha256": CHECKPOINT_SHA, "episodes": []}])
        malformed_results = template()["results"]
        malformed_results["clean"]["lift_pot"] = {"attempts": -1, "successes": 999}
        envelope = {"status": "PARTIAL", "stage": "baseline",
                    "checkpoint_manifest_sha256": CHECKPOINT_SHA,
                    "episodes": [], "results": malformed_results}
        with self.assertRaisesRegex(ValueError, "attempts"):
            self.aggregate([envelope])
        envelope = {"status": "PARTIAL", "stage": "baseline",
                    "checkpoint_manifest_sha256": CHECKPOINT_SHA, "episodes": [episode()],
                    "attempts": -1, "successes": 999}
        with self.assertRaisesRegex(ValueError, "attempts"):
            self.aggregate([envelope])
        envelope = {"status": "PARTIAL", "stage": "baseline",
                    "checkpoint_manifest_sha256": CHECKPOINT_SHA, "episodes": [episode()],
                    "results": template()["results"]}
        with self.assertRaisesRegex(ValueError, "disagree with completed episodes"):
            self.aggregate([envelope])

    def test_real_policy_error_requires_non_null_valid_stage_and_manifest(self):
        malformed = {"evidence_kind": "real_policy", "status": "ERROR",
                     "stage": None, "checkpoint_manifest_sha256": None, "error": "boom"}
        with self.assertRaisesRegex(ValueError, "invalid stage"):
            self.aggregate([malformed])

    def test_unreviewed_video_can_be_null_only_with_explicit_status(self):
        record = episode()
        record["video_path"] = None
        with self.assertRaisesRegex(ValueError, "NOT_REVIEWED"):
            self.aggregate([record])
        record["video_review_status"] = "NOT_REVIEWED"
        _, report = self.aggregate([record])
        self.assertEqual({"NOT_REVIEWED": 1}, report["video_review_status_counts"])

    def test_rejections_and_unresolved_starts_are_coverage_errors_not_attempts(self):
        rejected = {
            "record_type": "TERMINAL", "evidence_kind": "real_policy",
            "terminal_status": "REJECTED_SETUP",
            "run_config_sha256": "b" * 64, "finished_at_utc": "2026-10-22T00:00:00Z",
            "episode_id": "ep-rejected", "shard_id": "baseline-clean-lift_pot",
            "task": "lift_pot", "setting": "clean",
            "stage": "baseline", "scene_seed": 100000,
            "checkpoint_manifest_sha256": CHECKPOINT_SHA,
            "rejection": {"category": "EXPERT_UNSOLVED"},
        }
        started = {
            "record_type": "STARTED", "evidence_kind": "real_policy",
            "run_config_sha256": "b" * 64,
            "started_at_utc": "2026-10-22T00:00:00Z", "request_id_prefix": "req-ep-interrupted",
            "episode_id": "ep-interrupted", "shard_id": "baseline-clean-lift_pot",
            "task": "lift_pot", "setting": "clean", "stage": "baseline",
            "scene_seed": 100001, "checkpoint_manifest_sha256": CHECKPOINT_SHA,
        }
        official, report = self.aggregate([rejected, started])
        self.assertEqual(0, official["results"]["clean"]["lift_pot"]["attempts"])
        self.assertEqual(0, report["real_policy_episodes"])
        self.assertEqual(2, len(report["errors"]))
        self.assertEqual(10000, report["coverage"]["remaining_episodes"])

    def test_counted_episode_requires_finite_numeric_fields_and_canonical_request_list(self):
        malformed = episode()
        malformed["wall_seconds"] = float("inf")
        with self.assertRaisesRegex(ValueError, "wall_seconds"):
            self.aggregate([malformed])
        malformed = episode()
        malformed["scene_seed"] = True
        with self.assertRaisesRegex(ValueError, "scene_seed"):
            self.aggregate([malformed])
        malformed = episode()
        malformed["requests"][0]["request_id"] = "caller-chosen"
        with self.assertRaisesRegex(ValueError, "request identity"):
            self.aggregate([malformed])

    def test_invalid_terminal_status_and_success_boolean_fail_closed(self):
        malformed = episode()
        malformed["status"] = "ERROR"
        with self.assertRaisesRegex(ValueError, "status"):
            self.aggregate([malformed])
        malformed = episode()
        malformed["task_success"] = 1
        malformed["task_predicate"] = 1
        with self.assertRaisesRegex(ValueError, "boolean"):
            self.aggregate([malformed])

    def test_cli_reads_terminal_json_directory_and_writes_official_and_sidecar(self):
        completed = episode()
        terminal = {
            "record_type": "TERMINAL", "evidence_kind": "real_policy",
            "terminal_status": "COMPLETE_POLICY",
            "run_config_sha256": "b" * 64, "finished_at_utc": "2026-10-22T00:00:00Z",
            "episode_id": completed["episode_id"], "shard_id": completed["shard_id"],
            "task": completed["task"], "setting": completed["setting"],
            "stage": completed["stage"], "scene_seed": completed["scene_seed"],
            "checkpoint_manifest_sha256": completed["checkpoint_manifest_sha256"],
            "episode": completed,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            journal = root / "records"
            journal.mkdir()
            (journal / "one.terminal.json").write_text(json.dumps(terminal), encoding="utf-8")
            started = {
                "record_type": "STARTED", "evidence_kind": "real_policy",
                "run_config_sha256": "b" * 64,
                "started_at_utc": "2026-10-22T00:00:00Z", "request_id_prefix": "req-ep-open",
                "episode_id": "ep-open", "shard_id": "baseline-clean-lift_pot",
                "task": "lift_pot", "setting": "clean", "stage": "baseline",
                "scene_seed": 100001, "checkpoint_manifest_sha256": CHECKPOINT_SHA,
            }
            (journal / "events.jsonl").write_text(json.dumps(started) + "\n", encoding="utf-8")
            output = root / "official.json"
            command = [
                sys.executable, str(Path(__file__).resolve().parents[1] / "aggregate_results.py"),
                "--records", str(journal), "--checkpoint-manifest-sha256", CHECKPOINT_SHA,
                "--team-id", "fixture-team", "--output", str(output),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            official = json.loads(output.read_text(encoding="utf-8"))
            sidecar = json.loads(Path(str(output) + ".coverage.json").read_text(encoding="utf-8"))
            self.assertEqual({"schema_version", "team_id", "results"}, set(official))
            self.assertEqual(1, official["results"]["clean"]["lift_pot"]["attempts"])
            self.assertEqual(1, sidecar["real_policy_episodes"])
            self.assertEqual(1, len(sidecar["errors"]))

    def test_hash_stage_task_setting_and_malformed_counts_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "manifest SHA"):
            self.aggregate([episode(manifest_sha="b" * 64)])
        with self.assertRaisesRegex(ValueError, "mixed stage"):
            self.aggregate([episode(), episode(seed=100001, episode_id="episode-b", stage="candidate")])
        with self.assertRaisesRegex(ValueError, "unknown task"):
            self.aggregate([episode(task="not_an_official_task")])
        with self.assertRaisesRegex(ValueError, "setting"):
            self.aggregate([episode(setting="preview")])
        malformed = episode()
        malformed["actions_started"] = True
        with self.assertRaisesRegex(ValueError, "actions_started"):
            self.aggregate([malformed])

    def test_partial_error_envelope_keeps_its_completed_episode(self):
        completed = episode()
        envelope = {
            "status": "ERROR",
            "stage": "baseline",
            "episodes": [completed],
            "errors": [{"kind": "INFRA_ERROR", "message": "later shard failed"}],
        }
        official, report = self.aggregate([envelope])
        self.assertEqual(1, official["results"]["clean"]["lift_pot"]["attempts"])
        self.assertEqual(1, report["real_policy_episodes"])
        self.assertEqual("PARTIAL", report["status"])

    def test_fixtures_and_real_commissioning_example_are_excluded(self):
        fixture = episode(episode_id="fixture-episode")
        fixture["evidence_kind"] = "fixture"
        commission = json.loads((ROOT / "reference" / "commission-negative-example.json").read_text(encoding="utf-8"))
        official, report = self.aggregate([fixture, commission])
        self.assertEqual(0, report["real_policy_episodes"])
        self.assertEqual(0, official["results"]["clean"]["lift_pot"]["attempts"])
        self.assertEqual(1, report["excluded"]["fixture"])
        self.assertEqual(1, report["excluded"]["commissioning"])

    def test_missing_real_evidence_kind_and_wrong_official_predicate_are_rejected(self):
        record = episode()
        del record["evidence_kind"]
        with self.assertRaisesRegex(ValueError, "evidence_kind"):
            self.aggregate([record])
        record = episode()
        record["task_predicate"] = False
        with self.assertRaisesRegex(ValueError, "predicate"):
            self.aggregate([record])


if __name__ == "__main__":
    unittest.main()
