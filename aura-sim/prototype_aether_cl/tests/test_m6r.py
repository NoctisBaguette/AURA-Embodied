"""Single-factor transition, native-like contact fixture and exact repair pairing."""

import ast
from contextlib import ExitStack, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from aether_cl import m6r_sweep as sweep
from aether_cl.m6_policy import FixedPlacement, PlacementRecovery, RETRY_PHASES, PlacementRecoverySettings
from aether_cl.m6r_policy import EffectAlignedRecovery
from aether_cl.m6r_runtime import M6RConfig, run
from aether_cl.m6r_audit import check_trial, compare
from test_m6 import (PlacementEnvironment, reset_fixture, observe_fixture, shift_fixture,
                     SOFTWARE, NATIVE_SOURCES, state)
import test_m6 as legacy_fixtures
from test_policy import BASE


class ContactConstrained(PlacementEnvironment):
    """Native-like supported cube limits closed-gripper lowering; no native claim."""
    def step(self, action):
        super().step(action)
        if self.held and self.obs["extra"]["tcp_pose"][0][2] < .04:
            self.obs["extra"]["tcp_pose"][0][2] = .033
            self.obs["extra"]["obj_pose"][0][2] = .02
        return copy.deepcopy(self.obs), [0.], [False], [self.step_number == 800], self.info()

    def info(self):
        info = super().info()
        if not self.false_labels and abs(self.obs["extra"]["obj_pose"][0][2] - .02) <= .004:
            info["cube_table_contact_force_world_n"] = [[0., 0., .5]]
        return info


def fixture_run(config, factory=ContactConstrained, **kwargs):
    return run(config, env_factory=lambda _: factory(), reset_fn=reset_fixture, observe_fn=observe_fixture,
               shift_fn=shift_fixture, native_sources_fn=lambda: NATIVE_SOURCES, **kwargs)


def lower_controller(cls, observation):
    policy = FixedPlacement(observation, BASE)
    controller = cls(policy, BASE)
    controller.retry = policy
    controller.state = "attempting"
    controller.attempts = 1
    controller.stage = RETRY_PHASES.index("lower")
    controller.stage_steps = 3
    controller.previous_pose = np.array(observation["extra"]["obj_pose"][0])
    controller.previous_tcp = np.array(observation["extra"]["tcp_pose"][0][:3])
    controller.max_lift = .10
    controller.candidate_steps = 5
    return controller


def lower_state():
    obs = state()
    obs["extra"]["obj_pose"][0][:3] = [.07, .04, .02]
    obs["extra"]["tcp_pose"][0][:3] = [.07, .04, .033]
    obs["agent"]["qpos"][0][-2:] = [.02, .02]
    return obs


class ContractTests(unittest.TestCase):
    def test_only_one_observe_predicate_changes_all_motion_methods_are_inherited(self):
        import inspect
        old = inspect.getsource(PlacementRecovery.observe)
        repaired = inspect.getsource(EffectAlignedRecovery.observe)
        expected = old.replace('ready &= abs(g["tcp"][2] - target[2]) <= self.settings.lower_vertical_tolerance_m',
                               'ready &= g["supported_geometry"] and g["horizontal_error_m"] <= SETTINGS.horizontal_tolerance_m')
        self.assertEqual(repaired, expected)
        for method in ("__init__", "action", "snapshot", "abort"):
            self.assertIs(getattr(EffectAlignedRecovery, method), getattr(PlacementRecovery, method))
        self.assertEqual(EffectAlignedRecovery(FixedPlacement(state(), BASE), BASE).settings, PlacementRecoverySettings())

    def test_supported_in_target_transitions_despite_z_residual_and_never_reads_labels(self):
        obs = lower_state()
        old, new = lower_controller(PlacementRecovery, obs), lower_controller(EffectAlignedRecovery, obs)
        old.observe(obs); new.observe(obs)
        self.assertEqual(old.snapshot()["phase"], "lower")
        self.assertEqual(new.snapshot()["phase"], "release")
        changed = copy.deepcopy(obs)
        changed["extra"].update(is_grasped=True, contact_force="poison", success=True, reference="poison", disturbance="poison")
        changed["info"] = {"is_grasped": "poison"}
        other = lower_controller(EffectAlignedRecovery, changed); other.observe(changed)
        self.assertEqual(new.snapshot(), other.snapshot())

    def test_replacement_and_all_retained_gates_are_required(self):
        for reason in ("unsupported", "off_target", "distance", "rotation", "minimum_steps", "attachment"):
            with self.subTest(reason=reason):
                obs = lower_state(); c = lower_controller(EffectAlignedRecovery, obs)
                if reason == "unsupported": obs["extra"]["obj_pose"][0][2] = .025
                if reason == "off_target": obs["extra"]["obj_pose"][0][0] += .026
                if reason == "distance": obs["extra"]["tcp_pose"][0][0] += .021
                if reason == "rotation": obs["extra"]["tcp_pose"][0][3:] = [1., 0., 0., 0.]
                if reason == "minimum_steps": c.stage_steps = 2
                if reason == "attachment":
                    obs["agent"]["qpos"][0][-2:] = [0., 0.]
                    c.missing_steps = 2
                c.observe(obs)
                self.assertEqual(c.snapshot()["phase"], "lower")
                if reason == "attachment": self.assertEqual(c.failure_detail, "attachment_lost_during_retry")

    def test_same_local_timeout_budget_and_one_attempt_terminal_hold(self):
        obs = lower_state(); obs["extra"]["obj_pose"][0][0] += .026
        c = lower_controller(EffectAlignedRecovery, obs); c.stage_steps = 40
        c.last_action = np.ones((1, 7)); c.last_decision = {"phase": "recovery_lower", "phase_step": 40}
        c.observe(obs)
        self.assertEqual(c.failure_detail, "retry_lower_not_completed")
        snapshot = c.snapshot()
        for step in range(500, 510):
            action, decision = c.action(obs, step, {"status": "failed", "failure": "OBJECT_LOST"})
            c.observe(obs)
            np.testing.assert_array_equal(action, np.ones((1, 7)))
            self.assertEqual(c.snapshot(), snapshot)
            self.assertEqual(decision["phase"], "recovery_aborted")
        c = lower_controller(EffectAlignedRecovery, obs); c.steps = 400
        c.observe(obs); self.assertEqual(c.failure_detail, "remaining_action_budget_exhausted")


class RuntimeAuditTests(unittest.TestCase):
    def test_contact_boundary_old_aborts_repair_releases_and_common_prefix_is_exact(self):
        with tempfile.TemporaryDirectory() as temporary, patch("aether_cl.m6r_runtime.software_manifest", return_value=SOFTWARE):
            root = Path(temporary); paths = {}
            for condition in ("none", "post_release_shift"):
                for system in sweep.SYSTEMS:
                    c = M6RConfig(system=system, verification=system != "baseline", seed=100, disturbance=condition,
                                  output=root / condition / system)
                    result = fixture_run(c); directory = Path(result["run_directory"])
                    checked = check_trial(directory, c, SOFTWARE)
                    self.assertTrue(checked["passed"], checked["failed_checks"])
                    episode = result["episodes"][0]
                    self.assertEqual(episode["task_success_at_end"], condition == "none" or system == "v2r")
                    if condition != "none" and system == "v2-old":
                        self.assertTrue(episode["lower_phase_timeout"])
                        self.assertFalse(episode["recovery_release_executed"])
                    if condition != "none" and system == "v2r":
                        self.assertTrue(episode["recovery_release_executed"])
                        self.assertTrue(episode["recovery_retraction_executed"])
                        self.assertTrue(episode["controller_complete"])
                        self.assertEqual(episode["recovery"]["attempts"], 1)
                    paths[(condition, system)] = directory
                for left, right, kind in (("baseline", "v1", "passive"), ("v1", "v2-old", "recovery"), ("v2-old", "v2r", "repair")):
                    paired = compare(paths[(condition, left)], paths[(condition, right)], kind)
                    self.assertTrue(paired["passed"], paired)
                    if kind == "repair": self.assertEqual(paired["first_lower_state_divergence_step"] is not None, condition != "none")
            self.assertTrue(compare(paths[("none", "baseline")], paths[("post_release_shift", "baseline")], "control")["passed"])
            path = paths[("post_release_shift", "v2r")] / "events.jsonl"
            events = [json.loads(line) for line in path.read_text().splitlines()]
            step = next(e for e in events if e["event"] == "step" and e["step"] == 100)
            step["verification"]["status"] = "failed"
            path.write_text("\n".join(json.dumps(e) for e in events) + "\n")
            bad = compare(paths[("post_release_shift", "v2-old")], paths[("post_release_shift", "v2r")], "repair")
            self.assertFalse(bad["passed"])
            self.assertFalse(check_trial(paths[("post_release_shift", "v2r")], c, SOFTWARE)["passed"])

    def test_contact_labels_do_not_change_recovery_or_verifier_and_zero_action_exclusion(self):
        with tempfile.TemporaryDirectory() as temporary, patch("aether_cl.m6r_runtime.software_manifest", return_value=SOFTWARE):
            root = Path(temporary); traces = []
            for i, factory in enumerate((ContactConstrained, lambda: ContactConstrained(false_labels=True))):
                c = M6RConfig(seed=100, disturbance="post_release_shift", output=root / str(i))
                result = fixture_run(c, factory)
                events = [json.loads(line) for line in (Path(result["run_directory"]) / "events.jsonl").read_text().splitlines()]
                traces.append([{k: e[k] for k in ("action", "controller_decision", "verification", "recovery")} for e in events if e["event"] == "step"])
            self.assertEqual(traces[0], traces[1])
            c = M6RConfig(seed=111, output=root / "excluded")
            result = fixture_run(c)
            self.assertEqual(result["episodes"][0]["steps"], 0)
            self.assertTrue(check_trial(Path(result["run_directory"]), c, SOFTWARE)["passed"])

    def test_bad_config_and_native_history_fail_before_new_fresh_seed_run(self):
        for changes in ({"system": "v2"}, {"protocol": "m6"}, {"max_steps": 801}, {"episodes": 2}):
            with self.assertRaises(ValueError): M6RConfig(**changes).validate()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); events = root / "events.jsonl"
            events.write_text(json.dumps({"event": "reset", "seed": 100}) + "\n")
            self.assertEqual(sweep.verify_seed_history(root)["selected_overlap"], [])
            events.write_text(json.dumps({"event": "reset", "seed": 120}) + "\n")
            with self.assertRaisesRegex(ValueError, "already have recorded resets"): sweep.verify_seed_history(root)


class SweepTests(unittest.TestCase):
    def child(self, config, environment=None):
        self.calls.append((config.seed, config.system, config.disturbance, config.disturbance_magnitude))
        directory = config.output / "fixture"; directory.mkdir(parents=True)
        (directory / "raw.json").write_text(json.dumps({"seed": config.seed, "system": config.system}))
        return {"run_directory": str(directory)}

    def checked(self, trial, software):
        adapted = copy.deepcopy(trial)
        adapted["config"]["seed"] = 111 if trial["seed"] == 127 else trial["seed"]
        if trial["system"] in ("v2-old", "v2r"): adapted["config"]["system"] = "v2"
        result = legacy_fixtures.SweepTests.check(self, adapted, software)
        result["passed"] = np.bool_(True)  # Reproduce the native M6 parent-report bug.
        result["checks"] = {"fixture": np.bool_(True)}
        e = result["episodes"][0]; e["seed"] = trial["seed"]
        attempt = e["recovery"]["attempts"] > 0
        completed = attempt and trial["system"] == "v2r" and e["task_success_at_end"]
        if attempt and trial["system"] == "v2-old":
            e.update(task_success_at_end=False, release_success_at_end=False, support_stability_success_at_end=False,
                     retraction_success_at_end=False, controller_complete=False, recovery_task_success=False)
            e["recovery"].update(state="aborted", failure_detail="retry_lower_not_completed")
        e.update(lower_transition_step=410 if completed else None, lower_phase_timeout=attempt and trial["system"] == "v2-old",
                 recovery_release_reached=completed, recovery_release_first_action_step=411 if completed else None,
                 recovery_release_executed=completed, recovery_retraction_reached=completed,
                 recovery_retraction_first_action_step=425 if completed else None, recovery_retraction_executed=completed)
        return result

    def mocks(self, stack):
        self.calls = []
        stack.enter_context(patch.object(sweep, "software_manifest", return_value=SOFTWARE))
        stack.enter_context(patch.object(sweep, "checked_trial", side_effect=self.checked))
        stack.enter_context(patch.object(sweep, "compare", return_value={"passed": True, "first_lower_state_divergence_step": 410}))
        stack.enter_context(redirect_stdout(io.StringIO()))

    def verify_archive(self, path, root="m6r-placement"):
        with tarfile.open(path) as bundle:
            index = json.load(bundle.extractfile(root + "/archive_index.json"))
            self.assertEqual(set(bundle.getnames()), {e["path"] for e in index["files"]} | {root + "/archive_index.json"})
            self.assertEqual(len(bundle.getnames()), len(set(bundle.getnames())))
            for e in index["files"]:
                data = bundle.extractfile(e["path"]).read()
                self.assertEqual(len(data), e["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), e["sha256"])

    def test_480_distinct_slots_first24_resume_scalar_safe_report_and_460_comparisons(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            self.mocks(stack); root = Path(temporary); output, archive = root / "study", root / "final.tar.gz"
            first = sweep.run_sweep(output, archive, stop_after=24, run_fn=self.child)
            self.assertEqual(first["state"], "paused")
            self.assertTrue(sweep.check_pilot(first)["passed"])
            self.assertTrue(all(c["validated_curve_success_rate"] is None for c in first["cells"]))
            pilot = Path(first["saved_archive"]); sha = hashlib.sha256(pilot.read_bytes()).hexdigest()
            self.verify_archive(pilot)
            final = sweep.run_sweep(output, archive, resume=True, run_fn=self.child)
            self.assertEqual(final["state"], "passed")
            self.assertEqual(len(self.calls), 480); self.assertEqual(len(set(self.calls)), 480)
            self.assertEqual(final["episode_trials"][:24], first["episode_trials"])
            self.assertEqual(len(final["cells"]), 24)
            for group, count in sweep.protocol()["comparison_counts"].items(): self.assertEqual(len(final[group]), count)
            hard = final["paired_outcomes"][3]
            self.assertGreater(hard["v2r_vs_v2old"]["right_only_success"], 0)
            self.assertEqual(hard["v2r_vs_v2old"]["left_only_success"], 0)
            self.assertEqual(hashlib.sha256(pilot.read_bytes()).hexdigest(), sha)
            self.verify_archive(archive)

    def test_known16_development_is_separate_and_never_launches_fresh_seeds(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            self.mocks(stack); root = Path(temporary)
            report = sweep.run_sweep(root / "known", root / "known.tar.gz", run_fn=self.child, commission_known=True)
            self.assertEqual(report["state"], "passed")
            self.assertFalse(report["protocol"]["confirmatory"])
            self.assertTrue(sweep.check_commission(report)["passed"])
            self.assertEqual({x[0] for x in self.calls}, {100, 101})
            self.assertEqual(len(self.calls), 16)
            self.assertEqual(report["paired_outcomes"], [])
            self.verify_archive(Path(report["saved_archive"]), "m6r-commission")
            provenance = sweep.validate_commission(root / "known" / "suite.json", SOFTWARE)
            self.assertTrue(provenance["validated"])
            raw = Path(report["episode_trials"][0]["run_directory"]) / "raw.json"
            raw.write_text("tampered")
            with self.assertRaisesRegex(ValueError, "raw hashes"): sweep.validate_commission(root / "known" / "suite.json", SOFTWARE)

    def test_replay_failure_or_source_drift_nulls_effects_and_rates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trials = [{**t, **self.checked(t, SOFTWARE), "run_directory": str(root / "fixture")} for t in sweep.plan(root)]
            trials[-1]["native_sources_sha256"] = {"drift": "changed"}
            report = {"episode_trials": trials}
            with patch.object(sweep, "compare", return_value={"passed": True}): sweep.summarize(report, root)
            self.assertFalse(report["native_source_identity_consistent"])
            self.assertTrue(all(c["validated_curve_success_rate"] is None for c in report["cells"]))
            self.assertTrue(all(p["v2r_vs_v2old"]["success_rate_difference"] is None for p in report["paired_outcomes"]))

    def test_resume_checks_environment_hash_raw_bytes_and_lock(self):
        import fcntl
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            self.mocks(stack); root = Path(temporary); output, archive = root / "study", root / "final.tar.gz"
            report = sweep.run_sweep(output, archive, stop_after=1, run_fn=self.child)
            with patch.dict("os.environ", {"M6R_DRIFT": "1"}):
                with self.assertRaisesRegex(ValueError, "environment"): sweep.run_sweep(output, archive, resume=True, run_fn=self.child)
            with (output / "runner.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError, "owns"): sweep.run_sweep(output, archive, resume=True, run_fn=self.child)
            raw = Path(report["episode_trials"][0]["run_directory"]) / "raw.json"; raw.write_text("changed")
            with self.assertRaisesRegex(ValueError, "hashes"): sweep.run_sweep(output, archive, resume=True, run_fn=self.child)

    def test_strict_preregistration_and_nan_guard_and_fresh_native_entry_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad = root / "bad.json"; bad.write_text(json.dumps({**sweep.protocol(), "max_steps": 801}))
            with patch.object(sweep, "PROTOCOL_PATH", bad):
                with self.assertRaisesRegex(ValueError, "preregistration"): sweep.run_sweep(root / "absent", root / "out.tar.gz")
            self.assertFalse((root / "absent").exists())
            with self.assertRaises(ValueError): sweep.write_json(root / "nan.json", {"x": np.float64(float("nan"))})
            self.assertFalse((root / "nan.json").exists())
            with patch.object(sweep, "software_manifest", return_value=SOFTWARE):
                with self.assertRaisesRegex(ValueError, "commission-report"): sweep.run_sweep(root / "fresh", root / "fresh.tar.gz")
            self.assertFalse((root / "fresh").exists())


if __name__ == "__main__": unittest.main()
