import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from support import CHECKPOINT_SHA, EVALUATION, TEMPLATE_PATH
from evaluate import SerialEvaluator, SubprocessBackend, build_plan, load_tasks


FAKE_BACKEND = Path(__file__).with_name("fake_backend.py")


def one_cell_plan(output_dir, *, stage="baseline"):
    return build_plan(
        tasks=load_tasks(TEMPLATE_PATH),
        selected_tasks=["lift_pot"],
        setting="clean",
        episodes=1,
        max_candidates=2,
        seed_start=100000,
        manifest_sha256=CHECKPOINT_SHA,
        stage=stage,
        output_dir=output_dir,
    )


class RunnerTests(unittest.TestCase):
    def make_evaluator(self, temp, mode, *, stage="baseline", timeout=5):
        root = Path(temp)
        counter = root / "backend-count.txt"
        command = [sys.executable, str(FAKE_BACKEND), mode, str(counter)]
        plan = one_cell_plan(root / "run", stage=stage)
        runner = SerialEvaluator(
            plan=plan,
            output_dir=root / "run",
            policy_package="TEST_FIXTURE_ONLY",
            backend_command=command,
            episode_timeout_seconds=timeout,
            cell_timeout_seconds=30,
            stage_timeout_seconds=60,
            test_only_fixture=True,
        )
        return runner, counter

    def test_typed_scene_rejection_advances_then_resume_skips_completed_episode(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "typed_then_success")
            first = runner.run(resume=False)
            self.assertEqual("fixture", first["evidence_kind"])
            self.assertEqual(0, first["real_policy_episodes"])
            self.assertEqual(1, first["completed_episodes"])
            self.assertEqual(1, len(first["rejections"]))
            self.assertEqual("EXPERT_UNSOLVED", first["rejections"][0]["category"])
            self.assertEqual("2", counter.read_text(encoding="utf-8"))
            terminal = runner.ledger.terminal_records()
            self.assertEqual(["REJECTED_SETUP", "COMPLETE_POLICY"], [r["terminal_status"] for r in terminal])
            saved_logs = {}
            for item in terminal:
                evidence = item["execution_evidence"]
                for name in ("backend_stdout_path", "backend_stderr_path"):
                    path = Path(evidence[name])
                    self.assertTrue(path.is_file())
                    self.assertEqual(Path(evidence["output_dir"]), path.parent)
                    saved_logs[path] = path.read_bytes()
            second = runner.run(resume=True)
            self.assertEqual(1, second["completed_episodes"])
            self.assertEqual("2", counter.read_text(encoding="utf-8"))
            for path, contents in saved_logs.items():
                self.assertEqual(contents, path.read_bytes())
            terminal = runner.ledger.terminal_records()
            self.assertEqual(["REJECTED_SETUP", "COMPLETE_POLICY"], [r["terminal_status"] for r in terminal])
            self.assertEqual(777, terminal[1]["episode"]["requests"][0]["noise_seed"])

    def test_planner_failure_is_terminal_for_cell_and_does_not_try_next_seed(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "fatal")
            report = runner.run(resume=False)
            self.assertEqual("fixture", report["evidence_kind"])
            self.assertEqual(0, report["completed_episodes"])
            self.assertEqual(1, len(report["errors"]))
            self.assertEqual("PLANNER_ERROR", report["errors"][0]["kind"])
            self.assertEqual("1", counter.read_text(encoding="utf-8"))
            self.assertEqual(["INFRA_ERROR"], [r["terminal_status"] for r in runner.ledger.terminal_records()])

    def test_backend_identity_mismatch_is_fatal_before_counting_episode(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "mismatched_identity")
            report = runner.run(resume=False)
            self.assertEqual(0, report["completed_episodes"])
            self.assertEqual(1, report["errors"][0]["count"])
            self.assertIn("identity", report["errors"][0]["message"])
            self.assertEqual("1", counter.read_text(encoding="utf-8"))

    def test_backend_cannot_relabel_fixture_output_as_real_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "wrong_evidence_kind")
            report = runner.run(resume=False)
            self.assertEqual("fixture", report["evidence_kind"])
            self.assertEqual(0, report["real_policy_episodes"])
            self.assertIn("evidence_kind", report["errors"][0]["message"])
            self.assertEqual("1", counter.read_text(encoding="utf-8"))

    def test_boolean_chunk_index_is_rejected_as_protocol_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "bool_chunk_index")
            report = runner.run(resume=False)
            self.assertEqual(0, report["completed_episodes"])
            self.assertEqual("PROTOCOL_ERROR", report["errors"][0]["kind"])
            self.assertIn("chunk", report["errors"][0]["message"])
            self.assertEqual("1", counter.read_text(encoding="utf-8"))

    def test_candidate_budget_exhaustion_is_reported_after_typed_rejections(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "always_reject")
            report = runner.run(resume=False)
            self.assertEqual(0, report["completed_episodes"])
            self.assertEqual(2, len(report["rejections"]))
            self.assertTrue(any(e["kind"] == "CANDIDATE_BUDGET_EXHAUSTED" for e in report["errors"]))
            for terminal in runner.ledger.terminal_records():
                self.assertIn("execution_evidence", terminal)
                self.assertEqual("NOT_REVIEWED", terminal["execution_evidence"]["video_review_status"])
                self.assertEqual(0, terminal["execution_evidence"]["actions_started"])
            self.assertEqual("2", counter.read_text(encoding="utf-8"))

    def test_timeout_kills_child_process_tree_that_inherits_log_handles(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "spawn_child", timeout=1)
            started = time.monotonic()
            report = runner.run(resume=False)
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 3.5)
            self.assertEqual("BACKEND_TIMEOUT", report["errors"][0]["kind"])
            marker = Path(str(counter) + ".child-marker")
            time.sleep(2.0)
            self.assertFalse(marker.exists(), "descendant kept running after the episode timeout")

    def test_attempt_log_files_preserve_complete_stdout_and_stderr_for_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, _ = self.make_evaluator(temporary, "large_success")
            runner.run(resume=False)
            terminal = runner.ledger.terminal_records()[0]
            evidence = terminal["execution_evidence"]
            stdout_path = Path(evidence["backend_stdout_path"])
            stderr_path = Path(evidence["backend_stderr_path"])
            stdout = stdout_path.read_text(encoding="utf-8")
            stderr = stderr_path.read_text(encoding="utf-8")
            self.assertIn("OUT_BEGIN_", stdout)
            self.assertIn("_OUT_END", stdout)
            self.assertIn("ERR_BEGIN_", stderr)
            self.assertIn("_ERR_END", stderr)
            self.assertEqual(Path(evidence["output_dir"]), stdout_path.parent)
            self.assertEqual(Path(evidence["output_dir"]), stderr_path.parent)

    def test_attempt_log_files_are_exclusive_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "success")
            runner.run(resume=False)
            terminal = runner.ledger.terminal_records()[0]
            evidence = terminal["execution_evidence"]
            stdout_path = Path(evidence["backend_stdout_path"])
            stderr_path = Path(evidence["backend_stderr_path"])
            before = {stdout_path: stdout_path.read_bytes(), stderr_path: stderr_path.read_bytes()}
            with self.assertRaises(FileExistsError):
                runner.backend.evaluate({"output_dir": evidence["output_dir"]}, timeout_seconds=1)
            for path, contents in before.items():
                self.assertEqual(contents, path.read_bytes())
            self.assertEqual("1", counter.read_text(encoding="utf-8"))

    def test_attempt_log_files_preserve_complete_output_for_crash_invalid_json_and_timeout(self):
        expected_markers = {
            "large_crash": ("CRASH_OUT_BEGIN_", "_CRASH_OUT_END", "CRASH_ERR_BEGIN_", "_CRASH_ERR_END"),
            "large_invalid_json": ("JSON_OUT_BEGIN_", "_JSON_OUT_END", "JSON_ERR_BEGIN_", "_JSON_ERR_END"),
            "sleep": ("TIMEOUT_OUT_BEGIN_", "_TIMEOUT_OUT_END", "TIMEOUT_ERR_BEGIN_", "_TIMEOUT_ERR_END"),
        }
        for mode, markers in expected_markers.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                runner, _ = self.make_evaluator(temporary, mode, timeout=1)
                runner.run(resume=False)
                terminal = runner.ledger.terminal_records()[0]
                self.assertEqual("INFRA_ERROR", terminal["terminal_status"])
                evidence = terminal["execution_evidence"]
                stdout_path = Path(evidence["backend_stdout_path"])
                stderr_path = Path(evidence["backend_stderr_path"])
                self.assertTrue(stdout_path.is_file())
                self.assertTrue(stderr_path.is_file())
                stdout = stdout_path.read_text(encoding="utf-8")
                stderr = stderr_path.read_text(encoding="utf-8")
                self.assertIn(markers[0], stdout)
                self.assertIn(markers[1], stdout)
                self.assertIn(markers[2], stderr)
                self.assertIn(markers[3], stderr)
                self.assertEqual(Path(evidence["output_dir"]), stdout_path.parent)
                self.assertEqual(Path(evidence["output_dir"]), stderr_path.parent)

    def test_pending_video_review_status_is_rejected_before_terminal_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "pending_video")
            report = runner.run(resume=False)
            self.assertEqual(0, report["completed_episodes"])
            self.assertEqual("PROTOCOL_ERROR", report["errors"][0]["kind"])
            self.assertIn("video_review_status", report["errors"][0]["message"])
            self.assertEqual("INFRA_ERROR", runner.ledger.terminal_records()[0]["terminal_status"])
            self.assertEqual("1", counter.read_text(encoding="utf-8"))

    def test_cli_rejects_fixture_manifest_before_backend_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "policy"
            package.mkdir()
            (package / "manifest.json").write_text('{"fixture":true}\n', encoding="utf-8")
            counter = root / "backend-count.txt"
            output = root / "run"
            command = [
                sys.executable, str(EVALUATION / "evaluate.py"),
                "--policy-package", str(package),
                "--tasks-file", str(TEMPLATE_PATH),
                "--setting", "clean", "--task", "lift_pot",
                "--episodes", "1", "--max-candidates", "1",
                "--seed-start", "100000", "--stage", "baseline",
                "--episode-timeout-seconds", "5", "--cell-timeout-seconds", "30",
                "--stage-timeout-seconds", "60", "--output", str(output),
                "--backend-executable", sys.executable,
                "--backend-arg", str(FAKE_BACKEND), "--backend-arg", "fatal", "--backend-arg", str(counter),
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertIn("package-manifest.json", result.stderr)
            self.assertFalse(counter.exists())
            self.assertFalse((output / "run-config.json").exists())

    def test_subprocess_timeout_is_bounded_and_fails_cell(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner, counter = self.make_evaluator(temporary, "sleep", timeout=1)
            report = runner.run(resume=False)
            self.assertEqual(0, report["completed_episodes"])
            self.assertIn("timeout", report["errors"][0]["message"].lower())
            self.assertEqual("1", counter.read_text(encoding="utf-8"))

    def test_subprocess_dry_run_works_under_python_s_without_external_modules(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fixture-plan"
            command = [
                sys.executable, "-S", str(EVALUATION / "evaluate.py"),
                "--tasks-file", str(TEMPLATE_PATH),
                "--setting", "clean", "--task", "lift_pot",
                "--episodes", "1", "--max-candidates", "1",
                "--seed-start", "100000", "--stage", "baseline",
                "--fixture-only", "--policy-manifest-sha256", CHECKPOINT_SHA,
                "--output", str(output), "--dry-run",
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads((output / "evaluation-report.json").read_text(encoding="utf-8"))
            plan = json.loads((output / "run-plan.json").read_text(encoding="utf-8"))
            self.assertEqual("fixture", report["evidence_kind"])
            self.assertEqual(0, report["real_policy_episodes"])
            self.assertEqual(1, len(plan["cells"]))
            self.assertEqual(["lift_pot"], [cell["task"] for cell in plan["cells"]])


if __name__ == "__main__":
    unittest.main()
