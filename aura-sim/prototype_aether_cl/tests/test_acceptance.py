"""Acceptance must reject trace drift/errors and preserve failed evidence."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

from aether_cl.acceptance import run_acceptance, run_in_process
from aether_cl.runtime import RunConfig, run
from test_m2 import Environment, inject


def fixture_run(config):
    return run(config, env_factory=lambda _: Environment(), disturbance_fn=inject)


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.software = patch("aether_cl.runtime.software_manifest", return_value={
            "git_commit": "fixture-revision", "git_dirty": False})
        self.software.start()
        self.addCleanup(self.software.stop)

    def test_six_matched_trials_pass_and_archive_hashes_are_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "evidence.tar.gz"
            report = run_acceptance(Path(temporary) / "runs", archive, run_fn=fixture_run)
            self.assertEqual(report["state"], "passed")
            self.assertEqual(len(report["trials"]), 6)
            self.assertTrue(all(p["passed"] for p in report["pairs"]))
            self.assertEqual(report["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            with tarfile.open(archive) as bundle:
                index = json.load(bundle.extractfile("acceptance/archive_index.json"))
                self.assertEqual(sum(p["path"].endswith("events.jsonl") for p in index["files"]), 6)
                for item in index["files"]:
                    content = bundle.extractfile(item["path"]).read()
                    self.assertEqual(item["bytes"], len(content))
                    self.assertEqual(item["sha256"], hashlib.sha256(content).hexdigest())

    def test_one_changed_action_rejects_pair_without_discarding_logs(self):
        def drift(config):
            result = fixture_run(config)
            if config.verification and config.disturbance == "none":
                path = Path(result["run_directory"]) / "events.jsonl"
                events = [json.loads(line) for line in path.read_text().splitlines()]
                next(e for e in events if e["event"] == "step")["action"][0] += .001
                path.write_text("".join(json.dumps(e) + "\n" for e in events))
            return result
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(temporary, run_fn=drift)
            self.assertEqual(report["state"], "failed")
            pair = report["pairs"][0]
            self.assertFalse(pair["checks"]["trace_equal"])
            self.assertEqual(pair["first_difference"]["field"], "action")
            self.assertEqual(pair["first_difference"]["step"], 1)
            self.assertTrue(Path(report["archive"]).is_file())

    def test_wrong_task_outcome_fails_even_when_pair_traces_match(self):
        def wrong_result(config):
            result = fixture_run(config)
            if config.disturbance == "none":
                path = Path(result["run_directory"]) / "result.json"
                result["episodes"][0]["task_success_at_end"] = False
                path.write_text(json.dumps(result))
            return result
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(temporary, run_fn=wrong_result)
            self.assertEqual(report["state"], "failed")
            self.assertIn("expected_task_outcome", report["trials"][0]["failed_checks"])
            self.assertTrue(report["pairs"][0]["checks"]["trace_equal"])

    def test_execution_failure_keeps_error_result_and_runs_remaining_cells(self):
        def failing(config):
            if config.disturbance == "object_shift" and not config.verification:
                def fail(_):
                    raise RuntimeError("fixture initialization failed")
                return run(config, env_factory=fail, disturbance_fn=inject)
            return fixture_run(config)
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(temporary, run_fn=failing)
            self.assertEqual(report["state"], "failed")
            self.assertEqual(len(report["trials"]), 6)
            trial = report["trials"][2]
            self.assertEqual(trial["state"], "error")
            with tarfile.open(report["archive"]) as bundle:
                matches = [m for m in bundle.getnames() if "object_shift-baseline" in m and m.endswith("result.json")]
                self.assertEqual(len(matches), 1)
                self.assertEqual(json.load(bundle.extractfile(matches[0]))["state"], "error")

    def test_interrupt_archives_partial_run_and_does_not_start_more_cells(self):
        def interrupt(config):
            def fail(_):
                raise KeyboardInterrupt()
            return run(config, env_factory=fail)
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(temporary, run_fn=interrupt)
            self.assertEqual(report["state"], "interrupted")
            self.assertEqual(len(report["trials"]), 1)
            self.assertTrue(Path(report["archive"]).is_file())

    def test_excluded_reset_does_not_pass_or_get_replaced_with_another_seed(self):
        seeds = []
        class AlreadySolved(Environment):
            def reset(self, seed):
                seeds.append(seed)
                return super().reset(8)
        def excluded(config):
            return run(config, env_factory=lambda _: AlreadySolved(), disturbance_fn=inject)
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(temporary, run_fn=excluded)
            self.assertEqual(report["state"], "failed")
            self.assertEqual(seeds, [0] * 6)
            for trial in report["trials"]:
                self.assertIn("complete_eligible_episode", trial["failed_checks"])
                self.assertIn("full_budget", trial["failed_checks"])
                self.assertTrue(trial["episode"]["excluded"])

    def test_existing_archive_and_missing_live_run_stop_before_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "existing.tar.gz"
            archive.write_bytes(b"previous evidence")
            with patch("aether_cl.acceptance.run_in_process") as mock_run:
                with self.assertRaises(FileExistsError):
                    run_acceptance(Path(temporary) / "runs", archive, run_fn=mock_run)
                with self.assertRaises(ValueError):
                    run_acceptance(Path(temporary) / "runs", live_run=Path(temporary) / "missing", run_fn=mock_run)
                mock_run.assert_not_called()
            self.assertEqual(archive.read_bytes(), b"previous evidence")
            self.assertFalse((Path(temporary) / "runs").exists())

    def test_dirty_revision_is_rejected_and_prior_live_evidence_is_included(self):
        with tempfile.TemporaryDirectory() as temporary:
            live = fixture_run(RunConfig(
                controller="fixed_pick_cube", protocol="m2", verification=True,
                disturbance="object_shift", max_steps=360, render=False, output=Path(temporary) / "live"))
            with patch("aether_cl.runtime.software_manifest", return_value={"git_commit": "fixture-revision", "git_dirty": True}):
                report = run_acceptance(Path(temporary) / "runs", live_run=live["run_directory"], run_fn=fixture_run)
            self.assertEqual(report["state"], "failed")
            self.assertIn("clean_revision_recorded", report["trials"][0]["failed_checks"])
            with tarfile.open(report["archive"]) as bundle:
                self.assertIn("prior-live-run/events.jsonl", bundle.getnames())

    def test_library_environment_difference_still_rejects_a_pair(self):
        def change_manifest(config):
            result = fixture_run(config)
            if config.verification and config.disturbance == "none":
                path = Path(result["run_directory"]) / "manifest.json"
                manifest = json.loads(path.read_text())
                manifest["software"]["native_library_environment"] = {"LD_LIBRARY_PATH": "/unexpected"}
                path.write_text(json.dumps(manifest))
            return result
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(temporary, run_fn=change_manifest)
            self.assertEqual(report["state"], "failed")
            self.assertTrue(report["pairs"][0]["checks"]["trace_equal"])
            self.assertFalse(report["pairs"][0]["checks"]["software_equal"])

    def test_each_trial_has_a_fresh_interpreter_and_identical_start_environment(self):
        program = """
import json, os, sys
from pathlib import Path
p = Path(sys.argv[1]) / 'child-run'
p.mkdir()
original = os.environ.get('LD_LIBRARY_PATH')
os.environ['LD_LIBRARY_PATH'] = 'cv2-added:' + (original or '')
(p / 'result.json').write_text(json.dumps({'run_directory': str(p), 'initial_path': original, 'pid': os.getpid()}))
print('child completed', flush=True)
"""
        real_popen = subprocess.Popen
        commands = []
        def launch(command, **kwargs):
            commands.append(command)
            output = command[command.index("--output") + 1]
            return real_popen([sys.executable, "-c", program, output], **kwargs)
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"LD_LIBRARY_PATH": "suite-start"}):
            environment = os.environ.copy()
            with patch("aether_cl.acceptance.subprocess.Popen", side_effect=launch):
                first = run_in_process(RunConfig(output=Path(temporary) / "baseline", verification=False), environment)
                second = run_in_process(RunConfig(output=Path(temporary) / "v1", verification=True), environment)
            self.assertEqual(first["initial_path"], second["initial_path"])
            self.assertEqual(second["initial_path"], "suite-start")
            self.assertNotEqual(first["pid"], second["pid"])
            self.assertEqual(os.environ["LD_LIBRARY_PATH"], "suite-start")
            self.assertEqual(commands[0][commands[0].index("--system") + 1], "baseline")
            self.assertEqual(commands[1][commands[1].index("--system") + 1], "v1")
            self.assertIn("child completed", (Path(temporary) / "v1/process.stdout.log").read_text())

    def test_nonzero_child_exit_preserves_result_and_stderr(self):
        program = """
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / 'child-run'
p.mkdir()
(p / 'result.json').write_text(json.dumps({'state': 'error'}))
print('native fixture failure', file=sys.stderr)
sys.exit(3)
"""
        real_popen = subprocess.Popen
        def launch(command, **kwargs):
            return real_popen([sys.executable, "-c", program,
                               command[command.index("--output") + 1]], **kwargs)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "trial"
            with patch("aether_cl.acceptance.subprocess.Popen", side_effect=launch):
                with self.assertRaisesRegex(RuntimeError, "exited 3"):
                    run_in_process(RunConfig(output=directory), os.environ.copy())
            self.assertEqual(json.loads((directory / "child-run/result.json").read_text())["state"], "error")
            self.assertIn("native fixture failure", (directory / "process.stderr.log").read_text())

    def test_interrupt_joins_child_before_returning_evidence_to_suite(self):
        program = """
import json, sys, time
from pathlib import Path
p = Path(sys.argv[1]) / 'child-run'
p.mkdir()
try:
    (p / 'ready').write_text('ready')
    time.sleep(30)
finally:
    (p / 'result.json').write_text(json.dumps({'state': 'error', 'error': 'interrupted'}))
"""
        real_popen = subprocess.Popen
        children = []
        def launch(command, **kwargs):
            output = command[command.index("--output") + 1]
            process = real_popen([sys.executable, "-c", program, output], **kwargs)
            children.append(process)
            original_wait = process.wait
            first = True
            def interrupt_wait(*args, **kwargs):
                nonlocal first
                if first:
                    first = False
                    deadline = time.monotonic() + 5
                    while not (Path(output) / "child-run/ready").exists():
                        if time.monotonic() > deadline:
                            process.kill()
                            original_wait()
                            self.fail("Child fixture did not initialize")
                        time.sleep(.01)
                    raise KeyboardInterrupt()
                return original_wait(*args, **kwargs)
            process.wait = interrupt_wait
            return process
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "trial"
            with patch("aether_cl.acceptance.subprocess.Popen", side_effect=launch):
                with self.assertRaises(KeyboardInterrupt):
                    run_in_process(RunConfig(output=directory), os.environ.copy())
            self.assertIsNotNone(children[0].poll())
            self.assertEqual(json.loads((directory / "child-run/result.json").read_text())["error"], "interrupted")


if __name__ == "__main__":
    unittest.main()
