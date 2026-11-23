"""Frozen magnitude plan, continuation and measured failures; no native physics."""

from contextlib import ExitStack
import csv
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from aether_cl import m4_robustness as m4
from aether_cl.m3_runtime import M3Config, run
from aether_cl.verification import VerificationMetrics
from test_m2 import inject
from test_m3_screening import VariedEnvironment


SOFTWARE = {"git_commit": "fixture", "git_dirty": False}


class M4Tests(unittest.TestCase):
    def fixture(self, trial, software):
        config = trial["config"]
        excluded = config["seed"] == 68
        attempted = config["system"] == "v2" and config["disturbance"] != "none" and not excluded
        success = not excluded and (config["disturbance"] == "none" or config["disturbance_magnitude"] == .02
                                   or attempted and config["disturbance_magnitude"] < .20)
        failure = None if success or excluded else {"step": 125, "failure": "GRASP_FAILURE"}
        episode = {"episode": 0, "seed": config["seed"], "excluded": excluded,
                   "task_success_at_end": success, "first_detected_failure": failure,
                   "first_failure_latency_steps": 2 if failure else None,
                   "final_cube_goal_distance_m": .01 if success else .3,
                   "recovery_task_success": attempted and success,
                   "recovery": {"attempts": int(attempted), "state": "aborted" if attempted and not success else "nominal",
                                "action_steps": 200 if attempted else 0, "observed_tcp_path_m": .5 if attempted else 0.,
                                "failure_detail": "fixture_timeout" if attempted and not success else None}}
        metrics = VerificationMetrics()
        if not excluded:
            metrics.observe({"failure": "GRASP_FAILURE" if failure else None},
                            {"failure": "GRASP_FAILURE" if failure else None})
        return {"passed": True, "checks": {"fixture": True}, "failed_checks": [], "episodes": [episode],
                "evaluation": {"verification_metrics": metrics.result(True) if config["verification"] else None}}

    def child(self, config, environment, module):
        self.assertEqual(module, "aether_cl.m3")
        self.assertEqual(config.episodes, 1)
        self.assertEqual(config.fps, 5)
        self.assertFalse(config.render)
        config.validate()
        self.calls.append((config.disturbance, config.disturbance_magnitude, config.seed, config.system))
        self.environments.append(environment.copy())
        directory = config.output / "fixture"
        directory.mkdir(parents=True)
        (directory / "raw.json").write_text(json.dumps({"seed": config.seed, "magnitude": config.disturbance_magnitude}))
        return {"run_directory": str(directory)}

    def mocks(self, stack):
        self.calls, self.environments = [], []
        stack.enter_context(patch.object(m4, "software_manifest", return_value=SOFTWARE))
        stack.enter_context(patch.object(m4, "run_in_process", side_effect=self.child))
        stack.enter_context(patch.object(m4, "checked_trial", side_effect=self.fixture))
        for name in ("compare_pair", "compare_recovery", "compare_control"):
            stack.enter_context(patch.object(m4, name, return_value={"passed": True, "checks": {"fixture": True}}))

    def verify_archive(self, path):
        with tarfile.open(path) as bundle:
            index = json.load(bundle.extractfile("m4-robustness/archive_index.json"))
            self.assertEqual(len(bundle.getnames()), len(set(bundle.getnames())))
            self.assertEqual(set(bundle.getnames()), {x["path"] for x in index["files"]} | {"m4-robustness/archive_index.json"})
            for item in index["files"]:
                data = bundle.extractfile(item["path"]).read()
                self.assertEqual(len(data), item["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])

    def test_660_selected_calls_pause_resume_without_rerunning_or_replacing_raw_evidence(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            self.mocks(stack)
            root = Path(temporary)
            output, archive = root / "study", root / "evidence.tar.gz"
            first = m4.run_sweep(output, archive, stop_after=61)
            self.assertEqual(first["state"], "paused")
            self.assertEqual(len(first["episode_trials"]), 61)
            self.assertFalse(archive.exists())
            partial = Path(first["saved_archive"])
            self.verify_archive(partial)
            old_hash = hashlib.sha256(partial.read_bytes()).hexdigest()
            self.assertTrue(all(c["validated_curve_success_rate"] is None for c in first["cells"] if not c["complete"]))
            report = m4.run_sweep(output, archive, resume=True)
            self.assertEqual(report["state"], "passed")
            self.assertEqual(len(self.calls), 660)
            self.assertEqual(len(set(self.calls)), 660)
            self.assertEqual(self.calls[:3], [("none", .12, 60, s) for s in m4.SYSTEMS])
            self.assertEqual(self.calls[-3:], [("object_drop", .20, 79, s) for s in m4.SYSTEMS])
            self.assertTrue(all(e == self.environments[0] for e in self.environments))
            self.assertTrue(all(k not in self.environments[0] for k in m4.VOLATILE_ENVIRONMENT))
            self.assertEqual((len(report["cells"]), len(report["pairs"]), len(report["recovery_pairs"]), len(report["control_pairs"])), (33, 220, 220, 200))
            self.assertTrue(all(c["excluded_seeds"] == [68] and c["eligible_episodes"] == 19 for c in report["cells"]))
            large = next(c for c in report["cells"] if c["point_id"] == "object_shift-200mm" and c["system"] == "v2")
            self.assertEqual((large["task_success_rate_at_end"], large["aborted_attempts"], large["mean_attempt_action_steps"]), (0, 19, 200))
            self.assertEqual(large["verification_metrics"]["diagnosis_accuracy_when_failure_detected"], 1)
            self.assertEqual(next(p for p in report["paired_outcomes"] if p["point_id"] == "object_shift-120mm")["recovery_only_success"], 19)
            self.assertEqual(next(p for p in report["paired_outcomes"] if p["point_id"] == "object_shift-200mm")["both_failed"], 19)
            self.assertEqual(hashlib.sha256(partial.read_bytes()).hexdigest(), old_hash)
            self.verify_archive(archive)
            with (output / "curve.csv").open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 33)
            with self.assertRaises(ValueError):
                m4.run_sweep(output, archive, resume=True)

    def test_resume_rejects_raw_tampering_changed_environment_and_competing_writer(self):
        import fcntl
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            self.mocks(stack)
            root = Path(temporary)
            output, archive = root / "study", root / "evidence.tar.gz"
            report = m4.run_sweep(output, archive, stop_after=3)
            with patch.dict("os.environ", {"M4_FIXTURE_ENVIRONMENT_CHANGE": "1"}):
                with self.assertRaisesRegex(ValueError, "environment"):
                    m4.run_sweep(output, archive, resume=True)
            with (output / "runner.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError, "owns"):
                    m4.run_sweep(output, archive, resume=True)
            raw = Path(report["episode_trials"][0]["run_directory"]) / "raw.json"
            raw.write_text("tampered")
            with self.assertRaisesRegex(ValueError, "hashes"):
                m4.run_sweep(output, archive, resume=True)
            self.assertEqual(len(self.calls), 3)

    def test_child_error_and_interrupt_retained_and_never_rerun_on_continuation(self):
        for error, state in ((RuntimeError("fixture failure"), "paused"), (KeyboardInterrupt(), "interrupted")):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
                self.mocks(stack)
                root = Path(temporary)
                with patch.object(m4, "run_in_process", side_effect=error):
                    first = m4.run_sweep(root / "study", root / "evidence.tar.gz", stop_after=1)
                self.assertEqual(first["state"], state)
                self.assertFalse(first["episode_trials"][0]["passed"])
                second = m4.run_sweep(root / "study", root / "evidence.tar.gz", resume=True, stop_after=1)
                self.assertEqual(second["episode_trials"][0], first["episode_trials"][0])
                self.assertEqual(self.calls[0][-1], "v1")
                self.assertTrue(all(c["task_success_rate_at_end"] is None for c in second["cells"]))
                self.assertTrue(all(p["success_rate_difference_v2_minus_v1"] is None for p in second["paired_outcomes"]))
                self.verify_archive(Path(second["saved_archive"]))

    def test_protocol_source_settings_guard_runs_before_output_or_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            altered = m4.protocol()
            altered["magnitudes_m"] = [.12]
            path = root / "protocol.json"
            path.write_text(json.dumps(altered))
            with patch.object(m4, "PROTOCOL_PATH", path):
                with self.assertRaisesRegex(ValueError, "preregistration"):
                    m4.run_sweep(root / "study", root / "evidence.tar.gz", run_fn=lambda _: self.fail("launched"))
            self.assertFalse((root / "study").exists())
            with patch.dict(m4.FROZEN_SOURCES, {"m3_isolated_screening.py": "bad"}):
                with self.assertRaisesRegex(ValueError, "sources"):
                    m4.preflight()

    def test_dense_metrics_aggregate_misdiagnosis_uncertainty_and_null_incomplete_rates(self):
        trials, expected = [], VerificationMetrics()
        cases = (("GRASP_FAILURE", "OBJECT_LOST"), (None, "UNCERTAIN"),
                 ("OBJECT_LOST", "OBJECT_LOST"), ("UNCERTAIN", "UNCERTAIN"))
        for index, seed in enumerate(m4.SEEDS):
            config = {"seed": seed, "system": "v1", "disturbance": "none", "disturbance_magnitude": .12, "verification": True}
            trial = {"seed": seed, "system": "v1", **self.fixture({"config": config}, SOFTWARE)}
            metrics = VerificationMetrics()
            if not trial["episodes"][0]["excluded"]:
                truth, prediction = cases[index % len(cases)]
                metrics.observe({"failure": truth}, {"failure": prediction})
                expected.observe({"failure": truth}, {"failure": prediction})
            trial["evaluation"]["verification_metrics"] = metrics.result(True)
            trials.append(trial)
        self.assertEqual(m4.summarize_cell(trials)["verification_metrics"], expected.result(True))
        incomplete = m4.summarize_cell(trials[:-1])
        self.assertIsNone(incomplete["task_success_rate_at_end"])
        self.assertIsNone(incomplete["verification_metrics"]["diagnosis_accuracy_when_failure_detected"])

    def test_real_fixture_different_magnitudes_retain_strict_pairs_and_control_prefixes(self):
        with tempfile.TemporaryDirectory() as temporary, patch("aether_cl.m3_runtime.software_manifest", return_value=SOFTWARE):
            root = Path(temporary)
            normal_config = M3Config(system="baseline", verification=False, seed=60, render=False, output=root / "normal")
            normal = Path(run(normal_config, env_factory=lambda _: VariedEnvironment(), disturbance_fn=inject)["run_directory"])
            for condition in ("object_shift", "object_drop"):
                for magnitude in (.02, .20):
                    paths = {}
                    for system in m4.SYSTEMS:
                        config = M3Config(system=system, verification=system != "baseline", seed=60,
                                          disturbance=condition, disturbance_magnitude=magnitude, render=False,
                                          output=root / f"{condition}-{magnitude}-{system}")
                        result = run(config, env_factory=lambda _: VariedEnvironment(), disturbance_fn=inject)
                        trial = {"config": {**config.__dict__, "output": str(config.output)}, "run_directory": result["run_directory"]}
                        checked = m4.checked_trial(trial, SOFTWARE)
                        self.assertTrue(checked["passed"], checked["failed_checks"])
                        paths[system] = Path(result["run_directory"])
                    self.assertTrue(m4.compare_pair(paths["baseline"], paths["v1"])["passed"])
                    self.assertTrue(m4.compare_recovery(paths["v1"], paths["v2"])["passed"])
                    self.assertTrue(m4.compare_control(normal, paths["baseline"], 80 if condition == "object_shift" else 180)["passed"])
            events = paths["baseline"] / "events.jsonl"
            lines = [json.loads(line) for line in events.read_text().splitlines()]
            next(e for e in lines if e["event"] == "step" and e["step"] == 20)["observation"]["extra"]["goal_pos"][0][0] += .001
            events.write_text("\n".join(json.dumps(e) for e in lines) + "\n")
            self.assertFalse(m4.compare_control(normal, paths["baseline"], 180)["passed"])


if __name__ == "__main__":
    unittest.main()
